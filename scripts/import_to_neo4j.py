"""
将知识图谱数据从JSON文件导入Neo4j
"""
import json
import os
from neo4j import GraphDatabase


def import_to_neo4j():
    """导入所有数据到Neo4j"""
    # 连接Neo4j
    uri = "neo4j://127.0.0.1:7687"
    user = "neo4j"
    password = "zx_advisor_2026"
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    with driver.session() as session:
        # 清空数据库
        print("清空数据库...")
        session.run("MATCH (n) DETACH DELETE n")
        
        # 1. 导入城市数据
        print("\n导入城市数据...")
        cities_file = os.path.join(base_dir, "data", "neo4j", "cities.json")
        if os.path.exists(cities_file):
            with open(cities_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for city in data.get("cities", []):
                session.run("""
                    MERGE (c:City {name: $name})
                    SET c.province = $province, c.tier = $tier
                """, name=city["name"], province=city["province"], tier=city["tier"])
                
                # 创建省份节点和关系
                session.run("""
                    MERGE (p:Province {name: $province})
                    WITH p
                    MATCH (c:City {name: $city_name})
                    MERGE (c)-[:IN_PROVINCE]->(p)
                """, province=city["province"], city_name=city["name"])
            
            print(f"  导入 {len(data.get('cities', []))} 个城市")
        
        # 2. 导入行业数据
        print("\n导入行业数据...")
        industries_file = os.path.join(base_dir, "data", "neo4j", "industries.json")
        if os.path.exists(industries_file):
            with open(industries_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for industry in data.get("industries", []):
                session.run("""
                    MERGE (i:Industry {name: $name})
                    SET i.sector = $sector, i.growth = $growth, i.avg_salary = $avg_salary
                """, name=industry["name"], sector=industry.get("sector", ""),
                    growth=industry.get("growth", ""), avg_salary=industry.get("avg_salary_national", 0))
            
            print(f"  导入 {len(data.get('industries', []))} 个行业")
        
        # 3. 导入技术数据
        print("\n导入技术数据...")
        tech_file = os.path.join(base_dir, "data", "neo4j", "technologies.json")
        if os.path.exists(tech_file):
            with open(tech_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for tech in data.get("technologies", []):
                session.run("""
                    MERGE (t:Technology {name: $name})
                    SET t.field = $field, t.maturity = $maturity
                """, name=tech["name"], field=tech.get("field", ""),
                    maturity=tech.get("maturity", ""))
                
                # 创建技术-专业关系
                for major in tech.get("related_majors", []):
                    session.run("""
                        MERGE (m:Major {name: $major_name})
                        WITH m
                        MATCH (t:Technology {name: $tech_name})
                        MERGE (t)-[:RELATED_TO]->(m)
                    """, major_name=major, tech_name=tech["name"])
            
            print(f"  导入 {len(data.get('technologies', []))} 个技术")
        
        # 4. 导入政策数据
        print("\n导入政策数据...")
        policies_file = os.path.join(base_dir, "data", "neo4j", "policies.json")
        if os.path.exists(policies_file):
            with open(policies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for policy in data.get("policies", []):
                session.run("""
                    MERGE (p:Policy {name: $name})
                    SET p.city = $city, p.province = $province, 
                        p.type = $type, p.description = $description,
                        p.eligibility = $eligibility, p.amount = $amount
                """, name=policy["name"], city=policy.get("city", ""),
                    province=policy.get("province", ""), type=policy.get("type", ""),
                    description=policy.get("description", ""),
                    eligibility=policy.get("eligibility", ""),
                    amount=policy.get("amount", 0))
                
                # 创建政策-城市关系
                if policy.get("city") and policy["city"] != "全国":
                    session.run("""
                        MATCH (p:Policy {name: $policy_name})
                        MATCH (c:City {name: $city_name})
                        MERGE (p)-[:APPLIES_TO]->(c)
                    """, policy_name=policy["name"], city_name=policy["city"])
            
            print(f"  导入 {len(data.get('policies', []))} 个政策")
        
        # 5. 导入薪资数据
        print("\n导入薪资数据...")
        salary_file = os.path.join(base_dir, "data", "neo4j", "salary_data.json")
        if os.path.exists(salary_file):
            with open(salary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for salary in data.get("salary_data", []):
                session.run("""
                    MERGE (s:SalaryData {city: $city, industry: $industry})
                    SET s.avg = $avg, s.median = $median, s.p90 = $p90, s.year = $year
                """, city=salary["city"], industry=salary["industry"],
                    avg=salary.get("avg", 0), median=salary.get("median", 0),
                    p90=salary.get("p90", 0), year=salary.get("year", 2025))
                
                # 创建薪资-城市关系
                session.run("""
                    MATCH (s:SalaryData {city: $city, industry: $industry})
                    MATCH (c:City {name: $city})
                    MERGE (s)-[:IN_CITY]->(c)
                """, city=salary["city"], industry=salary["industry"])
                
                # 创建薪资-行业关系
                session.run("""
                    MATCH (s:SalaryData {city: $city, industry: $industry})
                    MATCH (i:Industry {name: $industry})
                    MERGE (s)-[:FOR_INDUSTRY]->(i)
                """, city=salary["city"], industry=salary["industry"])
            
            print(f"  导入 {len(data.get('salary_data', []))} 条薪资数据")
        
        # 6. 导入院校数据
        print("\n导入院校数据...")
        unis_file = os.path.join(base_dir, "data", "crawl_results", "universities", "all_universities.json")
        if os.path.exists(unis_file):
            with open(unis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for uni in data.get("universities", []):
                session.run("""
                    MERGE (u:University {name: $name})
                    SET u.province = $province, u.admin = $admin,
                        u.level = $level, u.tags = $tags, u.satisfaction = $satisfaction
                """, name=uni["name"], province=uni.get("province", ""),
                    admin=uni.get("admin", ""), level=uni.get("level", ""),
                    tags=uni.get("tags", ""), satisfaction=uni.get("satisfaction", 0))
                
                # 创建院校-省份关系
                if uni.get("province"):
                    session.run("""
                        MATCH (u:University {name: $uni_name})
                        MATCH (p:Province {name: $province})
                        MERGE (u)-[:IN_PROVINCE]->(p)
                    """, uni_name=uni["name"], province=uni["province"])
            
            print(f"  导入 {len(data.get('universities', []))} 所院校")
        
        # 7. 导入专业数据
        print("\n导入专业数据...")
        majors_file = os.path.join(base_dir, "data", "crawl_results", "majors", "all_majors.json")
        if os.path.exists(majors_file):
            with open(majors_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for major in data.get("majors", []):
                name = major.get("zymc", major.get("name", ""))
                code = major.get("zydm", major.get("code", ""))
                category = major.get("category", "")
                
                if not name:
                    continue
                
                session.run("""
                    MERGE (m:Major {name: $name})
                    SET m.code = $code, m.category = $category
                """, name=name, code=code, category=category)
                
                # 创建专业-门类关系
                if category:
                    session.run("""
                        MERGE (c:Category {name: $category})
                        WITH c
                        MATCH (m:Major {name: $major_name})
                        MERGE (m)-[:BELONGS_TO]->(c)
                    """, category=category, major_name=name)
            
            print(f"  导入 {len(data.get('majors', []))} 个专业")
        
        # 统计
        print("\n=== 导入完成 ===")
        result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC")
        for record in result:
            print(f"  {record['label']}: {record['count']}")
        
        result = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC")
        print("\n关系统计:")
        for record in result:
            print(f"  {record['type']}: {record['count']}")
    
    driver.close()
    print("\nNeo4j数据导入完成！")


if __name__ == "__main__":
    import_to_neo4j()
