"""
VLLM 视觉大模型工厂：图片理解、图文分析

支持 OpenAI 兼容的视觉 API（GLM-4V、Qwen-VL、GPT-4o 等）
"""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Type

import yaml

from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _resolve_api_key(raw: str) -> str:
    if raw.startswith("${") and raw.endswith("}"):
        return os.getenv(raw[2:-1], "")
    return raw


class VLLMProvider(BaseProvider):
    """视觉大模型供应商基类"""
    provider_type = "vllm"

    async def analyze_image(self, image_bytes: bytes, prompt: str, mime_type: str = "image/jpeg") -> str:
        """分析图片，返回文本描述"""
        return await self.execute_with_resilience(self._do_analyze, image_bytes, prompt, mime_type)

    async def _do_analyze(self, image_bytes: bytes, prompt: str, mime_type: str = "image/jpeg") -> str:
        raise NotImplementedError


class OpenAIVLLMProvider(VLLMProvider):
    """OpenAI 兼容视觉供应商（GLM-4V / Qwen-VL / GPT-4o）"""

    async def _do_analyze(self, image_bytes: bytes, prompt: str, mime_type: str = "image/jpeg") -> str:
        import httpx

        api_key = _resolve_api_key(self.config.get("api_key", ""))
        base_url = self.config.get("base_url", "https://api.openai.com/v1")
        model = self.config.get("model_name", "gpt-4o-mini")
        max_tokens = self.config.get("max_tokens", 2048)
        temperature = self.config.get("temperature", 0.7)

        # 图片 base64 编码
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return "图片分析无结果"


class VLLMFactory:
    """VLLM 视觉工厂"""

    _registry: Dict[str, Type[VLLMProvider]] = {
        "openai": OpenAIVLLMProvider,
    }

    @classmethod
    def create(cls, config: dict) -> VLLMProvider:
        vllm_type = config.get("type", "openai")
        provider_cls = cls._registry.get(vllm_type, OpenAIVLLMProvider)
        config["name"] = config.get("name", config.get("model_name", "unknown"))
        return provider_cls(config)

    @classmethod
    def create_from_config(cls) -> VLLMProvider:
        config = cls._load_config()
        if config:
            return cls.create(config)
        return cls.create({"type": "openai", "model_name": "glm-4v-flash"})

    @classmethod
    def _load_config(cls) -> dict | None:
        user_cfg = {}
        user_cfg_path = ROOT / "configs" / ".config.yaml"
        if user_cfg_path.exists():
            with open(user_cfg_path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}

        selected = user_cfg.get("selected_module", {}).get("VLLM", "")
        api_keys = user_cfg.get("api_keys", {})

        # 从 vllm_config.yaml 查找预设
        vllm_cfg = ROOT / "configs" / "vllm_config.yaml"
        if vllm_cfg.exists():
            with open(vllm_cfg, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            presets = raw.get("vllm", {}).get("presets", {})
            target = selected or raw.get("vllm", {}).get("active", "")
            if target in presets:
                cfg = dict(presets[target])
                cls._apply_api_keys(cfg, api_keys)
                return cfg
        return None

    @staticmethod
    def _apply_api_keys(cfg: dict, api_keys: dict) -> None:
        if not api_keys:
            return
        for key in ("api_key", "access_token"):
            val = cfg.get(key, "")
            if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
                env_name = val[2:-1]
                if env_name in api_keys and api_keys[env_name]:
                    cfg[key] = api_keys[env_name]

    @classmethod
    def list_presets(cls) -> list[dict]:
        """列出所有可用预设"""
        vllm_cfg = ROOT / "configs" / "vllm_config.yaml"
        if not vllm_cfg.exists():
            return []
        with open(vllm_cfg, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        presets = raw.get("vllm", {}).get("presets", {})
        active = raw.get("vllm", {}).get("active", "")
        return [
            {"name": name, "model": cfg.get("model_name", ""), "description": cfg.get("description", ""), "is_active": name == active}
            for name, cfg in presets.items()
        ]

    @classmethod
    def register(cls, type_name: str, provider_cls: Type[VLLMProvider]) -> None:
        cls._registry[type_name] = provider_cls
