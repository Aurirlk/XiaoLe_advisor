"""
反方审计引擎 (Red Team Auditor / Devil's Advocate Engine)

设计理念来源于投研分析：
- 绝不顺着用户的思路说好话
- 专门负责"挑刺"和寻找方案中的致命硬伤
- 作为硬约束层，阻断大模型的"讨好型"幻觉

架构位置：
Worker Nodes → RedTeamAuditor (找漏洞) → SynthesisGuard (防端水) → 输出

审计视角：
1. 招生办视角：体检退档、分数不足、单科限制
2. HR/就业视角：预算击穿、专业天坑、AI替代
3. 家长视角：隐性成本、培养周期、就业风险
4. 学生视角：兴趣错配、能力不足、发展空间
5. 应届生视角：真实就业、薪资预期、发展路径
"""
from __future__ import annotations

from typing import Any, Dict, List


class RedTeamAuditor:
    """
    反方审计引擎
    
    在SynthesisAgent之前，用极其严苛的条件对推荐列表进行"压力测试"。
    该模块完全基于纯Python实现，作为硬约束层，不依赖LLM。
    """
    
    def __init__(self):
        # ── 红线规则库 ──
        
        # 高成本专业（学费或隐性成本极高）
        self.high_cost_majors = [
            "中外合作", "艺术", "飞行", "音乐", "美术",
            "临床医学(长学制)", "口腔医学", "建筑学(5年)",
        ]
        
        # 体检严格专业
        self.physical_strict_majors = [
            "公安", "军事", "航海", "飞行", "消防", "警察",
        ]
        
        # AI高风险任务（入门岗位易被替代）
        self.ai_high_risk_tasks = [
            "基础翻译", "传统财会", "初级代码", "基础客服",
            "插画设计", "数据录入", "报表制作", "基础法律文书",
            "电话销售", "简单文案",
        ]
        
        # 高壁垒任务（不易被替代）
        self.high_barrier_tasks = [
            "手术操作", "现场勘查", "精密装配", "心理咨询",
            "复杂谈判", "战略决策", "伦理审查", "跨学科创新",
            "深度研究", "高级管理",
        ]
        
        # 天坑专业（需要特别提醒）
        self.pitfall_majors = {
            "生物工程": "本科就业困难，需读研读博",
            "化学工程": "工作环境差，薪资偏低",
            "环境工程": "行业周期性强，就业面窄",
            "材料科学与工程": "传统材料方向就业困难",
            "土木工程": "行业下行，工作强度大",
            "建筑学": "房地产行业收缩",
        }
    
    def audit_recommendations(
        self, 
        user_profile: Dict[str, Any], 
        raw_recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        对推荐列表进行致命性审查
        
        Args:
            user_profile: CRM用户画像
                - budget: 预算
                - health_restrictions: 体检限制
                - score: 分数
                - rank: 位次
                - postgraduate_plan: 读研意愿
            raw_recommendations: 初步选出的大学与专业列表
                - university_name/university: 大学名称
                - major_name/major: 专业名称
                - min_score: 最低分
                - tier/level: 院校层次
        
        Returns:
            passed: 是否通过审计
            audit_summary: 审计报告文本（可直接注入LLM）
            audit_details: 详细审计结果
        """
        audit_reports = []
        is_critical_fail = False
        
        # 提取约束条件
        budget_limit = user_profile.get("budget") or user_profile.get("family_budget") or 999999
        health_issues = user_profile.get("health_restrictions", [])
        user_score = user_profile.get("score", 0)
        user_rank = user_profile.get("rank", 0)
        postgraduate_plan = user_profile.get("postgraduate_plan", "")
        
        for rec in raw_recommendations:
            major = rec.get("major_name") or rec.get("major", "")
            university = rec.get("university_name") or rec.get("university", "")
            min_score = rec.get("min_score", 0)
            tier = rec.get("tier") or rec.get("level", "")
            tuition_fee = rec.get("tuition_fee", 5000)  # 默认5000
            
            flaws = []
            
            # ══════════════════════════════════════════
            # 1. 预算硬伤审计（家长/财务视角）
            # ══════════════════════════════════════════
            if tuition_fee > budget_limit:
                flaws.append(f"[预算击穿] 该专业学费 {tuition_fee}/年，超出家庭预算上限 {budget_limit}/年！")
                is_critical_fail = True
            
            for hc_major in self.high_cost_majors:
                if hc_major in major and budget_limit < 30000:
                    flaws.append(f"[隐性破产风险] '{major}'类专业不仅学费高，后期培养/出国/实习成本极大")
            
            # ══════════════════════════════════════════
            # 2. 体检/硬性门槛审计（招生办视角）
            # ══════════════════════════════════════════
            if health_issues:
                for strict_major in self.physical_strict_majors:
                    if strict_major in major:
                        flaws.append(f"[退档红线] 考生有 {health_issues} 记录，'{major}'属于极高体检退档风险专业")
                        is_critical_fail = True
            
            # ══════════════════════════════════════════
            # 3. 分数风险审计（录取概率视角）
            # ══════════════════════════════════════════
            if user_score > 0 and min_score > 0:
                if user_score < min_score - 30:
                    flaws.append(f"[分数严重不足] 考生{user_score}分低于该校最低分{min_score}分达{min_score - user_score}分")
                    is_critical_fail = True
                elif user_score < min_score - 10:
                    flaws.append(f"[分数边缘] 考生{user_score}分低于该校最低分{min_score}分，录取风险较高")
            
            # ══════════════════════════════════════════
            # 4. AI暴露度审计（未来职场视角）
            # ══════════════════════════════════════════
            for ai_risk in self.ai_high_risk_tasks:
                if ai_risk in major:
                    flaws.append(f"[技术淘汰警告] '{major}'对应的初级岗位任务暴露度过高，极易被AI大模型取代")
                    break
            
            # ══════════════════════════════════════════
            # 5. 天坑专业审计（就业前景视角）
            # ══════════════════════════════════════════
            for pitfall, reason in self.pitfall_majors.items():
                if pitfall in major:
                    flaws.append(f"[天坑警告] '{major}'：{reason}")
                    break
            
            # ══════════════════════════════════════════
            # 6. 读研意愿审计（培养路径视角）
            # ══════════════════════════════════════════
            postgrad_required = ["临床医学", "口腔医学", "法学", "生物", "化学", "材料", "环境"]
            if postgraduate_plan == "no" and any(kw in major for kw in postgrad_required):
                flaws.append(f"[读研不匹配] '{major}'通常需要读研深造，但学生表示不打算读研")
            
            # ══════════════════════════════════════════
            # 7. 院校层次审计（平台价值视角）
            # ══════════════════════════════════════════
            if tier and "民办" in str(tier) and budget_limit > 30000:
                flaws.append(f"[性价比警告] 民办院校学费高但平台价值有限，建议优先考虑公办")
            
            # 汇总该推荐的缺陷
            if flaws:
                audit_reports.append({
                    "target": f"{university} - {major}",
                    "university": university,
                    "major": major,
                    "fatal_flaws": flaws,
                })
        
        # ══════════════════════════════════════════
        # 构建审计报告
        # ══════════════════════════════════════════
        if audit_reports:
            report_text = "⚠️【反方审计员强制警告】：目前的推荐列表存在以下致命硬伤，必须向用户揭示：\n\n"
            
            for report in audit_reports:
                report_text += f"→ 针对 {report['target']}:\n"
                for flaw in report['fatal_flaws']:
                    report_text += f"   ❌ {flaw}\n"
                report_text += "\n"
            
            report_text += "【审计结论】以上问题必须在最终推荐中明确告知用户，不得回避或弱化！\n"
            report_text += "【审计原则】我们宁可让用户失望，也不能让用户后悔。"
            
            return {
                "passed": not is_critical_fail,
                "audit_summary": report_text,
                "audit_details": audit_reports,
            }
        else:
            return {
                "passed": True,
                "audit_summary": "✅ 审计通过，未发现明显的硬性逻辑冲突或退档风险。",
                "audit_details": [],
            }
    
    def get_audit_stats(self, audit_result: Dict[str, Any]) -> str:
        """获取审计统计摘要"""
        details = audit_result.get("audit_details", [])
        if not details:
            return "审计通过"
        
        total_flaws = sum(len(r.get("fatal_flaws", [])) for r in details)
        affected_majors = len(details)
        
        return f"发现{total_flaws}个问题，涉及{affected_majors}个专业推荐"


# ── 便捷函数 ──

def quick_audit(
    user_profile: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
) -> str:
    """快速审计，返回审计报告文本"""
    auditor = RedTeamAuditor()
    result = auditor.audit_recommendations(user_profile, recommendations)
    return result["audit_summary"]


def has_critical_issues(
    user_profile: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
) -> bool:
    """检查是否存在严重问题"""
    auditor = RedTeamAuditor()
    result = auditor.audit_recommendations(user_profile, recommendations)
    return not result["passed"]
