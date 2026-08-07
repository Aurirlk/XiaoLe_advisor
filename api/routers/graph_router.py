"""知识图谱API路由 - 使用 kg_client 连接 Neo4j"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/graph", tags=["graph"])


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    x: float = 0
    y: float = 0
    properties: Optional[dict] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


@router.get("/query", response_model=GraphResponse)
async def query_graph(
    query_type: str = Query("university", description="查询类型: university/major/city/career"),
    keyword: str = Query("", description="搜索关键词"),
    depth: int = Query(2, ge=1, le=3, description="查询深度"),
):
    """查询知识图谱"""
    from core.kg_client import kg_client
    
    # 根据查询类型调用对应方法
    if query_type == "university" and keyword:
        result = kg_client.query("university_info", university_name=keyword)
    elif query_type == "major" and keyword:
        result = kg_client.query("major_info", major_name=keyword)
    elif query_type == "city" and keyword:
        result = kg_client.query("city_info", city_name=keyword)
    elif query_type == "industry" and keyword:
        result = kg_client.query("industry_info", industry_name=keyword)
    else:
        # 返回统计信息
        stats = kg_client.get_stats()
        return GraphResponse(
            nodes=[],
            edges=[],
            total_nodes=stats["total_nodes"],
            total_edges=stats["total_edges"],
        )
    
    # 转换为图格式
    nodes = []
    edges = []
    
    if result and "error" not in result[0]:
        data = result[0]
        # 添加主节点
        main_id = f"{query_type}:{keyword}"
        nodes.append(GraphNode(
            id=main_id,
            label=keyword,
            type=query_type.capitalize(),
            properties=data.get(query_type, data.get("university", data.get("major", {})))
        ))
        
        # 添加关联节点
        for key, value in data.items():
            if isinstance(value, list):
                for i, item in enumerate(value[:10]):
                    if isinstance(item, dict):
                        item_name = item.get("name", f"{key}_{i}")
                        item_id = f"{key}:{item_name}"
                        nodes.append(GraphNode(
                            id=item_id,
                            label=item_name,
                            type=key.replace("_", " ").title()
                        ))
                        edges.append(GraphEdge(
                            id=f"{main_id}-{item_id}",
                            source=main_id,
                            target=item_id,
                            label=key
                        ))
    
    return GraphResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


@router.get("/health")
async def graph_health():
    """检查图谱服务状态"""
    from core.kg_client import kg_client
    
    try:
        stats = kg_client.get_stats()
        return {
            "neo4j_connected": kg_client._connected if hasattr(kg_client, '_connected') else False,
            "data_source": "neo4j" if kg_client._connected else "networkx",
            "total_nodes": stats["total_nodes"],
            "total_edges": stats["total_edges"],
            "node_types": stats["node_types"],
        }
    except Exception as e:
        return {
            "neo4j_connected": False,
            "data_source": "error",
            "error": str(e),
        }


@router.get("/stats")
async def graph_stats():
    """获取图谱统计信息"""
    from core.kg_client import kg_client
    
    try:
        return kg_client.get_stats()
    except Exception as e:
        return {"error": str(e)}
