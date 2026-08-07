"""
知识图谱客户端 - 使用 Neo4j 实现
"""
import json
import os
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase


class KnowledgeGraphClient:
    """知识图谱客户端（Neo4j版本）"""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        if uri is None:
            uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        if user is None:
            user = os.getenv("NEO4J_USER", "neo4j")
        if password is None:
            password = os.getenv("NEO4J_PASSWORD", "")
        
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None
        self._connected = False
    
    def _get_driver(self):
        """获取Neo4j驱动"""
        if self._driver is None:
            if not self.password:
                # fail-fast：拒绝用空/弱默认密码连接（原 P0-1 同类问题）
                raise RuntimeError("NEO4J_PASSWORD 未配置，无法连接知识图谱")
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._driver = None
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            driver = self._get_driver()
            with driver.session() as session:
                result = session.run("RETURN 1 AS test")
                self._connected = True
                return True
        except Exception as e:
            print(f"Neo4j连接失败: {e}")
            self._connected = False
            return False
    
    def query(self, query_type: str, **params) -> List[Dict]:
        """查询知识图谱"""
        driver = self._get_driver()
        
        with driver.session() as session:
            if query_type == "city_info":
                return self._query_city_info(session, params.get("city_name"))
            elif query_type == "industry_info":
                return self._query_industry_info(session, params.get("industry_name"))
            elif query_type == "salary_by_city":
                return self._query_salary_by_city(session, params.get("city_name"))
            elif query_type == "technology_related_majors":
                return self._query_technology_majors(session, params.get("tech_name"))
            elif query_type == "policies_by_city":
                return self._query_policies_by_city(session, params.get("city_name"))
            elif query_type == "cities_by_tier":
                return self._query_cities_by_tier(session, params.get("tier"))
            elif query_type == "industries_by_sector":
                return self._query_industries_by_sector(session, params.get("sector"))
            elif query_type == "university_info":
                return self._query_university_info(session, params.get("university_name"))
            elif query_type == "major_info":
                return self._query_major_info(session, params.get("major_name"))
            elif query_type == "universities_by_city":
                return self._query_universities_by_city(session, params.get("city_name"))
            elif query_type == "universities_by_tier":
                return self._query_universities_by_tier(session, params.get("tier"))
            elif query_type == "universities_by_province":
                return self._query_universities_by_province(session, params.get("province"))
            elif query_type == "majors_by_category":
                return self._query_majors_by_category(session, params.get("category"))
            else:
                return [{"error": f"未知查询类型: {query_type}"}]
    
    def _query_city_info(self, session, city_name: str) -> List[Dict]:
        """查询城市信息"""
        result = session.run("""
            MATCH (c:City {name: $city_name})
            OPTIONAL MATCH (c)<-[:IN_CITY]-(s:SalaryData)
            OPTIONAL MATCH (c)<-[:APPLIES_TO]-(p:Policy)
            OPTIONAL MATCH (c)<-[:IN_PROVINCE]-(u:University)
            RETURN c, 
                   collect(DISTINCT s) as salaries,
                   collect(DISTINCT p) as policies,
                   collect(DISTINCT u) as universities
        """, city_name=city_name)
        
        record = result.single()
        if not record:
            return [{"error": f"城市 {city_name} 不存在"}]
        
        city = dict(record["c"])
        salaries = [dict(s) for s in record["salaries"]]
        policies = [dict(p) for p in record["policies"]]
        universities = [dict(u) for u in record["universities"]]
        
        return [{
            "city": city,
            "salary_data": salaries,
            "policies": policies,
            "universities": universities[:20]  # 限制返回数量
        }]
    
    def _query_industry_info(self, session, industry_name: str) -> List[Dict]:
        """查询行业信息"""
        result = session.run("""
            MATCH (i:Industry {name: $industry_name})
            OPTIONAL MATCH (i)<-[:FOR_INDUSTRY]-(s:SalaryData)
            RETURN i, collect(DISTINCT s) as salaries
        """, industry_name=industry_name)
        
        record = result.single()
        if not record:
            return [{"error": f"行业 {industry_name} 不存在"}]
        
        industry = dict(record["i"])
        salaries = [dict(s) for s in record["salaries"]]
        
        return [{
            "industry": industry,
            "salary_data": salaries
        }]
    
    def _query_salary_by_city(self, session, city_name: str) -> List[Dict]:
        """查询城市薪资数据"""
        result = session.run("""
            MATCH (s:SalaryData)-[:IN_CITY]->(c:City {name: $city_name})
            RETURN s
        """, city_name=city_name)
        
        return [dict(record["s"]) for record in result]
    
    def _query_technology_majors(self, session, tech_name: str) -> List[Dict]:
        """查询技术相关专业"""
        result = session.run("""
            MATCH (t:Technology {name: $tech_name})-[:RELATED_TO]->(m:Major)
            RETURN t, collect(m) as majors
        """, tech_name=tech_name)
        
        record = result.single()
        if not record:
            return [{"error": f"技术 {tech_name} 不存在"}]
        
        tech = dict(record["t"])
        majors = [dict(m) for m in record["majors"]]
        
        return [{
            "technology": tech,
            "related_majors": majors
        }]
    
    def _query_policies_by_city(self, session, city_name: str) -> List[Dict]:
        """查询城市政策"""
        result = session.run("""
            MATCH (p:Policy)-[:APPLIES_TO]->(c:City {name: $city_name})
            RETURN p
        """, city_name=city_name)
        
        return [dict(record["p"]) for record in result]
    
    def _query_cities_by_tier(self, session, tier: str) -> List[Dict]:
        """查询某等级城市"""
        result = session.run("""
            MATCH (c:City {tier: $tier})
            RETURN c
            ORDER BY c.name
        """, tier=tier)
        
        return [dict(record["c"]) for record in result]
    
    def _query_industries_by_sector(self, session, sector: str) -> List[Dict]:
        """查询某部门行业"""
        result = session.run("""
            MATCH (i:Industry {sector: $sector})
            RETURN i
            ORDER BY i.name
        """, sector=sector)
        
        return [dict(record["i"]) for record in result]
    
    def _query_university_info(self, session, university_name: str) -> List[Dict]:
        """查询院校信息"""
        result = session.run("""
            MATCH (u:University {name: $university_name})
            OPTIONAL MATCH (u)-[:IN_PROVINCE]->(p:Province)
            RETURN u, p
        """, university_name=university_name)
        
        record = result.single()
        if not record:
            return [{"error": f"院校 {university_name} 不存在"}]
        
        uni = dict(record["u"])
        province = dict(record["p"]) if record["p"] else None
        
        return [{
            "university": uni,
            "province": province
        }]
    
    def _query_major_info(self, session, major_name: str) -> List[Dict]:
        """查询专业信息"""
        result = session.run("""
            MATCH (m:Major {name: $major_name})
            OPTIONAL MATCH (m)-[:BELONGS_TO]->(c:Category)
            OPTIONAL MATCH (t:Technology)-[:RELATED_TO]->(m)
            RETURN m, c, collect(DISTINCT t) as technologies
        """, major_name=major_name)
        
        record = result.single()
        if not record:
            return [{"error": f"专业 {major_name} 不存在"}]
        
        major = dict(record["m"])
        category = dict(record["c"]) if record["c"] else None
        technologies = [dict(t) for t in record["technologies"]]
        
        return [{
            "major": major,
            "category": category,
            "related_technologies": technologies
        }]
    
    def _query_universities_by_city(self, session, city_name: str) -> List[Dict]:
        """查询某城市院校"""
        result = session.run("""
            MATCH (u:University)-[:IN_PROVINCE]->(p:Province)<-[:IN_PROVINCE]-(c:City {name: $city_name})
            RETURN u
            ORDER BY u.name
            LIMIT 50
        """, city_name=city_name)
        
        return [dict(record["u"]) for record in result]
    
    def _query_universities_by_tier(self, session, tier: str) -> List[Dict]:
        """查询某等级院校"""
        result = session.run("""
            MATCH (u:University)
            WHERE u.tags CONTAINS $tier
            RETURN u
            ORDER BY u.name
            LIMIT 100
        """, tier=tier)
        
        return [dict(record["u"]) for record in result]
    
    def _query_universities_by_province(self, session, province: str) -> List[Dict]:
        """查询某省份院校"""
        result = session.run("""
            MATCH (u:University)-[:IN_PROVINCE]->(p:Province {name: $province})
            RETURN u
            ORDER BY u.name
        """, province=province)
        
        return [dict(record["u"]) for record in result]
    
    def _query_majors_by_category(self, session, category: str) -> List[Dict]:
        """查询某门类专业"""
        result = session.run("""
            MATCH (m:Major)-[:BELONGS_TO]->(c:Category {name: $category})
            RETURN m
            ORDER BY m.name
        """, category=category)
        
        return [dict(record["m"]) for record in result]
    
    def get_stats(self) -> Dict:
        """获取图谱统计信息"""
        driver = self._get_driver()
        
        with driver.session() as session:
            # 节点统计
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY count DESC
            """)
            node_types = {record["label"]: record["count"] for record in result}
            
            # 关系统计
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(r) AS count
                ORDER BY count DESC
            """)
            edge_types = {record["type"]: record["count"] for record in result}
            
            total_nodes = sum(node_types.values())
            total_edges = sum(edge_types.values())
            
            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_types": node_types,
                "edge_types": edge_types
            }


# 全局实例
kg_client = KnowledgeGraphClient()
