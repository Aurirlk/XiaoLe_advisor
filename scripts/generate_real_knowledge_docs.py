"""
真实数据知识库文档生成器

将阳光高考网爬取的真实数据转换为 RAG 可用的知识库文档

运行方式：
python scripts/generate_real_knowledge_docs.py
"""
import json
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CRAWL_DIR = ROOT / "data" / "crawl_results"
DOCS_DIR = ROOT / "data" / "documents"


def generate_major_docs():
    """从真实爬取数据生成专业详解文档"""
    majors_file = CRAWL_DIR / "majors" / "all_majors.json"
    if not majors_file.exists():
        print("❌ 专业数据文件不存在")
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
        doc += f"**数据来源**: 阳光高考网 (gaokao.chsi.com.cn)\n"
        doc += f"**更新时间**: {datetime.now().strftime('%Y-%m-%d')}\n"
        doc += f"**专业数量**: {len(cat_majors)} 个\n\n"
        doc += "---\n\n"
        
        # 按专业类分组
        by_subcategory = {}
        for major in cat_majors:
            subcat = major.get("subcategory", "其他")
            if subcat not in by_subcategory:
                by_subcategory[subcat] = []
            by_subcategory[subcat].append(major)
        
        for subcategory, sub_majors in by_subcategory.items():
            doc += f"### {subcategory}（{len(sub_majors)} 个）\n\n"
            
            for major in sub_majors:
                name = major.get("name", "未知")
                code = major.get("code", "")
                degree = major.get("degree", "")
                duration = major.get("duration", "")
                
                doc += f"#### {name}\n\n"
                doc += f"- **专业代码**: {code}\n"
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
    """从真实爬取数据生成院校详情文档"""
    unis_file = CRAWL_DIR / "universities" / "all_universities.json"
    if not unis_file.exists():
        print("❌ 院校数据文件不存在")
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
        doc += f"**数据来源**: 阳光高考网 (gaokao.chsi.com.cn)\n"
        doc += f"**更新时间**: {datetime.now().strftime('%Y-%m-%d')}\n"
        doc += f"**院校数量**: {len(prov_unis)} 所\n\n"
        doc += "---\n\n"
        
        # 按类型分组
        by_type = {"双一流": [], "公办本科": [], "民办本科": [], "高职": []}
        for uni in prov_unis:
            tags = uni.get("tags", "")
            level = uni.get("level", "")
            if "双一流" in tags:
                by_type["双一流"].append(uni)
            elif "民办" in tags:
                by_type["民办本科"].append(uni)
            elif "高职" in level:
                by_type["高职"].append(uni)
            else:
                by_type["公办本科"].append(uni)
        
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
                if level:
                    doc += f" [{level}]"
                if satisfaction > 0:
                    doc += f" ⭐{satisfaction}"
                doc += "\n"
            doc += "\n"
        
        filepath = output_dir / f"{province}院校汇总.md"
        filepath.write_text(doc, encoding="utf-8")
        count += 1
    
    # 生成 985/211/双一流 专题文档
    tier_docs = {
        "985工程院校": [u for u in universities if "985" in u.get("tags", "")],
        "211工程院校": [u for u in universities if "211" in u.get("tags", "")],
        "双一流院校": [u for u in universities if "双一流" in u.get("tags", "")],
    }
    
    for doc_name, tier_unis in tier_docs.items():
        if not tier_unis:
            continue
        doc = f"# {doc_name}\n\n"
        doc += f"**数据来源**: 阳光高考网\n"
        doc += f"**院校数量**: {len(tier_unis)} 所\n\n"
        doc += "---\n\n"
        
        # 按省份分组
        by_prov = {}
        for uni in tier_unis:
            prov = uni.get("province", "未知")
            if prov not in by_prov:
                by_prov[prov] = []
            by_prov[prov].append(uni)
        
        for prov, prov_unis in sorted(by_prov.items()):
            doc += f"### {prov}（{len(prov_unis)} 所）\n\n"
            for uni in sorted(prov_unis, key=lambda x: x.get("name", "")):
                doc += f"- {uni['name']}\n"
            doc += "\n"
        
        filepath = output_dir / f"{doc_name}.md"
        filepath.write_text(doc, encoding="utf-8")
        count += 1
    
    print(f"✅ 生成 {count} 个院校文档")
    return count


def main():
    print("=" * 50)
    print("真实数据知识库文档生成器")
    print("=" * 50)
    print(f"数据来源: 阳光高考网 (gaokao.chsi.com.cn)")
    print()
    
    total = 0
    total += generate_major_docs()
    total += generate_university_docs()
    
    print(f"\n总计生成 {total} 个文档")
    print(f"输出目录: {DOCS_DIR}")


if __name__ == "__main__":
    main()
