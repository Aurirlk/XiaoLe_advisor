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

# P1-19：高考领域热词（OpenAI 兼容接口通过 prompt 参数做词级引导，
# 显著降低"投档线→投单线"类误识别；可用 asr 配置 hotwords 覆盖）
DEFAULT_ASR_HOTWORDS = (
    "平行志愿,投档线,位次,强基计划,一分一段,批次线,调剂,服从专业调剂,"
    "选科,物理类,历史类,综合改革,专科批,本科批,提前批,专项计划,滑档,退档"
)


def _resolve_api_key(raw: str) -> str:
    """解析 ${ENV_VAR} 占位符；缺失时 fail-fast，避免带空 key 发请求拿到难懂的 401。"""
    if not raw:
        raise ValueError("ASR 供应商未配置 api_key")
    if raw.startswith("${") and raw.endswith("}"):
        env_name = raw[2:-1]
        val = os.getenv(env_name, "")
        if not val:
            raise ValueError(f"缺少环境变量 {env_name}（ASR api_key 未配置）")
        return val
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
                # OpenAI /audio/transcriptions 接口的表单字段名是 file（非 audio）
                files={"file": ("recording.webm", audio_bytes, "audio/webm")},
                data={
                    "model": model,
                    "language": "zh",
                    # P1-19：领域热词引导
                    "prompt": self.config.get("hotwords", DEFAULT_ASR_HOTWORDS),
                },
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
                # OpenAI 兼容接口的表单字段名是 file（非 audio）
                files={"file": ("recording.webm", audio_bytes, "audio/webm")},
                data={
                    "model": model,
                    # P1-19：领域热词引导
                    "prompt": self.config.get("hotwords", DEFAULT_ASR_HOTWORDS),
                },
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


class MiMoASRProvider(ASRProvider):
    """小米 MiMo ASR（OpenAI 兼容接口）"""
    async def _do_transcribe(self, audio_bytes: bytes) -> str:
        import httpx
        api_key = _resolve_api_key(self.config.get("api_key", ""))
        url = self.config.get("url", "https://api.minimax.chat/v1/audio/asr")
        model = self.config.get("model", "mimo-v2.5-asr")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"audio": ("recording.webm", audio_bytes, "audio/webm")},
                data={"model": model},
            )
            resp.raise_for_status()
            return resp.json().get("text", "")


class ASRFactory:
    """ASR 工厂"""

    _registry: Dict[str, Type[ASRProvider]] = {
        "fun_local": FunASRProvider,
        "funasr": FunASRProvider,
        "openai": OpenAIASRProvider,
        "qwen3_asr_flash": Qwen3ASRProvider,
        "sherpa_onnx_local": SherpaASRProvider,
        "mimo": MiMoASRProvider,
    }

    @classmethod
    def create(cls, config: dict) -> ASRProvider:
        asr_type = config.get("type", "fun_local")
        provider_cls = cls._registry.get(asr_type)
        if provider_cls is None:
            # 禁止静默降级：未实现的引擎必须显式报错，否则用户选流式云端引擎
            # 实际跑的是本地整段引擎且零告警（原 P0-9）
            raise ValueError(
                f"未实现的 ASR type={asr_type!r}，可用类型: {sorted(cls._registry)}。"
                "请检查 configs/.config.yaml 的 selected_module.ASR 与预设的 type 字段。"
            )
        config["name"] = config.get("name", asr_type)
        return provider_cls(config)

    @classmethod
    def create_from_config(cls) -> ASRProvider:
        return cls.create(cls._load_config())

    @classmethod
    def _load_config(cls) -> dict:
        user_cfg = {}
        user_cfg_path = ROOT / "configs" / ".config.yaml"
        if user_cfg_path.exists():
            with open(user_cfg_path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}

        selected = user_cfg.get("selected_module", {}).get("ASR", "")
        api_keys = user_cfg.get("api_keys", {})

        # 合并两处 preset 源：asr_config.yaml 的 presets + .config.yaml 的 ASR 段
        presets: dict = {}
        active = ""
        asr_cfg = ROOT / "configs" / "asr_config.yaml"
        if asr_cfg.exists():
            with open(asr_cfg, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            presets.update(raw.get("asr", {}).get("presets", {}) or {})
            active = raw.get("asr", {}).get("active", "")
        inline = user_cfg.get("ASR", {})
        if isinstance(inline, dict):
            presets.update({k: v for k, v in inline.items() if isinstance(v, dict)})

        target = selected or active
        if not target:
            raise ValueError("未配置 ASR 引擎：请设置 .config.yaml 的 selected_module.ASR 或 asr_config.yaml 的 asr.active")
        if target not in presets:
            raise ValueError(f"selected_module.ASR={target!r} 未找到预设，可用: {sorted(presets)}")

        cfg = dict(presets[target])
        cls._apply_api_keys(cfg, api_keys)
        return cfg

    @staticmethod
    def _apply_api_keys(cfg: dict, api_keys: dict) -> None:
        """用 .config.yaml 的 api_keys 覆盖配置中的 ${ENV_VAR}；
        若覆盖值本身仍是 ${ENV_VAR} 占位符，保留占位符由 provider 在使用时从环境变量解析。"""
        if not api_keys:
            return
        for key in ("api_key", "access_token", "api_secret"):
            val = cfg.get(key, "")
            if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
                env_name = val[2:-1]
                if env_name in api_keys and api_keys[env_name]:
                    cfg[key] = api_keys[env_name]

    @classmethod
    def register(cls, type_name: str, provider_cls: Type[ASRProvider]) -> None:
        cls._registry[type_name] = provider_cls
