"""
Celery 应用配置

使用 Redis 作为 broker 和 result backend。
启动 worker: celery -A celery_app worker --loglevel=info -Q default,rag,crm
"""
from __future__ import annotations

import os
from pathlib import Path

from celery import Celery

ROOT = Path(__file__).resolve().parent

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "1")
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

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

    # 任务超时
    task_soft_time_limit=300,
    task_time_limit=600,

    # 结果过期
    result_expires=3600,

    # 定时任务（可选）
    beat_schedule={
        "cleanup-expired-cache": {
            "task": "tasks.cache_tasks.cleanup_expired_cache",
            "schedule": 3600.0,  # 每小时执行一次
        },
        "daily-cost-report": {
            "task": "tasks.cost_tasks.generate_daily_report",
            "schedule": 86400.0,  # 每天执行一次
        },
    },
)

# 自动发现任务模块
app.autodiscover_tasks(["tasks"])
