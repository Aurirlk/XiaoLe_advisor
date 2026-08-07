import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


AllowedNode = Literal[
    "supervisor_agent",
    "profile_agent",
    "parent_agent",
    "family_agent",
    "match_agent",
    "career_agent",
    "web_search_agent",   # P2-5：此前缺失，mypy 会报错
    "sql_agent",
    "red_team_auditor",
    "conflict_detector",
    "synthesis_agent",
    "chat_agent",
    "decision_detector",
    "result_fusion",      # 蓝图 Phase 3.3：synthesis 前结果融合节点
    "write_agent",        # 蓝图 write_Agent：唯一写权限 worker（2026-08-06）
    "END",
]

# 九门学科名称（固定顺序，数组索引对齐）
SUBJECT_NAMES = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]

# ── 画像完整性判据：单一真源 ─────────────────────────────────
# supervisor 与 profile_agent 必须使用同一份判据。
# 历史教训：两处字段集不一致（一个查 major_name、一个查 score）曾造成
# profile_agent ↔ supervisor 确定性死循环（交接手册 P0-5）。
#
# 判据 = 画像"核心三要素"：省份 / 选科 / 意向专业。
# 分数与位次属于查询时动态提取项（extracted_score / extracted_rank），
# 不阻塞路由：就业/搜索等场景无需分数也能作答，查分场景由 match_agent
# 内部用 rank / extracted_score 兜底（routing_golden.json 30 条黄金用例以此为准）。
REQUIRED_PROFILE_FIELDS = ("province", "subject_type", "major_name")


def missing_profile(profile: dict | None) -> List[str]:
    """返回画像缺失的必填字段列表（空列表 = 画像齐全）"""
    p = profile or {}
    return [k for k in REQUIRED_PROFILE_FIELDS if not p.get(k)]


class ProfileChange(TypedDict, total=False):
    """单次画像字段变更记录"""
    field: str
    old_value: Optional[str]
    new_value: str
    ts: str
    trigger_query: str


class ParentProfile(TypedDict, total=False):
    """家长画像"""
    role: str                    # father/mother/grandfather/other
    name: str                    # 姓名
    occupation: str              # 职业
    industry: str                # 行业（金融/医疗/教育/IT/制造/公务员/自由职业等）
    education: str               # 学历：高中/大专/本科/硕士/博士
    expectation: str             # 对孩子的期望（考公/稳定/赚钱/学术/创业等）
    concerns: List[str]          # 担忧点（就业/安全/距离/费用/健康等）
    decision_weight: str         # 决策权重：dominant/consultative/independent
    phone: str                   # 联系方式
    conversation_history: List[dict]  # 家长对话历史


class FamilyContext(TypedDict, total=False):
    """家庭背景（由 family_agent 从学生+家长画像融合生成）"""
    income_level: str            # low/medium/high
    annual_budget: int           # 年预算（元）
    total_budget: int            # 总预算（含读研 4-8 年）
    is_only_child: bool          # 独生子女
    sibling_count: int           # 兄弟姐妹数量
    family_resources: List[str]  # 家庭资源（人脉/行业/地域）
    decision_maker: str          # student/parent/joint
    location_preference: str     # local/nearby/anywhere
    financial_urgency: str       # none/moderate/high
    parent_consensus: str        # agree/disagree/partial — 家长与学生意向一致性


class SubjectScores(TypedDict, total=False):
    """学科评分（九门，null 表示未选考）

    索引顺序：语文(0) 数学(1) 英语(2) 物理(3) 化学(4) 生物(5) 政治(6) 历史(7) 地理(8)
    值：int 分数 或 null(未选考)
    """
    self_assessment: List[Optional[int]]  # 学生自评各科分数（满分100或150）
    gaokao_scores: List[Optional[int]]    # 高考/模考各科实际分数
    self_rank: List[Optional[str]]        # 学生自评各科水平：excellent/good/average/weak
    strong_subjects: List[str]            # 强势学科名称列表
    weak_subjects: List[str]              # 弱势学科名称列表


class ParentConstraints(TypedDict, total=False):
    """家长硬约束（不可协商）

    用于冲突检测器判断家庭内部矛盾
    """
    budget_ceiling: int               # 预算绝对上限（元/年）
    must_public: bool                 # 必须公办
    must_local: bool                  # 必须省内
    must_safe: bool                   # 必须稳妥
    health_restrictions: List[str]    # 体检限制（色弱/色盲/近视等）
    blacklist_majors: List[str]       # 禁止专业列表
    blacklist_cities: List[str]       # 禁止城市列表


class StudentPreferences(TypedDict, total=False):
    """学生软偏好（可协商）

    用于冲突检测器与家长约束对比
    """
    preferred_cities: List[str]       # 偏好城市
    preferred_majors: List[str]       # 偏好专业
    risk_tolerance: str               # low/medium/high
    freedom_level: str                # 高自由度/中等/保守
    postgraduate_plan: str            # yes/no/uncertain


