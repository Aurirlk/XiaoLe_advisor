"""
Celery 应用配置

使用 Redis 作为 broker 和 result backend。
启动 worker: celery -A celery_app worker --loglevel=info -Q default,rag,crm
"""
from __future__ import annotations

import os
from pathlib import Path

from celery import Celery
from celery.schedules import crontab

ROOT = Path(__file__).resolve().parent

# Redis 配置（P1-21：broker 与 result backend 分开 DB，避免相互干扰）
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
BROKER_DB = os.getenv("REDIS_DB", "1")
RESULT_DB = os.getenv("REDIS_RESULT_DB", "2")
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{BROKER_DB}"
RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{RESULT_DB}"

# 创建 Celery 应用
app = Celery(
    "xiaole_ai",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# 配置
app.conf.update(
    # 序列化
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务路由
    task_routes={
        "tasks.rag_tasks.*": {"queue": "rag"},
        "tasks.crm_tasks.*": {"queue": "crm"},
        "tasks.cost_tasks.*": {"queue": "default"},
        "tasks.cache_tasks.*": {"queue": "default"},
    },

    # 默认队列
    task_default_queue="default",

    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,

    # 可靠性（P1-21）：任务确认延迟到执行完成后；worker 崩溃/被杀时任务重投，
    # 而非静默丢失。配合 Redis broker 的 visibility_timeout 使用。
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,

    # 任务超时
    task_soft_time_limit=300,
    task_time_limit=600,
    task_acks_on_failure_or_timeout=False,

    # 结果过期
    result_expires=3600,
    result_backend_transport_options={"visibility_timeout": 3600},

    # 定时任务（P1-21：用 crontab 而非浮点秒，避免"每天"相位随启动漂移）
    beat_schedule={
        "cleanup-expired-cache": {
            "task": "tasks.cache_tasks.cleanup_expired_cache",
            "schedule": crontab(minute=0),  # 每小时整点执行
        },
        "daily-cost-report": {
            "task": "tasks.cost_tasks.generate_daily_report",
            "schedule": crontab(hour=0, minute=5),  # 每天 00:05 执行
        },
    },
)

# 自动发现任务模块
app.autodiscover_tasks(["tasks"])
