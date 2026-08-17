# -*- coding: utf-8 -*-
"""
SiliconFlow（硅基流动）Embedding API 封装（2026-08-17 新增）

背景：本地 SentenceTransformer 模型（MiniLM）在 zxf 环境存在 DLL 符号冲突
（pyarrow/torch，EXIT=139），且中文语义召回噪声大。改为调用硅基流动
Embedding API（BGE-M3 1024 维），消除本地依赖、中文效果更好。

接口设计：encode() 与 sentence_transformers.SentenceTransformer 对齐——
  - encode(texts, normalize_embeddings=True) -> List[List[float]]
  这样 XuefengStore / vector_store 等调用方无需改动调用方式，
  只需把 embedder 实例替换为本类即可（依赖注入式切换）。

配置：
  SILICONFLOW_API_KEY  必填（.env / 环境变量）
  SILICONFLOW_EMBEDDING_MODEL  可选，默认 BAAI/bge-m3（1024 维）

说明：SiliconFlow 的 embedding 返回本身已归一化（默认 normalize=True），
这里 normalize_embeddings 参数保留以对齐 SentenceTransformer 语义。
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-m3"
EMBEDDING_ENDPOINT = "https://api.siliconflow.cn/v1/embeddings"
BATCH_SIZE = 16          # 单请求最大条数（SiliconFlow 限制 32，留余量）
CACHE_MAX = 4096         # 文本→向量缓存上限（防重复调用同一句）


class SiliconFlowEmbedder:
    """硅基流动 Embedding API 客户端，encode 接口兼容 SentenceTransformer。"""

    def __init__(self, api_key: Optional[str] = None,
                 model: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("SILICONFLOW_API_KEY", "")
        self._model = model or os.getenv("SILICONFLOW_EMBEDDING_MODEL", DEFAULT_MODEL)
        self._cache: dict[str, List[float]] = {}
        if not self._api_key:
            raise ValueError(
                "SILICONFLOW_API_KEY 未配置：请在 .env 或环境变量中设置"
            )

    @property
    def model_name(self) -> str:
        """对外暴露当前模型名（供维度校验/统计展示）。"""
        return self._model

    def encode(self, texts: List[str], normalize_embeddings: bool = True,
               batch_size: int = BATCH_SIZE) -> List[List[float]]:
        """批量编码文本为向量（自动分批 + 缓存去重）。

        参数与 SentenceTransformer.encode 对齐（batch_size 兼容，
        normalize_embeddings 为保留参数——API 返回已归一化）。
        """
        if not texts:
            return []
        # 命中缓存
        uncached = [t for t in texts if t not in self._cache]
        if uncached:
            for i in range(0, len(uncached), batch_size):
                chunk = uncached[i:i + batch_size]
                vectors = self._call_api(chunk)
                for t, v in zip(chunk, vectors):
                    self._cache[t] = v
            # 缓存超限时清理（简单 FIFO 丢弃一半）
            if len(self._cache) > CACHE_MAX:
                drop = CACHE_MAX // 2
                for k in list(self._cache)[:drop]:
                    self._cache.pop(k, None)
        return [self._cache[t] for t in texts]

    def _call_api(self, texts: List[str]) -> List[List[float]]:
        """调用硅基 /v1/embeddings，失败抛异常（调用方决定降级策略）。"""
        resp = httpx.post(
            EMBEDDING_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self._model, "input": texts},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        # 按 index 排序保证与输入顺序一致
        items.sort(key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in items]


def get_siliconflow_embedder() -> SiliconFlowEmbedder:
    """工厂：便捷获取实例（key 缺失时抛错，由调用方降级本地模型）。"""
    return SiliconFlowEmbedder()
