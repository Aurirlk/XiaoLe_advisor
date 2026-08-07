"""
信息差弥合引擎 — 主动告知用户该知道的事

功能：
- 检测用户可能不知道的信息
- 基于 RAG 经验库生成弥合内容
- 基于就业数据生成现实信息
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List
from pathlib import Path

from tools.rag_tools import RAGTools

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]


class InfoGapBridger:
    """信息差弥合引擎"""
    
    def __init__(self, rag_tools: RAGTools):
        self.rag = rag_tools
    
    async def bridge_info_gap(self, query: str, profile: Dict[str, Any], scene: str) -> str:
        """弥合信息差"""
        
        # 检测用户可能不知道的信息
        gaps = self._detect_gaps(query, profile, scene)
        
        if not gaps:
            return ""
        
        # 生成信息差弥合内容
        bridge_content = []
        for gap in gaps[:3]:  # 最多 3 个
            content = await self._generate_bridge_content(gap, profile)
            if content:
                bridge_content.append(content)
        
        return "\n\n".join(bridge_content)
    
    def _detect_gaps(self, query: str, profile: Dict[str, Any], scene: str) -> List[Dict[str, Any]]:
        """检测信息差"""
        gaps = []
        
        # 基于查询检测
        major_keywords = {
            "计算机": "计算机", "软件": "软件工程", "医学": "临床医学",
            "临床": "临床医学", "口腔": "口腔医学", "法学": "法学",
            "金融": "金融学", "会计": "会计学", "土木": "土木工程",
            "电气": "电气工程", "机械": "机械工程", "电子": "电子信息",
            "通信": "通信工程", "人工智能": "人工智能", "AI": "人工智能",
        }
        
        for keyword, major in major_keywords.items():
            if keyword in query:
                gaps.append({"type": "major_reality", "major": major})
                break
        
        if "考研" in query:
            gaps.append({"type": "postgrad_reality"})
        
        if "就业" in query or "工作" in query:
            gaps.append({"type": "employment_reality"})
        
        # 基于画像检测
        if profile.get("major_name") and not profile.get("employment_rate_checked"):
            gaps.append({"type": "employment_rate", "major": profile["major_name"]})
        
        return gaps
    
    async def _generate_bridge_content(self, gap: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """生成弥合内容"""
        if gap["type"] == "major_reality":
            return await self._bridge_major_reality(gap["major"])
        elif gap["type"] == "postgrad_reality":
            return self._bridge_postgrad_reality()
        elif gap["type"] == "employment_reality":
            return self._bridge_employment_reality()
        elif gap["type"] == "employment_rate":
            return await self._bridge_employment_rate(gap["major"])
        return ""
    
    async def _bridge_major_reality(self, major: str) -> str:
        """弥合专业现实信息差"""
        # 查询 RAG 经验库
        docs = self.rag.search(f"{major} 就业 现实", top_k=3)
        context = "\n".join([d.get("text", "") for d in docs]) if docs else ""
        
        # 查询就业数据
        employment_data = self._query_employment_data(major)
        
        parts = [f"💡 **关于{major}专业，你可能不知道的事**："]
        
        if context:
            parts.append(f"\n{context[:300]}")
        
        if employment_data:
            parts.append(f"\n{employment_data}")
        
        return "\n".join(parts) if len(parts) > 1 else ""
    
    def _bridge_postgrad_reality(self) -> str:
        """弥合考研现实信息差"""
        return """
💡 **关于考研，你可能不知道的事**：

1. **考研不是避风港** — 很多人考研是因为不知道干什么，但读研后依然迷茫
2. **学历贬值** — 硕士学历的溢价在缩小，有些行业本科就够
3. **时间成本** — 读研 2-3 年，意味着少赚 2-3 年工资
4. **考研难度** — 2024 年考研报名 438 万，录取率约 30%

**考研适合**：
- 确实想深入研究某个领域
- 目标职业明确要求硕士学历
- 有学术热情

**考研不适合**：
- 不知道干什么，先考个研
- 觉得硕士一定比本科好
- 家长逼的

你属于哪种情况？
"""
    
    def _bridge_employment_reality(self) -> str:
        """弥合就业现实信息差"""
        return """
💡 **关于就业，你可能不知道的事**：

1. **专业对口率低** — 很多人毕业后从事与专业无关的工作
2. **起薪差异大** — 同一专业不同学校起薪可能差 2-3 倍
3. **城市很重要** — 同一专业在一线城市和三四线城市薪资差距巨大
4. **实习比成绩重要** — 很多企业更看重实习经验

**就业建议**：
- 大一就开始实习
- 多参加比赛和项目
- 建立人脉关系
- 不要只看专业名字

你更看重什么？稳定还是高薪？
"""
    
    async def _bridge_employment_rate(self, major: str) -> str:
        """弥合就业率信息差"""
        data = self._query_employment_data(major)
        if data:
            return f"""
📊 **{major}的就业现实**：

{data}

这些数据可以帮助你更理性地做决定。
"""
        return ""
    
    def _query_employment_data(self, major: str) -> str:
        """查询就业数据"""
        try:
            import sqlite3
            
            db_path = ROOT / "data" / "zx_advisor.db"
            if not db_path.exists():
                return ""
            
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            
            # 查询就业去向
            dest = conn.execute(
                "SELECT * FROM major_destination_stats WHERE major_name = ? ORDER BY year DESC LIMIT 1",
                (major,)
            ).fetchone()
            
            # 查询薪资分布
            salary = conn.execute(
                "SELECT * FROM major_salary_stats WHERE major_name = ? ORDER BY year DESC LIMIT 1",
                (major,)
            ).fetchone()
            
            conn.close()
            
            parts = []
            
            if dest:
                if dest['employed_rate']:
                    parts.append(f"- 实际就业率：{dest['employed_rate']*100:.1f}%")
                if dest['postgraduate_rate']:
                    parts.append(f"- 升学率：{dest['postgraduate_rate']*100:.1f}%")
                if dest['avg_start_salary']:
                    parts.append(f"- 起薪中位数：{dest['avg_start_salary']}元")
            
            if salary:
                if salary['salary_p50']:
                    parts.append(f"- 薪资中位数：{salary['salary_p50']}元")
                if salary['salary_p75']:
                    parts.append(f"- 75分位薪资：{salary['salary_p75']}元")
            
            return "\n".join(parts) if parts else ""
            
        except Exception as e:
            logger.warning(f"查询就业数据失败: {e}")
            return ""
