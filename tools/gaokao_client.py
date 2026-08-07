"""
阳光高考数据查询工具 — 查询教育部官方院校/专业/政策数据

数据来源：阳光高考网 (gaokao.chsi.com.cn)
功能：院校查询、专业查询、政策查询
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


class GaokaoDataClient:
    """阳光高考数据查询客户端"""

    BASE_URL = "https://gaokao.chsi.com.cn"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def search_universities(self, keyword: str = "", province: str = "", tier: str = "") -> List[Dict[str, Any]]:
        """搜索院校信息

        Args:
            keyword: 院校名称关键词
            province: 省份筛选
            tier: 层次筛选 (985/211/双一流/普通)

        Returns:
            [{"name": "清华大学", "province": "北京市", "tier": "985", ...}]
        """
        # 构建搜索URL
        url = f"{self.BASE_URL}/sch/search?"
        params = []
        if keyword:
            params.append(f"schname={quote_plus(keyword)}")
        if province:
            params.append(f"province={quote_plus(province)}")
        if tier:
            params.append(f"schtype={quote_plus(tier)}")
        url += "&".join(params)

        try:
            request = Request(url=url, headers=self._headers(), method="GET")
            with urlopen(request, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            return self._parse_university_list(body)
        except Exception as e:
            logger.debug("阳光高考院校查询失败: %s", e)
            return []

    def get_university_detail(self, sch_id: str) -> Dict[str, Any]:
        """获取院校详情"""
        url = f"{self.BASE_URL}/sch/{sch_id}"
        try:
            request = Request(url=url, headers=self._headers(), method="GET")
            with urlopen(request, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            return self._parse_university_detail(body, sch_id)
        except Exception as e:
            logger.debug("阳光高考院校详情查询失败: %s", e)
            return {}

    def search_majors(self, keyword: str = "", category: str = "") -> List[Dict[str, Any]]:
        """搜索专业信息

        Args:
            keyword: 专业名称关键词
            category: 专业类别 (工学/理学/医学/文学/...)

        Returns:
            [{"name": "计算机科学与技术", "code": "080901", "category": "工学", ...}]
        """
        url = f"{self.BASE_URL}/zyk/search?"
        params = []
        if keyword:
            params.append(f"zymc={quote_plus(keyword)}")
        if category:
            params.append(f"yxdm={quote_plus(category)}")
        url += "&".join(params)

        try:
            request = Request(url=url, headers=self._headers(), method="GET")
            with urlopen(request, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            return self._parse_major_list(body)
        except Exception as e:
            logger.debug("阳光高考专业查询失败: %s", e)
            return []

    def get_province_policies(self, province: str = "") -> List[Dict[str, Any]]:
        """查询招生政策（阳光高考政策库）

        Args:
            province: 省份名称，留空查全国

        Returns:
            [{"title": "...", "province": "...", "date": "...", "summary": "..."}]
        """
        url = f"{self.BASE_URL}/gkxx/zc/"
        if province:
            url += f"?province={quote_plus(province)}"

        try:
            request = Request(url=url, headers=self._headers(), method="GET")
            with urlopen(request, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            return self._parse_policies(body)
        except Exception as e:
            logger.debug("阳光高考政策查询失败: %s", e)
            return []

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _parse_university_list(self, html: str) -> List[Dict[str, Any]]:
        """解析院校列表HTML"""
        results = []
        # 匹配院校卡片
        pattern = re.compile(
            r'<a[^>]*href="/sch/([^"]+)"[^>]*>.*?<h4[^>]*>([^<]+)</h4>.*?'
            r'<span[^>]*>([^<]*)</span>.*?<span[^>]*>([^<]*)</span>',
            re.DOTALL
        )
        for match in pattern.finditer(html):
            sch_id, name, province, tier = match.groups()
            results.append({
                "sch_id": sch_id.strip("/"),
                "name": name.strip(),
                "province": province.strip(),
                "tier": tier.strip(),
                "source": "阳光高考",
            })
        return results

    def _parse_university_detail(self, html: str, sch_id: str) -> Dict[str, Any]:
        """解析院校详情HTML"""
        result = {"sch_id": sch_id, "source": "阳光高考"}

        # 提取院校名称
        name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if name_match:
            result["name"] = name_match.group(1).strip()

        # 提取层次
        tier_match = re.search(r'院校类型[：:]?\s*([^<\n]+)', html)
        if tier_match:
            result["tier"] = tier_match.group(1).strip()

        # 提取城市
        city_match = re.search(r'所属地区[：:]?\s*([^<\n]+)', html)
        if city_match:
            result["city"] = city_match.group(1).strip()

        return result

    def _parse_major_list(self, html: str) -> List[Dict[str, Any]]:
        """解析专业列表HTML"""
        results = []
        pattern = re.compile(
            r'<a[^>]*href="/zyk/zy/detail/([^"]+)"[^>]*>.*?<span[^>]*>([^<]+)</span>.*?'
            r'<span[^>]*>([^<]*)</span>',
            re.DOTALL
        )
        for match in pattern.finditer(html):
            zy_id, name, category = match.groups()
            results.append({
                "zy_id": zy_id.strip("/"),
                "name": name.strip(),
                "category": category.strip(),
                "source": "阳光高考",
            })
        return results

    def _parse_policies(self, html: str) -> List[Dict[str, Any]]:
        """解析政策列表HTML"""
        results = []
        pattern = re.compile(
            r'<a[^>]*href="(/gkxx/zc/[^"]+)"[^>]*>([^<]+)</a>.*?'
            r'<span[^>]*>([^<]*)</span>',
            re.DOTALL
        )
        for match in pattern.finditer(html):
            url, title, date = match.groups()
            results.append({
                "title": title.strip(),
                "url": f"{self.BASE_URL}{url}",
                "date": date.strip(),
                "source": "阳光高考",
            })
        return results


# 全局实例
_client: Optional[GaokaoDataClient] = None


def get_gaokao_client() -> GaokaoDataClient:
    global _client
    if _client is None:
        _client = GaokaoDataClient()
    return _client
