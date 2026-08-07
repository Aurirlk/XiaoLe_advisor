"""
推荐理由生成器 - 为推荐结果生成清晰的理由说明

基于数据和规则生成有说服力的推荐理由。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RecommendationReason:
    """推荐理由"""
    university: str
    major: str
    reasons: List[str] = field(default_factory=list)
    data_support: Dict[str, Any] = field(default_factory=dict)
    risk_notes: List[str] = field(default_factory=list)
    confidence: float = 0.0


class ReasonGenerator:
    """
    推荐理由生成器
    
    为每个推荐生成清晰、有数据支撑的理由
    """
    
    def __init__(self):
        self._reason_templates = {
            "score_match": "根据{year}年{province}录取数据，{university}的{major}专业最低分为{score}分，与您的分数（{user_score}分）匹配度较高。",
            "rank_match": "您的位次（{rank}位）接近{university}{major}专业的录取位次（{admit_rank}位），录取概率较大。",
            "tier_match": "{university}是{tier}院校，与您的分数层次匹配。",
            "employment": "{major}专业就业前景良好，{employment_info}。",
            "location": "{university}位于{city}，{location_advantage}。",
            "recommendation_rate": "{university}保研率为{rate}%，适合有深造计划的学生。",
        }
    
    def generate_reason(
        self,
        university: str,
        major: str,
        user_profile: Dict[str, Any],
        admission_data: Dict[str, Any],
        employment_data: Optional[Dict[str, Any]] = None,
    ) -> RecommendationReason:
        """
        生成推荐理由
        
        Args:
            university: 院校名称
            major: 专业名称
            user_profile: 用户画像（分数、位次、省份等）
            admission_data: 录取数据
            employment_data: 就业数据（可选）
        
        Returns:
            推荐理由对象
        """
        reasons = []
        data_support = {}
        risk_notes = []
        
        user_score = user_profile.get("score", 0)
        user_rank = user_profile.get("rank", 0)
        province = user_profile.get("province", "")
        
        # 1. 分数匹配理由
        admit_score = admission_data.get("min_score", 0)
        if admit_score and user_score:
            score_diff = user_score - admit_score
            if score_diff >= 0:
                reasons.append(f"您的分数（{user_score}分）高于{university}{major}专业的录取分数线（{admit_score}分），录取把握较大。")
                data_support["score_advantage"] = score_diff
            elif score_diff >= -10:
                reasons.append(f"您的分数（{user_score}分）接近{university}{major}专业的录取分数线（{admit_score}分），属于冲刺范围。")
                risk_notes.append("分数略低于录取线，建议作为冲刺志愿。")
            else:
                risk_notes.append(f"分数差距较大（{abs(score_diff)}分），录取风险较高。")
        
        # 2. 位次匹配理由
        admit_rank = admission_data.get("lowest_rank", 0)
        if admit_rank and user_rank:
            if user_rank <= admit_rank:
                reasons.append(f"您的位次（{user_rank}位）优于录取位次（{admit_rank}位），竞争力较强。")
                data_support["rank_advantage"] = admit_rank - user_rank
        
        # 3. 院校层次理由
        tier = admission_data.get("tier", "")
        if tier:
            reasons.append(f"{university}是{tier}院校，学历认可度高。")
        
        # 4. 就业前景理由
        if employment_data:
            employment_rate = employment_data.get("employment_rate", "")
            avg_salary = employment_data.get("avg_salary", "")
            if employment_rate:
                reasons.append(f"{major}专业就业率为{employment_rate}，就业前景良好。")
            if avg_salary:
                reasons.append(f"该专业毕业生平均薪资为{avg_salary}。")
        
        # 5. 保研率理由
        recommendation_rate = admission_data.get("graduate_recommendation_rate", 0)
        if recommendation_rate and recommendation_rate > 20:
            reasons.append(f"{university}保研率为{recommendation_rate}%，适合有深造计划的学生。")
        
        # 6. 城市优势理由
        city = admission_data.get("city", "")
        if city:
            city_advantages = {
                "北京": "首都资源丰富，实习就业机会多",
                "上海": "经济中心，国际化程度高",
                "广州": "南方经济中心，粤港澳大湾区核心",
                "深圳": "科技创新中心，高新技术企业密集",
                "杭州": "互联网产业发达，创业氛围浓厚",
                "成都": "西南经济中心，生活成本适中",
            }
            advantage = city_advantages.get(city, "城市发展潜力大")
            reasons.append(f"{university}位于{city}，{advantage}。")
        
        # 计算置信度
        confidence = 0.7  # 基础置信度
        if data_support.get("score_advantage", 0) > 20:
            confidence += 0.1
        if data_support.get("rank_advantage", 0) > 1000:
            confidence += 0.1
        if not risk_notes:
            confidence += 0.1
        
        return RecommendationReason(
            university=university,
            major=major,
            reasons=reasons,
            data_support=data_support,
            risk_notes=risk_notes,
            confidence=min(1.0, confidence),
        )
    
    def format_reason_text(self, reason: RecommendationReason) -> str:
        """格式化理由为文本"""
        parts = []
        
        # 推荐理由
        if reason.reasons:
            parts.append("**推荐理由：**")
            for i, r in enumerate(reason.reasons, 1):
                parts.append(f"{i}. {r}")
        
        # 风险提示
        if reason.risk_notes:
            parts.append("\n**风险提示：**")
            for note in reason.risk_notes:
                parts.append(f"⚠️ {note}")
        
        # 置信度
        confidence_text = "高" if reason.confidence >= 0.8 else "中" if reason.confidence >= 0.6 else "低"
        parts.append(f"\n**推荐置信度：** {confidence_text}（{reason.confidence:.0%}）")
        
        return "\n".join(parts)
