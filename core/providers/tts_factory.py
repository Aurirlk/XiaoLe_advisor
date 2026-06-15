"""
TTS 工厂：根据配置动态创建语音合成供应商实例

支持：
- 情绪 TTS：根据 emotion/style 参数调整语调
- 流式 TTS：synthesize_stream() 异步生成器逐 chunk 推送
- 整段合成：synthesize() 返回完整 bytes
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import AsyncIterator, Dict, Optional, Type

import yaml

from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _resolve_api_key(raw: str) -> str:
    if raw.startswith("${") and raw.endswith("}"):
        return os.getenv(raw[2:-1], "")
    return raw


class TTSProvider(BaseProvider):
    """TTS 供应商基类"""
    provider_type = "tts"

    async def synthesize(self, text: str, emotion: Optional[dict] = None) -> bytes:
        """整段合成，返回完整音频 bytes"""
        return await self.execute_with_resilience(self._do_synthesize, text, emotion)

    async def synthesize_stream(self, text: str, emotion: Optional[dict] = None) -> AsyncIterator[bytes]:
        """流式合成，逐 chunk 返回音频数据

        默认实现：调用 _do_synthesize 然后一次性 yield
        子类可覆盖为真正的流式实现
        """
        data = await self.synthesize(text, emotion)
        yield data

    async def _do_synthesize(self, text: str, emotion: Optional[dict] = None) -> bytes:
        raise NotImplementedError


class EdgeTTSProvider(TTSProvider):
    """微软 Edge TTS（免费）— 支持流式"""

    async def _do_synthesize(self, text: str, emotion: Optional[dict] = None) -> bytes:
        import edge_tts
        voice = self.config.get("voice", "zh-CN-XiaoxiaoNeural")
        rate = (emotion or {}).get("rate", "+0%")
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    async def synthesize_stream(self, text: str, emotion: Optional[dict] = None) -> AsyncIterator[bytes]:
        """Edge TTS 真正的流式实现"""
        import edge_tts
        voice = self.config.get("voice", "zh-CN-XiaoxiaoNeural")
        rate = (emotion or {}).get("rate", "+0%")
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                yield chunk["data"]


class SiliconFlowProvider(TTSProvider):
    """硅基流动 CosyVoice — 支持情绪 style"""

    async def _do_synthesize(self, text: str, emotion: Optional[dict] = None) -> bytes:
        import httpx
        api_key = _resolve_api_key(self.config.get("access_token", ""))
        model = self.config.get("model", "FunAudioLLM/CosyVoice2-0.5B")
        voice = self.config.get("voice", "FunAudioLLM/CosyVoice2-0.5B:alex")

        payload = {"model": model, "input": text, "voice": voice}
        # 情绪参数
        if emotion and emotion.get("style"):
            payload["style"] = emotion["style"]
            payload["style_weight"] = emotion.get("style_weight", 0.5)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.siliconflow.cn/v1/audio/speech",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.content


class AliyunStreamTTSProvider(TTSProvider):
    """阿里云 CosyVoice 流式 TTS — 支持情绪 style"""

    async def _do_synthesize(self, text: str, emotion: Optional[dict] = None) -> bytes:
        import httpx
        api_key = _resolve_api_key(self.config.get("api_key", ""))
        voice = self.config.get("voice", "longxiaochun")

        payload = {"model": "cosyvoice-v2", "input": text, "voice": voice}
        # 情绪参数
        if emotion and emotion.get("style"):
            payload["style"] = emotion["style"]
            payload["style_weight"] = emotion.get("style_weight", 0.5)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/audio/speech",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.content


class TTSFactory:
    """TTS 工厂"""

    _registry: Dict[str, Type[TTSProvider]] = {
        "edge": EdgeTTSProvider,
        "siliconflow": SiliconFlowProvider,
        "aliyun_stream": AliyunStreamTTSProvider,
    }

    @classmethod
    def create(cls, config: dict) -> TTSProvider:
        tts_type = config.get("type", "edge")
        provider_cls = cls._registry.get(tts_type, EdgeTTSProvider)
        config["name"] = config.get("name", tts_type)
        return provider_cls(config)

    @classmethod
    def create_from_config(cls) -> TTSProvider:
        config = cls._load_config()
        if config:
            return cls.create(config)
        return cls.create({"type": "edge", "voice": "zh-CN-XiaoxiaoNeural"})

    @classmethod
    def _load_config(cls) -> dict | None:
        user_cfg = {}
        user_cfg_path = ROOT / "configs" / ".config.yaml"
        if user_cfg_path.exists():
            with open(user_cfg_path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}

        selected = user_cfg.get("selected_module", {}).get("TTS", "")
        api_keys = user_cfg.get("api_keys", {})

        # 从 tts_config.yaml 查找预设
        tts_cfg = ROOT / "configs" / "tts_config.yaml"
        if tts_cfg.exists():
            with open(tts_cfg, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            presets = raw.get("tts", {}).get("presets", {})
            target = selected or raw.get("tts", {}).get("active", "")
            if target in presets:
                cfg = dict(presets[target])
                cls._apply_api_keys(cfg, api_keys)
                return cfg
        return None

    @staticmethod
    def _apply_api_keys(cfg: dict, api_keys: dict) -> None:
        if not api_keys:
            return
        for key in ("api_key", "access_token", "appid", "group_id"):
            val = cfg.get(key, "")
            if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
                env_name = val[2:-1]
                if env_name in api_keys and api_keys[env_name]:
                    cfg[key] = api_keys[env_name]

    @classmethod
    def register(cls, type_name: str, provider_cls: Type[TTSProvider]) -> None:
        cls._registry[type_name] = provider_cls
