from __future__ import annotations

import io
import json
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.providers.asr_factory import ASRFactory
from core.providers.tts_factory import TTSFactory
from core.emotion_analyzer import get_emotion_analyzer, get_emotion_tts_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

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


@router.post("/asr")
async def speech_to_text(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()
        provider = _get_asr()
        text = await provider.transcribe(audio_bytes)
        return {"ok": True, "text": text, "provider": provider.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("ASR 处理失败")
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


class TTSRequest(BaseModel):
    text: str
    emotion: str = ""        # 情绪标签（可选，由后端 emotion_analyzer 生成）
    emotion_intensity: float = 0.5


@router.post("/tts")
async def text_to_speech(payload: TTSRequest):
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
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "msg": "无效 JSON"}))
                continue

            text = msg.get("text", "").strip()
            if not text:
                await websocket.send_text(json.dumps({"type": "error", "msg": "文本为空"}))
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
