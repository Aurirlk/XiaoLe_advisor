from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


def build_soul_questions(user_profile: Dict[str, Any]) -> List[str]:
    """
    "灵魂追问"清单：缺什么就问什么。
    这些问题用于 synthesis 阶段生成下一步行动，不直接做路由。
    """
    if user_profile is None:
        user_profile = {}
    questions: List[str] = []

    if not user_profile.get("province"):
        questions.append("你哪个省的？（不同省录取难度完全不一样）")
    if not user_profile.get("subject_type"):
        questions.append("你是物理类还是历史类？（新高考选科决定可报范围）")
    if not user_profile.get("score") and not user_profile.get("rank"):
        questions.append("你多少分/全省位次多少？（没有这个我就是瞎扯）")
    if not user_profile.get("major_name"):
        questions.append("你想冲哪个专业？还是你更看重就业，专业可调整？")
    if not user_profile.get("target_city"):
        questions.append("你想去哪座城市发展？（城市比专业更影响机会）")
    if not user_profile.get("budget"):
        questions.append("家里一年能给你拿多少钱？（别用爱好挑战现实）")
    if user_profile.get("postgraduate_plan") is None:
        questions.append("你能不能接受读研/读博？（有些赛道不读就是死）")

    return questions


async def generate_progressive_questions(
    user_profile: Dict[str, Any],
    scene_type: str,
    path_type: Optional[str] = None,
    rag_tools=None,
    graph_rag=None,
    crm_manager=None,
) -> List[Dict[str, Any]]:
    """
    生成渐进式引导问题（集成 RAG/图谱/CRM）
    
    返回格式：
    [
        {
            "field": "province",
            "question": "你哪个省的？",
            "options": ["广东", "北京", ...],  # 可选
            "source": "base|rag|graph|crm",
            "priority": 1,
        }
    ]
    """
    questions: List[Dict[str, Any]] = []
    
    # 1. 基础问题
    base_qs = build_soul_questions(user_profile)
    for q in base_qs:
        questions.append({
            "field": _extract_field_from_question(q),
            "question": q,
            "source": "base",
            "priority": 1,
        })
    
    # 2. RAG 增强问题
    if rag_tools:
        try:
            rag_qs = await _generate_from_rag(user_profile, scene_type, rag_tools)
            questions.extend(rag_qs)
        except Exception as e:
            logger.warning(f"RAG 渐进询问生成失败: {e}")
    
    # 3. 图谱增强问题
    if graph_rag:
        try:
            graph_qs = await _generate_from_graph(user_profile, scene_type, graph_rag)
            questions.extend(graph_qs)
        except Exception as e:
            logger.warning(f"图谱渐进询问生成失败: {e}")
    
    # 4. CRM 增强问题
    if crm_manager:
        try:
            crm_qs = await _generate_from_crm(user_profile, scene_type, path_type, crm_manager)
            questions.extend(crm_qs)
        except Exception as e:
            logger.warning(f"CRM 渐进询问生成失败: {e}")
    
    # 去重并排序
    return _deduplicate_and_rank(questions)


def _extract_field_from_question(question: str) -> str:
    """从问题中提取字段名"""
    field_mapping = {
        "省": "province",
        "物理": "subject_type",
        "历史": "subject_type",
        "分": "score",
        "位次": "rank",
        "专业": "major_name",
        "城市": "target_city",
        "钱": "budget",
        "预算": "budget",
        "考研": "postgraduate_plan",
        "读研": "postgraduate_plan",
    }
    
    for keyword, field in field_mapping.items():
        if keyword in question:
            return field
    
    return "unknown"


async def _generate_from_rag(
    user_profile: Dict[str, Any],
    scene_type: str,
    rag_tools,
) -> List[Dict[str, Any]]:
    """基于 RAG 经验库生成问题"""
    questions: List[Dict[str, Any]] = []
    
    # 如果没有专业偏好，检索相关经验
    if not user_profile.get("major_preferences"):
        docs = rag_tools.search("专业选择 建议", top_k=3)
        if docs:
            context = "\n".join([d.get("text", "") for d in docs])
            questions.append({
                "field": "major_preferences",
                "question": f"关于专业选择，你可能需要知道：{context[:100]}...",
                "source": "rag",
                "priority": 2,
            })
    
    return questions


