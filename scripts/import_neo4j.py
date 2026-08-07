"""
Neo4j 数据导入脚本（增强版 V2）
从SQLite导入现有数据 + 种子数据到Neo4j图谱

节点类型（10种）：University, Province, Major, Career, City, Industry, Technology, CityIndustrySalary, Policy, IndustryCluster
关系类型（10种）：LOCATED_IN, BELONGS_TO, OFFERS, LEADS_TO, REQUIRES, DRIVES, HAS_SALARY, FOR_INDUSTRY, APPLIES_TO, AFFECTS

用法:
    python scripts/import_neo4j.py

前置条件:
    1. 已启动Neo4j: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.15-community
    2. 已初始化SQLite: python scripts/init_sqlite.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "zx_advisor.db"
CONFIG_PATH = ROOT / "configs" / "neo4j_config.yaml"


def _load_neo4j_config() -> dict:
    """加载Neo4j配置（兼容无yaml环境）"""
    if not CONFIG_PATH.exists():
        return {"uri": "bolt://localhost:7687", "username": "neo4j", "password": "password"}
    
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("neo4j", {})
    except ImportError:
        # 无yaml时使用默认配置
        return {"uri": "bolt://localhost:7687", "username": "neo4j", "password": "password"}


def create_schema(driver) -> None:
    """创建Neo4j约束和索引"""
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:University) REQUIRE u.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Province) REQUIRE p.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Major) REQUIRE m.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Career) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ci:City) REQUIRE ci.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:Industry) REQUIRE i.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE")
        session.run("CREATE INDEX IF NOT EXISTS FOR (u:University) ON (u.level)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (o:OFFERS) ON (o.min_score)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (o:OFFERS) ON (o.year)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (s:CityIndustrySalary) ON (s.city)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (s:CityIndustrySalary) ON (s.year)")
    print("✓ Schema 创建完成")


def import_universities(driver, conn) -> int:
    """导入大学节点"""
    rows = conn.execute("SELECT name, tier, city, tags FROM universities").fetchall()
    with driver.session() as session:
        for row in rows:
            session.run("""
                MERGE (u:University {name: $name})
                SET u.level = $level, u.city = $city, u.tags = $tags
            """, name=row[0], level=row[1], city=row[2], tags=row[3])
    print(f"✓ 导入 {len(rows)} 所大学")
    return len(rows)


def import_provinces(driver, conn) -> int:
    """导入省份节点"""
    rows = conn.execute("SELECT DISTINCT province FROM admission_scores ORDER BY province").fetchall()
    provinces = [r[0] for r in rows]
    with driver.session() as session:
        for prov in provinces:
            session.run("MERGE (p:Province {name: $name})", name=prov)
    print(f"✓ 导入 {len(provinces)} 个省份")
    return len(provinces)


def import_majors(driver, conn) -> int:
    """导入专业节点"""
    rows = conn.execute("SELECT DISTINCT major_name FROM admission_scores ORDER BY major_name").fetchall()
    majors = [r[0] for r in rows]
    with driver.session() as session:
        for major in majors:
            session.run("MERGE (m:Major {name: $name})", name=major)
    print(f"✓ 导入 {len(majors)} 个专业")
    return len(majors)


def import_offers(driver, conn) -> int:
    """导入OFFERS关系（大学-专业-分数线）"""
    rows = conn.execute("""
        SELECT u.name, s.province, s.major_name, s.min_score, s.lowest_rank, s.year, s.subject_type
        FROM admission_scores s
        JOIN universities u ON u.id = s.university_id
        ORDER BY s.year DESC, s.min_score DESC
    """).fetchall()
    count = 0
    with driver.session() as session:
        for row in rows:
            session.run("""
                MATCH (u:University {name: $uni_name})
                MATCH (m:Major {name: $major})
                MERGE (u)-[o:OFFERS {year: $year, subject_type: $subject_type}]->(m)
                SET o.min_score = $score, o.min_rank = $rank
            """, uni_name=row[0], major=row[2], score=row[3], rank=row[4], year=row[5], subject_type=row[6])
            count += 1
    print(f"✓ 创建 {count} 条 OFFERS 关系")
    return count


def create_city_nodes(driver) -> int:
    """创建全国地级市节点（从 JSON 文件读取）"""
    cities_json = ROOT / "data" / "neo4j" / "cities.json"
    if not cities_json.exists():
        print(f"⚠ 城市数据文件不存在: {cities_json}")
        return 0
    with open(cities_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    cities = data.get("cities", [])
    tier_map = {"一线": 1, "新一线": 2, "二线": 3, "三线": 4, "四线": 5, "五线": 6}
    count = 0
    with driver.session() as session:
        for c in cities:
            name = c["name"]
            province = c["province"]
            tier = c["tier"]
            tier_rank = tier_map.get(tier, 5)
            session.run("""
                MERGE (ci:City {name: $name})
                SET ci.province = $province, ci.tier = $tier, ci.tier_rank = $tier_rank
            """, name=name, province=province, tier=tier, tier_rank=tier_rank)
            count += 1
    print(f"✓ 创建 {count} 个城市节点")
    return count


def create_city_province_relations(driver) -> int:
    """创建城市-省份关系"""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:City), (p:Province)
            WHERE c.province = p.name
            MERGE (c)-[:BELONGS_TO]->(p)
            RETURN count(*) as count
        """)
        count = result.single()["count"]
    print(f"✓ 创建 {count} 条 City-BELONGS_TO-Province 关系")
    return count


