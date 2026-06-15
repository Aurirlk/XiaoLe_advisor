"""
缓存清理异步任务
"""
from __future__ import annotations

import logging
from pathlib import Path

from celery_app import app

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


@app.task(name="tasks.cache_tasks.cleanup_expired_cache")
def cleanup_expired_cache() -> dict:
    """清理过期的 TTS 缓存文件"""
    try:
        cache_dir = ROOT / "data" / "tts_cache"
        if not cache_dir.exists():
            return {"ok": True, "cleaned": 0}

        import time
        max_age_hours = 168  # 7 天
        now = time.time()
        cleaned = 0

        for f in cache_dir.iterdir():
            if f.is_file():
                age_hours = (now - f.stat().st_mtime) / 3600
                if age_hours > max_age_hours:
                    f.unlink()
                    cleaned += 1

        logger.info("清理过期缓存: %d 个文件", cleaned)
        return {"ok": True, "cleaned": cleaned}
    except Exception as e:
        logger.exception("缓存清理失败")
        return {"ok": False, "error": str(e)}


@app.task(name="tasks.cache_tasks.cleanup_old_logs")
def cleanup_old_logs() -> dict:
    """清理过期的日志文件"""
    try:
        import time
        log_dir = ROOT / "logs"
        if not log_dir.exists():
            return {"ok": True, "cleaned": 0}

        max_age_days = 30
        now = time.time()
        cleaned = 0

        for f in log_dir.iterdir():
            if f.is_file() and f.suffix == ".log":
                age_days = (now - f.stat().st_mtime) / 86400
                if age_days > max_age_days:
                    f.unlink()
                    cleaned += 1

        return {"ok": True, "cleaned": cleaned}
    except Exception as e:
        logger.exception("日志清理失败")
        return {"ok": False, "error": str(e)}
