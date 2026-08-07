"""
知识库文档生成器

将爬取的专业和院校数据转换为 RAG 可用的知识库文档

运行方式：
python scripts/generate_knowledge_docs.py
"""
import json
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CRAWL_DIR = ROOT / "data" / "crawl_results"
DOCS_DIR = ROOT / "data" / "documents"


def generate_major_docs():
    """从爬取数据生成专业详解文档"""
    majors_file = CRAWL_DIR / "majors" / "all_majors.json"
    if not majors_file.exists():
        print("❌ 专业数据文件不存在，请先运行 crawl_majors.py")
        return 0
    
    data = json.loads(majors_file.read_text(encoding="utf-8"))
    majors = data.get("majors", [])
    
    # 按门类分组
    by_category = {}
    for major in majors:
        cat = major.get("category", "其他")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(major)
    
    count = 0
    output_dir = DOCS_DIR / "majors"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成每个门类的汇总文档
    for category, cat_majors in by_category.items():
        doc = f"# {category}类专业汇总\n\n"
        doc += f"共 {len(cat_majors)} 个专业\n\n"
        doc += "---\n\n"
        
        for major in cat_majors:
            name = major.get("name", "未知")
            code = major.get("code", "")
            degree = major.get("degree", "")
            duration = major.get("duration", "")
            subcategory = major.get("subcategory", "")
            
            doc += f"## {name}\n\n"
            doc += f"- **专业代码**: {code}\n"
            doc += f"- **所属门类**: {category}\n"
            doc += f"- **专业类**: {subcategory}\n"
            if degree:
                doc += f"- **授予学位**: {degree}\n"
            if duration:
                doc += f"- **修业年限**: {duration}\n"
            doc += "\n"
        
        filepath = output_dir / f"{category}类专业汇总.md"
        filepath.write_text(doc, encoding="utf-8")
        count += 1
    
    print(f"✅ 生成 {count} 个专业文档")
    return count


def generate_university_docs():
    """从爬取数据生成院校详情文档"""
    unis_file = CRAWL_DIR / "universities" / "all_universities.json"
    if not unis_file.exists():
        print("❌ 院校数据文件不存在，请先运行 crawl_universities_auto.py")
        return 0
    
    data = json.loads(unis_file.read_text(encoding="utf-8"))
    universities = data.get("universities", [])
    
    # 按省份分组
    by_province = {}
    for uni in universities:
        province = uni.get("province", "未知")
        if province not in by_province:
            by_province[province] = []
        by_province[province].append(uni)
    
    count = 0
    output_dir = DOCS_DIR / "universities"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成每个省份的院校汇总文档
    for province, prov_unis in by_province.items():
        doc = f"# {province}院校汇总\n\n"
        doc += f"共 {len(prov_unis)} 所院校\n\n"
        doc += "---\n\n"
        
        # 按类型分组
        by_type = {"双一流": [], "公办": [], "民办": []}
        for uni in prov_unis:
            tags = uni.get("tags", "")
            if "双一流" in tags:
                by_type["双一流"].append(uni)
            elif "公办" in tags:
                by_type["公办"].append(uni)
            elif "民办" in tags:
                by_type["民办"].append(uni)
        
        for utype, type_unis in by_type.items():
            if not type_unis:
                continue
            doc += f"### {utype}（{len(type_unis)} 所）\n\n"
            for uni in sorted(type_unis, key=lambda x: x.get("satisfaction", 0), reverse=True):
                name = uni.get("name", "未知")
                admin = uni.get("admin", "")
                level = uni.get("level", "")
                satisfaction = uni.get("satisfaction", 0)
                
                doc += f"- **{name}**"
                if admin:
                    doc += f"（{admin}）"
                if satisfaction > 0:
                    doc += f" ⭐{satisfaction}"
                doc += "\n"
            doc += "\n"
        
        filepath = output_dir / f"{province}院校汇总.md"
        filepath.write_text(doc, encoding="utf-8")
        count += 1
    
    # 生成 985/211/双一流 专题文档
    tier_docs = {
        "985工程院校": [u for u in universities if "985" in u.get("tags", "") or "985" in u.get("name", "")],
        "211工程院校": [u for u in universities if "211" in u.get("tags", "")],
        "双一流院校": [u for u in universities if "双一流" in u.get("tags", "")],
    }
    
    for doc_name, tier_unis in tier_docs.items():
        if not tier_unis:
            continue
        doc = f"# {doc_name}\n\n"
        doc += f"共 {len(tier_unis)} 所\n\n"
        doc += "---\n\n"
        for uni in sorted(tier_unis, key=lambda x: x.get("name", "")):
            doc += f"- {uni['name']}（{uni.get('province', '')}）\n"
        filepath = output_dir / f"{doc_name}.md"
        filepath.write_text(doc, encoding="utf-8")
        count += 1
    
    print(f"✅ 生成 {count} 个院校文档")
    return count


def generate_employment_docs():
    """生成就业数据文档"""
    output_dir = DOCS_DIR / "employment"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 高薪行业分析
    doc = """# 高薪行业分析

## 2025年高薪行业TOP10

| 排名 | 行业 | 平均年薪 | 发展前景 |
|------|------|----------|----------|
| 1 | 人工智能 | 35-50万 | 极高 |
| 2 | 集成电路 | 25-40万 | 极高 |
| 3 | 金融科技 | 25-35万 | 高 |
| 4 | 医疗健康 | 20-35万 | 高 |
| 5 | 新能源 | 18-30万 | 高 |
| 6 | 互联网 | 20-35万 | 中高 |
| 7 | 法律 | 15-30万 | 中 |
| 8 | 咨询 | 18-30万 | 中 |
| 9 | 教育 | 10-20万 | 中 |
| 10 | 公务员 | 8-15万 | 稳定 |

## 行业趋势

### 人工智能
- 需求持续增长
- 算法工程师薪资最高
- 需要扎实的数学和编程基础

### 集成电路
- 国家重点扶持
- 人才缺口大
- 薪资增长快

### 新能源
- 双碳政策推动
- 电动车、光伏、储能
- 就业前景广阔
"""
    filepath = output_dir / "高薪行业分析.md"
    filepath.write_text(doc, encoding="utf-8")
    
    print("✅ 生成 1 个就业文档")
    return 1


def main():
    print("=" * 50)
    print("知识库文档生成器")
    print("=" * 50)
    print()
    
    total = 0
    total += generate_major_docs()
    total += generate_university_docs()
    total += generate_employment_docs()
    
    print(f"\n总计生成 {total} 个文档")
    print(f"输出目录: {DOCS_DIR}")


if __name__ == "__main__":
    main()