def create_university_city_relations(driver) -> int:
    """创建大学-城市关系"""
    with driver.session() as session:
        result = session.run("""
            MATCH (u:University), (c:City)
            WHERE u.city = c.name
            MERGE (u)-[:LOCATED_IN]->(c)
            RETURN count(*) as count
        """)
        count = result.single()["count"]
    print(f"✓ 创建 {count} 条 University-LOCATED_IN-City 关系")
    return count


def import_career_paths(driver) -> int:
    """导入职业路径（扩展版）"""
    career_paths = [
        # 计算机类
        ("计算机科学与技术", "软件工程师", "绿牌"),
        ("计算机科学与技术", "算法工程师", "绿牌"),
        ("计算机科学与技术", "数据分析师", "绿牌"),
        ("计算机科学与技术", "产品经理", "绿牌"),
        ("软件工程", "前端开发工程师", "绿牌"),
        ("软件工程", "后端开发工程师", "绿牌"),
        ("软件工程", "全栈工程师", "绿牌"),
        ("人工智能", "机器学习工程师", "绿牌"),
        ("人工智能", "NLP工程师", "绿牌"),
        ("人工智能", "计算机视觉工程师", "绿牌"),
        ("数据科学与大数据技术", "数据工程师", "绿牌"),
        ("数据科学与大数据技术", "数据分析师", "绿牌"),
        # 电子信息类
        ("电子信息工程", "硬件工程师", "绿牌"),
        ("电子信息工程", "嵌入式工程师", "绿牌"),
        ("通信工程", "通信工程师", "绿牌"),
        ("通信工程", "射频工程师", "绿牌"),
        # 医学类
        ("临床医学", "主治医师", "绿牌"),
        ("临床医学", "住院医师", "绿牌"),
        ("口腔医学", "口腔医师", "绿牌"),
        # 法学
        ("法学", "律师", "绿牌"),
        ("法学", "法官", "绿牌"),
        ("法学", "检察官", "绿牌"),
        ("法学", "法务", "绿牌"),
        # 财经类
        ("金融学", "金融分析师", "绿牌"),
        ("金融学", "投资银行分析师", "绿牌"),
        ("会计学", "注册会计师", "绿牌"),
        # 土木建筑
        ("土木工程", "结构工程师", "红牌"),
        ("土木工程", "施工员", "红牌"),
        ("建筑学", "建筑师", "红牌"),
        # 生化环材
        ("生物工程", "生物技术研究员", "红牌"),
        ("化学工程", "化工工程师", "红牌"),
        ("环境工程", "环境工程师", "红牌"),
        ("材料科学与工程", "材料研发工程师", "红牌"),
        # 文科
        ("汉语言文学", "文案策划", "红牌"),
        ("汉语言文学", "编辑", "红牌"),
        ("新闻学", "记者", "红牌"),
        ("新闻学", "新媒体运营", "红牌"),
        ("英语", "翻译", "红牌"),
        # 电气
        ("电气工程及其自动化", "电气工程师", "绿牌"),
        ("电气工程及其自动化", "自动化工程师", "绿牌"),
        # 机械
        ("机械工程", "机械工程师", "黄牌"),
        ("机械工程", "自动化工程师", "黄牌"),
    ]
    count = 0
    with driver.session() as session:
        for major, career, prospect in career_paths:
            session.run("""
                MERGE (m:Major {name: $major})
                MERGE (c:Career {name: $career})
                MERGE (m)-[:LEADS_TO]->(c)
                SET c.prospect = $prospect
            """, major=major, career=career, prospect=prospect)
            count += 1
    print(f"✓ 导入 {count} 条职业路径")
    return count


