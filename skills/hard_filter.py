"""
硬编码条件判断模块 (Hard Filter)

设计理念：
- 将条件判断下沉到Python，减少Token消耗
- 所有规则硬编码，禁止大模型推理
- 结果直接注入Prompt，大模型只需翻译

规则类型：
1. 分数过滤：根据分数/位次筛选可报院校
2. 专业过滤：根据黑名单排除专业
3. 地域过滤：根据限制筛选城市/校区
4. 预算过滤：根据学费筛选院校类型
5. 体检过滤：根据体检限制排除专业
"""
from __future__ import annotations

from typing import Any, Dict, List, Set


# ═══════════════════════════════════════════════════════════════
# 专业黑名单映射（排雷问卷 → 专业关键词）
# ═══════════════════════════════════════════════════════════════

BLACKLIST_MAJOR_KEYWORDS = {
    "土木建筑": ["土木工程", "建筑学", "城市规划", "给排水", "道路桥梁", "工程管理"],
    "生化环材": ["生物工程", "生物技术", "化学工程", "化学", "环境工程", "环境科学", "材料科学", "材料工程"],
    "医学护理": ["临床医学", "口腔医学", "护理学", "药学", "中医学", "医学检验"],
    "军事公安": ["军事", "公安", "警校", "消防", "武警"],
    "艺术设计": ["美术", "音乐", "设计", "艺术", "动画", "影视"],
    "计算机IT": ["计算机", "软件", "人工智能", "数据科学", "网络工程", "信息安全"],
    "人文社科": ["哲学", "历史", "文学", "中文", "新闻", "传播", "社会学"],
    "金融经济": ["金融", "经济", "会计", "财务", "投资", "证券"],
    "师范教育": ["师范", "教育学", "学前教育", "小学教育"],
}

# ═══════════════════════════════════════════════════════════════
# 体检限制 → 专业排除映射
# ═══════════════════════════════════════════════════════════════

HEALTH_RESTRICTION_MAJOR_EXCLUSION = {
    "色弱": ["化学", "化工", "材料", "医学", "临床", "口腔", "药学", "美术", "绘画", "设计"],
    "色盲": ["化学", "化工", "美术", "绘画", "设计", "艺术", "医学", "临床"],
    "近视": ["公安", "军事", "警校", "消防", "航海", "飞行", "刑事科学技术"],
    "听力障碍": ["外语", "英语", "日语", "音乐", "学前教育", "护理", "医学"],
    "嗅觉障碍": ["医学", "化工", "食品", "酿酒", "香料"],
    "肢体残疾": ["体育", "军事", "公安", "舞蹈"],
}

# ═══════════════════════════════════════════════════════════════
# 偏远校区识别关键词
# ═══════════════════════════════════════════════════════════════

REMOTE_CAMPUS_KEYWORDS = [
    "威海", "珠海", "秦皇岛", "丹东", "延边", "昌吉",
    "克拉玛依", "石河子", "塔里木", "偏远", "新校区",
]


