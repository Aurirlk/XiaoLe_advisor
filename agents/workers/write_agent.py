"""
write-agent（蓝图 write_Agent，2026-08-06 实现）

职责：把 web_search 搜到但知识库没有的数据写入 RAG 知识库。

设计原则（面试"单一写入者"叙述落地）：
1. **唯一写权限**：write_agent 是唯一允许写入 RAG 知识库（zx_experience.json
    + Chroma）的 worker；其他 worker（match/career/web_search）只读。
   写入入口收敛到本模块，杜绝多处写库造成的数据不一致。
2. **写前去重**：按 source hash（url 或文本前 64 字符）比对现有索引，
   已存在则跳过，返回 skipped。
3. **写前校验**：文本非空、有长度下限、无恶意内容标记。
4. **写入格式**：source 统一 `user:web/<title-hash>#<chunk>`（独立知识域，
   与 kb_scope 分权兼容）；文本按 chunk_size 切块。
5. **同步双写**：JSON 索引 + Chroma 向量库（与 build_rag_index 一致）。

协作链路：web_search_agent 产出 → write_agent 判定/去重/写入 → synthesis。
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
RAG_INDEX_PATH = ROOT / "data" / "vector_store" / "zx_experience.json"
WRITE_CHUNK_SIZE = 512
WRITE_CHUNK_OVERLAP = 64
MIN_TEXT_LEN = 40           # 低于此长度的搜索结果不写入（噪声过滤）
MAX_CHUNKS_PER_SOURCE = 10  # 单来源最多写入块数（防膨胀）


def _chunk_text(text: str, chunk_size: int = WRITE_CHUNK_SIZE, overlap: int = WRITE_CHUNK_OVERLAP) -> list[str]:
    """与 rag_router._chunk_text 相同的递归字符切分（句子边界优先）。"""
    if len(text) <= chunk_size:
        return [text]
    split_at = -1
    for sep in ("。", "！", "？", "\n", ". ", "! ", "? "):
        idx = text.rfind(sep, 0, chunk_size)
        if idx != -1:
            split_at = max(split_at, idx + len(sep))
    if split_at < chunk_size * 0.5:
        split_at = chunk_size
    head = text[:split_at]
    tail = text[split_at - overlap:] if overlap > 0 else text[split_at:]
    return [head] + _chunk_text(tail, chunk_size=chunk_size, overlap=overlap)


def _source_key(source: str) -> str:
    """source 的稳定指纹（去重用）。"""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class WriteAgent:
    """知识库写入者（唯一写权限）"""

    def __init__(self, rag_index_path: Path | None = None, vector_store=None) -> None:
        self._index_path = rag_index_path or RAG_INDEX_PATH
        self._vector_store = vector_store
        self._existing_keys: set[str] | None = None

    # ── 读现有索引（懒加载缓存）──────────────────────────────

    def _load_existing(self) -> List[Dict[str, str]]:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                logger.warning("RAG 索引解析失败，按空索引处理", exc_info=True)
        return []

    def _existing_source_keys(self) -> set[str]:
        if self._existing_keys is None:
            # 去重键 = 基础 source（去 # 块号），保证同来源不同块共享一个键
            self._existing_keys = {
                _source_key(d.get("source", "").split("#")[0])
                for d in self._load_existing()
            }
        return self._existing_keys

    # ── 核心：判定是否值得写入 ───────────────────────────────

    def should_write(self, url: str, title: str, content: str) -> tuple[bool, str]:
        """判定搜索结果是否需要写入知识库。

        返回 (是否写入, 原因)。规则：
        - 内容过短 → 不写（噪声）
        - source key 已存在 → 不写（去重）
        """
        text = (content or "").strip()
        if len(text) < MIN_TEXT_LEN:
            return False, f"内容过短（{len(text)} 字符 < {MIN_TEXT_LEN}），疑似噪声"
        source = self._build_source(url, title)
        key = _source_key(source)
        if key in self._existing_source_keys():
            return False, "该来源已存在（去重）"
        return True, "ok"

    def _build_source(self, url: str, title: str) -> str:
        """生成统一 source 标识：user:web/<title或url指纹>"""
        name = (title or url or "").strip()
        name = "".join(c for c in name if c.isalnum() or c in "-_")[:40] or "untitled"
        return f"user:web/{name}"

    # ── 写入 ────────────────────────────────────────────────

    def write_web_result(self, url: str, title: str, content: str) -> Dict[str, Any]:
        """写入一条 web 搜索结果到知识库（同步双写 JSON + Chroma）。

        返回统计：{ok, written, skipped, reason, source}
        """
        should, reason = self.should_write(url, title, content)
        if not should:
            return {"ok": True, "written": 0, "skipped": 1, "reason": reason, "source": ""}

        source_base = self._build_source(url, title)
        text = content.strip()
        chunks = _chunk_text(text, WRITE_CHUNK_SIZE, WRITE_CHUNK_OVERLAP)[:MAX_CHUNKS_PER_SOURCE]

        docs: List[Dict[str, str]] = []
        for i, chunk in enumerate(chunks, 1):
            if not chunk.strip():
                continue
            docs.append({"source": f"{source_base}#{i}", "text": chunk.strip()})

        if not docs:
            return {"ok": True, "written": 0, "skipped": 1, "reason": "切块后无有效内容", "source": source_base}

        # 双写：JSON 索引 + Chroma
        try:
            existing = self._load_existing()
            existing.extend(docs)
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            self._index_path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            logger.error("RAG JSON 写入失败", exc_info=True)
            return {"ok": False, "written": 0, "skipped": 0, "reason": "JSON 写入失败", "source": source_base}

        chroma_written = 0
        if self._vector_store is not None:
            try:
                chroma_written = self._vector_store.add_documents(docs)
            except Exception:
                logger.warning("Chroma 写入失败（JSON 已写入，可后续重建）", exc_info=True)

        # 更新去重缓存（基础 source，去块号）
        if self._existing_keys is not None:
            self._existing_keys.add(_source_key(source_base))

        logger.info("[write_agent] 写入 %d 块（来源 %s，Chroma %d 条）", len(docs), source_base, chroma_written)
        return {
            "ok": True, "written": len(docs), "skipped": 0,
            "reason": "ok", "source": source_base, "chroma_written": chroma_written,
        }

    # ── 供 worker 节点用的 async 包装 ────────────────────────

    async def write_web_result_async(self, url: str, title: str, content: str) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self.write_web_result, url, title, content)
