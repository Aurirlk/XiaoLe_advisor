from __future__ import annotations

import os
from typing import Dict, List

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from api.dependencies import get_vector_store, get_rag_tools
from tools.vector_store import ChromaVectorStore

router = APIRouter(prefix="/rag", tags=["rag"])


def _verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="管理员 API Key 未配置")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="无效的管理员 API Key")


class IngestRequest(BaseModel):
    documents: List[Dict[str, str]] = Field(
        ..., description="文档列表，每项包含 source 和 text 字段"
    )


class IngestResponse(BaseModel):
    ok: bool
    ingested_count: int
    total_count: int


class StatsResponse(BaseModel):
    collection_name: str
    document_count: int
    persist_dir: str
    embedding_model: str


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(
    payload: IngestRequest,
    store: ChromaVectorStore = Depends(get_vector_store),
    _: None = Depends(_verify_admin_key),
):
    if not payload.documents:
        raise HTTPException(status_code=400, detail="documents 不能为空")
    for doc in payload.documents:
        if "text" not in doc:
            raise HTTPException(status_code=400, detail="每条文档必须包含 text 字段")
    count = store.add_documents(payload.documents)
    return IngestResponse(
        ok=True,
        ingested_count=count,
        total_count=store.count,
    )


@router.post("/rebuild", response_model=IngestResponse)
async def rebuild_index(
    payload: IngestRequest,
    store: ChromaVectorStore = Depends(get_vector_store),
    _: None = Depends(_verify_admin_key),
):
    if not payload.documents:
        raise HTTPException(status_code=400, detail="documents 不能为空")
    count = store.rebuild(payload.documents)
    return IngestResponse(
        ok=True,
        ingested_count=count,
        total_count=store.count,
    )


@router.delete("/collection")
async def clear_collection(
    store: ChromaVectorStore = Depends(get_vector_store),
    _: None = Depends(_verify_admin_key),
):
    store.delete_collection()
    return {"ok": True, "message": "向量集合已清空并重建"}


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    store: ChromaVectorStore = Depends(get_vector_store),
):
    stats = store.get_stats()
    return StatsResponse(**stats)


@router.post("/sync-from-json")
async def sync_from_json(
    store: ChromaVectorStore = Depends(get_vector_store),
    _: None = Depends(_verify_admin_key),
):
    """从本地 zx_experience.json 同步数据到向量数据库"""
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[2]
    json_path = root / "data" / "vector_store" / "zx_experience.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="zx_experience.json 不存在，请先生成")

    docs = json.loads(json_path.read_text(encoding="utf-8"))
    count = store.rebuild(docs)
    return {"ok": True, "synced_count": count, "total_count": store.count}


@router.post("/scan-documents")
async def scan_documents(
    store: ChromaVectorStore = Depends(get_vector_store),
    _: None = Depends(_verify_admin_key),
):
    """重新扫描 data/documents/ 下所有文件（md/csv/pdf/txt），重建 RAG 索引并同步到向量库"""
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[2]

    try:
        from scripts.build_rag_index import main as build_index
        build_index()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"索引重建失败: {exc}")
    json_path = root / "data" / "vector_store" / "zx_experience.json"
    if not json_path.exists():
        raise HTTPException(status_code=500, detail="zx_experience.json 生成失败")
    docs = json.loads(json_path.read_text(encoding="utf-8"))
    count = store.rebuild(docs)
    return {"ok": True, "synced_count": count, "total_count": store.count, "index_doc_count": len(docs)}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    store: ChromaVectorStore = Depends(get_vector_store),
    _: None = Depends(_verify_admin_key),
):
    """上传单个文档文件（md/csv/pdf/txt），即时解析并加入向量库"""
    from pathlib import Path
    import io, csv

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in {".md", ".csv", ".pdf", ".txt"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}，支持 md/csv/pdf/txt")

    raw = await file.read()
    try:
        if suffix == ".pdf":
            try:
                import pdfplumber
            except ImportError:
                raise HTTPException(status_code=500, detail="pdfplumber 未安装")
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                text = "\n\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        elif suffix == ".csv":
            text_parts = []
            reader = csv.reader(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
            headers = next(reader, None)
            if headers:
                text_parts.append(" | ".join(headers))
            for row in reader:
                text_parts.append(" | ".join(row))
            text = "\n".join(text_parts)
        else:
            text = raw.decode("utf-8", errors="ignore")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {exc}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    # P1-7：按 chunk_size + overlap 递归切分（替代粗暴 split("\n\n")）。
    # 优先按段落聚合，超长段落按句子/字符切，保证 chunk 不超过 embedding 窗口。
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    docs = []
    chunk_id = 0
    for para in paragraphs[:500]:
        for chunk in _chunk_text(para, chunk_size=512, overlap=64):
            if not chunk.strip():
                continue
            chunk_id += 1
            docs.append({
                "source": f"{filename}#{chunk_id}",
                "page": 0,          # PDF 多页场景后续接入 pdfplumber 分页信息
                "chunk_id": chunk_id,
                "text": chunk,
            })
    count = store.add_documents(docs)
    return {"ok": True, "filename": filename, "ingested_count": count, "total_count": store.count}


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """递归字符切分：优先按句子边界，其次按字符边界，保留 overlap。

    对标 langchain SentenceSplitter(chunk_size=512, chunk_overlap=64)。
    """
    if len(text) <= chunk_size:
        return [text]

    # 尝试在句子边界处切分（中文句号/感叹/问号/换行），取最靠后的边界
    split_at = -1
    for sep in ("。", "！", "？", "\n", ". ", "! ", "? "):
        idx = text.rfind(sep, 0, chunk_size)
        if idx != -1:
            split_at = max(split_at, idx + len(sep))
    # 边界过前（head 不足一半）说明是罕见标点，硬切更合理
    if split_at < chunk_size * 0.5:
        split_at = chunk_size

    head = text[:split_at]
    tail = text[split_at - overlap:] if overlap > 0 else text[split_at:]
    return [head] + _chunk_text(tail, chunk_size=chunk_size, overlap=overlap)
