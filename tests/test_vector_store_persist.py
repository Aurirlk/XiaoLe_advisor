"""
vector_store 持久化回归测试（P1-7 环境缺陷修复）

背景：chromadb 1.5.9 + Windows 有两个环境级坑：
  1. 绝对路径（D:\\...）打开 hnsw 段报 "Error loading hnsw index"，项目根相对路径正常
  2. 非默认 settings（如 anonymized_telemetry=False）触发 SharedSystemClient
     identifier 冲突，同样导致 hnsw 加载失败

修复后要求：
  - persist_dir 统一规范化为项目根相对路径
  - 默认 settings 创建 client
  - 写入后可跨进程/同进程查询
本测试验证这些约束不回归。
"""
from __future__ import annotations

from pathlib import Path

from tools.vector_store import ChromaVectorStore, DEFAULT_PERSIST_DIR


def test_normalize_persist_dir_relative():
    """绝对路径被规范化为项目根相对路径"""
    rel = ChromaVectorStore._normalize_persist_dir(DEFAULT_PERSIST_DIR)
    assert rel == "data/chroma_db"
    assert "\\" not in rel  # 禁止反斜杠（Windows hnsw bug）


def test_normalize_persist_dir_explicit(tmp_path):
    """显式传入相对路径保持原样"""
    assert ChromaVectorStore._normalize_persist_dir("data/other_db") == "data/other_db"


def test_normalize_persist_dir_absolute_outside(tmp_path):
    """项目外绝对路径退回绝对形式（不报错）"""
    p = ChromaVectorStore._normalize_persist_dir(tmp_path / "outside")
    assert Path(p).is_absolute()


def test_vector_store_write_then_read(tmp_path):
    """写入后同库可读回（持久化回归）"""
    persist = tmp_path / "chroma_regress"
    store = ChromaVectorStore(
        persist_dir=str(persist),
        collection_name="zx_regress",
        embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
    )
    n = store.add_documents([
        {"source": "回归测试", "text": "临床医学就业前景好"},
        {"source": "回归测试2", "text": "计算机专业薪资高"},
    ])
    assert n == 2
    assert store.count == 2
    # 同进程查询（不依赖 embedding 质量，只验证链路通）
    results = store.query("临床医学", top_k=2)
    assert isinstance(results, list)
    assert len(results) >= 1
    store.close()


def test_collection_has_data_no_crash(tmp_path):
    """collection_has_data 不因 hnsw 缺陷抛异常"""
    # 空目录 → False
    empty = tmp_path / "empty_db"
    empty.mkdir()
    assert ChromaVectorStore.collection_has_data(persist_dir=str(empty), collection_name="zx") is False
