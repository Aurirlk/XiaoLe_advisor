"""
WebSocket 全双工对话端点

支持：
- 文本对话（与 HTTP /stream/advice 等价的 WebSocket 版本）
- 流式音频输入（前端 PCM chunk → 后端 VAD 检测 → ASR → LLM → 流式回复）
- 流式 TTS 推送（LLM 回复后逐 chunk 推送语音）
- 实时状态推送（typing、status、emotion）
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.dependencies import (
    get_checkpoint_manager,
    get_compiled_graph,
    get_conversation_turn_store,
)
from core.web_search_status import drain_status
from core.emotion_analyzer import get_emotion_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# VAD 实例（延迟初始化）
_vad_detector = None


def _get_vad():
    global _vad_detector
    if _vad_detector is None:
        from core.vad_detector import SileroVADDetector
        _vad_detector = SileroVADDetector()
    return _vad_detector


AGENT_NODES = frozenset({
    "profile_agent", "parent_agent", "family_agent", "match_agent", "career_agent",
    "web_search_agent", "sql_agent", "synthesis_agent", "supervisor_agent",
})


async def _process_text_query(
    ws: WebSocket,
    query: str,
    session_id: str,
    turn_store,
    conversation_role: str = "student",
) -> None:
    """处理文本查询：走完整 LangGraph 流程，通过 WebSocket 推送 SSE 事件"""
    graph = get_compiled_graph()
    cm = get_checkpoint_manager()

    turn_id = str(uuid.uuid4())
    init_state = cm.build_init_state(query, session_id=session_id)
    init_state["current_datetime"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    init_state["conversation_role"] = conversation_role

    # 情感分析
    emotion_analyzer = get_emotion_analyzer(method="keyword")
    emotion_result = await emotion_analyzer.analyze(query)
    init_state["emotion_label"] = emotion_result.label
    init_state["emotion_intensity"] = emotion_result.intensity
    init_state["emotion_valence"] = emotion_result.valence

    config = cm.build_config(session_id, recursion_limit=50)

    route_path: list[str] = []
    assistant_response = ""

    # 推送 status
    await _send_json(ws, {"type": "status", "msg": "正在思考..."})

    try:
        async for chunk in graph.astream(init_state, config=config):
            # 推送搜索状态
            for status_msg in drain_status(session_id):
                await _send_json(ws, {"type": "status", "msg": status_msg})

            for node_name in chunk:
                if node_name in AGENT_NODES and (not route_path or route_path[-1] != node_name):
                    route_path.append(node_name)
                    await _send_json(ws, {"type": "status", "msg": f"经过 {node_name}..."})
    except Exception as e:
        logger.warning("[WS] graph.astream 异常: %s", e)
        await _send_json(ws, {"type": "error", "msg": f"处理异常: {e}"})
        return

    # 获取最终状态
    try:
        final_state = graph.get_state(config)
        if final_state and final_state.values:
            values = final_state.values

            # 推送 profile_update
            profile = values.get("user_profile")
            if profile:
                profile_event: Dict[str, Any] = {"type": "profile_update", "profile": profile}
                for key in ("parent_profile", "family_context", "subject_scores"):
                    val = values.get(key)
                    if val:
                        profile_event[key] = val
                el = values.get("emotion_label")
                if el:
                    profile_event["emotion"] = {
                        "label": el,
                        "intensity": values.get("emotion_intensity", 0.5),
                        "valence": values.get("emotion_valence", 0.0),
                    }
                await _send_json(ws, profile_event)

            # 提取回复
            messages = values.get("messages", [])
            assistant_msgs = [m for m in messages if getattr(m, "type", "") == "ai"]
            if assistant_msgs:
                assistant_response = str(getattr(assistant_msgs[-1], "content", ""))
            else:
                assistant_response = "服务暂时繁忙，请稍后重试。"
        else:
            assistant_response = "服务暂时不可用，请稍后重试。"
    except Exception as e:
        logger.warning("[WS] get_state 异常: %s", e)
        assistant_response = "服务暂时不可用，请稍后重试。"

    # 推送回复 token
    await _send_json(ws, {"type": "token", "msg": assistant_response})

    # 保存对话轮次
    if turn_store:
        try:
            await turn_store.save_turn(
                turn_id=turn_id,
                session_id=session_id,
                user_query=query,
                assistant_response=assistant_response,
                route_path=route_path,
                user_profile_snapshot=profile if 'profile' in dir() else {},
                sql_hit_count=0,
                risk_level="",
            )
        except Exception as e:
            logger.warning("[WS] save_turn 失败: %s", e)

    # 推送 meta
    await _send_json(ws, {"type": "meta", "session_id": session_id, "turn_id": turn_id})
    await _send_json(ws, {"type": "done"})


async def _process_audio_stream(
    ws: WebSocket,
    session_id: str,
    turn_store,
    conversation_role: str = "student",
) -> None:
    """处理音频流：接收 PCM chunk → VAD 检测端点 → ASR → LLM → 回复"""
    vad = _get_vad()
    audio_buffer = bytearray()
    speech_started = False

    await _send_json(ws, {"type": "status", "msg": "VAD 监听中..."})

    while True:
        try:
            data = await ws.receive()
        except WebSocketDisconnect:
            break

        # 文本消息：控制指令
        if "text" in data:
            try:
                msg = json.loads(data["text"])
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "audio_end":
                # 前端主动结束音频流
                break

            if msg_type == "text":
                # 切换到文本模式
                await _process_text_query(
                    ws, msg.get("query", ""), session_id, turn_store,
                    msg.get("conversation_role", conversation_role),
                )
                return

            continue

        # 二进制消息：音频 chunk
        if "bytes" in data:
            chunk = data["bytes"]
            if not chunk:
                continue

            is_speech, is_endpoint = vad.process_chunk(chunk)

            if is_speech and not speech_started:
                speech_started = True
                audio_buffer.clear()
                await _send_json(ws, {"type": "status", "msg": "检测到语音..."})

            if speech_started:
                audio_buffer.extend(chunk)

            if is_endpoint and speech_started:
                # 语音端点检测到，开始识别
                await _send_json(ws, {"type": "status", "msg": "语音结束，正在识别..."})
                vad.reset()

                if len(audio_buffer) < 1600:  # 太短的音频忽略
                    speech_started = False
                    audio_buffer.clear()
                    await _send_json(ws, {"type": "status", "msg": "音频太短，继续监听..."})
                    continue

                # ASR 识别
                from core.providers.asr_factory import ASRFactory
                asr = ASRFactory.create_from_config()
                try:
                    # PCM → WAV 转换
                    wav_bytes = _pcm_to_wav(bytes(audio_buffer))
                    text = await asr.transcribe(wav_bytes)
                except Exception as e:
                    logger.warning("[WS] ASR 失败: %s", e)
                    text = ""

                speech_started = False
                audio_buffer.clear()

                if not text.strip():
                    await _send_json(ws, {"type": "status", "msg": "未识别到内容，继续监听..."})
                    continue

                # 推送识别结果
                await _send_json(ws, {"type": "asr_result", "text": text})

                # 走 LLM 流程
                await _process_text_query(ws, text, session_id, turn_store, conversation_role)
                return

    vad.reset()
    await _send_json(ws, {"type": "status", "msg": "音频流结束"})


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bits: int = 16) -> bytes:
    """PCM 16-bit 转 WAV"""
    import struct
    data_size = len(pcm_data)
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, channels, sample_rate,
        sample_rate * channels * bits // 8,
        channels * bits // 8, bits,
        b'data', data_size,
    )
    return header + pcm_data


async def _send_json(ws: WebSocket, data: dict) -> None:
    """发送 JSON 消息"""
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """全双工对话 WebSocket

    客户端 → 服务端:
      {"type": "text", "query": "...", "session_id": "...", "role": "student"}
      {"type": "audio_start", "session_id": "..."}
      binary: PCM 16-bit 16kHz 单声道音频 chunk
      {"type": "audio_end"}

    服务端 → 客户端:
      {"type": "status", "msg": "..."}
      {"type": "token", "msg": "..."}
      {"type": "asr_result", "text": "..."}
      {"type": "profile_update", "profile": {...}, "emotion": {...}}
      {"type": "meta", "session_id": "...", "turn_id": "..."}
      {"type": "done"}
      {"type": "error", "msg": "..."}
    """
    await websocket.accept()
    turn_store = get_conversation_turn_store()
    session_id = ""

    logger.info("[WS] 客户端连接")

    try:
        while True:
            data = await websocket.receive()

            # 二进制消息（音频 chunk，仅在 audio_start 后有效）
            if "bytes" in data:
                # 不在音频模式下忽略
                continue

            if "text" not in data:
                continue

            try:
                msg = json.loads(data["text"])
            except json.JSONDecodeError:
                await _send_json(websocket, {"type": "error", "msg": "无效 JSON"})
                continue

            msg_type = msg.get("type", "")
            session_id = msg.get("session_id", "") or str(uuid.uuid4())
            role = msg.get("role", "student")

            if msg_type == "text":
                query = msg.get("query", "").strip()
                if not query:
                    await _send_json(websocket, {"type": "error", "msg": "查询为空"})
                    continue
                await _process_text_query(websocket, query, session_id, turn_store, role)

            elif msg_type == "audio_start":
                await _process_audio_stream(websocket, session_id, turn_store, role)

            elif msg_type == "ping":
                await _send_json(websocket, {"type": "pong"})

            else:
                await _send_json(websocket, {"type": "error", "msg": f"未知消息类型: {msg_type}"})

    except WebSocketDisconnect:
        logger.info("[WS] 客户端断开: %s", session_id)
    except Exception as e:
        logger.warning("[WS] 异常: %s", e)