async def _generate_from_graph(
    user_profile: Dict[str, Any],
    scene_type: str,
    graph_rag,
) -> List[Dict[str, Any]]:
    """基于知识图谱生成问题"""
    questions: List[Dict[str, Any]] = []
    
    # 如果有兴趣但没有专业偏好，查询关联专业
    interests = user_profile.get("interests") or []
    if interests and not user_profile.get("major_preferences"):
        for interest in interests[:3]:
            try:
                related = graph_rag.query(
                    f"MATCH (i:Interest {{name: $name}})-[:RELATED]->(m:Major) RETURN m.name LIMIT 5",
                    {"name": interest}
                )
                if related:
                    major_names = [r.get("m.name", "") for r in related[:5] if r.get("m.name")]
                    if major_names:
                        questions.append({
                            "field": "major_preferences",
                            "question": f"你对{interest}相关专业感兴趣吗？比如：{', '.join(major_names[:3])}",
                            "options": major_names,
                            "source": "graph",
                            "priority": 2,
                        })
            except Exception as e:
                logger.warning(f"图谱查询失败: {e}")
    
    return questions


async def _generate_from_crm(
    user_profile: Dict[str, Any],
    scene_type: str,
    path_type: Optional[str],
    crm_manager,
) -> List[Dict[str, Any]]:
    """基于 CRM 历史生成问题"""
    questions: List[Dict[str, Any]] = []
    
    try:
        # 查找相似用户
        similar_users = await crm_manager.find_similar_profiles(user_profile, limit=5)
        
        if similar_users and not path_type:
            # 统计相似用户的路径选择
            postgrad_count = sum(
                1 for u in similar_users 
                if u.get("postgraduate_plan") == "yes"
            )
            
            if postgrad_count > 0:
                total = len(similar_users)
                questions.append({
                    "field": "career_path",
                    "question": f"和你情况相似的考生中，{postgrad_count}/{total} 选择了考研。你更倾向哪个方向？",
                    "options": ["考研", "就业", "还没想好"],
                    "source": "crm",
                    "priority": 2,
                })
    except Exception as e:
        logger.warning(f"CRM 查询失败: {e}")
    
    return questions


def _deduplicate_and_rank(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去重并排序"""
    seen_fields = set()
    unique_questions = []
    
    # 按优先级排序
    sorted_questions = sorted(questions, key=lambda q: q.get("priority", 99))
    
    for q in sorted_questions:
        field = q.get("field", "unknown")
        if field not in seen_fields:
            seen_fields.add(field)
            unique_questions.append(q)
    
    return unique_questions[:10]  # 最多 10 个问题


def ten_year_pressure_test(user_profile: Dict[str, Any]) -> str:
    if user_profile is None:
        user_profile = {}
    target = user_profile.get("target_city") or "你想去的城市"
    return (
        f"我就问你一句狠的：你能不能接受你孩子工作10年后，"
        f"在{target}拿着普通工资，看着当年分数不如他的人反而混得更好？"
        "能接受你就按兴趣慢慢来；不能接受，就别端着，按就业和平台选。"
    )


def city_priority_hint(user_profile: Dict[str, Any]) -> str:
    if user_profile is None:
        user_profile = {}
    city = user_profile.get("target_city")
    if city:
        return f"城市优先：你既然想去{city}，就别光盯着专业名气，先看平台和落脚机会。"
    return "城市优先：能去更强的城市就别自我感动，机会密度决定上限。"


def summarize_decision_hints(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    if user_profile is None:
        user_profile = {}
    questions = build_soul_questions(user_profile)
    hints: List[Tuple[str, str]] = [
        ("city_priority", city_priority_hint(user_profile)),
        ("ten_year_test", ten_year_pressure_test(user_profile)),
    ]
    return {
        "soul_questions": questions,
        "hints": [{"type": t, "text": text} for t, text in hints],
    }

