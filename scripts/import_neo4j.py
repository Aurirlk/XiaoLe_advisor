"""
Neo4j 数据导入脚本
从SQLite导入现有数据到Neo4j图谱

用法:
    python scripts/import_neo4j.py

前置条件:
    1. 已启动Neo4j: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.15-community
    2. 已初始化SQLite: python scripts/init_sqlite.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "zx_advisor.db"
CONFIG_PATH = ROOT / "configs" / "neo4j_config.yaml"


def _load_neo4j_config() -> dict:
    """加载Neo4j配置"""
    import yaml
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Neo4j配置文件不存在: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("neo4j", {})


def create_schema(driver) -> None:
    """创建Neo4j约束和索引"""
    with driver.session() as session:
        # 唯一性约束
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:University) REQUIRE u.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Province) REQUIRE p.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Major) REQUIRE m.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Career) REQUIRE c.name IS UNIQUE")
        
        # 索引
        session.run("CREATE INDEX IF NOT EXISTS FOR (u:University) ON (u.level)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (o:OFFERS) ON (o.min_score)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (o:OFFERS) ON (o.year)")
    
    print("✓ Schema创建完成（约束+索引）")


def import_universities(driver, conn: sqlite3.Connection) -> int:
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


def import_provinces(driver, conn: sqlite3.Connection) -> int:
    """导入省份节点（从分数线数据提取）"""
    rows = conn.execute("SELECT DISTINCT province FROM admission_scores ORDER BY province").fetchall()
    provinces = [r[0] for r in rows]
    
    with driver.session() as session:
        for prov in provinces:
            session.run("MERGE (p:Province {name: $name})", name=prov)
    
    print(f"✓ 导入 {len(provinces)} 个省份")
    return len(provinces)


def import_majors(driver, conn: sqlite3.Connection) -> int:
    """导入专业节点"""
    rows = conn.execute("SELECT DISTINCT major_name FROM admission_scores ORDER BY major_name").fetchall()
    majors = [r[0] for r in rows]
    
    with driver.session() as session:
        for major in majors:
            session.run("MERGE (m:Major {name: $name})", name=major)
    
    print(f"✓ 导入 {len(majors)} 个专业")
    return len(majors)


def import_offers(driver, conn: sqlite3.Connection) -> int:
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
            """, 
                uni_name=row[0], 
                major=row[2], 
                score=row[3], 
                rank=row[4], 
                year=row[5], 
                subject_type=row[6]
            )
            count += 1
    
    print(f"✓ 创建 {count} 条OFFERS关系")
    return count


