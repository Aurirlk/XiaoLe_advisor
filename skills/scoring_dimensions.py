"""
评分维度定义 — 从 quantitative_scorer.py 拆分

职责：存放评分维度配置和各维度评分逻辑
"""
from __future__ import annotations

from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════════
# 评分维度定义（满分100分）
# ═══════════════════════════════════════════════════════════════

SCORING_DIMENSIONS = {
    "admission_risk": {
        "name": "录取风险",
        "max_score": 25,
        "description": "位次匹配度、往年波动幅度、招生计划调整、调剂概率",
    },
    "major_fit": {
        "name": "专业适配",
        "max_score": 20,
        "description": "学生兴趣与核心能力是否支撑课程难度，读研意愿匹配度",
    },
    "career_prospect": {
        "name": "就业与钱景",
        "max_score": 18,
        "description": "初级岗位市场容量、薪资分布区间、行业生命周期、入行门槛",
    },
    "city_industry": {
        "name": "城市与产业",
        "max_score": 12,
        "description": "周边实体产业集群密度、实习便利度、生活成本",
    },
    "school_platform": {
        "name": "学校平台",
        "max_score": 10,
        "description": "学科声誉、行政层级、保研比例、转专业门槛",
    },
    "ai_exposure": {
        "name": "AI暴露与增强",
        "max_score": 10,
        "description": "入门工作被技术替代概率、与数字化工具结合潜力",
    },
    "family_consensus": {
        "name": "家庭共识",
        "max_score": 5,
        "description": "学生与家长利益诉求是否公开透明、冲突是否显性化",
    },
}


