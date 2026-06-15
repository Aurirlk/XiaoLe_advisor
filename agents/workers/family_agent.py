"""
家庭融合 Agent — 从学生画像 + 家长画像 + 学科评分融合生成家庭背景

职责：
1. 综合学生和家长信息推断家庭背景
2. 比对学生意向与家长期望的一致性
3. 生成家庭决策建议
4. 写入 family_context 给 synthesis_agent 使用
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.state_schema import (
    GraphState, FamilyContext, ParentProfile, SubjectScores, SUBJECT_NAMES,
)

logger = logging.getLogger(__name__)


def _infer_income_level(budget: int | None, parent_education: str, parent_industry: str) -> str:
    """从预算/家长学历/行业推断收入水平"""
    if budget:
        if budget >= 200000:
            return "high"
        elif budget >= 80000:
            return "medium"
        else:
            return "low"

    # 从行业推断
    high_income_industries = {"金融", "IT", "医疗"}
    medium_income_industries = {"公务员", "教育", "商业", "建筑"}

    if parent_industry in high_income_industries:
        return "medium"  # 默认中等，除非有更明确信号
    elif parent_industry in medium_income_industries:
        return "medium"

    return ""


def _infer_financial_urgency(income_level: str, is_only_child: bool | None, budget: int | None) -> str:
    """推断经济紧迫度"""
    if income_level == "low":
        return "high"
    if budget and budget < 50000:
        return "high"
    if income_level == "high":
        return "none"
    return "moderate"


def _check_parent_student_consensus(
    student_profile: Dict[str, Any],
    parent_profile: ParentProfile,
) -> str:
    """检查家长与学生意向一致性"""
    student_major = student_profile.get("major_name", "")
    parent_expectation = parent_profile.get("expectation", "")

    if not student_major or not parent_expectation:
        return "unknown"

    # 简单规则匹配
    tech_majors = {"计算机", "软件", "人工智能", "电子", "通信", "数据"}
    stable_majors = {"法学", "师范", "会计", "金融"}
    medical_majors = {"医学", "口腔", "临床"}

    student_wants_tech = any(t in student_major for t in tech_majors)
    student_wants_stable = any(t in student_major for t in stable_majors)
    student_wants_medical = any(t in student_major for t in medical_majors)

    parent_wants_stable = "稳定" in parent_expectation or "考公" in parent_expectation
    parent_wants_money = "赚钱" in parent_expectation or "高薪" in parent_expectation

    if student_wants_tech and parent_wants_money:
        return "agree"  # 都追求高薪
    if student_wants_stable and parent_wants_stable:
        return "agree"
    if student_wants_tech and parent_wants_stable:
        return "partial"  # 有分歧
    if student_wants_medical and "稳定" in parent_expectation:
        return "agree"

    return "unknown"


def _analyze_subject_strengths(ss: SubjectScores) -> Dict[str, Any]:
    """分析学科数据，生成综合评估"""
    strong = ss.get("strong_subjects", [])
    weak = ss.get("weak_subjects", [])
    gaokao = ss.get("gaokao_scores", [])
    self_rank = ss.get("self_rank", [])

    analysis = {
        "strong_subjects": strong,
        "weak_subjects": weak,
        "has_detailed_scores": any(s is not None for s in gaokao),
        "subject_count": sum(1 for s in gaokao if s is not None),
    }

    # 计算已知学科总分
    known_scores = [s for s in gaokao if s is not None]
    if known_scores:
        analysis["known_total"] = sum(known_scores)
        analysis["known_avg"] = round(sum(known_scores) / len(known_scores), 1)

    # 强势学科是否与目标专业匹配
    major = ""  # 从外部传入
    if strong and major:
        pass  # 后续可扩展

    return analysis


def family_agent(state: GraphState) -> GraphState:
    """家庭融合 Agent"""
    student_profile = state.get("user_profile", {})
    parent_profile: ParentProfile = state.get("parent_profile", {})
    subject_scores: SubjectScores = state.get("subject_scores", {})

    # 1) 推断家庭背景
    budget = student_profile.get("budget")
    parent_edu = parent_profile.get("education", "")
    parent_industry = parent_profile.get("industry", "")

    income_level = _infer_income_level(budget, parent_edu, parent_industry)

    # 独生子女推断
    is_only = student_profile.get("is_only_child")
    sibling_count = student_profile.get("sibling_count", 0)

    # 家庭资源推断
    family_resources: List[str] = []
    if parent_industry:
        family_resources.append(f"{parent_industry}行业资源")
    if parent_edu in {"本科", "硕士", "博士"}:
        family_resources.append("家庭学历支持")

    # 决策人推断
    decision_weight = parent_profile.get("decision_weight", "")
    if decision_weight == "dominant":
        decision_maker = "parent"
    elif decision_weight == "independent":
        decision_maker = "student"
    else:
        decision_maker = "joint"

    # 地域偏好
    location_pref = student_profile.get("location_preference", "")
    if not location_pref:
        target_city = student_profile.get("target_city", "")
        province = student_profile.get("province", "")
        if target_city and province:
            location_pref = "nearby"  # 有明确目标城市
        else:
            location_pref = ""

    # 经济紧迫度
    financial_urgency = _infer_financial_urgency(income_level, is_only, budget)

    # 家长-学生一致性
    consensus = _check_parent_student_consensus(student_profile, parent_profile)

    # 2) 学科分析
    subject_analysis = _analyze_subject_strengths(subject_scores)

    # 3) 构建家庭背景
    family_context: FamilyContext = {
        "income_level": income_level,
        "annual_budget": budget or 0,
        "total_budget": (budget or 0) * 5 if budget else 0,  # 粗略估算5年
        "is_only_child": is_only if is_only is not None else False,
        "sibling_count": sibling_count,
        "family_resources": family_resources,
        "decision_maker": decision_maker,
        "location_preference": location_pref,
        "financial_urgency": financial_urgency,
        "parent_consensus": consensus,
    }

    return {
        "family_context": family_context,
        "next_node": "synthesis_agent",
    }
