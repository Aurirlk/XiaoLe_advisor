from __future__ import annotations

from typing import Any, Dict, List, Tuple


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

