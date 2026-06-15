"""
量化评分框架 (Quantitative Scorer)

设计理念：
- 100分制量化评分框架
- 7个维度：录取风险、专业适配、就业钱景、城市产业、学校平台、AI暴露、家庭共识
- 让家庭成员把各自在意的点摊在台面上进行博弈
- 打分不是为了算出绝对正确答案，而是为了决策透明化
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


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


class QuantitativeScorer:
    """量化评分引擎"""
    
    def __init__(self):
        self.dimensions = SCORING_DIMENSIONS
    
    def score_recommendation(
        self,
        recommendation: Dict[str, Any],
        user_profile: Dict[str, Any],
        family_context: Dict[str, Any] = None,
        audit_result: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        对单个推荐进行量化评分
        
        Args:
            recommendation: 推荐信息（大学、专业、分数线等）
            user_profile: 用户画像
            family_context: 家庭背景
            audit_result: 审计结果
        
        Returns:
            评分结果
        """
        scores = {}
        
        # 1. 录取风险评分
        scores["admission_risk"] = self._score_admission_risk(recommendation, user_profile)
        
        # 2. 专业适配评分
        scores["major_fit"] = self._score_major_fit(recommendation, user_profile)
        
        # 3. 就业与钱景评分
        scores["career_prospect"] = self._score_career_prospect(recommendation, user_profile)
        
        # 4. 城市与产业评分
        scores["city_industry"] = self._score_city_industry(recommendation, user_profile)
        
        # 5. 学校平台评分
        scores["school_platform"] = self._score_school_platform(recommendation, user_profile)
        
        # 6. AI暴露与增强评分
        scores["ai_exposure"] = self._score_ai_exposure(recommendation, user_profile)
        
        # 7. 家庭共识评分
        scores["family_consensus"] = self._score_family_consensus(
            recommendation, user_profile, family_context, audit_result
        )
        
        # 计算总分
        total_score = sum(s["score"] for s in scores.values())
        max_possible = sum(d["max_score"] for d in self.dimensions.values())
        
        # 生成等级
        if total_score >= 85:
            grade = "A"
            recommendation_text = "强烈推荐"
        elif total_score >= 70:
            grade = "B"
            recommendation_text = "推荐"
        elif total_score >= 55:
            grade = "C"
            recommendation_text = "可以考虑"
        elif total_score >= 40:
            grade = "D"
            recommendation_text = "谨慎选择"
        else:
            grade = "E"
            recommendation_text = "不推荐"
        
        return {
            "scores": scores,
            "total_score": total_score,
            "max_possible": max_possible,
            "grade": grade,
            "recommendation": recommendation_text,
        }
    
    def _score_admission_risk(
        self, 
        recommendation: Dict[str, Any], 
        user_profile: Dict[str, Any]
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
                # 分数明显高于最低分，录取把握大
                score = 25
                reasons.append(f"分数超线{gap}分，录取把握极大")
            elif gap >= 10:
                score = 20
                reasons.append(f"分数超线{gap}分，录取较稳")
            elif gap >= 0:
                score = 15
                reasons.append(f"分数刚好压线，有一定风险")
            elif gap >= -10:
                score = 8
                reasons.append(f"分数低于最低线{abs(gap)}分，风险较高")
            else:
                score = 3
                reasons.append(f"分数低于最低线{abs(gap)}分，风险极高")
        else:
            score = 12  # 默认中等
            reasons.append("数据不足，无法精确评估")
        
        return {"score": score, "max": max_score, "reasons": reasons}
    
    def _score_major_fit(
        self, 
        recommendation: Dict[str, Any], 
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """专业适配评分（满分20分）"""
        max_score = 20
        score = 0
        reasons = []
        
        major = recommendation.get("major_name", "")
        preferred_majors = user_profile.get("preferred_majors", [])
        strong_subjects = user_profile.get("strong_subjects", [])
        weak_subjects = user_profile.get("weak_subjects", [])
        
        # 兴趣匹配
        if major in preferred_majors:
            score += 8
            reasons.append("专业与兴趣高度匹配")
        elif any(m in major for m in preferred_majors):
            score += 5
            reasons.append("专业与兴趣部分匹配")
        else:
            score += 2
            reasons.append("专业与兴趣匹配度低")
        
        # 学科匹配（简单规则）
        stem_majors = ["计算机", "软件", "电子", "机械", "数学", "物理", "化学", "生物"]
        humanities_majors = ["法学", "文学", "新闻", "历史", "哲学", "教育"]
        
        if any(m in major for m in stem_majors):
            if "物理" in strong_subjects or "数学" in strong_subjects:
                score += 7
                reasons.append("学科基础扎实")
            elif "物理" in weak_subjects or "数学" in weak_subjects:
                score += 2
                reasons.append("学科基础薄弱")
            else:
                score += 5
        elif any(m in major for m in humanities_majors):
            if "语文" in strong_subjects or "英语" in strong_subjects:
                score += 7
                reasons.append("学科基础扎实")
            else:
                score += 5
        else:
            score += 4
        
        # 读研意愿匹配
        postgrad_plan = user_profile.get("postgraduate_plan", "")
        postgrad_required = ["临床医学", "口腔医学", "法学", "生物", "化学", "材料"]
        if postgrad_plan == "no" and any(p in major for p in postgrad_required):
            score -= 3
            reasons.append("不读研与专业要求不匹配")
        elif postgrad_plan in ["yes", "must"] and any(p in major for p in postgrad_required):
            score += 5
            reasons.append("读研意愿与专业要求匹配")
        
        return {"score": max(0, min(max_score, score)), "max": max_score, "reasons": reasons}
    
    def _score_career_prospect(
        self, 
        recommendation: Dict[str, Any], 
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """就业与钱景评分（满分18分）"""
        max_score = 18
        score = 0
        reasons = []
        
        major = recommendation.get("major_name", "")
        
        # 基于专业类型的预设评分
        high_prospect_majors = {
            "计算机科学与技术": 16, "软件工程": 16, "人工智能": 17,
            "数据科学与大数据技术": 16, "电子信息工程": 14, "通信工程": 14,
            "临床医学": 15, "口腔医学": 16, "法学": 14, "金融学": 13,
            "会计学": 12, "电气工程及其自动化": 13,
        }
        
        medium_prospect_majors = {
            "机械工程": 11, "土木工程": 9, "建筑学": 10,
            "汉语言文学": 10, "英语": 10, "新闻学": 9,
            "数学与应用数学": 12, "物理学": 11,
        }
        
        low_prospect_majors = {
            "生物工程": 7, "化学工程": 7, "环境工程": 7,
            "材料科学与工程": 7, "历史学": 8, "哲学": 8,
        }
        
        for key, val in high_prospect_majors.items():
            if key in major:
                score = val
                reasons.append("就业前景良好")
                break
        
        if score == 0:
            for key, val in medium_prospect_majors.items():
                if key in major:
                    score = val
                    reasons.append("就业前景中等")
                    break
        
        if score == 0:
            for key, val in low_prospect_majors.items():
                if key in major:
                    score = val
                    reasons.append("就业前景一般")
                    break
        
        if score == 0:
            score = 10  # 默认中等
            reasons.append("数据不足，默认中等评分")
        
        return {"score": score, "max": max_score, "reasons": reasons}
    
    def _score_city_industry(
        self, 
        recommendation: Dict[str, Any], 
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """城市与产业评分（满分12分）"""
        max_score = 12
        score = 0
        reasons = []
        
        university = recommendation.get("university_name", "")
        preferred_cities = user_profile.get("preferred_cities", [])
        
        # 一线城市加分
        tier1_cities = ["北京", "上海", "广州", "深圳"]
        tier15_cities = ["杭州", "南京", "成都", "武汉", "西安", "苏州"]
        
        # 简单匹配（实际应从数据库获取大学所在城市）
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
            score = 7  # 默认
            reasons.append("城市信息待补充")
        
        # 匹配偏好城市
        if any(c in str(preferred_cities) for c in ["不限", "都可以"]):
            score = min(12, score + 2)
            reasons.append("符合不限城市偏好")
        
        return {"score": score, "max": max_score, "reasons": reasons}
    
    def _score_school_platform(
        self, 
        recommendation: Dict[str, Any], 
        user_profile: Dict[str, Any]
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
    
    def _score_ai_exposure(
        self, 
        recommendation: Dict[str, Any], 
        user_profile: Dict[str, Any]
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
            
            # 风险越低，分数越高
            score = int((1 - risk) * 7)
            
            # 有高壁垒任务加分
            if barrier_tasks:
                score += 3
                reasons.append(f"存在高壁垒任务：{barrier_tasks[0]}")
            else:
                reasons.append("AI暴露度中等")
            
        except Exception:
            score = 5
            reasons.append("AI暴露度数据待补充")
        
        return {"score": min(max_score, score), "max": max_score, "reasons": reasons}
    
    def _score_family_consensus(
        self,
        recommendation: Dict[str, Any],
        user_profile: Dict[str, Any],
        family_context: Dict[str, Any] = None,
        audit_result: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """家庭共识评分（满分5分）"""
        max_score = 5
        score = 0
        reasons = []
        
        # 基于审计结果
        if audit_result:
            if audit_result.get("passed", True):
                score += 3
                reasons.append("审计通过，无重大冲突")
            else:
                score += 1
                reasons.append("存在审计问题，需家庭讨论")
        
        # 基于家庭背景
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
            score = 3  # 默认
            reasons.append("家庭共识待评估")
        
        return {"score": min(max_score, score), "max": max_score, "reasons": reasons}
    
    def batch_score(
        self,
        recommendations: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        family_context: Dict[str, Any] = None,
        audit_result: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """批量评分并排序"""
        scored = []
        for rec in recommendations:
            result = self.score_recommendation(rec, user_profile, family_context, audit_result)
            scored.append({**rec, "scoring": result})
        
        # 按总分降序排序
        scored.sort(key=lambda x: x["scoring"]["total_score"], reverse=True)
        
        return scored
    
    def generate_scoring_report(self, scored_recommendations: List[Dict[str, Any]]) -> str:
        """生成评分报告"""
        lines = [
            "📊 志愿填报量化评分报告",
            "=" * 40,
            "",
        ]
        
        for i, rec in enumerate(scored_recommendations[:5], 1):
            scoring = rec.get("scoring", {})
            uni = rec.get("university_name", rec.get("university", ""))
            major = rec.get("major_name", rec.get("major", ""))
            total = scoring.get("total_score", 0)
            grade = scoring.get("grade", "?")
            rec_text = scoring.get("recommendation", "")
            
            lines.append(f"{i}. {uni} - {major}")
            lines.append(f"   总分: {total}/100 | 等级: {grade} | {rec_text}")
            
            # 显示各维度分数
            scores = scoring.get("scores", {})
            for dim_key, dim_info in self.dimensions.items():
                dim_score = scores.get(dim_key, {})
                if dim_score:
                    lines.append(f"   - {dim_info['name']}: {dim_score.get('score', 0)}/{dim_info['max_score']}")
            lines.append("")
        
        return "\n".join(lines)


# 单例实例
_scorer: Optional[QuantitativeScorer] = None


def get_quantitative_scorer() -> QuantitativeScorer:
    """获取量化评分器单例"""
    global _scorer
    if _scorer is None:
        _scorer = QuantitativeScorer()
    return _scorer
