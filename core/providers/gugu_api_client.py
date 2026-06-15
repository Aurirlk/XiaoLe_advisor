"""咕咕数据API客户端 - 高考数据接口封装"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional
import httpx

GUGU_API_BASE = "https://api.gugudata.com"
GUGU_API_KEY = os.getenv("GUGU_API_KEY", "")


class GuguApiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GUGU_API_KEY
        self.base_url = GUGU_API_BASE
        self.timeout = 10.0

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            else:
                response = await client.post(url, headers=headers, json=params)

            response.raise_for_status()
            return response.json()

    async def query_college_info(self, college_name: str) -> Dict[str, Any]:
        """查询院校基础信息（985/211/双一流）"""
        return await self._request("GET", "/metadata/collegeinfo", {"name": college_name})

    async def query_college_line(
        self,
        college_name: str,
        province: str,
        year: int = 2025,
        subject_type: str = "物理类",
    ) -> Dict[str, Any]:
        """查询院校录取分数线"""
        return await self._request(
            "GET",
            "/metadata/ceecollegeline",
            {
                "collegeName": college_name,
                "province": province,
                "year": year,
                "subjectType": subject_type,
            },
        )

    async def query_major_line(
        self,
        major_name: str,
        province: str,
        year: int = 2025,
        subject_type: str = "物理类",
    ) -> Dict[str, Any]:
        """查询专业录取分数线"""
        return await self._request(
            "GET",
            "/metadata/ceemajorline",
            {
                "majorName": major_name,
                "province": province,
                "year": year,
                "subjectType": subject_type,
            },
        )

    async def query_province_cutoff(
        self,
        province: str,
        year: int = 2025,
        subject_type: str = "物理类",
    ) -> Dict[str, Any]:
        """查询各省批次线"""
        return await self._request(
            "GET",
            "/metadata/ceeprovince",
            {
                "province": province,
                "year": year,
                "subjectType": subject_type,
            },
        )

    async def predict_admission(
        self,
        score: int,
        province: str,
        subject_type: str = "物理类",
        college_name: Optional[str] = None,
        major_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """录取概率预测（冲/稳/保）"""
        params = {
            "score": score,
            "province": province,
            "subjectType": subject_type,
        }
        if college_name:
            params["collegeName"] = college_name
        if major_name:
            params["majorName"] = major_name
        return await self._request("POST", "/ai/gaokao/predict", params)

    async def query_news(self, keyword: str = "高考", limit: int = 10) -> Dict[str, Any]:
        """查询高考资讯"""
        return await self._request("GET", "/news/gaokao", {"keyword": keyword, "limit": limit})

    async def query_policy(self, province: str, keyword: str = "") -> Dict[str, Any]:
        """查询招生政策"""
        return await self._request(
            "GET",
            "/ai/gaokao/policy",
            {"province": province, "keyword": keyword},
        )


gugu_client = GuguApiClient()
