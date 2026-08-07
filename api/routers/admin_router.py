from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from core.data_importer.pipeline import ImportReport, get_data_stats, import_file, rollback_batch
from scripts.init_sqlite import DB_PATH, init_sqlite

router = APIRouter(prefix="/admin", tags=["admin"])


class ImportResponse(BaseModel):
    ok: bool
    kind: str
    batch_id: Optional[int] = None
    records_imported: int = 0
    records_updated: int = 0
    message: str = ""
    errors: List[str] = []


class BatchItem(BaseModel):
    id: int
    source_file: str
    source_type: str
    record_count: int
    status: str
    imported_at: str


class RollbackResponse(BaseModel):
    ok: bool
    batch_id: int
    deleted_rows: int


class KnowledgeItem(BaseModel):
    id: int
    source: str
    text: str
    created_at: str = ""


class KnowledgeUploadRequest(BaseModel):
    source: str
    text: str


class KnowledgeSyncRequest(BaseModel):
    api_type: str  # college_info, college_line, major_line, province_cutoff
    params: dict = {}


def _verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="管理员 API Key 未配置")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="无效的管理员 API Key")


def _connect() -> sqlite3.Connection:
    init_sqlite(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _report_to_response(report: ImportReport) -> ImportResponse:
    return ImportResponse(
        ok=report.ok,
        kind=report.kind,
        batch_id=report.batch_id,
        records_imported=report.records_imported,
        records_updated=report.records_updated,
        message=report.message,
        errors=report.errors,
    )


@router.post("/import", response_model=ImportResponse)
async def admin_import(
    file: UploadFile = File(...),
    dry_run: bool = Query(False),
    source: str = Query("", description="默认 data_source"),
    _: None = Depends(_verify_admin_key),
):
    suffix = Path(file.filename or "upload.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    conn = _connect()
    try:
        report = import_file(tmp_path, conn, dry_run=dry_run, default_source=source)
        return _report_to_response(report)
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


@router.post("/import/upload")
async def admin_import_upload(
    file: UploadFile = File(...),
    kind: str = Query("", description="数据类型: universities/admission_scores/majors"),
    source: str = Query("", description="数据来源标识"),
    dry_run: bool = Query(False, description="仅校验不写入"),
    _: None = Depends(_verify_admin_key),
):
    """向导式文件上传导入，返回预览和校验结果"""
    suffix = Path(file.filename or "upload.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    conn = _connect()
    try:
        from core.data_importer.pipeline import load_rows, detect_kind, validate_rows

        rows = load_rows(tmp_path)
        if not rows:
            return {"ok": False, "message": "文件为空或格式错误", "errors": [], "preview": [], "records": 0}

        detected_kind = kind if kind in ("universities", "admission_scores", "majors") else detect_kind(tmp_path, rows)

        # 校验
        errors = validate_rows(detected_kind, rows)

        # 预览前 5 行
        preview = rows[:5]

        if dry_run:
            return {
                "ok": len(errors) == 0,
                "kind": detected_kind,
                "message": f"校验完成: {len(rows)} 条记录, {len(errors)} 个错误",
                "errors": errors[:20],
                "preview": preview,
                "records": len(rows),
            }

        # 正式导入
        report = import_file(tmp_path, conn, dry_run=False, default_source=source)
        return {
            **_report_to_response(report).model_dump(),
            "preview": preview,
            "records": len(rows),
        }
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


@router.get("/import/batches", response_model=List[BatchItem])
async def list_batches(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: None = Depends(_verify_admin_key),
):
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, source_file, source_type, record_count, status, imported_at
            FROM data_import_batches
            ORDER BY imported_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [
            BatchItem(
                id=r[0],
                source_file=r[1],
                source_type=r[2],
                record_count=r[3],
                status=r[4],
                imported_at=r[5],
            )
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/data/stats")
async def data_stats(_: None = Depends(_verify_admin_key)):
    conn = _connect()
    try:
        return {"ok": True, **get_data_stats(conn)}
    finally:
        conn.close()


@router.delete("/import/batches/{batch_id}", response_model=RollbackResponse)
async def rollback_import_batch(
    batch_id: int,
    _: None = Depends(_verify_admin_key),
):
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id FROM data_import_batches WHERE id = ?",
            (batch_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="批次不存在")
        deleted = rollback_batch(conn, batch_id)
        conn.commit()
        return RollbackResponse(ok=True, batch_id=batch_id, deleted_rows=deleted)
    finally:
        conn.close()


@router.get("/knowledge/list")
async def list_knowledge(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: None = Depends(_verify_admin_key),
):
    """列出知识库内容"""
    try:
        index_path = Path(__file__).resolve().parents[2] / "data" / "vector_store" / "zx_experience.json"
        if not index_path.exists():
            return {"ok": True, "items": [], "total": 0}

        import json
        docs = json.loads(index_path.read_text(encoding="utf-8"))
        total = len(docs)
        items = docs[offset:offset + limit]
        return {"ok": True, "items": items, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库失败: {str(e)}")


@router.post("/knowledge/upload")
async def upload_knowledge(
    req: KnowledgeUploadRequest,
    _: None = Depends(_verify_admin_key),
):
    """上传知识到知识库"""
    try:
        index_path = Path(__file__).resolve().parents[2] / "data" / "vector_store" / "zx_experience.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)

        import json
        if index_path.exists():
            docs = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            docs = []

        new_item = {"source": req.source, "text": req.text}
        docs.append(new_item)

        index_path.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")

        # 同步到向量库
        try:
            from tools.vector_store import ChromaVectorStore
            store = ChromaVectorStore()
            store.add_documents([new_item])
        except Exception:
            pass

        return {"ok": True, "message": "知识上传成功", "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.delete("/knowledge/{item_index}")
async def delete_knowledge(
    item_index: int,
    _: None = Depends(_verify_admin_key),
):
    """删除知识条目"""
    try:
        index_path = Path(__file__).resolve().parents[2] / "data" / "vector_store" / "zx_experience.json"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="知识库不存在")

        import json
        docs = json.loads(index_path.read_text(encoding="utf-8"))

        if item_index < 0 or item_index >= len(docs):
            raise HTTPException(status_code=404, detail="索引超出范围")

        deleted_item = docs.pop(item_index)
        index_path.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")

        return {"ok": True, "message": "删除成功", "deleted": deleted_item}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/knowledge/sync-api")
async def sync_knowledge_from_api(
    req: KnowledgeSyncRequest,
    _: None = Depends(_verify_admin_key),
):
    """从咕咕数据API同步知识"""
    try:
        from core.providers.gugu_api_client import gugu_client

        if req.api_type == "college_info":
            result = await gugu_client.query_college_info(req.params.get("college_name", ""))
        elif req.api_type == "college_line":
            result = await gugu_client.query_college_line(
                req.params.get("college_name", ""),
                req.params.get("province", ""),
                req.params.get("year", 2025),
                req.params.get("subject_type", "物理类"),
            )
        elif req.api_type == "major_line":
            result = await gugu_client.query_major_line(
                req.params.get("major_name", ""),
                req.params.get("province", ""),
                req.params.get("year", 2025),
                req.params.get("subject_type", "物理类"),
            )
        elif req.api_type == "province_cutoff":
            result = await gugu_client.query_province_cutoff(
                req.params.get("province", ""),
                req.params.get("year", 2025),
                req.params.get("subject_type", "物理类"),
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的API类型: {req.api_type}")

        return {"ok": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API同步失败: {str(e)}")


@router.post("/restart-service/{service_key}")
async def restart_service(
    service_key: str,
    _: None = Depends(_verify_admin_key),
):
    """重启指定服务（Neo4j / Redis / Vector 等）"""
    try:
        if service_key == "neo4j":
            from core.kg_client import kg_client
            try:
                kg_client.close()
            except Exception:
                pass
            # 测试重新连接
            connected = kg_client.test_connection()
            return {
                "ok": connected,
                "message": "Neo4j 重连成功" if connected else "Neo4j 重连失败，请检查数据库是否运行",
            }
        elif service_key == "rag":
            # 重建 RAG 索引
            from scripts.build_rag_index import main as build_rag_index
            build_rag_index()
            return {"ok": True, "message": "RAG 索引重建完成"}
        else:
            raise HTTPException(status_code=400, detail=f"不支持重启的服务: {service_key}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启失败: {str(e)}")


@router.get("/service-health")
async def service_health():
    """获取所有服务健康状态（无需管理员密钥，供前端监控使用）"""
    from api.main import MODULE_STATUS
    
    # 检查 Neo4j
    neo4j_ok = False
    neo4j_info = {}
    try:
        from core.kg_client import kg_client
        neo4j_ok = kg_client.test_connection()
        if neo4j_ok:
            stats = kg_client.get_stats()
            neo4j_info = {"nodes": stats.get("total_nodes", 0), "edges": stats.get("total_edges", 0)}
    except Exception as e:
        neo4j_info = {"error": str(e)}
    
    return {
        "ok": True,
        "neo4j": {"connected": neo4j_ok, **neo4j_info},
        "modules": MODULE_STATUS,
    }