def import_career_paths(driver) -> int:
    """导入职业路径（预设数据）"""
    # 预设的职业路径数据
    career_paths = [
        # 计算机类
        ("计算机科学与技术", "软件工程师", "绿牌"),
        ("计算机科学与技术", "算法工程师", "绿牌"),
        ("计算机科学与技术", "数据分析师", "绿牌"),
        ("软件工程", "前端开发工程师", "绿牌"),
        ("软件工程", "后端开发工程师", "绿牌"),
        ("人工智能", "机器学习工程师", "绿牌"),
        ("数据科学与大数据技术", "数据工程师", "绿牌"),
        
        # 电子信息类
        ("电子信息工程", "硬件工程师", "绿牌"),
        ("通信工程", "通信工程师", "绿牌"),
        
        # 医学类
        ("临床医学", "主治医师", "绿牌"),
        ("口腔医学", "口腔医师", "绿牌"),
        
        # 法学
        ("法学", "律师", "绿牌"),
        ("法学", "法官", "绿牌"),
        ("法学", "检察官", "绿牌"),
        
        # 财经类
        ("金融学", "金融分析师", "绿牌"),
        ("会计学", "注册会计师", "绿牌"),
        
        # 土木建筑
        ("土木工程", "结构工程师", "红牌"),
        ("建筑学", "建筑师", "红牌"),
        
        # 生化环材
        ("生物工程", "生物技术研究员", "红牌"),
        ("化学工程", "化工工程师", "红牌"),
        ("环境工程", "环境工程师", "红牌"),
        ("材料科学与工程", "材料研发工程师", "红牌"),
        
        # 文科
        ("汉语言文学", "文案策划", "红牌"),
        ("新闻学", "记者", "红牌"),
        ("英语", "翻译", "红牌"),
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


def import_industry_clusters(driver) -> int:
    """导入产业集群节点"""
    clusters = [
        # 深圳
        ("南山科技园", "深圳", "科技", '["腾讯", "大疆", "百度", "字节跳动"]', 25000),
        ("福田金融中心", "深圳", "金融", '["平安", "招商银行", "国信证券"]', 22000),
        ("宝安制造业", "深圳", "制造", '["华为", "比亚迪", "立讯精密"]', 18000),
        ("龙华电子信息", "深圳", "电子", '["富士康", "华为终端", "小米"]', 16000),
        
        # 广州
        ("天河软件园", "广州", "软件", '["网易", "微信", "UC"]', 18000),
        ("黄埔开发区", "广州", "制造", '["广汽", "宝洁", "安利"]', 15000),
        ("南沙自贸区", "广州", "贸易", '["中铁", "中远海运"]', 14000),
        
        # 北京
        ("中关村", "北京", "科技", '["百度", "小米", "联想", "新浪"]', 28000),
        ("望京互联网", "北京", "互联网", '["美团", "陌陌", "雪球"]', 26000),
        ("亦庄开发区", "北京", "制造", '["京东方", "小米汽车"]', 20000),
        
        # 上海
        ("张江高科", "上海", "科技", '["中芯国际", "展讯", "ARM"]', 24000),
        ("陆家嘴金融", "上海", "金融", '["上交所", "浦发银行", "国泰君安"]', 25000),
        ("漕河泾开发区", "上海", "软件", '["微软", "腾讯", "字节"]', 22000),
        
        # 杭州
        ("未来科技城", "杭州", "互联网", '["阿里巴巴", "蚂蚁金服", "网易"]', 22000),
        ("滨江高新区", "杭州", "软件", '["海康威视", "大华", "网易"]', 20000),
        
        # 成都
        ("高新区软件园", "成都", "软件", '["腾讯", "阿里", "华为"]', 15000),
        ("天府新区", "成都", "科技", '["华为", "京东方"]', 14000),
        
        # 武汉
        ("光谷", "武汉", "光电", '["华工科技", "烽火通信", "长飞光纤"]', 14000),
        
        # 南京
        ("软件谷", "南京", "软件", '["华为", "中兴", "烽火"]', 16000),
        ("江北新区", "南京", "芯片", '["台积电", "紫光"]', 18000),
        
        # 西安
        ("高新区", "西安", "军工", '["中航工业", "航天四院", "三星"]', 13000),
    ]
    
    count = 0
    with driver.session() as session:
        for name, city, industry, companies, avg_salary in clusters:
            session.run("""
                MERGE (c:IndustryCluster {name: $name})
                SET c.city = $city, c.industry = $industry, 
                    c.core_companies = $companies, c.avg_salary = $salary
                WITH c
                MATCH (city:City {name: $city})
                MERGE (city)-[:HAS_CLUSTER]->(c)
            """, name=name, city=city, industry=industry, 
                 companies=companies, salary=avg_salary)
            count += 1
    
    print(f"✓ 导入 {count} 个产业集群")
    return count


def import_policies(driver) -> int:
    """导入就业政策节点"""
    policies = [
        # 深圳
        ("深圳孔雀计划", "深圳", "人才", "海外高层次人才引进计划", "硕士及以上", 1600000,
         "2026年 深圳市 孔雀计划 补贴 最新政策"),
        ("深圳新引进人才补贴", "深圳", "补贴", "新引进人才生活补贴", "本科及以上", 30000,
         "2026年 深圳市 新引进人才 补贴 最新政策"),
        ("深圳落户政策", "深圳", "落户", "全日制本科及以上可直接落户", "本科及以上", 0,
         "2026年 深圳市 落户 条件 最新政策"),
        
        # 广州
        ("广州人才绿卡", "广州", "人才", "人才绿卡制度", "符合产业需求", 0,
         "2026年 广州市 人才绿卡 申请条件"),
        ("广州租房补贴", "广州", "补贴", "新就业无房职工住房补贴", "本科及以上", 24000,
         "2026年 广州市 租房补贴 申请 最新政策"),
        
        # 杭州
        ("杭州人才补贴", "杭州", "补贴", "应届毕业生生活补贴", "硕士及以上", 100000,
         "2026年 杭州市 人才补贴 最新政策"),
        ("杭州落户政策", "杭州", "落户", "大专以上可直接落户", "大专及以上", 0,
         "2026年 杭州市 落户 条件 最新政策"),
        
        # 成都
        ("成都蓉漂计划", "成都", "人才", "蓉漂青年人才驿站", "毕业5年内", 0,
         "2026年 成都市 蓉漂计划 申请条件"),
        ("成都人才补贴", "成都", "补贴", "青年人才驿站7天免费住宿", "本科及以上", 0,
         "2026年 成都市 人才补贴 最新政策"),
        
        # 武汉
        ("武汉百万大学生留汉", "武汉", "人才", "大学生可八折买房租房", "全日制大学生", 0,
         "2026年 武汉市 大学生 买房优惠"),
        ("武汉落户政策", "武汉", "落户", "大学生可直接落户", "大专及以上", 0,
         "2026年 武汉市 落户 条件 最新政策"),
        
        # 南京
        ("南京人才安居", "南京", "住房", "人才安居办法", "硕士及以上", 0,
         "2026年 南京市 人才住房 政策"),
        
        # 西安
        ("西安人才新政", "西安", "人才", "西安人才新政23条", "全日制大学生", 0,
         "2026年 西安市 人才政策 最新"),
        ("西安落户政策", "西安", "落户", "大学生可直接落户", "全日制大学", 0,
         "2026年 西安市 落户 条件"),
    ]
    
    count = 0
    with driver.session() as session:
        for name, city, ptype, desc, eligibility, amount, keyword in policies:
            session.run("""
                MERGE (p:Policy {name: $name})
                SET p.city = $city, p.type = $ptype, p.description = $desc,
                    p.eligibility = $eligibility, p.amount = $amount,
                    p.search_keyword = $keyword, p.is_current = true
                WITH p
                MATCH (city:City {name: $city})
                MERGE (city)-[:HAS_POLICY]->(p)
            """, name=name, city=city, ptype=ptype, desc=desc, 
                 eligibility=eligibility, amount=amount, keyword=keyword)
            count += 1
    
    print(f"✓ 导入 {count} 个就业政策")
    return count


def create_city_nodes(driver) -> int:
    """创建城市节点"""
    cities = [
        "北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", 
        "南京", "西安", "苏州", "天津", "重庆", "长沙", "郑州",
    ]
    
    count = 0
    with driver.session() as session:
        for city in cities:
            session.run("MERGE (c:City {name: $name})", name=city)
            count += 1
    
    print(f"✓ 创建 {count} 个城市节点")
    return count


def get_stats(driver) -> dict:
    """获取图谱统计信息"""
    with driver.session() as session:
        uni_count = session.run("MATCH (u:University) RETURN count(u) as count").single()["count"]
        prov_count = session.run("MATCH (p:Province) RETURN count(p) as count").single()["count"]
        major_count = session.run("MATCH (m:Major) RETURN count(m) as count").single()["count"]
        career_count = session.run("MATCH (c:Career) RETURN count(c) as count").single()["count"]
        offers_count = session.run("MATCH ()-[o:OFFERS]->() RETURN count(o) as count").single()["count"]
        paths_count = session.run("MATCH ()-[r:LEADS_TO]->() RETURN count(r) as count").single()["count"]
        city_count = session.run("MATCH (c:City) RETURN count(c) as count").single()["count"]
        cluster_count = session.run("MATCH (c:IndustryCluster) RETURN count(c) as count").single()["count"]
        policy_count = session.run("MATCH (p:Policy) RETURN count(p) as count").single()["count"]
    
    return {
        "universities": uni_count,
        "provinces": prov_count,
        "cities": city_count,
        "majors": major_count,
        "careers": career_count,
        "industry_clusters": cluster_count,
        "policies": policy_count,
        "offers": offers_count,
        "career_paths": paths_count,
    }


def main():
    """主函数"""
    print("=" * 50)
    print("Neo4j 数据导入脚本")
    print("=" * 50)
    
    # 检查SQLite数据库
    if not DB_PATH.exists():
        print(f"✗ SQLite数据库不存在: {DB_PATH}")
        print("  请先运行: python scripts/init_sqlite.py")
        return
    
    # 加载配置
    try:
        cfg = _load_neo4j_config()
    except Exception as e:
        print(f"✗ 加载Neo4j配置失败: {e}")
        return
    
    # 连接Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            cfg.get("uri", "bolt://localhost:7687"),
            auth=(cfg.get("username", "neo4j"), cfg.get("password", "password"))
        )
        # 测试连接
        driver.verify_connectivity()
        print(f"✓ 已连接Neo4j: {cfg.get('uri')}")
    except Exception as e:
        print(f"✗ 连接Neo4j失败: {e}")
        print("  请确保Neo4j已启动: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.15-community")
        return
    
    try:
        # 连接SQLite
        conn = sqlite3.connect(str(DB_PATH))
        
        # 创建Schema
        create_schema(driver)
        
        # 导入数据
        print("\n开始导入数据...")
        import_universities(driver, conn)
        import_provinces(driver, conn)
        import_majors(driver, conn)
        import_offers(driver, conn)
        import_career_paths(driver)
        
        # 导入新增节点
        create_city_nodes(driver)
        import_industry_clusters(driver)
        import_policies(driver)
        
        conn.close()
        
        # 显示统计
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
