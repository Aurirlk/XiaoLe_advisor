from typing import Any, Dict, List, Optional


HIGH_RISK_MAJORS = {"生物工程", "化学工程", "环境工程", "材料科学与工程"}


def assess_major_risk(
    major: str,
    university_tier: str,
    *,
    user_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    返回可直接注入 synthesis 的风控结构。
    - 兼容旧字段：is_risk/reason
    - 新增字段：risk_level/warnings/must_say
    """
    warnings: List[str] = []
    must_say: List[str] = []
    risk_level = "low"

    if major in HIGH_RISK_MAJORS and university_tier not in {"985", "顶尖211"}:
        risk_level = "high"
        warnings.append("生化环材且院校层次不高，就业风险偏高。")
        must_say.append("别上头，这类组合对普通家庭不友好，除非你有明确读研读博路径和资源。")

    profile = user_profile or {}
    budget = profile.get("budget") or profile.get("family_budget")
    if isinstance(budget, (int, float)) and budget > 0 and major in {"临床医学", "口腔医学"} and budget < 80000:
        risk_level = "high"
        warnings.append("医学培养周期长、隐性成本高，家庭预算偏紧会非常吃力。")
        must_say.append("先把钱算明白：学医不是热爱就能扛住的，是时间+成本的双重消耗。")

    if not warnings:
        return {
            "is_risk": "false",
            "reason": "当前组合未触发硬规则风险。",
            "risk_level": risk_level,
            "warnings": [],
            "must_say": "",
        }

    return {
        "is_risk": "true",
        "reason": warnings[0],
        "risk_level": risk_level,
        "warnings": warnings,
        "must_say": " ".join(must_say).strip(),
    }
