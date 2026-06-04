"""
画像提取 Agent — 多轮对话 state merge 与回溯

策略:
- 每次调用从当前 query 抽取新画像字段
- 新值与 history 中已存在的值做 diff
- 发生覆盖时写入 profile_history 记录变更
- 返回的 profile 始终是 merge(历史 + 本次新增/覆盖)
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List

from core.state_schema import GraphState, ProfileChange


# Pattern 1: 有明确目标后缀（高置信度）
_CITY_PATTERN_STRONG = re.compile(
    r"(?:去|在|换到|改成|改去|还是|那就|那去|到|选)\s*"
    r"([^\s，。！？]{2,6})\s*"
    r"(?:发展|就业|工作|读书|上学|怎么样|吧|行不行|算了|好了|也不错)"
)

# Pattern 2: 只有"去XX"或"改去XX"等强意图前缀（中等置信度）
_CITY_PATTERN_WEAK = re.compile(
    r"(?:去|换到|改去|改成)\s*"
    r"([^\s，。！？]{2,6})"
    r"(?=[，。！？\s]|$)"
)
_PROVINCE_LIST = ["河北省", "河南省", "山东省", "广东省", "江苏省", "浙江省", "四川省",
                   "湖北省", "湖南省", "福建省", "安徽省", "江西省", "辽宁省",
                   "吉林省", "黑龙江省", "陕西省", "山西省", "甘肃省",
                   "云南省", "贵州省", "海南省", "青海省", "台湾省",
                   "内蒙古自治区", "西藏自治区", "新疆维吾尔自治区",
                   "宁夏回族自治区", "广西壮族自治区"]
_KNOWN_MAJORS = [
    "临床医学", "口腔医学", "计算机科学与技术", "软件工程", "法学",
    "汉语言文学", "金融学", "会计学", "土木工程", "电气工程及其自动化",
    "机械工程", "电子信息工程", "通信工程", "人工智能", "数据科学与大数据技术",
    "生物工程", "化学工程", "环境工程", "材料科学与工程",
    "数学与应用数学", "物理学", "英语", "新闻学", "工商管理",
]

# 部分匹配映射：常见简称 → 全称
_MAJOR_ALIASES: Dict[str, str] = {
    "计算机": "计算机科学与技术",
    "软工": "软件工程",
    "金融": "金融学",
    "会计": "会计学",
    "土木": "土木工程",
    "电气": "电气工程及其自动化",
    "机械": "机械工程",
    "电子": "电子信息工程",
    "通信": "通信工程",
    "临床": "临床医学",
    "口腔": "口腔医学",
    "法学": "法学",
    "汉语言": "汉语言文学",
    "新闻": "新闻学",
    "工商": "工商管理",
    "数学": "数学与应用数学",
    "物理": "物理学",
    "英语": "英语",
    "生物": "生物工程",
    "化学": "化学工程",
    "环境": "环境工程",
    "材料": "材料科学与工程",
    "AI": "人工智能",
    "人工智能": "人工智能",
    "大数据": "数据科学与大数据技术",
}


def _extract_from_query(query: str) -> Dict[str, Any]:
    """从单条 query 中提取所有可识别字段"""
    extracted: Dict[str, Any] = {}

    # 分数: 3位数字 + 分
    score_match = re.search(r"(\d{3})\s*分", query)
    if score_match:
        extracted["score"] = int(score_match.group(1))
        extracted["_extracted_score"] = int(score_match.group(1))

    # 位次
    rank_match = re.search(r"(?:位次|排名|省排)\s*[:：]?\s*(\d{1,7})", query)
    if rank_match:
        extracted["rank"] = int(rank_match.group(1))
        extracted["_extracted_rank"] = int(rank_match.group(1))

    # 预算
    budget_match = re.search(
        r"(?:预算|一年花费|年花费|家里能拿|学费)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(万|w|W|千|k|K)?", query
    )
    if budget_match:
        num = float(budget_match.group(1))
        unit = (budget_match.group(2) or "").lower()
        if unit in {"万", "w"}:
            extracted["budget"] = int(num * 10000)
        elif unit in {"千", "k"}:
            extracted["budget"] = int(num * 1000)
        else:
            extracted["budget"] = int(num)

    # 目标城市 (双模式: 强意图前缀 + 带后缀)
    city_match = _CITY_PATTERN_STRONG.search(query)
    if not city_match:
        city_match = _CITY_PATTERN_WEAK.search(query)
    if city_match:
        city = city_match.group(1)
        if city not in {"一个", "哪个", "什么", "哪里", "那儿", "一下", "一点"}:
            extracted["target_city"] = city

    # 省份（支持多个：第一个作为 province，后续出现的 "去/想去/在XX" 作为 target_province）
    found_provinces: list[str] = []
    for province in _PROVINCE_LIST:
        short = province.replace("省", "")
        if short in query or province in query:
            found_provinces.append(province)
    if found_provinces:
        extracted["province"] = found_provinces[0]
    if len(found_provinces) > 1:
        # 第二个出现的省份作为目标省份（通常是"想去XX"的语义）
        extracted["target_province"] = found_provinces[1]

    # 选科（使用明确后缀避免误匹配，如"物理变化"不应触发）
    _SUBJECT_PHYSICAL = ("物理类", "选物理", "选了物理", "选的是物理", "物理方向", "物理组合", "物理考生")
    _SUBJECT_HISTORY = ("历史类", "选历史", "选了历史", "选的是历史", "历史方向", "历史组合", "历史考生")
    if any(kw in query for kw in _SUBJECT_PHYSICAL):
        extracted["subject_type"] = "物理类"
    elif any(kw in query for kw in _SUBJECT_HISTORY):
        extracted["subject_type"] = "历史类"

    # 专业（全称匹配 + 别名映射）
    for major in _KNOWN_MAJORS:
        if major in query:
            extracted["major_name"] = major
            break
    else:
        for alias, full_name in _MAJOR_ALIASES.items():
            if alias in query:
                extracted["major_name"] = full_name
                break

    # 读研意愿（先检查否定再检查肯定，避免 "不打算考研" 误匹配肯定）
    has_positive = any(w in query for w in ["读研", "读博", "考研", "保研", "深造"])
    has_negative = any(w in query for w in ["不读", "不想", "不准备", "不考虑", "不打算"])
    if has_positive:
        if has_negative:
            extracted["postgraduate_plan"] = "no"
        else:
            extracted["postgraduate_plan"] = "yes"

    return extracted


def _merge_profile(
    new_fields: Dict[str, Any],
    existing: Dict[str, Any],
    query: str,
) -> tuple[Dict[str, Any], List[ProfileChange]]:
    """
    将新抽取字段合并到已有画像。
    返回 (merged_profile, changes)。
    - 新值覆盖旧值
    - 发生覆盖时记录变更
    """
    merged = dict(existing)
    changes: List[ProfileChange] = []

    user_facing_keys = {
        "score", "rank", "budget", "target_city", "province",
        "subject_type", "major_name", "postgraduate_plan",
    }

    for key, new_val in new_fields.items():
        if key.startswith("_"):
            continue
        old_val = merged.get(key)
        if new_val != old_val:
            merged[key] = new_val
            if key in user_facing_keys:
                changes.append(ProfileChange(
                    field=key,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val),
                    ts=datetime.now(timezone.utc).isoformat(),
                    trigger_query=query,
                ))

    return merged, changes


def profile_agent(state: GraphState) -> GraphState:
    query = state.get("user_query", "")

    # 1) 从当前 query 抽取新字段
    new_fields = _extract_from_query(query)

    # 2) 获取已有画像 (从 state，即上次 checkpoint 保存的值)
    existing_profile = dict(state.get("user_profile") or {})

    # 3) Merge & diff
    merged, changes = _merge_profile(new_fields, existing_profile, query)

    # 4) 追加变更历史
    history: List[ProfileChange] = list(state.get("profile_history") or [])
    history.extend(changes)

    # 5) 构建返回值（不直接修改传入的 state）
    extracted_score = new_fields.get("_extracted_score", state.get("extracted_score"))
    extracted_rank = new_fields.get("_extracted_rank", state.get("extracted_rank"))

    # 6) 判定画像是否齐全
    missing_fields = [
        key for key in ("province", "subject_type", "major_name")
        if not merged.get(key)
    ]
    if missing_fields:
        return {
            "user_profile": merged,
            "missing_profile_fields": missing_fields,
            "profile_history": history,
            "next_node": "synthesis_agent",
            "extracted_score": extracted_score,
            "extracted_rank": extracted_rank,
        }
    return {
        "user_profile": merged,
        "profile_history": history,
        "next_node": "supervisor_agent",
        "extracted_score": extracted_score,
        "extracted_rank": extracted_rank,
    }
