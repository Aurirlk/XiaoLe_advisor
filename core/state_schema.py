from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


AllowedNode = Literal[
    "supervisor_agent",
    "profile_agent",
    "parent_agent",
    "family_agent",
    "match_agent",
    "career_agent",
    "sql_agent",
    "red_team_auditor",
    "conflict_detector",
    "synthesis_agent",
    "END",
]

# 九门学科名称（固定顺序，数组索引对齐）
SUBJECT_NAMES = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]


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


class GraphState(TypedDict, total=False):
    # ── 对话基础 ──
    messages: Annotated[List[dict], add_messages]
    user_query: str
    session_id: str
    phone_number: str
    current_datetime: str
    conversation_role: str       # student/parent — 当前对话角色

    # ── 学生画像 ──
    user_profile: Dict[str, Any]        # 核心画像字段
    profile_history: List[ProfileChange]
    extracted_score: int
    extracted_rank: int
    subject_scores: SubjectScores       # 学科评分（新增）

    # ── 家长画像（新增）──
    parent_profile: ParentProfile

    # ── 家庭背景（新增）──
    family_context: FamilyContext

    # ── 下游数据 ──
    sql_results: List[Dict[str, str]]
    career_context: str
    web_search_results: str
    web_search_pages: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    reality_check: Dict[str, Any]
    decision_hints: Dict[str, Any]

    # ── 情绪分析（新增）──
    emotion_label: str               # happy/anxious/disappointed/angry/neutral/sad/excited/confused
    emotion_intensity: float         # 0.0-1.0
    emotion_valence: float           # -1.0 ~ +1.0

    # ── 路由 ──
    missing_profile_fields: List[str]
    next_node: AllowedNode
    error: str

    # ── 投研级升级（V5.0）──
    parent_constraints: ParentConstraints   # 家长硬约束
    student_preferences: StudentPreferences # 学生软偏好
    family_conflict: Dict[str, Any]        # 家庭冲突检测结果
    audit_result: Dict[str, Any]           # 反方审计结果