# ── reducers（P1-3）────────────────────────────────────────────
# 说明：仅为「增量语义」的 key 配置合并 reducer；返回全量/截断结果的
# key（sql_results / profile_history）保持覆盖（worker 已自行合并），
# 否则 operator.add 会造成重复追加。

def _merge_dict(a, b):
    """字典浅合并（后值覆盖前值同名 key），用于画像类字段"""
    return {**(a or {}), **(b or {})}


def _last_not_none(a, b):
    return b if b is not None else a


class GraphState(TypedDict, total=False):
    # ── 对话基础 ──
    messages: Annotated[List[dict], add_messages]
    user_query: str
    session_id: str
    phone_number: str
    current_datetime: str
    conversation_role: str       # student/parent — 当前对话角色

    # ── 学生画像 ──
    user_profile: Annotated[Dict[str, Any], _merge_dict]  # 核心画像字段（合并）
    profile_history: List[ProfileChange]   # 全量覆盖（worker 返回完整变更历史）
    extracted_score: int
    extracted_rank: int
    subject_scores: Annotated[SubjectScores, _merge_dict]  # 学科评分（合并）

    # ── 家长画像（新增）──
    parent_profile: Annotated[ParentProfile, _merge_dict]

    # ── 家庭背景（新增）──
    family_context: Annotated[FamilyContext, _merge_dict]

    # ── 下游数据 ──
    sql_results: List[Dict[str, str]]   # 全量覆盖（worker 返回融合/截断结果）
    career_context: str
    web_search_results: str
    # 蓝图 Phase 3.3：结果融合节点输出（synthesis 前融合的综合上下文，可选增强）
    fusion_context: str
    # 蓝图 write_Agent：知识库写入结果统计（可选增强，2026-08-06）
    write_result: Dict[str, Any]
    # 蓝图 Phase 3.1：Agent 通信总线协作统计（publish/request 次数，2026-08-07）
    bus_stats: Dict[str, Any]
    # 蓝图 Phase 3.2：自我反思质量门报告（match/career 输出反思结果，2026-08-07）
    reflexion_report: Annotated[Dict[str, Any], _merge_dict]
    web_search_pages: Annotated[List[Dict[str, Any]], operator.add]  # 增量追加
    web_search_platform: str         # 搜索平台名（如 知乎/微博/全网）
    web_search_keywords: str         # LLM 提取后的搜索关键词
    web_search_confidence: float     # 平台分类置信度
    risk_assessment: Annotated[Dict[str, Any], _merge_dict]
    reality_check: Annotated[Dict[str, Any], _merge_dict]
    decision_hints: Annotated[Dict[str, Any], _merge_dict]

    # ── 情绪分析（新增）──
    emotion_label: str               # happy/anxious/disappointed/angry/neutral/sad/excited/confused
    emotion_intensity: float         # 0.0-1.0
    emotion_valence: float           # -1.0 ~ +1.0

    # ── 路由 ──
    missing_profile_fields: Annotated[List[str], operator.add]  # 增量追加
    next_node: Annotated[AllowedNode, _last_not_none]           # last-wins
    error: str

    # ── 投研级升级（V5.0）──
    parent_constraints: Annotated[ParentConstraints, _merge_dict]   # 家长硬约束
    student_preferences: Annotated[StudentPreferences, _merge_dict] # 学生软偏好
    family_conflict: Annotated[Dict[str, Any], _merge_dict]        # 家庭冲突检测结果
    audit_result: Annotated[Dict[str, Any], _merge_dict]           # 反方审计结果

    # ── 多维意图识别（V6.0）──
    scene_type: str                        # chat / gaokao / postgraduate
    scene_confidence: float                # 0.0-1.0
    scene_reasoning: str                   # 场景识别理由
    path_type: str                         # postgrad / employment / uncertain（仅 postgraduate）
    path_confidence: float                 # 0.0-1.0
    path_reasoning: str                    # 路径识别理由
    decision_state: str                    # firm / hesitant / lost
    hesitation_signals: Annotated[List[str], operator.add]   # 增量追加
    fallback_type: str                     # 回退类型
    fallback_response: str                 # 回退响应

    # ── 渐进询问（V6.0）──
    missing_info: Annotated[List[Dict[str, Any]], operator.add]    # 增量追加
    progressive_questions: Annotated[List[Dict[str, Any]], operator.add]  # 增量追加
    question_history: Annotated[List[Dict[str, Any]], operator.add]        # 增量追加

    # ── 增强模块输出（V6.0）──
    info_gap_content: str                  # 信息差弥合内容
    decision_framework: str                # 决策框架内容
    reality_mapping: str                   # 现实映射内容
    family_mediation: str                  # 家庭调解内容
    emotional_support: str                 # 情感支持内容

    # ── CRM 集成（V6.0）──
    crm_journey: List[Dict[str, Any]]     # 用户决策旅程
    crm_pattern: Dict[str, Any]           # CRM 检测到的模式
    similar_decisions: List[Dict[str, Any]]  # 相似用户决策
