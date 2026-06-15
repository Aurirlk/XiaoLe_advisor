"""
LLM 工厂：根据配置动态创建 LLM 供应商实例，支持重试+熔断+回退
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Type

import yaml
from pathlib import Path

from core.providers.base import BaseProvider, CircuitBreakerOpen

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _resolve_api_key(raw: str) -> str:
    if raw.startswith("${") and raw.endswith("}"):
        return os.getenv(raw[2:-1], "")
    return raw


class LLMProvider(BaseProvider):
    """LLM 供应商基类"""
    provider_type = "llm"

    def create_llm(self) -> Any:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.config["model_name"],
            temperature=self.config.get("temperature", 0.7),
            base_url=self.config.get("base_url"),
            api_key=self.config.get("api_key", ""),
            timeout=self.config.get("timeout", 60),
            max_tokens=self.config.get("max_tokens", 4096),
        )

    async def invoke(self, messages: list) -> str:
        llm = self.create_llm()

        async def _do():
            resp = await llm.ainvoke(messages)
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                self._last_usage = {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                }
            return str(resp.content)

        return await self.execute_with_resilience(_do)

    def get_last_usage(self) -> dict:
        return getattr(self, "_last_usage", {"input_tokens": 0, "output_tokens": 0})


class OpenAILLMProvider(LLMProvider):
    """OpenAI 兼容供应商（DeepSeek / Qwen / GLM / Doubao / MiniMax）"""
    pass


class GeminiLLMProvider(LLMProvider):
    """Google Gemini 供应商"""
    def create_llm(self):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=self.config["model_name"],
                google_api_key=self.config.get("api_key", ""),
                temperature=self.config.get("temperature", 0.7),
            )
        except ImportError:
            logger.warning("langchain-google-genai 未安装，回退到 OpenAI 兼容模式")
            return super().create_llm()


class OllamaLLMProvider(LLMProvider):
    """Ollama 本地模型供应商"""
    def create_llm(self):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.config["model_name"],
            base_url=self.config.get("base_url", "http://localhost:11434/v1"),
            api_key="ollama",
            temperature=self.config.get("temperature", 0.7),
            timeout=self.config.get("timeout", 120),
        )


class ResilientLLMProvider(LLMProvider):
    """带自动回退的 LLM 供应商：主供应商熔断后自动切换到备用"""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        super().__init__(primary.config)
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name}(主) → {fallback.name}(备)"

    async def invoke(self, messages: list) -> str:
        try:
            return await self.primary.invoke(messages)
        except CircuitBreakerOpen:
            logger.warning("[%s] 主供应商熔断，切换到备用: %s", self.primary.name, self.fallback.name)
            return await self.fallback.invoke(messages)

    def get_last_usage(self) -> dict:
        return self.primary.get_last_usage()

    def get_status(self) -> dict:
        return {
            "primary": self.primary.get_status(),
            "fallback": self.fallback.get_status(),
        }


class LLMFactory:
    """LLM 工厂：创建 + 回退 + 配置管理"""

    _registry: Dict[str, Type[LLMProvider]] = {
        "openai": OpenAILLMProvider,
        "gemini": GeminiLLMProvider,
        "ollama": OllamaLLMProvider,
    }

    @classmethod
    def create(cls, config: dict) -> LLMProvider:
        provider_type = config.get("type", "openai")
        provider_cls = cls._registry.get(provider_type, OpenAILLMProvider)
        config["name"] = config.get("name", config.get("model_name", "unknown"))
        return provider_cls(config)

    @classmethod
    def create_from_config(cls, config_path: Path | None = None, fallback_preset: str | None = None) -> LLMProvider:
        """从配置文件创建 LLM 供应商，支持自动回退

        优先级：.config.yaml > llm_config.yaml
        如果指定 fallback_preset，创建带自动回退的 ResilientLLMProvider
        """
        config = cls._load_config(config_path)
        if not config:
            raise ValueError("无法加载 LLM 配置")

        primary = cls.create(config)
        logger.info("LLM 工厂创建: %s (%s)", primary.name, config.get("model_name"))

        if fallback_preset:
            fallback_config = cls._load_preset(fallback_preset)
            if fallback_config:
                fallback = cls.create(fallback_config)
                logger.info("LLM 回退供应商: %s (%s)", fallback.name, fallback_config.get("model_name"))
                return ResilientLLMProvider(primary, fallback)

        return primary

    @classmethod
    def _load_preset(cls, preset_name: str) -> dict | None:
        """从 .config.yaml 或 llm_config.yaml 加载指定预设"""
        user_cfg_path = ROOT / "configs" / ".config.yaml"
        if user_cfg_path.exists():
            with open(user_cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            if preset_name in cfg.get("LLM", {}):
                return cfg["LLM"][preset_name]

        llm_cfg_path = ROOT / "configs" / "llm_config.yaml"
        if llm_cfg_path.exists():
            with open(llm_cfg_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)["llm"]
            presets = raw.get("presets", {})
            if preset_name in presets:
                cfg = presets[preset_name]
                cfg["name"] = preset_name
                return cfg
        return None

    @classmethod
    def create_with_fallback(
        cls,
        primary_config: dict,
        fallback_config: dict | None = None,
    ) -> tuple[LLMProvider, Optional[LLMProvider]]:
        """创建主供应商 + 可选回退供应商"""
        primary = cls.create(primary_config)
        fallback = cls.create(fallback_config) if fallback_config else None
        return primary, fallback

    @classmethod
    def _load_config(cls, config_path: Path | None = None) -> dict | None:
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            return raw

        user_cfg_path = ROOT / "configs" / ".config.yaml"
        if user_cfg_path.exists():
            with open(user_cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            selected = cfg.get("selected_module", {}).get("LLM", "")
            if selected and selected in cfg.get("LLM", {}):
                return cfg["LLM"][selected]

        llm_cfg_path = ROOT / "configs" / "llm_config.yaml"
        if llm_cfg_path.exists():
            with open(llm_cfg_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)["llm"]
            presets = raw.get("presets", {})
            active = raw.get("active", "")
            if active in presets:
                cfg = presets[active]
                cfg["name"] = active
                return cfg

        return None

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def register(cls, type_name: str, provider_cls: Type[LLMProvider]) -> None:
        cls._registry[type_name] = provider_cls