def score_admission_risk(
    recommendation: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """录取风险评分（满分25分）"""
    max_score = 25
    score = 0
    reasons = []
    
    user_score = user_profile.get("score", 0) or user_profile.get("extracted_score", 0)
    min_score = recommendation.get("min_score", 0)
    
    if user_score > 0 and min_score > 0:
        gap = user_score - min_score
        
        if gap >= 30:
            score = 25
            reasons.append(f"分数超线{gap}分，录取把握极大")
        elif gap >= 10:
            score = 20
            reasons.append(f"分数超线{gap}分，录取较稳")
        elif gap >= 0:
            score = 15
            reasons.append(f"分数压线{gap}分，有一定风险")
        elif gap >= -10:
            score = 10
            reasons.append(f"分数低于线{abs(gap)}分，属于冲刺")
        else:
            score = 5
            reasons.append(f"分数低于线{abs(gap)}分，风险较大")
    else:
        score = 12
        reasons.append("分数线数据待补充")
    
    return {"score": score, "max": max_score, "reasons": reasons}


def score_major_fit(
    recommendation: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """专业适配评分（满分20分）"""
    max_score = 20
    score = 10  # 默认中等
    reasons = []
    
    major = recommendation.get("major_name", "")
    interests = user_profile.get("interests", [])
    strong_subjects = user_profile.get("strong_subjects", [])
    
    # 兴趣匹配
    if interests:
        interest_match = any(i.lower() in major.lower() for i in interests)
        if interest_match:
            score += 5
            reasons.append("专业与兴趣匹配")
    
    # 学科匹配
    if strong_subjects:
        subject_match = any(s in major for s in strong_subjects)
        if subject_match:
            score += 3
            reasons.append("专业与强势学科匹配")
    
    # 考研意愿
    postgrad = user_profile.get("postgraduate_plan", "")
    if postgrad == "yes":
        score += 2
        reasons.append("有读研意愿，适合深造型专业")
    
    return {"score": min(max_score, score), "max": max_score, "reasons": reasons}


def score_career_prospect(
    recommendation: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """就业与钱景评分（满分18分）"""
    max_score = 18
    score = 9  # 默认中等
    reasons = []
    
    major = recommendation.get("major_name", "")
    
    # 高薪专业
    high_salary_majors = ["计算机", "软件", "人工智能", "金融", "电子信息", "通信"]
    if any(m in major for m in high_salary_majors):
        score = 15
        reasons.append("高薪行业相关专业")
    
    # 稳定专业
    stable_majors = ["医学", "师范", "法学", "会计"]
    if any(m in major for m in stable_majors):
        score = 12
        reasons.append("就业稳定性较好")
    
    # 就业率
    employment_rate = recommendation.get("employment_rate", 0)
    if employment_rate > 0.9:
        score = min(max_score, score + 3)
        reasons.append(f"就业率{employment_rate*100:.0f}%")
    
    return {"score": min(max_score, score), "max": max_score, "reasons": reasons}


def score_city_industry(
    recommendation: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """城市与产业评分（满分12分）"""
    max_score = 12
    score = 0
    reasons = []
    
    university = recommendation.get("university_name", "")
    preferred_cities = user_profile.get("preferred_cities", [])
    
    tier1_cities = ["北京", "上海", "广州", "深圳"]
    tier15_cities = ["杭州", "南京", "成都", "武汉", "西安", "苏州"]
    
    for city in tier1_cities:
        if city in university:
            score = 12
            reasons.append(f"位于{city}，产业资源丰富")
            break
    
    if score == 0:
        for city in tier15_cities:
            if city in university:
                score = 10
                reasons.append(f"位于{city}，产业发展良好")
                break
    
    if score == 0:
        score = 7
        reasons.append("城市信息待补充")
    
    if any(c in str(preferred_cities) for c in ["不限", "都可以"]):
        score = min(12, score + 2)
        reasons.append("符合不限城市偏好")
    
    return {"score": score, "max": max_score, "reasons": reasons}


def score_school_platform(
    recommendation: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """学校平台评分（满分10分）"""
    max_score = 10
    score = 0
    reasons = []
    
    tier = recommendation.get("tier", "") or recommendation.get("level", "")
    
    if "985" in tier or "顶尖" in tier:
        score = 10
        reasons.append("985/顶尖院校，平台价值高")
    elif "211" in tier:
        score = 8
        reasons.append("211院校，平台价值较高")
    elif "双一流" in tier:
        score = 7
        reasons.append("双一流院校")
    elif "一本" in tier or "普通" in tier:
        score = 5
        reasons.append("普通一本院校")
    elif "民办" in tier:
        score = 3
        reasons.append("民办院校")
    else:
        score = 5
        reasons.append("院校层次待确认")
    
    return {"score": score, "max": max_score, "reasons": reasons}


def score_ai_exposure(
    recommendation: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """AI暴露与增强评分（满分10分）"""
    max_score = 10
    score = 0
    reasons = []
    
    major = recommendation.get("major_name", "")
    
    try:
        from skills.ai_exposure_checker import assess_ai_exposure
        exposure = assess_ai_exposure(major)
        
        risk = exposure.get("ai_exposure_risk", 0.5)
        barrier_tasks = exposure.get("high_barrier_tasks", [])
        
        score = int((1 - risk) * 7)
        
        if barrier_tasks:
            score += 3
            reasons.append(f"存在高壁垒任务：{barrier_tasks[0]}")
        else:
            reasons.append("AI暴露度中等")
        
    except Exception:
        score = 5
        reasons.append("AI暴露度数据待补充")
    
    return {"score": min(max_score, score), "max": max_score, "reasons": reasons}


def score_family_consensus(
    recommendation: Dict[str, Any],
    user_profile: Dict[str, Any],
    family_context: Dict[str, Any] = None,
    audit_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """家庭共识评分（满分5分）"""
    max_score = 5
    score = 0
    reasons = []
    
    if audit_result:
        if audit_result.get("passed", True):
            score += 3
            reasons.append("审计通过，无重大冲突")
        else:
            score += 1
            reasons.append("存在审计问题，需家庭讨论")
    
    if family_context:
        consensus = family_context.get("parent_consensus", "")
        if consensus == "agree":
            score += 2
            reasons.append("家长与学生意见一致")
        elif consensus == "partial":
            score += 1
            reasons.append("家长与学生意见部分一致")
        else:
            reasons.append("家长与学生意见待确认")
    
    if score == 0:
        score = 3
        reasons.append("家庭共识待评估")
    
    return {"score": min(max_score, score), "max": max_score, "reasons": reasons}
