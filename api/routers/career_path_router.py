"""跨领域学习路径推荐 + 资料检索 API（自 backend/app/routers 迁移，P1-20）"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query

from api.response import fail, ok

router = APIRouter(prefix="/api/career", tags=["career-path"])

ROOT = Path(__file__).resolve().parents[2]

# ======= 学习路径定义 =======
LEARNING_PATHS = [
    {
        "id": "high_school_gaokao",
        "name": "高考 → 大学 → 就业",
        "for": "高三学生",
        "steps": [
            {"order": 1, "title": "高考志愿填报", "desc": "结合分数/位次/兴趣，选择合适院校和专业", "domain": "gaokao"},
            {"order": 2, "title": "大学四年规划", "desc": "大一大二打基础，大三大四实习/考研/考公", "domain": "career"},
            {"order": 3, "title": "毕业选择", "desc": "就业/考研/考公/考编四选一", "domain": "career"},
        ]
    },
    {
        "id": "associate_upgrade",
        "name": "专科 → 专升本 → 考研/就业",
        "for": "专科在校生",
        "steps": [
            {"order": 1, "title": "确定升本目标", "desc": "了解本省专升本政策，选择对口院校和专业", "domain": "associate_bachelor"},
            {"order": 2, "title": "系统复习备考", "desc": "英语+数学/语文+专业课，大三参加统考", "domain": "associate_bachelor"},
            {"order": 3, "title": "升本后规划", "desc": "本科2年：过四级、考研复习或准备考公", "domain": "postgraduate"},
            {"order": 4, "title": "考研或考公", "desc": "本科学历到手后，继续考研或参加公务员考试", "domain": "civil_service"},
        ]
    },
    {
        "id": "undergrad_postgrad",
        "name": "本科 → 考研 → 学术/就业",
        "for": "本科在校生",
        "steps": [
            {"order": 1, "title": "择校定专业", "desc": "查报录比、复试线，确定目标院校和专业", "domain": "postgraduate"},
            {"order": 2, "title": "初试备考", "desc": "大三下学期开始系统复习（英语/政治/数学/专业课）", "domain": "postgraduate"},
            {"order": 3, "title": "复试与调剂", "desc": "初试成绩公布后准备复试，必要时走调剂", "domain": "postgraduate"},
            {"order": 4, "title": "研究生毕业出路", "desc": "高校任教/科研院所/企业研发/考公选调", "domain": "career"},
        ]
    },
    {
        "id": "civil_service_path",
        "name": "大学 → 考公/考编 → 铁饭碗",
        "for": "应届毕业生",
        "steps": [
            {"order": 1, "title": "了解考试类型", "desc": "国考/省考/选调/事业单位的区别与选择", "domain": "civil_service"},
            {"order": 2, "title": "系统备考", "desc": "行测5模块+申论4题型，6个月备考周期", "domain": "civil_service"},
            {"order": 3, "title": "职位筛选", "desc": "根据专业/学历/地域筛选合适岗位，关注竞争比", "domain": "civil_service"},
            {"order": 4, "title": "面试准备", "desc": "结构化/无领导/结构化小组，面试占比40-50%", "domain": "civil_service"},
        ]
    },
    {
        "id": "career_planning",
        "name": "职业规划全景",
        "for": "所有人生阶段",
        "steps": [
            {"order": 1, "title": "自我认知", "desc": "了解自己的兴趣/性格/能力/价值观", "domain": "career"},
            {"order": 2, "title": "行业探索", "desc": "研究目标行业的趋势/薪资/技能要求", "domain": "career"},
            {"order": 3, "title": "路径选择", "desc": "高考→大学→考研/考公/就业，多路径对比", "domain": "gaokao"},
            {"order": 4, "title": "持续迭代", "desc": "工作3-5年后重新评估，考虑MBA/转行/创业", "domain": "career"},
        ]
    },
]


@router.get("/paths")
async def get_learning_paths():
    """获取所有学习路径模板"""
    return ok(data={"paths": LEARNING_PATHS})


@router.get("/path/{path_id}")
async def get_path_detail(path_id: str):
    """获取指定学习路径详情"""
    for p in LEARNING_PATHS:
        if p["id"] == path_id:
            return ok(data=p)
    return fail(message="路径不存在", code=404)


# ======= 跨领域资料检索 =======
@router.get("/search")
async def search_all_documents(
    query: str = Query(..., min_length=1, max_length=100),
):
    """跨领域文档统一检索"""
    doc_root = ROOT / "data" / "documents"
    results = []
    if doc_root.exists():
        for md_file in doc_root.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            if query.lower() in content.lower():
                rel_path = str(md_file.relative_to(doc_root))
                domain = rel_path.split("\\")[0] if "\\" in rel_path else ""
                # 提取匹配行前后各1行作为摘要
                lines = content.split("\n")
                matched_lines = []
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        start = max(0, i - 1)
                        end = min(len(lines), i + 2)
                        matched_lines.append(" ".join(lines[start:end]))
                summary = " ... ".join(matched_lines[:3])[:200]
                results.append({
                    "title": md_file.stem,
                    "domain": domain,
                    "path": rel_path,
                    "summary": summary,
                })
    return ok(data={"items": results[:10], "total": len(results)})
