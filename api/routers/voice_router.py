from __future__ import annotations

import asyncio
import io
import json
import logging

from fastapi import (
    APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.security_utils import (
    ALLOWED_AUDIO_TYPES,
    MAX_AUDIO_BYTES,
    WS_IDLE_TIMEOUT,
    RateLimiter,
    authenticate_ws,
    check_content_type,
    read_limited,
    require_user,
    ws_semaphore,
)
from core.providers.asr_factory import ASRFactory
from core.providers.tts_factory import TTSFactory
from core.emotion_analyzer import get_emotion_analyzer, get_emotion_tts_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

# 高成本端点限流（可用 RATE_LIMIT_ASR / RATE_LIMIT_TTS 环境变量覆盖，0 表示关闭）
_asr_limit = RateLimiter("asr", limit=20, window=60)
_tts_limit = RateLimiter("tts", limit=60, window=60)

# TTS 单次合成文本上限，防止被拿来当免费长文本合成器
MAX_TTS_CHARS = 2000

_asr_provider = None
_tts_provider = None


def _get_asr():
    global _asr_provider
    if _asr_provider is None:
        _asr_provider = ASRFactory.create_from_config()
    return _asr_provider


def _get_tts():
    global _tts_provider
    if _tts_provider is None:
        _tts_provider = TTSFactory.create_from_config()
    return _tts_provider


def reload_voice_providers():
    global _asr_provider, _tts_provider
    _asr_provider = None
    _tts_provider = None


@router.post("/asr", dependencies=[Depends(_asr_limit)])
async def speech_to_text(
    audio: UploadFile = File(...),
    user: dict = Depends(require_user),
):
    check_content_type(audio, ALLOWED_AUDIO_TYPES, "音频")
    audio_bytes = await read_limited(audio, MAX_AUDIO_BYTES)
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="音频内容为空")
    try:
        provider = _get_asr()
        text = await provider.transcribe(audio_bytes)
        return {"ok": True, "text": text, "provider": provider.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("ASR 处理失败")
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=MAX_TTS_CHARS)
    emotion: str = Field(default="", max_length=32)  # 情绪标签（可选，由后端 emotion_analyzer 生成）
    emotion_intensity: float = Field(default=0.5, ge=0.0, le=1.0)


@router.post("/tts", dependencies=[Depends(_tts_limit)])
async def text_to_speech(payload: TTSRequest, user: dict = Depends(require_user)):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")
    try:
        provider = _get_tts()
        # 构建 TTS 情绪参数
        emotion_params = {}
        if payload.emotion:
            from core.emotion_analyzer import EmotionResult
            mock_emotion = EmotionResult(
                label=payload.emotion,
                intensity=payload.emotion_intensity,
                valence=0.0,
                confidence=1.0,
                raw_tags=[],
            )
            emotion_params = get_emotion_tts_params(mock_emotion, provider.config.get("type", "edge"))

        audio_data = await provider.synthesize(payload.text, emotion=emotion_params or None)
        media_type = "audio/wav" if provider.config.get("type") == "siliconflow" else "audio/mpeg"
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=media_type,
            headers={"Content-Disposition": "inline; filename=tts.mp3"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("TTS 处理失败")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.websocket("/tts-stream")
async def tts_stream_ws(websocket: WebSocket):
    """WebSocket 流式 TTS 端点

    客户端 → 服务端:
      {"text": "...", "emotion": "happy", "emotion_intensity": 0.8}

    服务端 → 客户端:
      binary: 音频 chunk（逐块推送）
      text: {"type": "done"} 或 {"type": "error", "msg": "..."}
    """
    user = await authenticate_ws(websocket)
    if user is None:
        return  # authenticate_ws 已关闭连接（4401）

    sem = ws_semaphore()
    if sem.locked():
        await websocket.close(code=1013, reason="服务繁忙，请稍后重试")
        return

    async with sem:
        await websocket.accept()
        await _tts_stream_loop(websocket)


async def _tts_stream_loop(websocket: WebSocket) -> None:
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=WS_IDLE_TIMEOUT)
            except asyncio.TimeoutError:
                logger.info("TTS WebSocket 空闲超时，主动关闭")
                await websocket.close(code=1000, reason="空闲超时")
                return
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "msg": "无效 JSON"}))
                continue

            text = msg.get("text", "").strip()
            if not text:
                await websocket.send_text(json.dumps({"type": "error", "msg": "文本为空"}))
                continue
            if len(text) > MAX_TTS_CHARS:
                await websocket.send_text(
                    json.dumps({"type": "error", "msg": f"文本超长（上限 {MAX_TTS_CHARS} 字）"})
                )
                continue

            provider = _get_tts()

            # 构建情绪参数
            emotion_params = {}
            emotion_label = msg.get("emotion", "")
            emotion_intensity = float(msg.get("emotion_intensity", 0.5))
            if emotion_label:
                from core.emotion_analyzer import EmotionResult
                mock_emotion = EmotionResult(
                    label=emotion_label,
                    intensity=emotion_intensity,
                    valence=0.0,
                    confidence=1.0,
                    raw_tags=[],
                )
                emotion_params = get_emotion_tts_params(mock_emotion, provider.config.get("type", "edge"))

            try:
                async for chunk in provider.synthesize_stream(text, emotion=emotion_params or None):
                    await websocket.send_bytes(chunk)
                await websocket.send_text(json.dumps({"type": "done"}))
            except Exception as e:
                logger.exception("流式 TTS 失败")
                await websocket.send_text(json.dumps({"type": "error", "msg": str(e)}))

    except WebSocketDisconnect:
        logger.info("TTS WebSocket 客户端断开")
    except Exception as e:
        logger.warning("TTS WebSocket 异常: %s", e)


@router.get("/voices")
async def list_voices():
    from core.providers.tts_factory import TTSFactory as _F
    config = _F._load_config() or {}
    return {"ok": True, "provider": config.get("type", ""), "voices": config.get("voices", [])}


@router.get("/status")
async def voice_status():
    asr = _get_asr()
    tts = _get_tts()
    return {"ok": True, "asr": asr.get_status(), "tts": tts.get_status()}
