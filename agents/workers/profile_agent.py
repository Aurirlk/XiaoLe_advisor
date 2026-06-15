"""
学生画像提取 Agent — 混合模式（画像采集 + 排雷问卷 + 意向探索）

三类问题混合触发：
1. 画像采集：基础信息、MBTI性格、学科能力
2. 排雷问卷：绝对不接受什么（硬约束提取）
3. 意向探索：长板发现、就业倾向（铁饭碗/大热方向）

设计原则：
- 排雷优先：先问"绝对不要什么"，再问"想要什么"
- 硬编码过滤：条件判断下沉到Python，减少Token消耗
- MBTI性格：作为专业推荐的重要参考维度
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

from core.state_schema import GraphState, ProfileChange, SubjectScores, SUBJECT_NAMES


# ── 城市匹配 ──
_CITY_PATTERN_STRONG = re.compile(
    r"(?:去|在|换到|改成|改去|还是|那就|那去|到|选)\s*"
    r"([^\s，。！？]{2,6})\s*"
    r"(?:发展|就业|工作|读书|上学|怎么样|吧|行不行|算了|好了|也不错)"
)
_CITY_PATTERN_WEAK = re.compile(
    r"(?:去|换到|改去|改成)\s*"
    r"([^\s，。！？]{2,6})"
    r"(?=[，。！？\s]|$)"
)

# ── 省份 ──
_PROVINCE_LIST = [
    "河北省", "河南省", "山东省", "广东省", "江苏省", "浙江省", "四川省",
    "湖北省", "湖南省", "福建省", "安徽省", "江西省", "辽宁省",
    "吉林省", "黑龙江省", "陕西省", "山西省", "甘肃省",
    "云南省", "贵州省", "海南省", "青海省", "台湾省",
    "内蒙古自治区", "西藏自治区", "新疆维吾尔自治区",
    "宁夏回族自治区", "广西壮族自治区",
]

# ── 专业 ──
_KNOWN_MAJORS = [
    "临床医学", "口腔医学", "计算机科学与技术", "软件工程", "法学",
    "汉语言文学", "金融学", "会计学", "土木工程", "电气工程及其自动化",
    "机械工程", "电子信息工程", "通信工程", "人工智能", "数据科学与大数据技术",
    "生物工程", "化学工程", "环境工程", "材料科学与工程",
    "数学与应用数学", "物理学", "英语", "新闻学", "工商管理",
]
_MAJOR_ALIASES: Dict[str, str] = {
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
_SUBJECT_KEYWORDS = {
    "语文": ["语文"], "数学": ["数学"], "英语": ["英语"],
    "物理": ["物理"], "化学": ["化学"], "生物": ["生物"],
    "政治": ["政治", "思政"], "历史": ["历史"], "地理": ["地理"],
}

# ── 兴趣爱好关键词 ──
_INTEREST_KEYWORDS = {
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
_GENDER_MALE = ["男", "男生", "男孩", "小伙子"]
_GENDER_FEMALE = ["女", "女生", "女孩", "姑娘"]

# ── 风险偏好 ──
_RISK_AGGRESSIVE = ["冲", "敢冲", "冒险", "激进", "搏一搏"]
_RISK_CONSERVATIVE = ["稳", "保守", "求稳", "安全", "保底", "不想冒险"]

# ── 院校 ──
_UNIVERSITY_KEYWORDS = [
    "清华", "北大", "复旦", "上交", "浙大", "南大", "中科大", "人大",
    "北航", "北理", "中大", "华工", "深大", "武大", "华科", "西交",
    "哈工大", "成电", "西电", "北邮", "南开", "天大", "厦大", "山大",
    "川大", "重大", "湖大", "中南", "东南", "同济", "华东师范", "上财",
    "中央财经", "对外经贸", "中国政法", "北师大", "华东理工",
]


def _extract_subject_scores(query: str, existing: SubjectScores | None) -> SubjectScores:
    """从 query 中提取学科评分信息，合并到已有数据"""
    ss: SubjectScores = dict(existing or {})
    self_assess: List[Optional[int]] = list(ss.get("self_assessment") or [None] * 9)
    gaokao: List[Optional[int]] = list(ss.get("gaokao_scores") or [None] * 9)
    self_rank: List[Optional[str]] = list(ss.get("self_rank") or [None] * 9)
    strong: List[str] = list(ss.get("strong_subjects") or [])
    weak: List[str] = list(ss.get("weak_subjects") or [])

    # 提取 "XX好/强/厉害" → 强势学科
    for subj, keywords in _SUBJECT_KEYWORDS.items():
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

    # 提取 "XX 120分" 或 "XX考了120"
    score_pattern = re.compile(r"([\u4e00-\u9fff]{2,3})\s*(?:考了?|得了?|拿了?)?\s*(\d{2,3})\s*分")
    for m in score_pattern.finditer(query):
        subj_name = m.group(1)
        score_val = int(m.group(2))
        for subj, keywords in _SUBJECT_KEYWORDS.items():
            if subj_name in keywords:
                idx = SUBJECT_NAMES.index(subj)
                gaokao[idx] = score_val
                break

    # 提取 "总分XXX"
    total_match = re.search(r"总分\s*(\d{3})", query)
    if total_match:
        ss["total_score"] = int(total_match.group(1))

    ss["self_assessment"] = self_assess
    ss["gaokao_scores"] = gaokao
    ss["self_rank"] = self_rank
    ss["strong_subjects"] = strong
    ss["weak_subjects"] = weak
    return ss


def _extract_interests(query: str) -> List[str]:
    """提取兴趣爱好"""
    found = []
    for interest, keywords in _INTEREST_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                if interest not in found:
                    found.append(interest)
                break
    return found


def _extract_target_universities(query: str) -> List[str]:
    """提取目标院校"""
    found = []
    for uni in _UNIVERSITY_KEYWORDS:
        if uni in query:
            if uni not in found:
                found.append(uni)
    return found


def _extract_from_query(query: str) -> Dict[str, Any]:
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
        unit = (budget_match.group(2) or "").lower()
        if unit in {"万", "w"}:
            extracted["budget"] = int(num * 10000)
        elif unit in {"千", "k"}:
            extracted["budget"] = int(num * 1000)
        else:
            extracted["budget"] = int(num)

    # 目标城市
    city_match = _CITY_PATTERN_STRONG.search(query)
    if not city_match:
        city_match = _CITY_PATTERN_WEAK.search(query)
    if city_match:
        city = city_match.group(1)
        if city not in {"一个", "哪个", "什么", "哪里", "那儿", "一下", "一点"}:
            extracted["target_city"] = city

    # 省份
    found_provinces: list[str] = []
    for province in _PROVINCE_LIST:
        short = province.replace("省", "")
        if short in query or province in query:
            found_provinces.append(province)
    if found_provinces:
        extracted["province"] = found_provinces[0]
    if len(found_provinces) > 1:
        extracted["target_province"] = found_provinces[1]

    # 选科
    _SUBJ_P = ("物理类", "选物理", "选了物理", "选的是物理", "物理方向", "物理组合", "物理考生")
    _SUBJ_H = ("历史类", "选历史", "选了历史", "选的是历史", "历史方向", "历史组合", "历史考生")
    if any(kw in query for kw in _SUBJ_P):
        extracted["subject_type"] = "物理类"
    elif any(kw in query for kw in _SUBJ_H):
        extracted["subject_type"] = "历史类"

    # 专业
    for major in _KNOWN_MAJORS:
        if major in query:
            extracted["major_name"] = major
            break
    else:
        for alias, full_name in _MAJOR_ALIASES.items():
            if alias in query:
                extracted["major_name"] = full_name
                break

    # 读研意愿
    has_positive = any(w in query for w in ["读研", "读博", "考研", "保研", "深造"])
    has_negative = any(w in query for w in ["不读", "不想", "不准备", "不考虑", "不打算"])
    if has_positive:
        extracted["postgraduate_plan"] = "no" if has_negative else "yes"

    # 性别
    if any(w in query for w in _GENDER_MALE):
        extracted["gender"] = "male"
    elif any(w in query for w in _GENDER_FEMALE):
        extracted["gender"] = "female"

    # 风险偏好
    if any(w in query for w in _RISK_AGGRESSIVE):
        extracted["risk_tolerance"] = "aggressive"
    elif any(w in query for w in _RISK_CONSERVATIVE):
        extracted["risk_tolerance"] = "conservative"

    # 兴趣爱好
    interests = _extract_interests(query)
    if interests:
        extracted["_interests"] = interests

    # 目标院校
    universities = _extract_target_universities(query)
    if universities:
        extracted["_target_universities"] = universities

    return extracted


def _merge_profile(
    new_fields: Dict[str, Any],
    existing: Dict[str, Any],
    query: str,
) -> tuple[Dict[str, Any], List[ProfileChange]]:
    merged = dict(existing)
    changes: List[ProfileChange] = []

    user_facing_keys = {
        "score", "rank", "budget", "target_city", "province", "target_province",
        "subject_type", "major_name", "postgraduate_plan", "gender",
        "risk_tolerance", "gaokao_city",
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

    # 兴趣爱好累积（不去重，append 模式）
    new_interests = new_fields.get("_interests", [])
    if new_interests:
        existing_interests = set(merged.get("interests") or [])
        existing_interests.update(new_interests)
        merged["interests"] = sorted(existing_interests)

    # 目标院校累积
    new_unis = new_fields.get("_target_universities", [])
    if new_unis:
        existing_unis = set(merged.get("target_universities") or [])
        existing_unis.update(new_unis)
        merged["target_universities"] = sorted(existing_unis)

    return merged, changes


# ═══════════════════════════════════════════════════════════════
# 排雷关键词：提取用户"绝对不要什么"
# ═══════════════════════════════════════════════════════════════
BLACKLIST_KEYWORDS = {
    "土木工程": ["土木", "建筑", "工地", "施工"],
    "生化环材": ["生物", "化学", "环境", "材料", "化工"],
    "临床医学": ["医学", "医生", "临床", "护士"],
    "军事公安": ["军事", "公安", "警察", "军校", "警校"],
    "艺术类": ["艺术", "美术", "音乐", "设计", "绘画"],
    "文科类": ["哲学", "历史", "文学", "中文"],
    "计算机": ["代码", "编程", "计算机", "IT", "程序员"],
    "倒班制": ["倒班", "夜班", "三班倒", "轮班"],
    "强销售": ["销售", "推销", "拉客户"],
    "高学费": ["中外合作", "民办", "高学费", "学费贵"],
}

# ═══════════════════════════════════════════════════════════════
# 铁饭碗/大热方向：家长认可的稳定职业
# ═══════════════════════════════════════════════════════════════
IRON_BOWL_KEYWORDS = {
    "考公": ["公务员", "考公", "编制", "体制", "事业单位"],
    "军校": ["军校", "国防", "军事", "入伍"],
    "警校": ["警校", "公安", "警察", "刑警"],
    "师范": ["师范", "老师", "教师", "教育"],
    "医学": ["医学", "医生", "临床", "口腔", "中医"],
    "计算机": ["计算机", "程序员", "软件", "互联网", "AI"],
    "金融": ["金融", "银行", "证券", "投资", "财经"],
    "电气": ["国家电网", "电力", "电气", "供电"],
}

# ═══════════════════════════════════════════════════════════════
# MBTI性格 → 专业推荐映射（硬编码，零Token消耗）
# ═══════════════════════════════════════════════════════════════
MBTI_MAJOR_MAPPING = {
    "ISTJ": {"适合": ["会计学", "法学", "审计学", "金融学", "行政管理"], "风格": "严谨务实"},
    "ISFJ": {"适合": ["护理学", "教育学", "社会工作", "人力资源"], "风格": "细心守护"},
    "INFJ": {"适合": ["心理学", "教育学", "哲学", "社会学"], "风格": "理想主义"},
    "INTJ": {"适合": ["计算机科学", "数学", "物理学", "金融工程"], "风格": "战略思维"},
    "ISTP": {"适合": ["机械工程", "电子信息", "计算机科学", "土木工程"], "风格": "动手实践"},
    "ISFP": {"适合": ["设计学", "艺术学", "护理学", "园林"], "风格": "艺术感知"},
    "INFP": {"适合": ["心理学", "文学", "教育学", "哲学"], "风格": "内心理想"},
    "INTP": {"适合": ["数学", "物理学", "计算机科学", "经济学"], "风格": "理论探索"},
    "ESTP": {"适合": ["市场营销", "体育", "传播学", "创业管理"], "风格": "行动派"},
    "ESFP": {"适合": ["表演", "市场营销", "传播学", "旅游管理"], "风格": "社交达人"},
    "ENFP": {"适合": ["传播学", "心理学", "教育学", "市场营销"], "风格": "创意激发"},
    "ENTP": {"适合": ["法学", "创业管理", "市场营销", "经济学"], "风格": "辩论创新"},
    "ESTJ": {"适合": ["工商管理", "法学", "金融学", "行政管理"], "风格": "组织管理"},
    "ESFJ": {"适合": ["教育学", "护理学", "社会工作", "人力资源"], "风格": "关怀服务"},
    "ENFJ": {"适合": ["教育学", "心理学", "人力资源", "传播学"], "风格": "领袖魅力"},
    "ENTJ": {"适合": ["工商管理", "金融学", "法学", "计算机科学"], "风格": "果断领导"},
}


def _extract_blacklist(query: str) -> List[str]:
    """从用户query中提取排雷关键词（硬约束）"""
    blacklist = []
    for category, keywords in BLACKLIST_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                blacklist.append(category)
                break
    return list(set(blacklist))


def _extract_iron_bowl_preference(query: str) -> List[str]:
    """从用户query中提取铁饭碗/大热方向偏好"""
    preferences = []
    for category, keywords in IRON_BOWL_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                preferences.append(category)
                break
    return list(set(preferences))


def _calculate_mbti(answers: Dict[str, str]) -> str:
    """根据简化的MBTI答案计算性格类型"""
    # 简化版：4个维度各2题
    e_count = sum(1 for v in answers.values() if v in ["E", "e"])
    i_count = sum(1 for v in answers.values() if v in ["I", "i"])
    s_count = sum(1 for v in answers.values() if v in ["S", "s"])
    n_count = sum(1 for v in answers.values() if v in ["N", "n"])
    t_count = sum(1 for v in answers.values() if v in ["T", "t"])
    f_count = sum(1 for v in answers.values() if v in ["F", "f"])
    j_count = sum(1 for v in answers.values() if v in ["J", "j"])
    p_count = sum(1 for v in answers.values() if v in ["P", "p"])
    
    mbti = ""
    mbti += "E" if e_count >= i_count else "I"
    mbti += "S" if s_count >= n_count else "N"
    mbti += "T" if t_count >= f_count else "F"
    mbti += "J" if j_count >= p_count else "P"
    return mbti


def _get_mbti_recommendations(mbti_type: str) -> Dict[str, Any]:
    """获取MBTI类型的专业推荐"""
    return MBTI_MAJOR_MAPPING.get(mbti_type, {"适合": [], "风格": "未知"})


def _build_profile_response(
    merged: Dict[str, Any], 
    blacklist: List[str],
    iron_bowl: List[str],
    mbti_type: str = "",
) -> str:
    """构建用户画像确认回复（减少后续对话轮次）"""
    parts = []
    
    # 基础信息确认
    if merged.get("province"):
        parts.append(f"省份：{merged['province']}")
    if merged.get("subject_type"):
        parts.append(f"选科：{merged['subject_type']}")
    if merged.get("score"):
        parts.append(f"分数：{merged['score']}分")
    
    # 排雷信息确认
    if blacklist:
        parts.append(f"❌ 绝对不接受：{', '.join(blacklist)}")
    
    # 铁饭碗偏好
    if iron_bowl:
        parts.append(f"🎯 倾向方向：{', '.join(iron_bowl)}")
    
    # MBTI性格
    if mbti_type:
        rec = _get_mbti_recommendations(mbti_type)
        parts.append(f"🧠 性格类型：{mbti_type}（{rec.get('风格', '')}）")
        if rec.get("适合"):
            parts.append(f"   适合专业：{', '.join(rec['适合'][:3])}")
    
    return "📊 已获取你的画像信息：\n" + "\n".join(parts) if parts else ""


def profile_agent(state: GraphState) -> GraphState:
    query = state.get("user_query", "")
    
    # ══════════════════════════════════════════════════════════
    # 第一步：提取排雷约束（硬编码，零Token）
    # ══════════════════════════════════════════════════════════
    blacklist = _extract_blacklist(query)
    iron_bowl = _extract_iron_bowl_preference(query)
    
    # 合并到现有黑名单
    existing_profile = dict(state.get("user_profile") or {})
    existing_blacklist = existing_profile.get("blacklist_majors", [])
    merged_blacklist = list(set(existing_blacklist + blacklist))
    
    # ══════════════════════════════════════════════════════════
    # 第二步：从当前 query 抽取基础字段
    # ══════════════════════════════════════════════════════════
    new_fields = _extract_from_query(query)
    
    # 添加排雷和铁饭碗信息
    if merged_blacklist:
        new_fields["blacklist_majors"] = merged_blacklist
    if iron_bowl:
        new_fields["iron_bowl_preference"] = iron_bowl
    
    # ══════════════════════════════════════════════════════════
    # 第三步：Merge & diff
    # ══════════════════════════════════════════════════════════
    merged, changes = _merge_profile(new_fields, existing_profile, query)
    
    # ══════════════════════════════════════════════════════════
    # 第四步：学科评分提取
    # ══════════════════════════════════════════════════════════
    existing_ss = state.get("subject_scores")
    subject_scores = _extract_subject_scores(query, existing_ss)
    
    # ══════════════════════════════════════════════════════════
    # 第五步：追加变更历史
    # ══════════════════════════════════════════════════════════
    history: List[ProfileChange] = list(state.get("profile_history") or [])
    history.extend(changes)
    
    # ══════════════════════════════════════════════════════════
    # 第六步：构建返回值
    # ══════════════════════════════════════════════════════════
    extracted_score = new_fields.get("_extracted_score", state.get("extracted_score"))
    extracted_rank = new_fields.get("_extracted_rank", state.get("extracted_rank"))
    
    # ══════════════════════════════════════════════════════════
    # 第七步：判定画像是否齐全
    # ══════════════════════════════════════════════════════════
    missing_fields = [
        key for key in ("province", "subject_type", "score")
        if not merged.get(key)
    ]
    
    result = {
        "user_profile": merged,
        "profile_history": history,
        "subject_scores": subject_scores,
        "extracted_score": extracted_score,
        "extracted_rank": extracted_rank,
    }
    
    # 如果有排雷信息，更新parent_constraints
    if merged_blacklist:
        parent_constraints = dict(state.get("parent_constraints") or {})
        parent_constraints["blacklist_majors"] = merged_blacklist
        result["parent_constraints"] = parent_constraints
    
    # 如果有铁饭碗偏好，更新student_preferences
    if iron_bowl:
        student_preferences = dict(state.get("student_preferences") or {})
        student_preferences["iron_bowl_preference"] = iron_bowl
        result["student_preferences"] = student_preferences
    
    if missing_fields:
        result["missing_profile_fields"] = missing_fields
        result["next_node"] = "synthesis_agent"
    else:
        result["next_node"] = "supervisor_agent"
    
    return result
