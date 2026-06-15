"""
家长画像提取 Agent — 从家长对话中提取家长信息

独立于学生画像，专门处理家长端的对话输入。
提取：角色、职业、行业、学历、期望、担忧、决策权重等。
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List

from core.state_schema import GraphState, ParentProfile, ProfileChange

# ── 家长角色 ──
_ROLE_KEYWORDS = {
    "father": ["爸爸", "父亲", "爸", "爹", "老爸"],
    "mother": ["妈妈", "母亲", "妈", "娘", "老妈"],
    "grandfather": ["爷爷", "外公", "姥爷", "祖父", "外祖父"],
    "grandmother": ["奶奶", "外婆", "姥姥", "祖母", "外祖母"],
}

# ── 行业 ──
_INDUSTRY_KEYWORDS = {
    "金融": ["银行", "证券", "基金", "保险", "金融", "会计", "财务"],
    "医疗": ["医院", "医生", "护士", "医药", "医疗", "卫生", "诊所"],
    "教育": ["老师", "教师", "学校", "教育", "培训", "校长"],
    "IT": ["IT", "互联网", "程序员", "软件", "计算机", "科技", "华为", "腾讯", "阿里"],
    "公务员": ["公务员", "政府", "机关", "事业单位", "体制内", "公检法"],
    "制造": ["工厂", "制造", "工程", "机械", "车间"],
    "建筑": ["建筑", "房地产", "装修", "施工"],
    "商业": ["做生意", "经商", "老板", "开店", "公司"],
    "农业": ["种地", "农业", "养殖", "农场"],
    "军人": ["当兵", "军人", "部队", "军官", "军"],
    "自由职业": ["自由职业", "个体", "灵活就业"],
}

# ── 学历 ──
_EDUCATION_KEYWORDS = {
    "博士": ["博士", "博导"],
    "硕士": ["硕士", "研究生", "考研"],
    "本科": ["本科", "大学毕业", "学士", "大本"],
    "大专": ["大专", "专科", "高职"],
    "高中": ["高中", "中专", "职高", "初中毕业"],
}

# ── 期望 ──
_EXPECTATION_KEYWORDS = {
    "考公": ["考公", "公务员", "编制", "体制内", "稳定"],
    "赚钱": ["赚钱", "高薪", "收入", "挣钱", "发财"],
    "学术": ["学术", "科研", "读博", "教授", "研究"],
    "稳定": ["稳定", "铁饭碗", "不要太大压力"],
    "创业": ["创业", "自己干", "做生意"],
    "技术": ["技术", "工程师", "码农"],
    "出国": ["出国", "留学", "移民", "海外"],
}

# ── 担忧 ──
_CONCERN_KEYWORDS = {
    "就业": ["就业", "找不到工作", "失业", "工作难找"],
    "安全": ["安全", "危险", "治安"],
    "距离": ["太远", "离家", "回家不方便", "距离"],
    "费用": ["费用", "贵", "花销", "负担不起"],
    "健康": ["健康", "压力大", "太累", "身体"],
    "婚恋": ["找对象", "结婚", "单身"],
    "竞争": ["竞争", "卷", "内卷", "压力"],
}

# ── 决策风格 ──
_DOMINANT = ["我说了算", "必须听我的", "我决定", "不同意也得同意"]
_CONSULTATIVE = ["商量", "一起决定", "尊重孩子", "看孩子意愿", "孩子喜欢就好"]
_INDEPENDENT = ["孩子自己决定", "我不干涉", "随他"]


def _extract_parent_from_query(query: str) -> Dict[str, Any]:
    """从家长对话中提取画像字段"""
    extracted: Dict[str, Any] = {}

    # 角色
    for role, keywords in _ROLE_KEYWORDS.items():
        if any(kw in query for kw in keywords):
            extracted["role"] = role
            break

    # 行业
    for industry, keywords in _INDUSTRY_KEYWORDS.items():
        if any(kw in query for kw in keywords):
            extracted["industry"] = industry
            break

    # 学历
    for edu, keywords in _EDUCATION_KEYWORDS.items():
        if any(kw in query for kw in keywords):
            extracted["education"] = edu
            break

    # 期望
    expectations = []
    for exp, keywords in _EXPECTATION_KEYWORDS.items():
        if any(kw in query for kw in keywords):
            expectations.append(exp)
    if expectations:
        extracted["expectation"] = "、".join(expectations)

    # 担忧
    concerns = []
    for concern, keywords in _CONCERN_KEYWORDS.items():
        if any(kw in query for kw in keywords):
            concerns.append(concern)
    if concerns:
        extracted["concerns"] = concerns

    # 决策风格
    if any(w in query for w in _DOMINANT):
        extracted["decision_weight"] = "dominant"
    elif any(w in query for w in _CONSULTATIVE):
        extracted["decision_weight"] = "consultative"
    elif any(w in query for w in _INDEPENDENT):
        extracted["decision_weight"] = "independent"

    # 预算（家长也可能提供预算信息）
    budget_match = re.search(
        r"(?:预算|一年能拿|能出|花费|学费|生活费)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(万|w|W|千|k|K)?", query
    )
    if budget_match:
        num = float(budget_match.group(1))
        unit = (budget_match.group(2) or "").lower()
        if unit in {"万", "w"}:
            extracted["_budget"] = int(num * 10000)
        elif unit in {"千", "k"}:
            extracted["_budget"] = int(num * 1000)
        else:
            extracted["_budget"] = int(num)

    # 手机号
    phone_match = re.search(r"1[3-9]\d{9}", query)
    if phone_match:
        extracted["phone"] = phone_match.group()

    return extracted


def _merge_parent_profile(
    new_fields: Dict[str, Any],
    existing: Dict[str, Any],
    query: str,
) -> tuple[Dict[str, Any], List[ProfileChange]]:
    merged = dict(existing)
    changes: List[ProfileChange] = []
    tracked_keys = {"role", "occupation", "industry", "education", "expectation", "decision_weight"}

    for key, new_val in new_fields.items():
        if key.startswith("_"):
            continue
        old_val = merged.get(key)
        if new_val != old_val:
            merged[key] = new_val
            if key in tracked_keys:
                changes.append(ProfileChange(
                    field=f"parent.{key}",
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if not isinstance(new_val, list) else str(new_val),
                    ts=datetime.now(timezone.utc).isoformat(),
                    trigger_query=query,
                ))

    # 担忧累积
    new_concerns = new_fields.get("concerns", [])
    if new_concerns:
        existing_concerns = set(merged.get("concerns") or [])
        existing_concerns.update(new_concerns)
        merged["concerns"] = sorted(existing_concerns)

    return merged, changes


def parent_agent(state: GraphState) -> GraphState:
    """家长画像提取 Agent"""
    query = state.get("user_query", "")

    # 1) 提取新字段
    new_fields = _extract_parent_from_query(query)

    # 2) 合并到已有家长画像
    existing = dict(state.get("parent_profile") or {})
    merged, changes = _merge_parent_profile(new_fields, existing, query)

    # 3) 变更历史
    history: List[ProfileChange] = list(state.get("profile_history") or [])
    history.extend(changes)

    # 4) 如果家长提供了预算信息，同步到 user_profile
    user_profile = dict(state.get("user_profile") or {})
    if "_budget" in new_fields and "budget" not in user_profile:
        user_profile["budget"] = new_fields["_budget"]

    # 5) 判定家长画像是否齐全
    essential = ["role", "industry", "expectation"]
    missing = [k for k in essential if not merged.get(k)]

    result: Dict[str, Any] = {
        "parent_profile": merged,
        "profile_history": history,
        "user_profile": user_profile,
    }

    if missing:
        result["next_node"] = "synthesis_agent"
    else:
        result["next_node"] = "family_agent"

    return result
