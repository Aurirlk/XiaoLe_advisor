# -*- coding: utf-8 -*-
"""
雪峰语料库 Milvus 就绪性自检脚本（2026-08-17 新增）

用途：Milvus 真实跑通的第一步验证——探测 Milvus 连接是否可用、
      明确告知当前实际后端（Milvus 或 Chroma 降级），可选重建向量索引。

用法：
    python scripts/check_xuefeng_milvus.py            # 默认模式探测
    python scripts/check_xuefeng_milvus.py --enable   # 模拟生产开启 MILVUS_ENABLED=1
    python scripts/check_xuefeng_milvus.py --enable --rebuild  # 探测 + 重灌向量索引
"""
from __future__ import annotations

import argparse
import json
import os
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

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="雪峰语料库 Milvus 就绪性自检")
    parser.add_argument("--enable", action="store_true", help="以 MILVUS_ENABLED=1 模式检测")
    parser.add_argument("--rebuild", action="store_true", help="探测成功后重建向量索引")
    args = parser.parse_args()

    if args.enable:
        os.environ["MILVUS_ENABLED"] = "1"

    from tools.xuefeng_store import CORPUS_PATH, XuefengStore

    store = XuefengStore()
    corpus_exists = CORPUS_PATH.exists()

    print("=" * 60)
    print("雪峰语料库 Milvus 就绪性自检")
    print("=" * 60)
    print(f"[1] MILVUS_ENABLED = {os.getenv('MILVUS_ENABLED', '0')}")
    print(f"[2] 语料文件       = {CORPUS_PATH.name} "
          f"{'✅ 存在' if corpus_exists else '❌ 缺失（先跑 build_xuefeng_corpus.py）'}")
    if corpus_exists:
        try:
            docs = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
            print(f"    语料条目       = {len(docs)} 条")
        except Exception as e:
            print(f"    语料解析       = ❌ {e}")

    print("-" * 60)
    milvus_client = store._get_milvus()
    if milvus_client is not None:
        cols = milvus_client.list_collections()
        names = {getattr(c, "name", c) for c in cols}
        has = "zx_xuefeng" in names
        print(f"[3] Milvus 连接   = ✅ 成功")
        print(f"    collection    = {'✅ 已存在' if has else '⚠️ 未创建（--rebuild 时自动建）'}")
        print(f"    实际后端       = ✅ Milvus（面试叙事链路）")
    else:
        print(f"[3] Milvus 连接   = ❌ 不可用")
        print(f"    实际后端       = ⚠️ Chroma 降级")
        print()
        print("    → 请先启动 Milvus：")
        print("      1. 打开 Docker Desktop")
        print("      2. docker compose up -d etcd minio milvus")
        print("      3. 等待 healthcheck 通过（约 1-2 分钟）")
        print("      4. 重跑: python scripts/check_xuefeng_milvus.py --enable")
        if args.rebuild:
            print("\n    ⚠️ Milvus 不可用，跳过 --rebuild。")
            return 1

    if args.rebuild and corpus_exists:
        print("-" * 60)
        print("[4] 重建向量索引（force 重灌）...")
        docs = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        from tools.xuefeng_store import _split_turns
        chunks = []
        for d in docs:
            source_base = d.get("source", "xuefeng").split("#")[0]
            for i, turn in enumerate(_split_turns(d.get("text", "")), 1):
                chunks.append({"source": f"{source_base}#turn{i}", "text": turn})
        if not chunks:
            print("    语料切块为空，跳过")
            return 1
        # 清空重灌：force=True 时会跳过已存在 source，所以先清 JSON 再写
        store._corpus_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        store._docs = []
        res = store.build_corpus([], force=True) if False else _reindex(store, chunks)
        print(f"    结果: {res}")
        print("    ✅ 可用 search 验证: 提问「学医周期长怎么规划」")

    print("=" * 60)
    print("自检完成")
    return 0


def _reindex(store, chunks: list) -> dict:
    """重灌向量索引：JSON 已重置为 chunks，直接走 build_corpus 的入库逻辑。

    直接调用内部双写（Milvus/Chroma）而不走 build_corpus 的去重逻辑。
    """
    from tools.xuefeng_store import _split_turns  # noqa
    texts = [c["text"] for c in chunks]
    vectors = store._embed(texts)
    dim = len(vectors[0]) if vectors else 0
    if dim == 0:
        return {"ok": False, "reason": "embedding 失败"}

    milvus_client = store._get_milvus()
    written = 0
    backend = "chroma"
    if milvus_client is not None:
        try:
            store._ensure_milvus_collection(milvus_client, dim)
            rows = [{"id": i, "source": c["source"], "text": c["text"], "vector": vectors[i]}
                    for i, c in enumerate(chunks)]
            milvus_client.delete(collection_name="zx_xuefeng", ids=[r["id"] for r in rows])  # 清旧
            milvus_client.insert(collection_name="zx_xuefeng", data=rows)
            written = len(rows)
            backend = "milvus"
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Milvus 重灌失败", exc_info=True)
    if written == 0:
        try:
            chroma = store._get_chroma()
            written = chroma.add_documents(chunks)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Chroma 重灌失败", exc_info=True)
    return {"ok": True, "written": written, "backend": backend}


if __name__ == "__main__":
    sys.exit(main())