def import_industries(driver) -> int:
    """导入行业节点（从 JSON 文件读取）"""
    industries_json = ROOT / "data" / "neo4j" / "industries.json"
    if not industries_json.exists():
        print(f"⚠ 行业数据文件不存在: {industries_json}")
        return 0
    with open(industries_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    industries = data.get("industries", [])
    count = 0
    with driver.session() as session:
        for ind in industries:
            session.run("""
                MERGE (i:Industry {name: $name})
                SET i.sector = $sector, i.growth_trend = $growth, i.avg_salary_national = $salary
            """, name=ind["name"], sector=ind["sector"], growth=ind["growth"], salary=ind.get("avg_salary_national", 0))
            count += 1
    print(f"✓ 导入 {count} 个行业")
    return count


def import_technologies(driver) -> int:
    """导入前沿技术节点（从 JSON 文件读取）"""
    tech_json = ROOT / "data" / "neo4j" / "technologies.json"
    if not tech_json.exists():
        print(f"⚠ 技术数据文件不存在: {tech_json}")
        return 0
    with open(tech_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    technologies = data.get("technologies", [])
    count = 0
    with driver.session() as session:
        for tech in technologies:
            name = tech["name"]
            field = tech["field"]
            maturity = tech["maturity"]
            related_majors = tech.get("related_majors", [])
            session.run("""
                MERGE (t:Technology {name: $name})
                SET t.field = $field, t.maturity = $maturity
            """, name=name, field=field, maturity=maturity)
            for major in related_majors:
                session.run("""
                    MERGE (m:Major {name: $major})
                    MERGE (t:Technology {name: $tech})
                    MERGE (m)-[:REQUIRES]->(t)
                """, major=major, tech=name)
            count += 1
    print(f"✓ 导入 {count} 个前沿技术")
    return count


def import_industry_salary_by_city(driver) -> int:
    """导入城市×行业薪资数据（从 JSON 文件读取）"""
    salary_json = ROOT / "data" / "neo4j" / "salary_data.json"
    if not salary_json.exists():
        print(f"⚠ 薪资数据文件不存在: {salary_json}")
        return 0
    with open(salary_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    salary_data = data.get("salary_data", [])
    count = 0
    with driver.session() as session:
        for item in salary_data:
            city = item["city"]
            industry = item["industry"]
            avg = item["avg"]
            median = item["median"]
            p90 = item["p90"]
            year = item.get("year", 2025)
            source = item.get("source", "综合估算")
            session.run("""
                MERGE (c:City {name: $city})
                MERGE (i:Industry {name: $industry})
                CREATE (s:CityIndustrySalary {
                    city: $city, industry: $industry,
                    avg_salary: $avg, median_salary: $median, p90_salary: $p90,
                    year: $year, data_source: $source
                })
                MERGE (c)-[:HAS_SALARY]->(s)
                MERGE (s)-[:FOR_INDUSTRY]->(i)
            """, city=city, industry=industry, avg=avg, median=median, p90=p90, year=year, source=source)
            count += 1
    print(f"✓ 导入 {count} 条城市×行业薪资数据")
    return count


def import_major_industry_relations(driver) -> int:
    """导入专业→行业关系（新增）"""
    relations = [
        ("计算机科学与技术", "互联网/IT", "强"),
        ("计算机科学与技术", "人工智能", "强"),
        ("计算机科学与技术", "半导体/芯片", "中"),
        ("计算机科学与技术", "金融", "中"),
        ("软件工程", "互联网/IT", "强"),
        ("软件工程", "人工智能", "中"),
        ("人工智能", "人工智能", "强"),
        ("人工智能", "互联网/IT", "强"),
        ("人工智能", "自动驾驶", "强"),
        ("数据科学与大数据技术", "互联网/IT", "强"),
        ("数据科学与大数据技术", "金融", "中"),
        ("电子信息工程", "半导体/芯片", "强"),
        ("电子信息工程", "物联网", "强"),
        ("通信工程", "5G/6G通信", "强"),
        ("通信工程", "物联网", "中"),
        ("临床医学", "医疗健康", "强"),
        ("临床医学", "生物医药", "中"),
        ("口腔医学", "医疗健康", "强"),
        ("法学", "法律", "强"),
        ("金融学", "金融", "强"),
        ("会计学", "金融", "中"),
        ("土木工程", "房地产", "强"),
        ("土木工程", "建筑设计", "强"),
        ("建筑学", "建筑设计", "强"),
        ("环境工程", "碳中和技术", "强"),
        ("材料科学与工程", "半导体/芯片", "中"),
        ("材料科学与工程", "新能源", "中"),
        ("生物工程", "生物医药", "强"),
        ("生物工程", "合成生物", "强"),
        ("化学工程", "新能源", "中"),
        ("化学工程", "生物医药", "中"),
        ("电气工程及其自动化", "电力/能源", "强"),
        ("电气工程及其自动化", "新能源", "中"),
        ("机械工程", "汽车", "中"),
        ("机械工程", "机器人", "中"),
        ("新闻学", "传媒/广告", "强"),
        ("英语", "教育", "中"),
        ("汉语言文学", "教育", "中"),
        ("汉语言文学", "传媒/广告", "中"),
    ]
    count = 0
    with driver.session() as session:
        for major, industry, relevance in relations:
            session.run("""
                MERGE (m:Major {name: $major})
                MERGE (i:Industry {name: $industry})
                MERGE (m)-[r:LEADS_TO_INDUSTRY]->(i)
                SET r.relevance = $relevance
            """, major=major, industry=industry, relevance=relevance)
            count += 1
    print(f"✓ 导入 {count} 条专业→行业关系")
    return count


def import_policies(driver) -> int:
    """导入政策节点（从 JSON 文件读取）"""
    policy_json = ROOT / "data" / "neo4j" / "policies.json"
    if not policy_json.exists():
        print(f"⚠ 政策数据文件不存在: {policy_json}")
        return 0
    with open(policy_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    policies = data.get("policies", [])
    count = 0
    with driver.session() as session:
        for p in policies:
            name = p["name"]
            city = p["city"]
            province = p.get("province", "")
            ptype = p.get("type", "")
            desc = p.get("description", "")
            eligibility = p.get("eligibility", "")
            amount = p.get("amount", 0)
            session.run("""
                MERGE (p:Policy {name: $name})
                SET p.city = $city, p.province = $province, p.type = $ptype,
                    p.description = $desc, p.eligibility = $eligibility, p.amount = $amount,
                    p.is_current = true
                WITH p
                MATCH (c:City {name: $city})
                MERGE (c)-[:HAS_POLICY]->(p)
            """, name=name, city=city, province=province, ptype=ptype,
                 desc=desc, eligibility=eligibility, amount=amount)
            count += 1
    print(f"✓ 导入 {count} 个政策")
    return count


def get_stats(driver) -> dict:
    """获取图谱统计信息"""
    with driver.session() as session:
        stats = {}
        for label in ["University", "Province", "Major", "Career", "City", "Industry", "Technology", "CityIndustrySalary", "Policy"]:
            stats[label] = session.run(f"MATCH (n:{label}) RETURN count(n) as count").single()["count"]
        for rel in ["OFFERS", "LEADS_TO", "REQUIRES", "DRIVES", "HAS_SALARY", "FOR_INDUSTRY", "HAS_POLICY", "LOCATED_IN", "BELONGS_TO", "LEADS_TO_INDUSTRY"]:
            stats[rel] = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) as count").single()["count"]
    return stats


def main():
    print("=" * 50)
    print("Neo4j 数据导入脚本（增强版 V2）")
    print("=" * 50)

    if not DB_PATH.exists():
        print(f"✗ SQLite数据库不存在: {DB_PATH}")
        print("  请先运行: python scripts/init_sqlite.py")
        return

    try:
        cfg = _load_neo4j_config()
    except Exception as e:
        print(f"✗ 加载Neo4j配置失败: {e}")
        return

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            cfg.get("uri", "bolt://localhost:7687"),
            auth=(cfg.get("username", "neo4j"), cfg.get("password", "password")),
            encrypted=False
        )
        driver.verify_connectivity()
        print(f"✓ 已连接Neo4j: {cfg.get('uri')}")
    except Exception as e:
        print(f"✗ 连接Neo4j失败: {e}")
        return

    try:
        conn = sqlite3.connect(str(DB_PATH))
        create_schema(driver)

        print("\n开始导入数据...")
        # 基础节点
        import_universities(driver, conn)
        import_provinces(driver, conn)
        import_majors(driver, conn)
        create_city_nodes(driver)
        import_industries(driver)
        import_technologies(driver)
        import_career_paths(driver)

        # 关系
        import_offers(driver, conn)
        create_city_province_relations(driver)
        create_university_city_relations(driver)
        import_major_industry_relations(driver)

        # 薪资数据
        import_industry_salary_by_city(driver)

        # 政策
        import_policies(driver)

        conn.close()

        print("\n" + "=" * 50)
        print("导入完成！图谱统计：")
        print("=" * 50)
        stats = get_stats(driver)
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\n✓ 所有数据导入完成！")
        print("  访问Neo4j浏览器: http://localhost:7474")

    except Exception as e:
        print(f"✗ 导入过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()


if __name__ == "__main__":
    main()
