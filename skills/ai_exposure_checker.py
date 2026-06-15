"""
AI任务暴露度评估器 (AI Exposure Checker)

设计理念：
- 评估专业入门岗位被AI替代的风险
- 基于任务分解而非专业标签
- 高风险任务：重复性、规则性、低创造性
- 高壁垒任务：物理场景、法律责任、伦理判断、复杂人际

数据来源：
- 宾大与OpenAI联合论文《GPTs are GPTs》
- 世界经济论坛《Future of Jobs Report 2025》
"""
from __future__ import annotations

from typing import Any, Dict, List


# ── 高风险任务关键词（入门岗位易被替代）──
HIGH_RISK_TASKS = {
    "基础翻译": "机器翻译已接近人类水平",
    "传统财会": "自动化记账、报税软件成熟",
    "初级代码": "Copilot等AI编程助手已能生成基础代码",
    "基础客服": "智能客服已能处理80%常见问题",
    "插画设计": "Midjourney/DALL-E可生成商业插画",
    "数据录入": "OCR+自动化工具已成熟",
    "报表制作": "BI工具可自动生成报表",
    "基础法律文书": "AI可生成标准合同、法律文书",
    "电话销售": "智能外呼系统已普及",
    "简单文案": "GPT可生成营销文案、产品描述",
    "基础设计": "AI设计工具已能完成基础排版",
    "新闻稿撰写": "AI可生成标准新闻稿",
}

# ── 高壁垒任务关键词（不易被替代）──
HIGH_BARRIER_TASKS = {
    "手术操作": "需要物理操作和实时判断",
    "现场勘查": "需要物理场景感知",
    "精密装配": "需要精细动作控制",
    "心理咨询": "需要深度人际信任",
    "复杂谈判": "需要多轮博弈和情感感知",
    "战略决策": "需要全局视野和风险权衡",
    "伦理审查": "需要价值判断和责任承担",
    "跨学科创新": "需要知识整合和原创思维",
    "深度研究": "需要假设生成和实验设计",
    "高级管理": "需要领导力和组织协调",
    "危机处理": "需要快速应变和资源调配",
    "客户关系": "需要长期信任建立",
}

# ── 专业→核心任务映射（预设数据）──
MAJOR_TASK_MAPPING = {
    "计算机科学与技术": {
        "high_risk": ["初级代码", "数据录入", "报表制作"],
        "high_barrier": ["系统架构设计", "技术决策", "跨学科创新"],
        "enhancement": ["AI工具应用", "算法优化", "系统设计"],
    },
    "软件工程": {
        "high_risk": ["初级代码", "基础测试"],
        "high_barrier": ["架构设计", "技术决策", "项目管理"],
        "enhancement": ["AI辅助开发", " DevOps", "安全审计"],
    },
    "人工智能": {
        "high_risk": ["数据标注", "基础模型调用"],
        "high_barrier": ["算法创新", "模型优化", "伦理审查"],
        "enhancement": ["AI研发", "提示工程", "模型部署"],
    },
    "会计学": {
        "high_risk": ["传统财会", "数据录入", "报表制作"],
        "high_barrier": ["审计判断", "税务筹划", "财务分析"],
        "enhancement": ["智能财务系统", "数据分析", "管理会计"],
    },
    "金融学": {
        "high_risk": ["基础客服", "数据录入"],
        "high_barrier": ["风险评估", "投资决策", "客户关系"],
        "enhancement": ["金融科技", "量化分析", "风险管理"],
    },
    "法学": {
        "high_risk": ["基础法律文书", "案例检索"],
        "high_barrier": ["法庭辩论", "法律咨询", "伦理审查"],
        "enhancement": ["法律科技", "合规审查", "知识产权"],
    },
    "临床医学": {
        "high_risk": ["基础问诊记录", "影像初筛"],
        "high_barrier": ["手术操作", "诊断决策", "医患沟通"],
        "enhancement": ["精准医疗", "手术机器人", "AI辅助诊断"],
    },
    "土木工程": {
        "high_risk": ["图纸绘制", "数据录入"],
        "high_barrier": ["现场施工管理", "质量监督", "安全管理"],
        "enhancement": ["BIM技术", "智能建造", "结构优化"],
    },
    "汉语言文学": {
        "high_risk": ["简单文案", "新闻稿撰写", "基础翻译"],
        "high_barrier": ["深度创作", "文化研究", "教育培训"],
        "enhancement": ["内容策划", "新媒体运营", "文化传播"],
    },
    "新闻学": {
        "high_risk": ["新闻稿撰写", "基础采访"],
        "high_barrier": ["深度调查", "舆论引导", "危机公关"],
        "enhancement": ["数据新闻", "融媒体", "国际传播"],
    },
    "英语": {
        "high_risk": ["基础翻译", "简单文案"],
        "high_barrier": ["同声传译", "跨文化沟通", "教育培训"],
        "enhancement": ["本地化", "国际商务", "AI辅助翻译"],
    },
    "数据科学与大数据技术": {
        "high_risk": ["数据录入", "基础分析"],
        "high_barrier": ["模型设计", "业务洞察", "战略决策"],
        "enhancement": ["AI模型", "数据工程", "业务智能"],
    },
    "电子信息工程": {
        "high_risk": ["电路设计辅助", "测试记录"],
        "high_barrier": ["系统设计", "硬件调试", "技术创新"],
        "enhancement": ["芯片设计", "嵌入式AI", "物联网"],
    },
}


