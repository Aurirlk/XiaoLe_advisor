"""
成本追踪异步任务
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from celery_app import app

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
CST = timezone(timedelta(hours=8))


@app.task(name="tasks.cost_tasks.generate_daily_report")
def generate_daily_report() -> dict:
    """生成每日成本报告"""
    try:
        from core.cost_tracker import CostTracker
        tracker = CostTracker()
        daily = tracker.get_daily_usage()
        monthly = tracker.get_monthly_usage()

        report = {
            "report_type": "daily",
            "generated_at": datetime.now(CST).isoformat(),
            "daily": daily,
            "monthly_summary": {
                "total_cost_yuan": monthly["total_cost_yuan"],
                "request_count": monthly["request_count"],
                "daily_limit": monthly["daily_limit"],
                "monthly_limit": monthly["monthly_limit"],
            },
        }

        report_path = ROOT / "data" / "eval" / "cost_report_daily.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info("日成本报告已生成: %s", report_path)
        return {"ok": True, "path": str(report_path)}
    except Exception as e:
        logger.exception("日成本报告生成失败")
        return {"ok": False, "error": str(e)}


@app.task(name="tasks.cost_tasks.check_cost_limit")
def check_cost_limit() -> dict:
    """检查成本是否超限"""
    try:
        from core.cost_tracker import CostTracker
        tracker = CostTracker()
        ok, reason = tracker.check_limit()
        if not ok:
            logger.warning("成本超限: %s", reason)
        return {"ok": ok, "reason": reason}
    except Exception as e:
        logger.exception("成本限额检查失败")
        return {"ok": False, "error": str(e)}
