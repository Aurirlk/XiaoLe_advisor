"""
数据缺失场景定义 — 从 harness.py 拆分

职责：存放所有数据缺失场景的配置
"""
from __future__ import annotations

from typing import Any, Dict, List


# ── 数据缺失场景定义 ──
MISSING_DATA_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "admission_score": {
        "trigger": "查询某校/某专业录取分数线但本地无数据",
        "prompt": "我暂时没有这所学校的录取数据。你可以：\n1. 上传该校的录取成绩单截图\n2. 上传招生简章PDF\n3. 提供一分一段表让我查询",
        "accept_types": ["image", "pdf", "csv"],
        "parse_strategy": "admission_data",
    },
    "score_segment": {
        "trigger": "查询一分一段表但无最新数据",
        "prompt": "我暂时没有最新的一分一段表数据。请上传省考试院发布的一分一段表（图片或CSV均可），我会自动解析并更新数据库。",
        "accept_types": ["image", "csv", "excel"],
        "parse_strategy": "score_segment",
    },
    "admission_plan": {
        "trigger": "查询招生计划但无数据",
        "prompt": "我暂时没有该校的招生计划数据。请上传招生计划表（PDF或图片），我会解析后为你分析。",
        "accept_types": ["image", "pdf"],
        "parse_strategy": "admission_plan",
    },
    "employment_data": {
        "trigger": "查询就业数据但无统计",
        "prompt": "我暂时没有该专业的详细就业数据。你可以：\n1. 上传学校发布的就业质量报告\n2. 上传招聘网站的薪资截图\n我会帮你分析就业前景。",
        "accept_types": ["image", "pdf"],
        "parse_strategy": "employment_data",
    },
    "university_detail": {
        "trigger": "查询院校详情但信息不全",
        "prompt": "这所院校的信息不够完整。请上传院校官网截图或招生简章，我来补充信息。",
        "accept_types": ["image"],
        "parse_strategy": "university_detail",
    },
    "batch_cutoff": {
        "trigger": "查询批次线但无数据",
        "prompt": "我暂时没有该省份的批次线数据。请上传省考试院公布的批次控制线（图片或文档），我会更新到数据库。",
        "accept_types": ["image", "pdf", "csv"],
        "parse_strategy": "batch_cutoff",
    },
}


def match_scenario(query: str) -> Dict[str, Any] | None:
    """根据查询内容匹配数据缺失场景"""
    query_lower = query.lower()

    # 分数线查询
    score_keywords = ["分数线", "录取分", "最低分", "投档线", "调档线"]
    if any(kw in query for kw in score_keywords):
        return MISSING_DATA_SCENARIOS["admission_score"]

    # 一分一段表查询
    segment_keywords = ["一分一段", "位次表", "成绩分段", "排名表"]
    if any(kw in query for kw in segment_keywords):
        return MISSING_DATA_SCENARIOS["score_segment"]

    # 招生计划查询
    plan_keywords = ["招生计划", "招生人数", "计划数", "招生名额"]
    if any(kw in query for kw in plan_keywords):
        return MISSING_DATA_SCENARIOS["admission_plan"]

    # 就业数据查询
    employment_keywords = ["就业率", "薪资", "工资", "就业去向", "就业质量"]
    if any(kw in query for kw in employment_keywords):
        return MISSING_DATA_SCENARIOS["employment_data"]

    # 院校详情查询
    university_keywords = ["院校介绍", "学校简介", "办学特色", "校园环境"]
    if any(kw in query for kw in university_keywords):
        return MISSING_DATA_SCENARIOS["university_detail"]

    # 批次线查询
    batch_keywords = ["批次线", "控制线", "一本线", "二本线", "本科线", "专科线"]
    if any(kw in query for kw in batch_keywords):
        return MISSING_DATA_SCENARIOS["batch_cutoff"]

    return None
