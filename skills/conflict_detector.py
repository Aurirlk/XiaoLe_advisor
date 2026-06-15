"""
家庭冲突检测器 (Conflict Detector)

设计理念：
- 双向约束矩阵：家长硬约束 vs 学生软偏好
- 冲突显性化：检测到冲突时强制触发家庭讨论
- 熔断机制：关键冲突未解决前，不给出最终推荐

数据来源：
- parent_constraints: 家长硬约束（预算、公办、体检限制等）
- student_preferences: 学生软偏好（城市、专业、风险偏好等）
"""
from __future__ import annotations

from typing import Any, Dict, List


def detect_family_conflict(
    parent_constraints: Dict[str, Any],
    student_preferences: Dict[str, Any],
    score: int,
    rank: int,
) -> Dict[str, Any]:
    """
    家庭期望与现实冲突检测
    
    Args:
        parent_constraints: 家长硬约束
        student_preferences: 学生软偏好
        score: 高考分数
        rank: 全省位次
    
    Returns:
        has_conflict: 是否存在冲突
        conflicts: 冲突列表
        requires_arbitration: 是否需要家庭仲裁（存在critical冲突）
        resolution_prompt: 注入SynthesisAgent的冲突解决提示词
    """
    conflicts = []
    
    # ── 冲突1：预算 vs 公办要求 ──
    budget_ceiling = parent_constraints.get("budget_ceiling", 0)
    must_public = parent_constraints.get("must_public", False)
    
    if must_public and budget_ceiling > 0 and budget_ceiling < 20000:
        if score < 500:  # 低分段公办竞争激烈
            conflicts.append({
                "type": "budget_vs_public",
                "severity": "critical",
                "message": f"家长要求公办但预算仅{budget_ceiling}元/年，该分数段公办竞争激烈，可能滑档到民办",
                "advice": "建议降低公办要求或增加预算，或考虑高学费民办院校的奖学金",
            })
    
    # ── 冲突2：城市偏好 vs 分数现实 ──
    high_competition_cities = ["北京", "上海", "深圳", "杭州", "南京", "广州"]
    preferred_cities = student_preferences.get("preferred_cities", [])
    
    for city in preferred_cities:
        if city in high_competition_cities and rank > 50000:
            conflicts.append({
                "type": "ambition_vs_reality",
                "severity": "high",
                "message": f"目标城市{city}竞争激烈，当前位次{rank}录取难度大",
                "advice": f"建议考虑{city}周边城市（如北京→天津/河北，上海→苏州/杭州）",
            })
    
    # ── 冲突3：专业偏好 vs 家长禁止 ──
    blacklist = set(parent_constraints.get("blacklist_majors", []))
    preferred_majors = set(student_preferences.get("preferred_majors", []))
    overlap = blacklist & preferred_majors
    
    if overlap:
        conflicts.append({
            "type": "preference_conflict",
            "severity": "critical",
            "message": f"家长禁止的专业与学生偏好重叠：{', '.join(overlap)}",
            "advice": "建议家庭成员公开讨论禁止原因，明确是就业前景、学费还是其他因素",
        })
    
    # ── 冲突4：体检限制 vs 目标专业 ──
    health_restrictions = parent_constraints.get("health_restrictions", [])
    health_major_conflicts = {
        "色弱": ["化学", "医学", "临床", "药学", "美术", "绘画", "设计"],
        "色盲": ["化学", "医学", "美术", "绘画", "设计", "艺术"],
        "近视": ["公安", "军事", "航海", "飞行", "消防"],
        "听力障碍": ["外语", "音乐", "医学", "护理", "学前教育"],
        "嗅觉障碍": ["医学", "化工", "食品"],
    }
    
    preferred_majors_str = str(preferred_majors)
    for issue in health_restrictions:
        for major_keyword in health_major_conflicts.get(issue, []):
            if major_keyword in preferred_majors_str:
                conflicts.append({
                    "type": "health_vs_major",
                    "severity": "critical",
                    "message": f"考生有{issue}限制，{major_keyword}类专业存在退档风险",
                    "advice": "请核实招生章程中对该体检项目的具体要求，部分院校有特殊规定",
                })
                break  # 每个健康问题只报一次
    
    # ── 冲突5：预算紧张 ──
    if budget_ceiling > 0 and budget_ceiling < 15000:
        conflicts.append({
            "type": "budget_tight",
            "severity": "warning",
            "message": f"年度预算仅{budget_ceiling}元，中外合作/民办院校难以承担",
            "advice": "建议重点关注公办院校普通专业，或申请助学贷款",
        })
    
    # ── 冲突6：读研意愿 vs 专业要求 ──
    postgraduate_plan = student_preferences.get("postgraduate_plan", "")
    major_name = student_preferences.get("preferred_majors", [""])[0] if student_preferences.get("preferred_majors") else ""
    
    # 需要读研的专业
    postgrad_required = ["临床医学", "口腔医学", "法学", "生物", "化学", "材料", "环境"]
    if postgraduate_plan == "no" and any(kw in major_name for kw in postgrad_required):
        conflicts.append({
            "type": "postgrad_mismatch",
            "severity": "high",
            "message": f"{major_name}通常需要读研深造，但学生表示不打算读研",
            "advice": "建议重新评估读研意愿，或考虑该专业的本科直接就业方向",
        })
    
    # ── 冲突7：学生风险偏好 vs 家长保守 ──
    risk_tolerance = student_preferences.get("risk_tolerance", "")
    if risk_tolerance == "aggressive" and parent_constraints.get("must_safe", False):
        conflicts.append({
            "type": "risk_conflict",
            "severity": "warning",
            "message": "学生倾向激进冲刺，但家长要求稳妥保底",
            "advice": "建议在志愿表中合理搭配冲、稳、保比例（如2:5:3）",
        })
    
    # 生成冲突解决提示词
    resolution_prompt = _generate_resolution_prompt(conflicts) if conflicts else ""
    
    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts,
        "requires_arbitration": any(c["severity"] == "critical" for c in conflicts),
        "resolution_prompt": resolution_prompt,
    }