def assess_ai_exposure(
    major_name: str,
    custom_tasks: List[str] = None,
) -> Dict[str, Any]:
    """
    评估专业入门岗位的AI暴露度
    
    Args:
        major_name: 专业名称
        custom_tasks: 自定义任务列表（可选，覆盖预设数据）
    
    Returns:
        Dict包含:
        - major: 专业名称
        - ai_exposure_risk: AI暴露度风险分 (0.0-1.0)
        - risk_level: 风险等级 (low/medium/high)
        - high_risk_tasks: 高风险任务列表
        - high_barrier_tasks: 高壁垒任务列表
        - enhancement_suggestions: 能力增强建议
        - career_advice: 职业发展建议
    """
    # 获取专业任务映射
    task_mapping = MAJOR_TASK_MAPPING.get(major_name, {})
    
    # 如果有自定义任务，使用自定义任务
    if custom_tasks:
        high_risk = [t for t in custom_tasks if t in HIGH_RISK_TASKS]
        high_barrier = [t for t in custom_tasks if t in HIGH_BARRIER_TASKS]
        enhancement = []
    else:
        high_risk = task_mapping.get("high_risk", [])
        high_barrier = task_mapping.get("high_barrier", [])
        enhancement = task_mapping.get("enhancement", [])
    
    # 计算风险分数
    risk_score = _calculate_risk_score(high_risk, high_barrier)
    
    # 确定风险等级
    if risk_score > 0.6:
        risk_level = "high"
    elif risk_score > 0.3:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    # 生成职业建议
    career_advice = _generate_career_advice(risk_level, high_risk, high_barrier, enhancement)
    
    return {
        "major": major_name,
        "ai_exposure_risk": round(risk_score, 2),
        "risk_level": risk_level,
        "high_risk_tasks": high_risk,
        "high_risk_explanations": {t: HIGH_RISK_TASKS.get(t, "") for t in high_risk},
        "high_barrier_tasks": high_barrier,
        "high_barrier_explanations": {t: HIGH_BARRIER_TASKS.get(t, "") for t in high_barrier},
        "enhancement_suggestions": enhancement,
        "career_advice": career_advice,
    }


def _calculate_risk_score(high_risk: List[str], high_barrier: List[str]) -> float:
    """计算AI暴露度风险分数"""
    if not high_risk and not high_barrier:
        return 0.5  # 未知专业默认中等风险
    
    # 高风险任务权重
    risk_weight = 0.0
    for task in high_risk:
        if task in HIGH_RISK_TASKS:
            risk_weight += 0.15
    
    # 高壁垒任务降低风险
    barrier_reduction = 0.0
    for task in high_barrier:
        if task in HIGH_BARRIER_TASKS:
            barrier_reduction += 0.1
    
    # 计算最终分数
    score = min(1.0, max(0.0, 0.3 + risk_weight - barrier_reduction))
    
    return score


def _generate_career_advice(
    risk_level: str,
    high_risk: List[str],
    high_barrier: List[str],
    enhancement: List[str],
) -> str:
    """生成职业发展建议"""
    if risk_level == "high":
        advice = "该专业入门岗位AI暴露度较高，建议："
        if enhancement:
            advice += f"\n- 重点发展{enhancement[0]}等复合能力"
        advice += "\n- 关注行业头部企业的校招要求"
        advice += "\n- 考虑读研提升竞争力"
        if high_barrier:
            advice += f"\n- 向{high_barrier[0]}等高壁垒方向发展"
    elif risk_level == "medium":
        advice = "该专业AI暴露度中等，建议："
        advice += "\n- 掌握AI工具提升效率"
        if enhancement:
            advice += f"\n- 发展{enhancement[0]}等差异化能力"
        advice += "\n- 关注行业技术变革动态"
    else:
        advice = "该专业AI暴露度较低，专业壁垒较强，建议："
        advice += "\n- 深耕专业核心能力"
        advice += "\n- 建立行业人脉和资源"
        if enhancement:
            advice += f"\n- 结合{enhancement[0]}提升竞争力"
    
    return advice


def get_major_exposure_summary(major_name: str) -> str:
    """获取专业AI暴露度摘要（用于前端展示）"""
    result = assess_ai_exposure(major_name)
    
    risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    emoji = risk_emoji.get(result["risk_level"], "⚪")
    
    summary = f"{emoji} {major_name} AI暴露度: {result['ai_exposure_risk']:.0%} ({result['risk_level']})"
    
    if result["high_risk_tasks"]:
        summary += f"\n高风险任务: {', '.join(result['high_risk_tasks'][:2])}"
    
    return summary


def batch_assess(majors: List[str]) -> Dict[str, Dict]:
    """批量评估多个专业"""
    results = {}
    for major in majors:
        results[major] = assess_ai_exposure(major)
    return results
