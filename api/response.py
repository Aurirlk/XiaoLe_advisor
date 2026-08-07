"""统一响应封装（自 backend/app/utils/response 迁移，P1-20）"""
from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "success") -> JSONResponse:
    return JSONResponse({"code": 0, "data": data, "message": message})


def fail(message: str = "error", code: int = 1) -> JSONResponse:
    return JSONResponse({"code": code, "data": None, "message": message})
