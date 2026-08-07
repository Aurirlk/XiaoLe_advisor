"""
模块管理器 — 管理模块的加载状态、配置、用户覆盖

从 api/main.py 拆分出来，职责：
1. 读取/保存管理员模块配置
2. 读取/保存用户模块覆盖
3. 解析最终生效的模块配置
4. 跟踪模块加载状态
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]

# ==================== 全局状态 ====================
MODULE_STATUS: Dict[str, Dict[str, Any]] = {}
MODULE_LOAD_PROGRESS: List[Dict[str, Any]] = []


# ==================== 配置读写 ====================

def get_enabled_modules() -> dict:
    """读取管理员配置的默认模块开关"""
    import yaml
    config_path = ROOT / "configs" / ".config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("enabled_modules", {})
    return {}


def save_enabled_modules(modules: dict):
    """保存管理员模块开关配置"""
    import yaml
    config_path = ROOT / "configs" / ".config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}
    cfg["enabled_modules"] = modules
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)


def get_user_module_overrides(session_id: str) -> dict:
    """获取用户自定义的模块开关（优先级高于管理员配置）"""
    cache_path = ROOT / "data" / f"module_overrides_{session_id}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return {}


def save_user_module_overrides(session_id: str, overrides: dict):
    """保存用户自定义的模块开关"""
    cache_path = ROOT / "data" / f"module_overrides_{session_id}.json"
    cache_path.write_text(json.dumps(overrides, ensure_ascii=False), encoding="utf-8")


def resolve_effective_modules(session_id: str = None) -> dict:
    """解析最终生效的模块配置（用户覆盖 > 管理员默认）"""
    admin_config = get_enabled_modules()
    effective = {k: v for k, v in admin_config.items() if not k.startswith("_")}
    
    if session_id:
        user_overrides = get_user_module_overrides(session_id)
        effective.update(user_overrides)
    
    return effective


# ==================== 加载进度 ====================

def log_progress(msg: str, success: bool = True, started_at: float = None):
    """记录加载进度"""
    if started_at is None:
        started_at = getattr(log_progress, '_started_at', time.time())
    MODULE_LOAD_PROGRESS.append({
        "time": time.time() - started_at,
        "message": msg,
        "success": success
    })
    logger.info(msg)


def set_started_at(ts: float):
    """设置启动时间戳"""
    log_progress._started_at = ts


def get_module_status() -> dict:
    """获取所有模块状态"""
    return MODULE_STATUS


def get_load_progress() -> list:
    """获取加载进度日志"""
    return MODULE_LOAD_PROGRESS


def set_module_status(name: str, loaded: bool, error: str = None, load_time: float = 0):
    """设置模块状态"""
    MODULE_STATUS[name] = {
        "loaded": loaded,
        "error": error,
        "load_time": load_time,
    }
