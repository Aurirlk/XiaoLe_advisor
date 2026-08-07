"""
就业数据联网搜索工具

功能：
1. 联网搜索就业/薪资数据（BOSS直聘、智联招聘等）
2. 解析搜索结果，提取结构化数据
3. 自动入库到本地知识库

使用方式：
python -c "from tools.employment_search import search_employment; import asyncio; print(asyncio.run(search_employment('深圳', '计算机')))"
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "data" / "documents" / "employment"


async def search_employment(city: str, major: str) -> Dict[str, Any]:
    """
    联网搜索就业数据
    
    Args:
        city: 城市名称
        major: 专业名称
    
    Returns:
        {
            "city": "深圳",
            "major": "计算机科学与技术",
            "positions": [...],
            "salary_range": {"min": 8000, "max": 25000, "avg": 15000},
            "job_count": 150,
            "source": "联网搜索"
        }
    """
    # 搜索关键词
    keywords = _major_to_keywords(major)
    
    all_results = []
    for keyword in keywords[:2]:
        results = await _search_web(city, keyword)
        all_results.extend(results)
    
    if not all_results:
        return {
            "city": city,
            "major": major,
            "positions": [],
            "salary_range": {"min": 0, "max": 0, "avg": 0},
            "job_count": 0,
            "source": "联网搜索"
        }
    
    # 统计薪资
    salaries = [r["salary_avg"] for r in all_results if r.get("salary_avg", 0) > 0]
    
    return {
        "city": city,
        "major": major,
        "positions": [r["position"] for r in all_results[:10]],
        "salary_range": {
            "min": min(salaries) if salaries else 0,
            "max": max(salaries) if salaries else 0,
            "avg": int(sum(salaries) / len(salaries)) if salaries else 0,
        },
        "job_count": len(all_results),
        "source": "联网搜索",
        "search_time": datetime.now().isoformat()
    }


async def _search_web(city: str, keyword: str) -> List[Dict[str, Any]]:
    """联网搜索岗位数据"""
    from tools.web_search_tools import WebSearchTools
    
    tools = WebSearchTools()
    query = f"{city} {keyword} 薪资 招聘"
    results = tools.search(query=query, top_k=5)
    
    parsed = []
    for result in results:
        text = result.get("text", "")
        url = result.get("url", "")
        
        # 解析薪资
        salary_match = re.search(r'(\d+)[kK]-(\d+)[kK]', text)
        if salary_match:
            salary_min = int(salary_match.group(1)) * 1000
            salary_max = int(salary_match.group(2)) * 1000
            salary_avg = (salary_min + salary_max) // 2
        else:
            salary_min = salary_max = salary_avg = 0
        
        parsed.append({
            "position": keyword,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_avg": salary_avg,
            "city": city,
            "source": url,
            "snippet": text[:200]
        })
    
    return parsed


def save_to_knowledge_base(data: Dict[str, Any]) -> str:
    """
    将搜索结果保存到本地知识库
    
    Returns:
        保存的文件路径
    """
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    
    city = data.get("city", "未知")
    major = data.get("major", "未知")
    
    doc = f"# {city}{major}就业数据\n\n"
    doc += f"**数据来源**: 联网搜索\n"
    doc += f"**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    doc += "---\n\n"
    
    salary_range = data.get("salary_range", {})
    doc += "## 薪资概况\n\n"
    doc += f"- **最低薪资**: ¥{salary_range.get('min', 0):,}/月\n"
    doc += f"- **最高薪资**: ¥{salary_range.get('max', 0):,}/月\n"
    doc += f"- **平均薪资**: ¥{salary_range.get('avg', 0):,}/月\n"
    doc += f"- **岗位数量**: {data.get('job_count', 0)} 个\n\n"
    
    positions = data.get("positions", [])
    if positions:
        doc += "## 热门岗位\n\n"
        for pos in positions[:10]:
            doc += f"- {pos}\n"
        doc += "\n"
    
    # 保存文件
    filename = f"{city}{major}就业数据.md"
    filepath = KNOWLEDGE_DIR / filename
    filepath.write_text(doc, encoding="utf-8")
    
    logger.info(f"保存就业数据到知识库: {filepath}")
    return str(filepath)


def _major_to_keywords(major: str) -> List[str]:
    """将专业名映射为搜索关键词"""
    mapping = {
        "计算机科学与技术": ["Java开发", "Python开发", "软件工程师"],
        "软件工程": ["软件工程师", "前端开发", "后端开发"],
        "人工智能": ["机器学习工程师", "AI算法", "NLP工程师"],
        "数据科学与大数据技术": ["数据分析师", "数据工程师", "大数据开发"],
        "电子信息工程": ["嵌入式工程师", "硬件工程师", "FPGA工程师"],
        "通信工程": ["通信工程师", "5G工程师", "射频工程师"],
        "临床医学": ["医生", "临床医师", "住院医师"],
        "口腔医学": ["口腔医师", "牙科医生"],
        "法学": ["律师", "法务", "合规"],
        "金融学": ["金融分析师", "投资顾问", "风控"],
        "会计学": ["会计师", "审计", "财务"],
        "土木工程": ["土木工程师", "结构工程师", "施工员"],
        "建筑学": ["建筑师", "室内设计", "景观设计"],
        "机械工程": ["机械工程师", "自动化工程师", "设备工程师"],
        "电气工程及其自动化": ["电气工程师", "自动化工程师", "PLC工程师"],
        "生物工程": ["生物技术", "研发工程师", "实验员"],
        "化学工程": ["化工工程师", "工艺工程师", "研发工程师"],
        "环境工程": ["环保工程师", "环境监测", "碳排放管理"],
        "材料科学与工程": ["材料工程师", "工艺工程师", "质量工程师"],
        "汉语言文学": ["编辑", "文案", "新媒体运营"],
        "新闻学": ["记者", "编辑", "新媒体"],
        "英语": ["翻译", "外贸", "英语老师"],
    }
    return mapping.get(major, [major, f"{major}相关"])
