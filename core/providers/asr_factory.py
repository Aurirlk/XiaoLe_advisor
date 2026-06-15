"""
ASR 工厂：根据配置动态创建语音识别供应商实例
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Type

import yaml

from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _resolve_api_key(raw: str) -> str:
    if raw.startswith("${") and raw.endswith("}"):
        return os.getenv(raw[2:-1], "")
    return raw


class ASRProvider(BaseProvider):
    """ASR 供应商基类"""
    provider_type = "asr"

    async def transcribe(self, audio_bytes: bytes) -> str:
        return await self.execute_with_resilience(self._do_transcribe, audio_bytes)

    async def _do_transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError


class FunASRProvider(ASRProvider):
    """FunASR 本地识别"""
    async def _do_transcribe(self, audio_bytes: bytes) -> str:
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        wav_path = tmp_path.replace(".webm", ".wav")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", wav_path],
                capture_output=True, timeout=10,
            )
            from funasr import AutoModel
            model_dir = self.config.get("model_dir", "models/SenseVoiceSmall")
            model = AutoModel(model=model_dir)
            result = model.generate(input=wav_path)
            if result and len(result) > 0:
                return result[0].get("text", "")
            return ""
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(wav_path).unlink(missing_ok=True)


class OpenAIASRProvider(ASRProvider):
    """OpenAI Whisper API"""
    async def _do_transcribe(self, audio_bytes: bytes) -> str:
        import httpx
        api_key = _resolve_api_key(self.config.get("api_key", ""))
        base_url = self.config.get("base_url", "https://api.openai.com/v1/audio/transcriptions")
        model = self.config.get("model_name", "whisper-1")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                base_url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"audio": ("recording.webm", audio_bytes, "audio/webm")},
                data={"model": model, "language": "zh"},
            )
            resp.raise_for_status()
            return resp.json().get("text", "")


class Qwen3ASRProvider(ASRProvider):
    """通义千问 Qwen3-ASR-Flash"""
    async def _do_transcribe(self, audio_bytes: bytes) -> str:
        import httpx
        api_key = _resolve_api_key(self.config.get("api_key", ""))
        base_url = self.config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        model = self.config.get("model_name", "qwen3-asr-flash")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"audio": ("recording.webm", audio_bytes, "audio/webm")},
                data={"model": model},
            )
            resp.raise_for_status()
            return resp.json().get("text", "")


class SherpaASRProvider(ASRProvider):
    """Sherpa-ONNX 本地识别"""
    async def _do_transcribe(self, audio_bytes: bytes) -> str:
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        wav_path = tmp_path.replace(".webm", ".wav")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", wav_path],
                capture_output=True, timeout=10,
            )
            model_dir = self.config.get("model_dir", "")
            cmd = ["sherpa-onnx-offline", "--model", f"{model_dir}/model.onnx",
                   "--tokens", f"{model_dir}/tokens.txt", wav_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.stdout.strip()
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(wav_path).unlink(missing_ok=True)


class ASRFactory:
    """ASR 工厂"""

    _registry: Dict[str, Type[ASRProvider]] = {
        "fun_local": FunASRProvider,
        "funasr": FunASRProvider,
        "openai": OpenAIASRProvider,
        "qwen3_asr_flash": Qwen3ASRProvider,
        "sherpa_onnx_local": SherpaASRProvider,
    }

    @classmethod
    def create(cls, config: dict) -> ASRProvider:
        asr_type = config.get("type", "fun_local")
        provider_cls = cls._registry.get(asr_type, FunASRProvider)
        config["name"] = config.get("name", asr_type)
        return provider_cls(config)

    @classmethod
    def create_from_config(cls) -> ASRProvider:
        config = cls._load_config()
        if config:
            return cls.create(config)
        return cls.create({"type": "fun_local", "model_dir": "models/SenseVoiceSmall"})

    @classmethod
    def _load_config(cls) -> dict | None:
        user_cfg = {}
        user_cfg_path = ROOT / "configs" / ".config.yaml"
        if user_cfg_path.exists():
            with open(user_cfg_path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}

        selected = user_cfg.get("selected_module", {}).get("ASR", "")
        api_keys = user_cfg.get("api_keys", {})

        # 从 asr_config.yaml 查找预设
        asr_cfg = ROOT / "configs" / "asr_config.yaml"
        if asr_cfg.exists():
            with open(asr_cfg, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            presets = raw.get("asr", {}).get("presets", {})
            target = selected or raw.get("asr", {}).get("active", "")
            if target in presets:
                cfg = dict(presets[target])
                cls._apply_api_keys(cfg, api_keys)
                return cfg
        return None

    @staticmethod
    def _apply_api_keys(cfg: dict, api_keys: dict) -> None:
        """用 .config.yaml 的 api_keys 覆盖配置中的 ${ENV_VAR}"""
        if not api_keys:
            return
        for key in ("api_key", "access_token", "api_secret"):
            val = cfg.get(key, "")
            if val.startswith("${") and val.endswith("}"):
                env_name = val[2:-1]
                if env_name in api_keys and api_keys[env_name]:
                    cfg[key] = api_keys[env_name]

    @classmethod
    def register(cls, type_name: str, provider_cls: Type[ASRProvider]) -> None:
        cls._registry[type_name] = provider_cls
