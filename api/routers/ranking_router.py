"""院校排名API路由"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/ranking", tags=["ranking"])

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "ranking_data.json"


class UniversityRank(BaseModel):
    rank: int
    name: str
    nameEn: str
    country: str
    flag: str
    score: float
    type: str
    website: str


class RankingResponse(BaseModel):
    source: str
    name: str
    description: str
    url: str
    universities: list[UniversityRank]
    total: int


def _load_ranking_data() -> dict:
    """加载排名数据"""
    if not DATA_PATH.exists():
        raise HTTPException(status_code=500, detail="排名数据文件不存在")
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载排名数据失败: {e}")


@router.get("/{source}", response_model=RankingResponse)
async def get_ranking(
    source: str,
    country: Optional[str] = Query(None, description="按国家筛选"),
    keyword: Optional[str] = Query(None, description="按关键词搜索"),
):
    """获取指定排名来源的院校排名"""
    data = _load_ranking_data()
    
    if source not in data:
        available = list(data.keys())
        raise HTTPException(status_code=404, detail=f"排名来源 '{source}' 不存在，可用: {available}")
    
    ranking_info = data[source]
    universities = ranking_info["universities"]
    
    # 按国家筛选
    if country:
        country_lower = country.lower()
        universities = [u for u in universities if country_lower in u["country"].lower() or country_lower in u.get("flag", "").lower()]
    
    # 按关键词搜索
    if keyword:
        keyword_lower = keyword.lower()
        universities = [u for u in universities if keyword_lower in u["name"].lower() or keyword_lower in u["nameEn"].lower()]
    
    return RankingResponse(
        source=source,
        name=ranking_info["name"],
        description=ranking_info["description"],
        url=ranking_info["url"],
        universities=universities,
        total=len(universities),
    )


@router.get("/")
async def list_ranking_sources():
    """列出所有可用的排名来源"""
    data = _load_ranking_data()
    sources = []
    for key, value in data.items():
        sources.append({
            "id": key,
            "name": value["name"],
            "description": value["description"],
            "url": value["url"],
            "university_count": len(value["universities"]),
        })
    return {"sources": sources, "total": len(sources)}
