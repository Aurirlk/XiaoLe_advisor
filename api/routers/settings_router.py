from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "configs" / "ui_settings.json"

router = APIRouter(prefix="/settings", tags=["settings"])


class UISettings(BaseModel):
    theme: str = "blue"
    reply_mode: str = "语音+文字"
    volume: int = 70
    voice: str = "zh-CN-XiaoxiaoNeural"
    ws_address: str = "ws://127.0.0.1:8001"
    api_address: str = "http://127.0.0.1:8000"
    llm_model: str = ""
    temperature: float = 0.7
    context_rounds: int = 3
    max_tokens: int = 4096
    asr_engine: str = ""
    tts_engine: str = ""
    vad_mode: str = "click"
    streaming_tts: bool = False
    emotion_method: str = "keyword"
    emotion_tts_enabled: bool = False
    emotion_intensity: float = 0.5
    enabled_tools: List[str] = []
    daily_limit: float = 10.0
    monthly_limit: float = 200.0


def _load_presets_from_config() -> Dict[str, Any]:
    """从 *_config.yaml 预设库加载所有可用预设"""
    result = {"llm": [], "asr": [], "tts": [], "vllm": []}

    # 读取 .config.yaml 获取当前选中项
    user_cfg = {}
    cfg_path = ROOT / "configs" / ".config.yaml"
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
    selected = user_cfg.get("selected_module", {})

    # LLM 预设
    llm_path = ROOT / "configs" / "llm_config.yaml"
    if llm_path.exists():
        with open(llm_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        for name, preset in raw.get("llm", {}).get("presets", {}).items():
            result["llm"].append({
                "name": name,
                "model": preset.get("model_name", ""),
                "provider": preset.get("type", ""),
                "description": preset.get("description", ""),
                "is_active": name == selected.get("LLM", ""),
            })

    # ASR 预设
    asr_path = ROOT / "configs" / "asr_config.yaml"
    if asr_path.exists():
        with open(asr_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        for name, preset in raw.get("asr", {}).get("presets", {}).items():
            result["asr"].append({
                "name": name,
                "type": preset.get("type", ""),
                "description": preset.get("description", ""),
                "is_active": name == selected.get("ASR", ""),
            })

    # TTS 预设
    tts_path = ROOT / "configs" / "tts_config.yaml"
    if tts_path.exists():
        with open(tts_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        for name, preset in raw.get("tts", {}).get("presets", {}).items():
            result["tts"].append({
                "name": name,
                "type": preset.get("type", ""),
                "description": preset.get("description", ""),
                "voices": preset.get("voices", []),
                "is_active": name == selected.get("TTS", ""),
            })

    # VLLM 预设
    vllm_path = ROOT / "configs" / "vllm_config.yaml"
    if vllm_path.exists():
        with open(vllm_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        for name, preset in raw.get("vllm", {}).get("presets", {}).items():
            result["vllm"].append({
                "name": name,
                "model": preset.get("model_name", ""),
                "provider": preset.get("type", ""),
                "description": preset.get("description", ""),
                "is_active": name == selected.get("VLLM", ""),
            })

    return result


@router.get("")
async def get_settings():
    """获取当前 UI 设置"""
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return UISettings().model_dump()


@router.post("")
async def save_settings(settings: UISettings):
    """保存 UI 设置"""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, "message": "设置已保存"}


@router.get("/models")
async def list_models():
    """列出所有可用的 LLM/ASR/TTS 预设（供设置界面下拉框）"""
    return _load_presets_from_config()


class SwitchModelRequest(BaseModel):
    preset: str


@router.post("/switch-model")
async def switch_model(payload: SwitchModelRequest):
    """运行时切换 LLM 模型"""
    cfg_path = ROOT / "configs" / ".config.yaml"
    if not cfg_path.exists():
        raise HTTPException(status_code=404, detail=".config.yaml 不存在")

    # 从 llm_config.yaml 获取可用预设列表
    llm_cfg_path = ROOT / "configs" / "llm_config.yaml"
    available = []
    if llm_cfg_path.exists():
        with open(llm_cfg_path, "r", encoding="utf-8") as f:
            llm_raw = yaml.safe_load(f)
        available = list(llm_raw.get("llm", {}).get("presets", {}).keys())

    if payload.preset not in available:
        raise HTTPException(status_code=400, detail=f"预设 '{payload.preset}' 不存在，可用: {available}")

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg.setdefault("selected_module", {})["LLM"] = payload.preset
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

    # 清除 LLM 缓存
    try:
        from api.dependencies import get_compiled_graph
        get_compiled_graph.cache_clear()
    except Exception:
        pass

    return {"ok": True, "message": f"已切换到 {payload.preset}"}
