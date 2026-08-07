"""
阳光高考网专业数据爬虫
使用API端点获取所有专业数据
"""
import json
import os
import time
import requests
from datetime import datetime


def crawl_all_majors():
    """爬取所有专业数据"""
    base_dir = "data/crawl_results"
    os.makedirs(os.path.join(base_dir, "majors", "by_category"), exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://gaokao.chsi.com.cn/zyk/zybk/'
    }
    
    # 13个门类
    categories = [
        {"key": "105001", "name": "哲学"},
        {"key": "105002", "name": "经济学"},
        {"key": "105003", "name": "法学"},
        {"key": "105004", "name": "教育学"},
        {"key": "105005", "name": "文学"},
        {"key": "105006", "name": "历史学"},
        {"key": "105007", "name": "理学"},
        {"key": "105008", "name": "工学"},
        {"key": "105009", "name": "农学"},
        {"key": "105010", "name": "医学"},
        {"key": "105012", "name": "管理学"},
        {"key": "105013", "name": "艺术学"},
        {"key": "105014", "name": "交叉学科"}
    ]
    
    all_majors = []
    
    for cat in categories:
        print(f"\n爬取门类: {cat['name']} ({cat['key']})")
        
        try:
            # 获取专业类列表
            url = f"https://gaokao.chsi.com.cn/zyk/zybk/xkCategory/{cat['key']}"
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            subcategories = response.json().get('msg', [])
            
            print(f"  专业类数量: {len(subcategories)}")
            
            for subcat in subcategories:
                # 获取专业列表
                url = f"https://gaokao.chsi.com.cn/zyk/zybk/specialityesByCategory/{subcat['key']}"
                response = requests.get(url, headers=headers, timeout=30, verify=False)
                majors = response.json().get('msg', [])
                
                for major in majors:
                    major['category'] = cat['name']
                    major['category_code'] = cat['key']
                    major['subcategory'] = subcat['name']
                    major['subcategory_code'] = subcat['key']
                    all_majors.append(major)
                
                print(f"    {subcat['name']}: {len(majors)} 个专业")
                time.sleep(0.5)
            
        except Exception as e:
            print(f"  爬取失败: {e}")
        
        time.sleep(1)
    
    # 保存总表
    filepath = os.path.join(base_dir, "majors", "all_majors.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(all_majors),
            "crawl_time": datetime.now().isoformat(),
            "majors": all_majors
        }, f, ensure_ascii=False, indent=2)
    
    # 按门类分类
    by_category = {}
    for major in all_majors:
        cat = major.get('category', '未知')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(major)
    
    for cat, majors in by_category.items():
        filepath = os.path.join(base_dir, "majors", "by_category", f"{cat}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"category": cat, "count": len(majors), "majors": majors}, f, ensure_ascii=False, indent=2)
    
    # 保存统计
    stats = {
        "last_crawl": datetime.now().isoformat(),
        "majors": {
            "total": len(all_majors),
            "by_category": {k: len(v) for k, v in by_category.items()}
        }
    }
    with open(os.path.join(base_dir, "metadata", "majors_stats.json"), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 爬取完成 ===")
    print(f"总计: {len(all_majors)} 个专业")
    for k, v in by_category.items():
        print(f"  {k}: {len(v)} 个")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    crawl_all_majors()
