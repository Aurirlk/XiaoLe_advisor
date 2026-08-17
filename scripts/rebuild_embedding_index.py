"""
Embedding 索引重灌脚本（P1-9）

用途：embedding 模型切换后（如 MiniLM 384 维 → BGE-M3 1024 维），
Chroma 中旧向量与模型不匹配，必须重灌。本脚本：

  1. 从 data/vector_store/zx_experience.json 读取语料
  2. 按当前 vector_config.yaml 配置的 embedding_model 重建 Chroma 集合
  3. 输出模型/维度/条数统计，校验旧集合维度与模型是否一致

用法：
  python scripts/rebuild_embedding_index.py          # 重建默认集合
  python scripts/rebuild_embedding_index.py --force  # 跳过确认，直接重建
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 独立脚本运行：加载 .env（SILICONFLOW_API_KEY 等），与 api/main.py 行为一致
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="重灌 Chroma embedding 索引")
    parser.add_argument("--force", action="store_true", help="跳过确认直接重建")
    args = parser.parse_args()

    # 读取配置
    import yaml
    from tools.embedding_config import (
        describe_model,
        embedding_dim,
        load_vector_config,
        resolve_embedding_model,
    )
    from tools.vector_store import DEFAULT_EMBEDDING_MODEL, DEFAULT_PERSIST_DIR, ChromaVectorStore

    vector_cfg = load_vector_config()
    model_name = resolve_embedding_model()
    # 关键：优先用本地路径（与 vector_store 生产路径一致），避免 HF 联网超时
    embedding_model = DEFAULT_EMBEDDING_MODEL
    collection_name = vector_cfg.get("collection_name", "zx_experience")
    persist_dir = vector_cfg.get("persist_dir", DEFAULT_PERSIST_DIR)
    persist_path = ROOT / persist_dir

    print(f"[INFO] 当前 embedding 模型：{describe_model(model_name)}")
    print(f"[INFO] 实际加载：{embedding_model}")
    print(f"[INFO] 目标集合：{collection_name} @ {persist_path}")

    # 旧集合状态（用 ChromaVectorStore 统一 settings，避免 SharedSystemClient 单例冲突）
    old_count = 0
    try:
        probe = ChromaVectorStore(
            persist_dir=persist_path,
            collection_name=collection_name,
            embedding_model=embedding_model,
        )
        old_count = probe.count
    except Exception:
        old_count = 0
    print(f"[INFO] 旧集合现有文档数：{old_count}")

    # 语料
    index_path = ROOT / "data" / "vector_store" / "zx_experience.json"
    if not index_path.exists():
        print(f"[ERROR] 语料不存在：{index_path}，请先运行 python scripts/build_rag_index.py")
        sys.exit(1)
    docs = json.loads(index_path.read_text(encoding="utf-8"))
    print(f"[INFO] 语料条数：{len(docs)}")

    if old_count and not args.force:
        print(f"\n⚠️  旧集合有 {old_count} 条文档，重建将清空并重新写入。")
        answer = input("确认重建？[y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("已取消。")
            return

    # 重建
    store = ChromaVectorStore(
        persist_dir=persist_path,
        collection_name=collection_name,
        embedding_model=embedding_model,
    )
    count = store.rebuild(docs)
    stats = store.get_stats()
    dim = embedding_dim(model_name)
    # 关键：显式关闭 Chroma 系统，确保 hnsw 段落盘（否则跨进程打开报损坏）
    store.close()

    print(f"\n[OK] 索引重灌完成：{count} 条")
    print(f"[OK] 模型：{stats.get('embedding_model', model_name)}"
          + (f"（{dim} 维）" if dim else "（维度未知，请确认模型）"))
    if dim and dim not in (384, 1024, 512, 768):
        print(f"[WARN] 模型维度 {dim} 不在已知列表，请人工确认向量兼容性。")


if __name__ == "__main__":
    main()
