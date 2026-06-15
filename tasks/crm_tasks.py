"""
CRM 异步任务
"""
from __future__ import annotations

import logging

from celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="tasks.crm_tasks.analyze_profile", bind=True, max_retries=2)
def analyze_profile(self, phone_number: str, profile_data: dict) -> dict:
    """异步分析用户画像，生成标签和推荐"""
    try:
        tags = []

        # 基于画像生成标签
        score = profile_data.get("score", 0)
        if score >= 650:
            tags.append("高分考生")
        elif score >= 550:
            tags.append("中等考生")
        elif score > 0:
            tags.append("需关注考生")

        budget = profile_data.get("budget", 0)
        if budget >= 200000:
            tags.append("高预算")
        elif budget < 50000:
            tags.append("低预算")

        postgraduate = profile_data.get("postgraduate_plan", "")
        if postgraduate == "yes":
            tags.append("有读研意愿")

        return {
            "ok": True,
            "phone_number": phone_number,
            "tags": tags,
        }
    except Exception as exc:
        logger.exception("CRM 画像分析失败: %s", phone_number)
        raise self.retry(exc=exc, countdown=30)


@app.task(name="tasks.crm_tasks.batch_analyze")
def batch_analyze(phone_numbers: list) -> dict:
    """批量分析多个用户画像"""
    results = []
    for phone in phone_numbers:
        try:
            result = analyze_profile.delay(phone, {})
            results.append({"phone": phone, "task_id": result.id})
        except Exception as e:
            results.append({"phone": phone, "error": str(e)})
    return {"ok": True, "submitted": len(results)}
