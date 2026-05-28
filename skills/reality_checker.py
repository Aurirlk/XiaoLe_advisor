from typing import Dict


def check_expectation_gap(user_score: int, target_min_score: int, tolerance: int = 8) -> Dict[str, str]:
    gap = user_score - target_min_score
    if gap < -tolerance:
        return {"is_realistic": "false", "reason": f"当前分数低于目标线 {abs(gap)} 分，风险较高。"}
    if gap > 35:
        return {"is_realistic": "warning", "reason": "分数明显高于目标，可能高分低报。"}
    return {"is_realistic": "true", "reason": "目标基本匹配当前分数段。"}
