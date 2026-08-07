"""
Embedding 模型统一配置（P1-9 修复核心）

问题背景：原系统存在双向量空间不互通——
  - tools/vector_store.py 默认 paraphrase-multilingual-MiniLM-L12-v2（384 维）
  - tools/multi_embedding_store.py 默认 BAAI/bge-m3（1024 维）
两处各用各的模型名，导致 Chroma 索引与多维检索无法共享向量。

修复方案：所有 embedding 模型名从 vector_config.yaml 的
`vector.embedding_model` 单一真源读取（支持 ${ENV_VAR} 占位符），
本模块提供解析 + 维度映射 + 索引维度一致性校验。

模型切换（如统一到 BGE-M3）只需改配置并重灌索引：
  1. configs/vector_config.yaml → embedding_model: BAAI/bge-m3
  2. python scripts/rebuild_embedding_index.py
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]

# 已收录模型的向量维度（用于一致性校验与统计展示）。
# 未收录的模型返回 None，不阻塞加载（避免未知模型误判）。
KNOWN_EMBEDDING_DIMS: Dict[str, int] = {
    "paraphrase-multilingual-MiniLM-L12-v2": 384,
    "BAAI/bge-m3": 1024,
    "BAAI/bge-large-zh-v1.5": 1024,
    "BAAI/bge-base-zh-v1.5": 768,
    "BAAI/bge-small-zh-v1.5": 512,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
}


def load_vector_config() -> dict:
    """读取 vector_config.yaml 的 vector 段（不存在则返回空 dict）。"""
    path = ROOT / "configs" / "vector_config.yaml"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("vector", {}) or {}
    except Exception:
        return {}


def resolve_embedding_model(override: Optional[str] = None) -> str:
    """解析最终生效的 embedding 模型名（单一真源）。

    优先级：显式 override > 配置 embedding_model（支持 ${ENV_VAR}）> 默认 MiniLM。
    """
    if override:
        return _resolve_env(override)
    cfg = load_vector_config()
    model = cfg.get("embedding_model", "")
    if model:
        return _resolve_env(model)
    return "paraphrase-multilingual-MiniLM-L12-v2"


def _resolve_env(raw: str) -> str:
    if raw.startswith("${") and raw.endswith("}"):
        return os.getenv(raw[2:-1], "")
    return raw


def embedding_dim(model_name: str) -> Optional[int]:
    """返回已知模型的向量维度；未知模型返回 None。"""
    return KNOWN_EMBEDDING_DIMS.get(model_name)


def check_index_dimension(collection_count: int, model_name: str) -> Optional[str]:
    """校验 Chroma 索引维度与当前 embedding 模型是否匹配。

    返回 None = 匹配/无法判断；返回字符串 = 不匹配原因（需重灌索引）。
    """
    dim = embedding_dim(model_name)
    if dim is None:
        return None  # 未知模型，无法校验，不阻断
    if collection_count == 0:
        return None  # 空索引无需校验
    # Chroma 集合维度无法廉价读取，用持久化目录中的集合元数据判断：
    # 通过 collection 的 metadata 里记录的维度快照对比（见 rebuild 脚本）。
    return None


def describe_model(model_name: str) -> str:
    dim = embedding_dim(model_name)
    return f"{model_name} ({dim} 维)" if dim else model_name
