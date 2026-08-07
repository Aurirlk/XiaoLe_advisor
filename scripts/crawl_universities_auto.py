"""
阳光高考网院校数据自动爬虫
使用Playwright自动遍历148页，提取所有院校数据
"""
import json
import os
import time
from datetime import datetime

# Playwright导入
from playwright.sync_api import sync_playwright


def extract_universities(page):
    """从当前页面提取院校数据"""
    txt = page.inner_text('body')
    lines = [l.strip() for l in txt.split('\n') if l.strip()]
    
    unis = []
    cur = None
    
    for i, line in enumerate(lines):
        # 检查是否是院校名称
        if ('大学' in line or '学院' in line) and len(line) < 30 and '主管部门' not in line and '双一流' not in line:
            if cur and cur.get('name'):
                unis.append(cur)
            cur = {'name': line, 'province': '', 'admin': '', 'level': '', 'tags': '', 'satisfaction': 0}
        elif cur and cur.get('name'):
            # 解析省份（中文字符，长度1-9）
            if 1 < len(line) < 10 and '|' not in line and '满意度' not in line and '搜索' not in line and '全部' not in line and '主管部门' not in line:
                is_province = all(ord(c) > 255 for c in line)
                if is_province and not cur.get('province'):
                    cur['province'] = line
            
            # 解析主管部门
            if line == '主管部门：':
                if i + 1 < len(lines):
                    cur['admin'] = lines[i + 1].strip()
            
            # 解析层次
            elif line == '本科' or '高职' in line:
                cur['level'] = line
            
            # 解析特性
            elif '双一流' in line or '公办' in line or '民办' in line:
                cur['tags'] = line
            
            # 解析满意度
            elif line.replace('.', '').isdigit() and '.' in line:
                try:
                    cur['satisfaction'] = float(line)
                except:
                    pass
    
    if cur and cur.get('name'):
        unis.append(cur)
    
    return unis


def crawl_all_pages():
    """爬取所有148页院校数据"""
    base_dir = "data/crawl_results"
    os.makedirs(os.path.join(base_dir, "universities", "by_province"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "metadata"), exist_ok=True)
    
    all_universities = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 访问首页
        print("正在访问阳光高考网院校库...")
        page.goto("https://gaokao.chsi.com.cn/sch/search--ss-on,start-0.dhtml", timeout=60000)
        page.wait_for_load_state('networkidle', timeout=30000)
        time.sleep(2)
        
        # 爬取第1页
        print("爬取第 1/148 页...")
        unis = extract_universities(page)
        all_universities.extend(unis)
        print(f"  提取到 {len(unis)} 所院校")
        
        # 爬取剩余页面（点击页码翻页）
        for page_num in range(2, 149):
            try:
                # 查找并点击页码
                page_link = page.locator(f'a:has-text("{page_num}")').first
                if page_link:
                    page_link.click()
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(1)
                    
                    unis = extract_universities(page)
                    all_universities.extend(unis)
                    print(f"爬取第 {page_num}/148 页... 提取到 {len(unis)} 所院校")
                else:
                    print(f"第 {page_num} 页链接未找到，跳过")
            except Exception as e:
                print(f"第 {page_num} 页爬取失败: {e}")
                # 尝试重新加载
                try:
                    page.goto(f"https://gaokao.chsi.com.cn/sch/search--ss-on,start-{(page_num-1)*20}.dhtml", timeout=30000)
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(1)
                    unis = extract_universities(page)
                    all_universities.extend(unis)
                    print(f"  重新加载成功，提取到 {len(unis)} 所院校")
                except:
                    print(f"  重新加载也失败，跳过")
        
        browser.close()
    
    # 去重（基于院校名称）
    seen = set()
    unique_unis = []
    for uni in all_universities:
        if uni['name'] not in seen:
            seen.add(uni['name'])
            unique_unis.append(uni)
    
    print(f"\n爬取完成！总计 {len(unique_unis)} 所院校（去重后）")
    
    # 保存总表
    filepath = os.path.join(base_dir, "universities", "all_universities.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(unique_unis),
            "crawl_time": datetime.now().isoformat(),
            "universities": unique_unis
        }, f, ensure_ascii=False, indent=2)
    print(f"保存总表: {filepath}")
    
    # 按省份分类
    by_province = {}
    for uni in unique_unis:
        province = uni.get("province", "未知")
        if province not in by_province:
            by_province[province] = []
        by_province[province].append(uni)
    
    for province, unis in by_province.items():
        filepath = os.path.join(base_dir, "universities", "by_province", f"{province}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "province": province,
                "count": len(unis),
                "universities": unis
            }, f, ensure_ascii=False, indent=2)
    
    print(f"按省份分类完成: {len(by_province)} 个省份")
    
    # 按类型分类
    by_type = {"双一流": [], "公办": [], "民办": [], "独立学院": [], "高职": []}
    for uni in unique_unis:
        tags = uni.get("tags", "")
        level = uni.get("level", "")
        if "双一流" in tags:
            by_type["双一流"].append(uni)
        if "公办" in tags:
            by_type["公办"].append(uni)
        if "民办" in tags:
            by_type["民办"].append(uni)
        if "独立学院" in tags:
            by_type["独立学院"].append(uni)
        if "高职" in level:
            by_type["高职"].append(uni)
    
    for tag, unis in by_type.items():
        if unis:
            filepath = os.path.join(base_dir, "universities", "by_type", f"{tag}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "type": tag,
                    "count": len(unis),
                    "universities": unis
                }, f, ensure_ascii=False, indent=2)
    
    print(f"按类型分类完成")
    
    # 保存统计信息
    stats = {
        "last_crawl": datetime.now().isoformat(),
        "universities": {
            "total": len(unique_unis),
            "by_province": {k: len(v) for k, v in by_province.items()},
            "by_type": {k: len(v) for k, v in by_type.items()}
        }
    }
    filepath = os.path.join(base_dir, "metadata", "stats.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 爬取完成 ===")
    print(f"总计: {len(unique_unis)} 所院校")
    print(f"省份: {len(by_province)} 个")
    for k, v in by_type.items():
        if v:
            print(f"  {k}: {len(v)} 所")


if __name__ == "__main__":
    crawl_all_pages()