class HardFilter:
    """硬编码条件过滤器"""
    
    def __init__(self):
        pass
    
    def filter_by_blacklist(
        self,
        recommendations: List[Dict[str, Any]],
        blacklist: List[str],
    ) -> List[Dict[str, Any]]:
        """
        根据黑名单过滤专业
        
        Args:
            recommendations: 推荐列表
            blacklist: 排除的专业类别列表
        
        Returns:
            过滤后的推荐列表
        """
        if not blacklist:
            return recommendations
        
        # 收集所有需要排除的专业关键词
        exclude_keywords = set()
        for category in blacklist:
            keywords = BLACKLIST_MAJOR_KEYWORDS.get(category, [])
            exclude_keywords.update(keywords)
        
        if not exclude_keywords:
            return recommendations
        
        # 过滤
        filtered = []
        excluded = []
        for rec in recommendations:
            major = rec.get("major_name", "")
            is_excluded = False
            for kw in exclude_keywords:
                if kw in major:
                    is_excluded = True
                    excluded.append(rec)
                    break
            if not is_excluded:
                filtered.append(rec)
        
        return filtered
    
    def filter_by_health(
        self,
        recommendations: List[Dict[str, Any]],
        health_restrictions: List[str],
    ) -> List[Dict[str, Any]]:
        """
        根据体检限制过滤专业
        """
        if not health_restrictions or "无限制" in health_restrictions:
            return recommendations
        
        # 收集所有需要排除的专业关键词
        exclude_keywords = set()
        for restriction in health_restrictions:
            keywords = HEALTH_RESTRICTION_MAJOR_EXCLUSION.get(restriction, [])
            exclude_keywords.update(keywords)
        
        if not exclude_keywords:
            return recommendations
        
        # 过滤
        filtered = []
        for rec in recommendations:
            major = rec.get("major_name", "")
            is_excluded = False
            for kw in exclude_keywords:
                if kw in major:
                    is_excluded = True
                    break
            if not is_excluded:
                filtered.append(rec)
        
        return filtered
    
    def filter_by_budget(
        self,
        recommendations: List[Dict[str, Any]],
        budget_ceiling: int,
    ) -> List[Dict[str, Any]]:
        """
        根据预算过滤院校类型
        """
        if budget_ceiling >= 100000:
            return recommendations  # 不限
        
        filtered = []
        for rec in recommendations:
            tier = rec.get("tier", "") or rec.get("level", "")
            tuition = rec.get("tuition_fee", 5000)
            
            # 民办/中外合作学费通常较高
            if "民办" in str(tier) and tuition > budget_ceiling:
                continue
            if "中外合作" in str(tier) and tuition > budget_ceiling:
                continue
            
            filtered.append(rec)
        
        return filtered
    
    def filter_by_location(
        self,
        recommendations: List[Dict[str, Any]],
        location_limit: str,
        user_province: str = "",
    ) -> List[Dict[str, Any]]:
        """
        根据地域限制过滤
        """
        if location_limit == "不限" or location_limit == "不限地域":
            return recommendations
        
        if location_limit == "必须省内":
            # 只保留省内院校（需要大学有省份信息）
            return recommendations  # 需要从图谱获取省份信息
        
        return recommendations
    
    def filter_remote_campus(
        self,
        recommendations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        识别并标记偏远校区
        """
        for rec in recommendations:
            university = rec.get("university_name", "")
            campus_warning = ""
            
            for keyword in REMOTE_CAMPUS_KEYWORDS:
                if keyword in university:
                    campus_warning = f"⚠️ 注意：{university}可能有偏远校区，请确认具体就读校区"
                    break
            
            if campus_warning:
                rec["campus_warning"] = campus_warning
        
        return recommendations
    
    def apply_all_filters(
        self,
        recommendations: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        应用所有过滤器
        
        Returns:
            filtered: 过滤后的推荐列表
            warnings: 风险提示列表
            excluded_count: 被排除的数量
        """
        original_count = len(recommendations)
        warnings = []
        
        # 1. 黑名单过滤
        blacklist = user_profile.get("blacklist_majors", [])
        recommendations = self.filter_by_blacklist(recommendations, blacklist)
        
        # 2. 体检过滤
        health = user_profile.get("health_restrictions", [])
        recommendations = self.filter_by_health(recommendations, health)
        
        # 3. 预算过滤
        budget = user_profile.get("budget_ceiling", 0) or user_profile.get("budget", 0)
        if budget:
            recommendations = self.filter_by_budget(recommendations, budget)
        
        # 4. 地域过滤
        location_limit = user_profile.get("location_limit", "不限")
        province = user_profile.get("province", "")
        recommendations = self.filter_by_location(recommendations, location_limit, province)
        
        # 5. 偏远校区标记
        recommendations = self.filter_remote_campus(recommendations)
        
        # 生成警告
        excluded_count = original_count - len(recommendations)
        if excluded_count > 0:
            warnings.append(f"已根据你的限制条件排除 {excluded_count} 个选项")
        
        # 检查过滤后是否为空
        if not recommendations:
            warnings.append("⚠️ 根据你的限制条件，没有找到匹配的选项，建议放宽部分条件")
        
        return {
            "filtered": recommendations,
            "warnings": warnings,
            "excluded_count": excluded_count,
        }
    
    def generate_filter_summary(self, user_profile: Dict[str, Any]) -> str:
        """生成过滤条件摘要"""
        parts = []
        
        blacklist = user_profile.get("blacklist_majors", [])
        if blacklist:
            parts.append(f"❌ 排除专业：{', '.join(blacklist)}")
        
        health = user_profile.get("health_restrictions", [])
        if health and "无限制" not in health:
            parts.append(f"🏥 体检限制：{', '.join(health)}")
        
        budget = user_profile.get("budget_ceiling", 0)
        if budget:
            parts.append(f"💰 预算上限：{budget}元/年")
        
        location = user_profile.get("location_limit", "")
        if location:
            parts.append(f"📍 地域限制：{location}")
        
        if not parts:
            return "无特殊限制条件"
        
        return "过滤条件：\n" + "\n".join(parts)


# 单例实例
_hard_filter: HardFilter = None


def get_hard_filter() -> HardFilter:
    """获取硬编码过滤器单例"""
    global _hard_filter
    if _hard_filter is None:
        _hard_filter = HardFilter()
    return _hard_filter
