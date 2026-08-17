# -*- coding: utf-8 -*-
"""
环境就绪性自检（冒烟测试）— 给 AI / 新接手者的第一道验证

用途：30 秒内验证各子系统是否就绪，输出状态矩阵。
设计原则：
  - 不调用外部 API（LLM / 硅基 embedding / 网络）——全 mock，保证可离线跑
  - 不启动 Docker / Milvus / Redis / Neo4j——只检查配置与导入
  - ⚠️ 状态不代表系统坏了：⚠️ = 该子系统依赖外部服务/数据文件，
    缺了不影响代码阅读与其他子系统

用法：
  python scripts/smoke_test.py            # 跑全部检查
  python scripts/smoke_test.py --quick    # 只检查导入 + 配置（更快）
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 独立脚本运行：加载 .env（与 api/main.py 行为一致）
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

PASS = "✅"
WARN = "⚠️"
FAIL = "❌"


def check_import(name: str) -> bool:
    """尝试导入模块，返回是否成功。"""
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def check_config(provider: str) -> bool:
    """解析 embedding 配置是否正常。"""
    try:
        from tools.embedding_config import (
            resolve_embedding_model,
            resolve_embedding_provider,
        )
        return resolve_embedding_provider() == provider and bool(resolve_embedding_model())
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="环境就绪性自检")
    parser.add_argument("--quick", action="store_true", help="只检查导入与配置")
    args = parser.parse_args()

    print("=" * 58)
    print("小乐AI · 环境就绪性自检")
    print("=" * 58)

    # ── 1. 核心依赖导入 ──────────────────────────────────────
    print("\n[1] 核心依赖导入")
    deps = {
        "langgraph": "langgraph",
        "fastapi": "fastapi",
        "chromadb": "chromadb",
        "pymilvus": "pymilvus",
        "httpx": "httpx",
        "yaml": "yaml",
    }
    for label, mod in deps.items():
        ok = check_import(mod)
        print(f"  {PASS if ok else FAIL} {label}")

    # ── 2. 核心模块导入 ──────────────────────────────────────
    print("\n[2] 核心模块导入")
    core_mods = [
        "core.agent_bus",
        "core.reflexion_agent",
        "core.result_fusion",
        "core.graph_builder",
        "core.state_schema",
        "tools.rag_tools",
        "tools.vector_store",
        "tools.xuefeng_store",
        "tools.siliconflow_embedder",
        "tools.embedding_config",
    ]
    for m in core_mods:
        ok = check_import(m)
        print(f"  {PASS if ok else FAIL} {m}")

    # ── 3. Embedding 配置（单一真源） ────────────────────────
    print("\n[3] Embedding 配置")
    try:
        from tools.embedding_config import (
            describe_model,
            resolve_embedding_model,
            resolve_embedding_provider,
        )
        provider = resolve_embedding_provider()
        model = resolve_embedding_model()
        key_ok = bool(os.getenv("SILICONFLOW_API_KEY"))
        print(f"  {PASS} provider = {provider}")
        print(f"  {PASS} model = {describe_model(model)}")
        if provider == "siliconflow":
            print(f"  {PASS if key_ok else WARN} SILICONFLOW_API_KEY {'已配置' if key_ok else '未配置（embedding 实际调用会降级/失败）'}")
        if args.quick:
            print("\n（--quick 模式跳过数据与测试检查）")
            print("=" * 58)
            return 0
    except Exception as e:
        print(f"  {FAIL} embedding 配置解析失败: {e}")

    # ── 4. 数据真相源（可重建，缺了不算坏） ──────────────────
    print("\n[4] 数据真相源（JSON，可从 data/documents 重建）")
    for name, path in [
        ("主 RAG 语料", ROOT / "data" / "vector_store" / "zx_experience.json"),
        ("雪峰语料", ROOT / "data" / "vector_store" / "xuefeng_corpus.json"),
    ]:
        if path.exists():
            try:
                n = len(json.loads(path.read_text(encoding="utf-8")))
                print(f"  {PASS} {name}: {n} 条")
            except Exception:
                print(f"  {FAIL} {name}: 文件存在但解析失败")
        else:
            print(f"  {WARN} {name}: 缺失（跑 build_rag_index.py / build_xuefeng_corpus.py 重建）")

    # ── 5. 关键测试可运行性 ──────────────────────────────────
    print("\n[5] 测试文件存在性")
    for t in [
        "tests/test_agent_bus.py",
        "tests/test_reflexion_agent.py",
        "tests/test_write_agent_xuefeng.py",
        "tests/test_rag_kb_scope.py",
    ]:
        p = ROOT / t
        print(f"  {PASS if p.exists() else WARN} {t}")

    print("\n" + "=" * 58)
    print("自检完成。⚠️ 表示依赖外部服务/数据文件，不影响代码理解。")
    print("下一步：看 AGENTS.md（认知引导）→ docs/ARCHITECTURE.md（架构真相源）")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
