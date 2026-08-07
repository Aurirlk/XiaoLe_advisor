"""
GraphRAG - 知识图谱增强检索（增强版 V2）

结合Neo4j知识图谱和ChromaDB向量检索，实现多跳查询和图嵌入检索。

新增：
- 城市×行业薪资查询
- 专业→技术→行业链路查询
- 政策→专业关联查询

⚠️ 状态标注（2026-08-06 架构拷打）：本模块当前【零调用方】——
生产链路里 Neo4j 查询由 match_agent（院校/分数）与 career_agent（职业路径）
各自直连 kg_client/neo4j_tools 实现，未走本模块。候选方向：把
match_agent/career_agent 的 Cypher 收敛到本模块（与 P1-13 Neo4j 客户端
收敛合并推进），作为"专业→技术→行业"多跳链路的统一出口。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]


class Neo4jClient:
    """Neo4j客户端封装"""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        import os
        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        # 不允许弱默认密码；未配置时连接自然失败并走已有的 WARN 分支
        self._password = password or os.getenv("NEO4J_PASSWORD", "")
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            except Exception as e:
                print(f"[WARN] Neo4j连接失败: {e}")
                return None
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def query(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        driver = self._get_driver()
        if not driver:
            return []
        try:
            with driver.session() as session:
                result = session.run(cypher, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            print(f"[WARN] Neo4j查询失败: {e}")
            return []

    def health_check(self) -> bool:
        driver = self._get_driver()
        if not driver:
            return False
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False


class GraphRAGEngine:
    """
    GraphRAG引擎 - 结合知识图谱和向量检索

    支持:
    1. 图谱查询: 多跳关系查询
    2. 子图检索: 提取相关子图
    3. 城市薪资对比
    4. 专业→技术→行业链路
    """

    def __init__(self, neo4j_client: Optional[Neo4jClient] = None, vector_store=None):
        self._neo4j = neo4j_client or Neo4jClient()
        self._vector_store = vector_store

    def _extract_subgraph(self, entity_name: str, depth: int = 2, limit: int = 50) -> Dict[str, Any]:
        """提取实体相关的子图"""
        cypher = """
        MATCH (start {name: $name})
        CALL apoc.path.subgraphAll(start, {maxLevel: $depth})
        YIELD nodes, relationships
        RETURN
            [n IN nodes | {id: elementId(n), labels: labels(n), properties: properties(n)}] as nodes,
            [r IN relationships | {id: elementId(r), type: type(r), start: elementId(startNode(r)), end: elementId(endNode(r))}] as relationships
        LIMIT $limit
        """
        results = self._neo4j.query(cypher, {"name": entity_name, "depth": depth, "limit": limit})
        return results[0] if results else {"nodes": [], "relationships": []}

    def query_city_salary(self, city1: str, city2: str, industry: str = "") -> List[Dict[str, Any]]:
        """城市×行业薪资对比"""
        cypher = """
        MATCH (c:City)-[:HAS_SALARY]->(s:CityIndustrySalary)-[:FOR_INDUSTRY]->(i:Industry)
        WHERE c.name IN [$city1, $city2]
        """
        params = {"city1": city1, "city2": city2}
        if industry:
            cypher += " AND i.name CONTAINS $industry "
            params["industry"] = industry
        cypher += """
        RETURN c.name AS city, i.name AS industry,
               s.avg_salary AS avg, s.median_salary AS median, s.p90_salary AS p90
        ORDER BY c.name, s.avg_salary DESC
        """
        return self._neo4j.query(cypher, params)

    def query_major_technology(self, major_name: str) -> List[Dict[str, Any]]:
        """专业→技术→行业链路"""
        cypher = """
        MATCH (m:Major {name: $major})-[:REQUIRES]->(t:Technology)
        OPTIONAL MATCH (t)-[:DRIVES]->(i:Industry)
        RETURN t.name AS tech, t.field AS field, t.maturity AS maturity,
               collect(DISTINCT i.name) AS industries
        """
        return self._neo4j.query(cypher, {"major": major_name})

    def query_policy_by_province(self, province: str) -> List[Dict[str, Any]]:
        """查询省份相关政策"""
        cypher = """
        MATCH (p:Policy)-[:HAS_POLICY]->(c:City)
        WHERE c.province = $province OR p.province = $province
        RETURN p.name AS name, p.type AS type, p.description AS desc,
               p.eligibility AS eligibility, p.amount AS amount
        """
        return self._neo4j.query(cypher, {"province": province})

    def search(self, query: str, entity_name: Optional[str] = None, top_k: int = 5) -> List[Dict[str, str]]:
        """GraphRAG检索 - 结合图谱和向量检索"""
        results = []

        # 1. 向量检索
        if self._vector_store:
            try:
                vector_results = self._vector_store.query(query, top_k=top_k)
                results.extend(vector_results)
            except Exception:
                pass

        # 2. 图谱检索
        if entity_name:
            subgraph = self._extract_subgraph(entity_name, depth=2)
            graph_text = self._subgraph_to_text(subgraph)
            if graph_text:
                results.append({"source": f"graph:{entity_name}", "text": graph_text})

        # 3. 去重
        seen = set()
        unique = []
        for doc in results:
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            if key not in seen:
                seen.add(key)
                unique.append(doc)
        return unique[:top_k]

    def _subgraph_to_text(self, subgraph: Dict[str, Any]) -> str:
        nodes = subgraph.get("nodes", [])
        relationships = subgraph.get("relationships", [])
        if not nodes:
            return ""
        node_texts = []
        for node in nodes[:10]:
            props = node.get("properties", {})
            name = props.get("name", "")
            labels = node.get("labels", [])
            if name:
                node_texts.append(f"{name} ({', '.join(labels)})")
        rel_texts = list({r.get("type", "") for r in relationships[:10] if r.get("type")})
        parts = []
        if node_texts:
            parts.append(f"相关实体: {', '.join(node_texts)}")
        if rel_texts:
            parts.append(f"关系类型: {', '.join(rel_texts)}")
        return '; '.join(parts)

    def health_check(self) -> Dict[str, Any]:
        neo4j_ok = self._neo4j.health_check()
        vector_ok = self._vector_store is not None
        return {
            "neo4j_connected": neo4j_ok,
            "vector_store_ready": vector_ok,
            "status": "ready" if (neo4j_ok or vector_ok) else "degraded",
        }
