"""
阳光高考网院校数据爬虫（requests版本）
使用webfetch获取页面，解析院校数据
"""
import json
import os
import re
import time
import requests
from datetime import datetime


def parse_universities_from_html(html):
    """从HTML中解析院校数据"""
    unis = []
    
    # 使用正则表达式提取院校信息
    # 匹配院校名称
    name_pattern = r'<a[^>]*class="sch-name"[^>]*>([^<]+)</a>'
    # 匹配省份和主管部门
    info_pattern = r'<span[^>]*class="sch-info"[^>]*>([^<]+)</span>'
    # 匹配满意度
    score_pattern = r'<span[^>]*class="sch-score"[^>]*>([^<]+)</span>'
    
    # 简单的文本解析
    text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    cur = None
    for i, line in enumerate(lines):
        # 检查是否是院校名称
        if ('大学' in line or '学院' in line) and len(line) < 40 and '主管部门' not in line and '双一流' not in line and '满意度' not in line:
            if cur and cur.get('name'):
                unis.append(cur)
            cur = {'name': line, 'province': '', 'admin': '', 'level': '', 'tags': '', 'satisfaction': 0}
        elif cur and cur.get('name'):
            # 解析省份和主管部门
            if '主管部门' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    cur['province'] = parts[0].strip()
                    cur['admin'] = parts[1].replace('主管部门：', '').strip()
                elif cur.get('province'):
                    cur['admin'] = line.replace('主管部门：', '').strip()
            # 解析层次
            elif line == '本科' or '高职' in line:
                cur['level'] = line
            # 解析特性
            elif '双一流' in line or '公办' in line or '民办' in line:
                cur['tags'] = line
            # 解析满意度
            elif re.match(r'^\d+\.\d+$', line):
                cur['satisfaction'] = float(line)
            # 解析省份（单独一行）
            elif 1 < len(line) < 10 and not any(x in line for x in ['|', '满意度', '搜索', '全部', '主管部门']):
                if all(ord(c) > 255 for c in line) and not cur.get('province'):
                    cur['province'] = line
    
    if cur and cur.get('name'):
        unis.append(cur)
    
    return unis


def crawl_all_pages():
    """爬取所有148页院校数据"""
    base_dir = "data/crawl_results"
    os.makedirs(os.path.join(base_dir, "universities", "by_province"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "metadata"), exist_ok=True)
    
    all_universities = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for page_num in range(1, 149):
        start = (page_num - 1) * 20
        url = f"https://gaokao.chsi.com.cn/sch/search--ss-on,start-{start}.dhtml"
        
        try:
            print(f"爬取第 {page_num}/148 页...", end=" ")
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.encoding = 'utf-8'
            
            unis = parse_universities_from_html(response.text)
            all_universities.extend(unis)
            print(f"提取到 {len(unis)} 所院校")
            
            time.sleep(1)  # 延迟1秒
            
        except Exception as e:
            print(f"失败: {e}")
    
    # 去重
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
            json.dump({"province": province, "count": len(unis), "universities": unis}, f, ensure_ascii=False, indent=2)
    
    print(f"按省份分类完成: {len(by_province)} 个省份")
    
    # 保存统计
    stats = {
        "last_crawl": datetime.now().isoformat(),
        "universities": {"total": len(unique_unis), "by_province": {k: len(v) for k, v in by_province.items()}}
    }
    with open(os.path.join(base_dir, "metadata", "stats.json"), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 爬取完成 ===")
    print(f"总计: {len(unique_unis)} 所院校")
    for k, v in sorted(by_province.items(), key=lambda x: -len(x[1])):
        print(f"  {k}: {len(v)} 所")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    crawl_all_pages()
