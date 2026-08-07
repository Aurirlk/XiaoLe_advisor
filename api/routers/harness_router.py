"""
Harness API - 数据上传与知识注入端点

支持用户上传文件（图片/CSV/Excel/PDF），自动解析并入库
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.security_utils import (
    ALLOWED_DOC_TYPES,
    ALLOWED_IMAGE_TYPES,
    MAX_DOC_BYTES,
    MAX_IMAGE_BYTES,
    RateLimiter,
    check_content_type,
    read_limited,
    require_user,
    validate_image_bytes,
)
from core.harness import harness

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/harness", tags=["harness"])

_upload_limit = RateLimiter("harness_upload", limit=20, window=60)


class UploadResponse(BaseModel):
    ok: bool
    message: str
    parsed_count: int = 0
    saved: bool = False
    save_message: str = ""


class ScenarioResponse(BaseModel):
    scenario: Optional[str] = None
    prompt: Optional[str] = None
    accept_types: list = []


@router.get("/scenarios")
async def list_scenarios():
    """列出所有数据缺失场景"""
    scenarios = []
    for key, config in harness.MISSING_DATA_SCENARIOS.items():
        scenarios.append({
            "id": key,
            "trigger": config["trigger"],
            "prompt": config["prompt"],
            "accept_types": config["accept_types"],
        })
    return {"scenarios": scenarios}


@router.post("/detect")
async def detect_missing_data(
    query: str = Form(...),
    tool_result: str = Form(default=""),
):
    """检测用户查询是否涉及缺失数据"""
    scenario = harness.detect_missing_data(query, tool_result)
    if scenario:
        return ScenarioResponse(
            scenario=scenario.get("parse_strategy"),
            prompt=harness.generate_upload_prompt(scenario),
            accept_types=scenario.get("accept_types", []),
        )
    return ScenarioResponse()


@router.post("/upload", response_model=UploadResponse, dependencies=[Depends(_upload_limit)])
async def upload_data(
    file: UploadFile = File(...),
    scenario: str = Form(default="generic"),
    province: str = Form(default=""),
    year: int = Form(default=2025),
    subject_type: str = Form(default=""),
    user: dict = Depends(require_user),
):
    """
    上传数据文件

    - 支持格式：图片(JPEG/PNG/WebP)、CSV、Excel、PDF
    - 自动解析并入库
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择文件")

    check_content_type(file, ALLOWED_DOC_TYPES, "文件")
    content = await read_limited(file, MAX_DOC_BYTES)
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if (file.content_type or "").lower().startswith("image/"):
        validate_image_bytes(content)

    # 获取场景配置
    scenario_config = harness.MISSING_DATA_SCENARIOS.get(scenario, {
        "parse_strategy": scenario,
        "accept_types": ["image", "csv", "pdf"],
    })

    # 解析文件
    success, message, parsed_data = harness.parse_uploaded_file(
        content, file.filename, file.content_type, scenario_config
    )

    if not success:
        return UploadResponse(ok=False, message=message)

    # 图片需要调用视觉模型
    if parsed_data and parsed_data[0].get("type") == "image":
        return UploadResponse(
            ok=True,
            message="图片已接收，正在调用视觉模型解析...",
            parsed_count=1,
            saved=False,
            save_message="vision_pending",
        )

    # 保存到数据库
    metadata = {
        "province": province,
        "year": year,
        "subject_type": subject_type,
    }

    saved, save_message = harness.save_to_database(parsed_data, scenario, metadata)

    return UploadResponse(
        ok=True,
        message=f"文件解析成功，共{len(parsed_data)}条数据",
        parsed_count=len(parsed_data),
        saved=saved,
        save_message=save_message,
    )


@router.post("/upload-and-analyze", dependencies=[Depends(_upload_limit)])
async def upload_and_analyze(
    file: UploadFile = File(...),
    prompt: str = Form(default="请分析这张图片中的数据"),
    province: str = Form(default=""),
    year: int = Form(default=2025),
    subject_type: str = Form(default=""),
    user: dict = Depends(require_user),
):
    """
    上传图片并调用视觉模型分析

    用于需要视觉识别的场景（成绩单、招生简章截图等）
    """
    check_content_type(file, ALLOWED_IMAGE_TYPES, "图片")
    content = await read_limited(file, MAX_IMAGE_BYTES)
    validate_image_bytes(content)

    try:
        from core.providers.vllm_factory import VLLMFactory
        provider = VLLMFactory.create_from_config()

        # 调用视觉模型
        analysis_prompt = f"""请分析这张图片中的高考相关数据。

要求：
1. 识别图片中的所有数字数据（分数、位次、人数等）
2. 识别院校名称、专业名称
3. 识别省份、年份信息
4. 以JSON格式返回结构化数据

用户提示：{prompt}

请返回JSON格式：
{{
  "province": "省份",
  "year": 年份,
  "data_type": "admission_score/score_segment/batch_cutoff/admission_plan",
  "entries": [
    {{"university": "院校名", "major": "专业名", "score": 分数, "rank": 位次}}
  ]
}}"""

        result = await provider.analyze_image(
            content,
            prompt=analysis_prompt,
            mime_type=file.content_type,
        )

        # 尝试解析视觉模型返回的JSON
        try:
            import json
            # 提取JSON部分
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(result[json_start:json_end])

                # 保存到数据库
                data_type = parsed.get("data_type", "generic")
                entries = parsed.get("entries", [])
                metadata = {
                    "province": parsed.get("province", province),
                    "year": parsed.get("year", year),
                    "subject_type": subject_type,
                }

                if entries:
                    saved, save_message = harness.save_to_database(entries, data_type, metadata)
                    return {
                        "ok": True,
                        "analysis": result,
                        "parsed_data": parsed,
                        "saved": saved,
                        "save_message": save_message,
                    }
        except json.JSONDecodeError:
            pass

        # JSON解析失败，返回原始分析结果
        return {
            "ok": True,
            "analysis": result,
            "parsed_data": None,
            "saved": False,
            "save_message": "视觉分析完成，但无法自动解析为结构化数据",
        }

    except Exception as e:
        logger.exception("视觉分析失败")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/stats")
async def get_harness_stats():
    """获取 Harness 数据统计"""
    import sqlite3

    stats = {}
    try:
        conn = sqlite3.connect(harness.sqlite_db)
        cursor = conn.cursor()

        # 一分一段数据
        try:
            cursor.execute("SELECT COUNT(*) FROM score_segments")
            stats["score_segments"] = cursor.fetchone()[0]
        except:
            stats["score_segments"] = 0

        # 批次线数据
        try:
            cursor.execute("SELECT COUNT(*) FROM province_cutoffs")
            stats["province_cutoffs"] = cursor.fetchone()[0]
        except:
            stats["province_cutoffs"] = 0

        # 录取数据
        cursor.execute("SELECT COUNT(*) FROM admission_scores")
        stats["admission_scores"] = cursor.fetchone()[0]

        # 院校数据
        cursor.execute("SELECT COUNT(*) FROM universities")
        stats["universities"] = cursor.fetchone()[0]

        conn.close()
    except Exception as e:
        stats["error"] = str(e)

    return stats
