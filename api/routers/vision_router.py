"""
视觉分析 API — 图片理解端点

支持：
- POST /vision/analyze — 单张图片分析
- POST /vision/chat — 图文对话（带上下文）
- GET /vision/models — 列出可用视觉模型
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from core.providers.vllm_factory import VLLMFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])

_vllm_provider = None


def _get_vllm():
    global _vllm_provider
    if _vllm_provider is None:
        _vllm_provider = VLLMFactory.create_from_config()
    return _vllm_provider


def reload_vllm_provider():
    global _vllm_provider
    _vllm_provider = None


@router.post("/analyze")
async def analyze_image(
    image: UploadFile = File(...),
    prompt: str = Form(default="请详细描述这张图片的内容"),
):
    """分析单张图片

    支持 JPEG、PNG、WebP、GIF 格式
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        image_bytes = await image.read()
        if len(image_bytes) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片大小不能超过 20MB")

        provider = _get_vllm()
        result = await provider.analyze_image(
            image_bytes,
            prompt=prompt,
            mime_type=image.content_type,
        )
        return {
            "ok": True,
            "result": result,
            "model": provider.config.get("model_name", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("图片分析失败")
        raise HTTPException(status_code=500, detail=f"图片分析失败: {str(e)}")


class ChatWithImageRequest(BaseModel):
    prompt: str = "请分析这张图片"
    history: list = []  # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]


@router.post("/chat")
async def chat_with_image(
    image: UploadFile = File(...),
    prompt: str = Form(default="请分析这张图片"),
    history_json: str = Form(default="[]"),
):
    """图文对话（带上下文历史）"""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        import json
        history = json.loads(history_json) if history_json else []
    except json.JSONDecodeError:
        history = []

    try:
        image_bytes = await image.read()
        if len(image_bytes) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片大小不能超过 20MB")

        provider = _get_vllm()
        # 构建带上下文的 prompt
        full_prompt = prompt
        if history:
            context_lines = []
            for msg in history[-6:]:  # 最近 3 轮
                role = "用户" if msg.get("role") == "user" else "助手"
                context_lines.append(f"{role}: {msg.get('content', '')}")
            full_prompt = "对话历史：\n" + "\n".join(context_lines) + f"\n\n当前问题：{prompt}"

        result = await provider.analyze_image(
            image_bytes,
            prompt=full_prompt,
            mime_type=image.content_type,
        )
        return {
            "ok": True,
            "result": result,
            "model": provider.config.get("model_name", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("图文对话失败")
        raise HTTPException(status_code=500, detail=f"图文对话失败: {str(e)}")


@router.get("/models")
async def list_vision_models():
    """列出所有可用的视觉模型预设"""
    presets = VLLMFactory.list_presets()
    return {"ok": True, "models": presets}


@router.get("/status")
async def vision_status():
    """视觉模块状态"""
    provider = _get_vllm()
    return {
        "ok": True,
        "provider": provider.get_status(),
        "model": provider.config.get("model_name", ""),
    }