def _generate_resolution_prompt(conflicts: List[Dict]) -> str:
    """生成冲突解决提示词，注入SynthesisAgent"""
    if not conflicts:
        return ""
    
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "【⚠️ 家庭冲突检测报告 - 必须显性化处理】",
        "",
        "以下冲突已被系统检测到，必须向用户明确指出并引导讨论：",
        "",
    ]
    
    for i, conflict in enumerate(conflicts, 1):
        severity = conflict.get("severity", "warning")
        if severity == "critical":
            emoji = "🔴"
        elif severity == "high":
            emoji = "🟡"
        else:
            emoji = "⚪"
        
        lines.append(f"{emoji} 冲突{i}: {conflict['message']}")
        lines.append(f"   建议: {conflict['advice']}")
        lines.append("")
    
    lines.extend([
        "━━━━ 强制输出要求 ━━━━",
        "1. 必须在回复开头列出上述冲突，不能回避或弱化",
        "2. 必须引导家庭成员公开讨论并达成共识",
        "3. 在关键冲突解决前，不得给出最终志愿推荐",
        "4. 使用确定性语言：'这个矛盾必须解决'而不是'建议考虑'",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ])
    
    return "\n".join(lines)


def get_conflict_summary(conflicts: List[Dict]) -> str:
    """获取冲突摘要（用于前端展示）"""
    if not conflicts:
        return "无冲突检测"
    
    critical = sum(1 for c in conflicts if c.get("severity") == "critical")
    high = sum(1 for c in conflicts if c.get("severity") == "high")
    warning = sum(1 for c in conflicts if c.get("severity") == "warning")
    
    parts = []
    if critical > 0:
        parts.append(f"{critical}个严重冲突")
    if high > 0:
        parts.append(f"{high}个重要冲突")
    if warning > 0:
        parts.append(f"{warning}个警告")
    
    return f"检测到{', '.join(parts)}，需要家庭讨论"
