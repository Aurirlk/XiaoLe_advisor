"""
画像关键词库 — 从 profile_agent.py 拆分

职责：存放所有关键词常量和提取函数
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# 九门学科名称（与 core/state_schema.py 保持一致）
SUBJECT_NAMES = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]


# ── 城市匹配 ──
CITY_PATTERN_STRONG = re.compile(
    r"(?:去|在|换到|改成|改去|还是|那就|那去|到|选)\s*"
    r"([^\s，。！？]{2,6})\s*"
    r"(?:发展|就业|工作|读书|上学|怎么样|吧|行不行|算了|好了|也不错)"
)
CITY_PATTERN_WEAK = re.compile(
    r"(?:去|换到|改去|改成)\s*"
    r"([^\s，。！？]{2,6})"
    r"(?=[，。！？\s]|$)"
)

# ── 省份 ──
PROVINCE_LIST = [
    "河北省", "河南省", "山东省", "广东省", "江苏省", "浙江省", "四川省",
    "湖北省", "湖南省", "福建省", "安徽省", "江西省", "辽宁省",
    "吉林省", "黑龙江省", "陕西省", "山西省", "甘肃省",
    "云南省", "贵州省", "海南省", "青海省", "台湾省",
    "内蒙古自治区", "西藏自治区", "新疆维吾尔自治区",
    "宁夏回族自治区", "广西壮族自治区",
]

# ── 专业 ──
KNOWN_MAJORS = [
    "临床医学", "口腔医学", "计算机科学与技术", "软件工程", "法学",
    "汉语言文学", "金融学", "会计学", "土木工程", "电气工程及其自动化",
    "机械工程", "电子信息工程", "通信工程", "人工智能", "数据科学与大数据技术",
    "生物工程", "化学工程", "环境工程", "材料科学与工程",
    "数学与应用数学", "物理学", "英语", "新闻学", "工商管理",
]
MAJOR_ALIASES: Dict[str, str] = {
    "计算机": "计算机科学与技术", "软工": "软件工程", "金融": "金融学",
    "会计": "会计学", "土木": "土木工程", "电气": "电气工程及其自动化",
    "机械": "机械工程", "电子": "电子信息工程", "通信": "通信工程",
    "临床": "临床医学", "口腔": "口腔医学", "法学": "法学",
    "汉语言": "汉语言文学", "新闻": "新闻学", "工商": "工商管理",
    "数学": "数学与应用数学", "物理": "物理学", "英语": "英语",
    "生物": "生物工程", "化学": "化学工程", "环境": "环境工程",
    "材料": "材料科学与工程", "AI": "人工智能", "人工智能": "人工智能",
    "大数据": "数据科学与大数据技术",
}

# ── 九门学科 ──
SUBJECT_KEYWORDS = {
    "语文": ["语文"], "数学": ["数学"], "英语": ["英语"],
    "物理": ["物理"], "化学": ["化学"], "生物": ["生物"],
    "政治": ["政治", "思政"], "历史": ["历史"], "地理": ["地理"],
}

# ── 兴趣爱好关键词 ──
INTEREST_KEYWORDS = {
    "编程": ["编程", "写代码", "coding", "程序", "代码"],
    "数学": ["数学", "算数", "几何", "代数"],
    "物理": ["物理", "力学", "电学"],
    "化学": ["化学", "实验"],
    "生物": ["生物", "基因", "细胞"],
    "历史": ["历史", "朝代", "古"],
    "地理": ["地理", "地图"],
    "文学": ["写作", "作文", "文学", "小说", "诗歌"],
    "英语": ["英语", "口语", "翻译"],
    "体育": ["篮球", "足球", "跑步", "游泳", "体育", "健身"],
    "音乐": ["音乐", "唱歌", "乐器", "钢琴", "吉他"],
    "美术": ["画画", "美术", "设计", "绘画"],
    "科技": ["科技", "机器人", "AI", "人工智能", "无人机"],
    "经济": ["经济", "投资", "股票", "商业"],
    "医学": ["医学", "医生", "临床", "解剖"],
    "法律": ["法律", "律师", "法"],
}

# ── 性别 ──
GENDER_MALE = ["男", "男生", "男孩", "小伙子"]
GENDER_FEMALE = ["女", "女生", "女孩", "姑娘"]

# ── 风险偏好 ──
RISK_AGGRESSIVE = ["冲", "敢冲", "冒险", "激进", "搏一搏"]
RISK_CONSERVATIVE = ["稳", "保守", "求稳", "安全", "保底", "不想冒险"]

# ── 院校 ──
UNIVERSITY_KEYWORDS = [
    "清华", "北大", "复旦", "上交", "浙大", "南大", "中科大", "人大",
    "北航", "北理", "中大", "华工", "深大", "武大", "华科", "西交",
    "哈工大", "成电", "西电", "北邮", "南开", "天大", "厦大", "山大",
    "川大", "重大", "湖大", "中南", "东南", "同济", "华东师范", "上财",
    "中央财经", "对外经贸", "中国政法", "北师大", "华东理工",
]


def extract_subject_scores(query: str, existing: SubjectScores | None) -> SubjectScores:
    """从 query 中提取学科评分信息，合并到已有数据"""
    ss: SubjectScores = dict(existing or {})
    self_assess: List[Optional[int]] = list(ss.get("self_assessment") or [None] * 9)
    gaokao: List[Optional[int]] = list(ss.get("gaokao_scores") or [None] * 9)
    self_rank: List[Optional[str]] = list(ss.get("self_rank") or [None] * 9)
    strong: List[str] = list(ss.get("strong_subjects") or [])
    weak: List[str] = list(ss.get("weak_subjects") or [])

    for subj, keywords in SUBJECT_KEYWORDS.items():
        idx = SUBJECT_NAMES.index(subj)
        for kw in keywords:
            if f"{kw}好" in query or f"{kw}强" in query or f"{kw}厉害" in query or f"{kw}不错" in query:
                if subj not in strong:
                    strong.append(subj)
                self_rank[idx] = "excellent"
            elif f"{kw}差" in query or f"{kw}弱" in query or f"{kw}不好" in query or f"{kw}不行" in query:
                if subj not in weak:
                    weak.append(subj)
                self_rank[idx] = "weak"

    score_pattern = re.compile(r"([\u4e00-\u9fff]{2,3})\s*(?:考了?|得了?|拿了?)?\s*(\d{2,3})\s*分")
    for m in score_pattern.finditer(query):
        subj_name = m.group(1)
        score_val = int(m.group(2))
        for subj, keywords in SUBJECT_KEYWORDS.items():
            if subj_name in keywords:
                idx = SUBJECT_NAMES.index(subj)
                gaokao[idx] = score_val
                break

    total_match = re.search(r"总分\s*(\d{3})", query)
    if total_match:
        ss["total_score"] = int(total_match.group(1))

    ss["self_assessment"] = self_assess
    ss["gaokao_scores"] = gaokao
    ss["self_rank"] = self_rank
    ss["strong_subjects"] = strong
    ss["weak_subjects"] = weak
    return ss


def extract_interests(query: str) -> List[str]:
    """提取兴趣爱好"""
    found = []
    for interest, keywords in INTEREST_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                if interest not in found:
                    found.append(interest)
                break
    return found


def extract_target_universities(query: str) -> List[str]:
    """提取目标院校"""
    found = []
    for uni in UNIVERSITY_KEYWORDS:
        if uni in query:
            if uni not in found:
                found.append(uni)
    return found


def extract_from_query(query: str) -> Dict[str, Any]:
    """从单条 query 中提取所有可识别字段"""
    extracted: Dict[str, Any] = {}

    # 分数
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
        unit = budget_match.group(2) or ""
        if unit.lower() in ("万", "w"):
            extracted["budget"] = int(num * 10000)
        elif unit.lower() in ("千", "k"):
            extracted["budget"] = int(num * 1000)
        else:
            extracted["budget"] = int(num)

    # 省份
    for prov in PROVINCE_LIST:
        if prov in query or prov.replace("省", "") in query:
            extracted["province"] = prov
            break

    # 选科类型
    if "物理" in query:
        extracted["subject_type"] = "物理类"
    elif "历史" in query:
        extracted["subject_type"] = "历史类"

    # 专业
    for alias, full_name in MAJOR_ALIASES.items():
        if alias in query:
            extracted["major_name"] = full_name
            break

    # 性别
    for kw in GENDER_MALE:
        if kw in query:
            extracted["gender"] = "male"
            break
    for kw in GENDER_FEMALE:
        if kw in query:
            extracted["gender"] = "female"
            break

    # 风险偏好
    for kw in RISK_AGGRESSIVE:
        if kw in query:
            extracted["risk_tolerance"] = "high"
            break
    for kw in RISK_CONSERVATIVE:
        if kw in query:
            extracted["risk_tolerance"] = "low"
            break

    # 城市
    city_match = CITY_PATTERN_STRONG.search(query)
    if city_match:
        extracted["target_city"] = city_match.group(1)
    else:
        city_match = CITY_PATTERN_WEAK.search(query)
        if city_match:
            extracted["target_city"] = city_match.group(1)

    # 考研意向
    if "考研" in query or "读研" in query or "研究生" in query:
        extracted["postgraduate_plan"] = "yes"
    elif "不考研" in query or "直接工作" in query or "不读研" in query:
        extracted["postgraduate_plan"] = "no"

    # 兴趣
    interests = extract_interests(query)
    if interests:
        extracted["interests"] = interests

    # 目标院校
    unis = extract_target_universities(query)
    if unis:
        extracted["target_universities"] = unis

    return extracted


def extract_blacklist(query: str) -> List[str]:
    """提取用户绝不接受的专业"""
    blacklist = []
    patterns = [
        r"不想学\s*(\S+)", r"不学\s*(\S+)", r"绝不学\s*(\S+)",
        r"不考虑\s*(\S+)", r"排除\s*(\S+)",
    ]
    for p in patterns:
        for m in re.finditer(p, query):
            major = m.group(1)
            if major in MAJOR_ALIASES:
                blacklist.append(MAJOR_ALIASES[major])
            else:
                blacklist.append(major)
    return blacklist


def extract_iron_bowl_preference(query: str) -> List[str]:
    """提取铁饭碗偏好"""
    prefs = []
    if any(kw in query for kw in ["考公", "公务员", "体制内"]):
        prefs.append("公务员")
    if any(kw in query for kw in ["教师", "老师", "教书"]):
        prefs.append("教师")
    if any(kw in query for kw in ["医生", "医院", "临床"]):
        prefs.append("医生")
    if any(kw in query for kw in ["国企", "央企", "烟草", "电网"]):
        prefs.append("国企")
    return prefs
