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
