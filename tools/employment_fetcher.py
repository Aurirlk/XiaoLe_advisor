"""
就业数据抓取工具 — 从 BOSS直聘/智联招聘 获取实时薪资和岗位数据

数据来源：
- BOSS直聘：https://www.zhipin.com
- 智联招聘：https://www.zhaopin.com

返回结构化的薪资/岗位数据，供图谱和对话使用。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


class EmploymentDataFetcher:
    """就业数据抓取器"""

    def __init__(self, user_agent: str | None = None, timeout: float = 10.0):
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.timeout = timeout

    def fetch_salary_by_city_major(self, city: str, major: str) -> Dict[str, Any]:
        """查询某城市某专业的薪资数据

        Returns:
            {
                "city": "深圳",
                "major": "计算机科学与技术",
                "related_positions": [...],
                "salary_range": {"min": 8000, "max": 25000, "avg": 15000},
                "job_count": 150,
                "source": "综合估算"
            }
        """
        # 将专业映射到搜索关键词
        search_keywords = self._major_to_keywords(major)
        results = []

        for keyword in search_keywords[:2]:  # 最多查2个关键词
            data = self._search_zhipin(city, keyword)
            if data:
                results.extend(data)

        if not results:
            return {
                "city": city,
                "major": major,
                "related_positions": [],
                "salary_range": {"min": 0, "max": 0, "avg": 0},
                "job_count": 0,
                "source": "无数据",
            }

        # 统计薪资
        salaries = [r["salary_avg"] for r in results if r.get("salary_avg", 0) > 0]
        return {
            "city": city,
            "major": major,
            "related_positions": [r["position"] for r in results[:10]],
            "salary_range": {
                "min": min(salaries) if salaries else 0,
                "max": max(salaries) if salaries else 0,
                "avg": int(sum(salaries) / len(salaries)) if salaries else 0,
            },
            "job_count": len(results),
            "source": "BOSS直聘",
        }

    def fetch_industry_salary(self, city: str, industry: str) -> Dict[str, Any]:
        """查询某城市某行业的薪资分布"""
        keywords = self._industry_to_keywords(industry)
        results = []

        for keyword in keywords[:2]:
            data = self._search_zhipin(city, keyword)
            if data:
                results.extend(data)

        salaries = [r["salary_avg"] for r in results if r.get("salary_avg", 0) > 0]
        if not salaries:
            return {"city": city, "industry": industry, "avg": 0, "median": 0, "p90": 0, "count": 0}

        salaries.sort()
        return {
            "city": city,
            "industry": industry,
            "avg": int(sum(salaries) / len(salaries)),
            "median": salaries[len(salaries) // 2],
            "p90": salaries[int(len(salaries) * 0.9)] if len(salaries) >= 10 else salaries[-1],
            "count": len(salaries),
            "source": "BOSS直聘",
        }

    def _search_zhipin(self, city: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索 BOSS 直聘（解析 HTML）"""
        url = f"https://www.zhipin.com/web/geek/job?query={quote_plus(keyword)}&city={quote_plus(city)}"
        request = Request(url=url, headers={"User-Agent": self.user_agent}, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.debug("BOSS直聘查询失败: %s", e)
            return []

        # 解析岗位信息
        results = []
        # 匹配薪资格式：15-25K, 15-25k·13薪
        salary_pattern = re.compile(r'(\d+)[kK]-(\d+)[kK](?:·(\d+)薪)?')
        position_pattern = re.compile(r'class="job-name"[^>]*>([^<]+)<')

        positions = position_pattern.findall(body)
        salaries = salary_pattern.findall(body)

        for i, pos in enumerate(positions[:20]):
            salary_min = 0
            salary_max = 0
            salary_avg = 0
            if i < len(salaries):
                s_min, s_max, bonus = salaries[i]
                salary_min = int(s_min) * 1000
                salary_max = int(s_max) * 1000
                if bonus:
                    salary_max = salary_max * int(bonus) // 12
                salary_avg = (salary_min + salary_max) // 2

            results.append({
                "position": pos.strip(),
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_avg": salary_avg,
                "city": city,
            })

        return results

    def _major_to_keywords(self, major: str) -> List[str]:
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


    def _industry_to_keywords(self, industry: str) -> List[str]:
        """将行业名映射为搜索关键词"""
        mapping = {
            "互联网/IT": ["Java", "Python", "前端"],
            "人工智能": ["机器学习", "AI算法", "深度学习"],
            "半导体/芯片": ["芯片设计", "IC设计", "FPGA"],
            "金融": ["金融分析师", "投资顾问", "风控"],
            "医疗健康": ["医生", "医药代表", "医疗器械"],
            "新能源": ["电池工程师", "新能源研发", "光伏"],
            "汽车": ["汽车工程师", "自动驾驶", "新能源汽车"],
            "教育": ["教师", "培训讲师", "教研"],
        }
        return mapping.get(industry, [industry])


# 全局实例
_fetcher: Optional[EmploymentDataFetcher] = None


def get_employment_fetcher() -> EmploymentDataFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = EmploymentDataFetcher()
    return _fetcher
