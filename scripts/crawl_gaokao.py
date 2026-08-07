"""
阳光高考网分布式爬虫（Puppeteer版本）
- 院校列表爬取
- 专业列表爬取
- 按省份/门类分类存储
"""
import json
import os
import re
import time
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GaokaoCrawler:
    """阳光高考网爬虫（Puppeteer版本）"""
    
    def __init__(self, base_dir="data/crawl_results"):
        self.base_url = "https://gaokao.chsi.com.cn"
        self.base_dir = base_dir
        self.delay = 3  # 请求间隔（秒）
        
        # 创建目录结构
        self._create_dirs()
        
        # 爬取日志
        self.log_file = os.path.join(base_dir, "metadata", "crawl_log.json")
        self.stats_file = os.path.join(base_dir, "metadata", "stats.json")
    
    def _create_dirs(self):
        """创建目录结构"""
        dirs = [
            "universities/by_province",
            "universities/by_type",
            "majors/by_category",
            "metadata"
        ]
        for d in dirs:
            os.makedirs(os.path.join(self.base_dir, d), exist_ok=True)
    
    def _load_json(self, filepath):
        """加载JSON文件"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _save_json(self, filepath, data):
        """保存JSON文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _log_crawl(self, task_id, status, message=""):
        """记录爬取日志"""
        logs = self._load_json(self.log_file) or []
        logs.append({
            "task_id": task_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        self._save_json(self.log_file, logs)
    
    def parse_universities_from_text(self, text):
        """
        从页面文本中提取院校数据
        
        Args:
            text: 页面文本内容
        
        Returns:
            院校列表
        """
        lines = [line for line in text.split('\n') if line.strip()]
        
        universities = []
        current = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 检查是否是院校名称
            if ('大学' in line or '学院' in line) and len(line) < 30 and '主管部门' not in line and '双一流' not in line:
                if current and current.get('name'):
                    universities.append(current)
                current = {'name': line, 'province': '', 'admin': '', 'level': '', 'tags': '', 'satisfaction': 0}
            elif current and current.get('name'):
                # 解析省份
                if 1 < len(line) < 10 and '|' not in line and '满意度' not in line and '搜索' not in line and '全部' not in line and '主管部门' not in line:
                    # 检查是否是省份（中文字符，且不是单个特殊字符）
                    is_province = all(ord(c) > 255 for c in line)
                    if is_province and not current.get('province'):
                        current['province'] = line
                
                # 解析主管部门（下一行）
                if line == '主管部门：':
                    # 下一行是主管部门名称
                    if i + 1 < len(lines):
                        current['admin'] = lines[i + 1].strip()
                
                # 解析层次
                elif line == '本科' or '高职' in line:
                    current['level'] = line
                
                # 解析特性
                elif '双一流' in line or '公办' in line or '民办' in line:
                    current['tags'] = line
                
                # 解析满意度
                elif re.fullmatch(r'\d+\.\d+', line):
                    current['satisfaction'] = float(line)
        
        if current and current.get('name'):
            universities.append(current)
        
        return universities
    
    def save_universities(self, universities):
        """
        保存院校数据
        
        Args:
            universities: 院校列表
        """
        # 保存总表
        self._save_json(
            os.path.join(self.base_dir, "universities", "all_universities.json"),
            {
                "total": len(universities),
                "crawl_time": datetime.now().isoformat(),
                "universities": universities
            }
        )
        
        # 按省份分类
        by_province = {}
        for uni in universities:
            province = uni.get("province", "未知")
            if province not in by_province:
                by_province[province] = []
            by_province[province].append(uni)
        
        for province, unis in by_province.items():
            filepath = os.path.join(self.base_dir, "universities", "by_province", f"{province}.json")
            self._save_json(filepath, {
                "province": province,
                "count": len(unis),
                "universities": unis
            })
        
        # 按类型分类
        by_type = {
            "双一流": [],
            "公办": [],
            "民办": [],
            "独立学院": [],
            "中外合作办学": []
        }
        
        for uni in universities:
            tags = uni.get("tags", "")
            for tag in by_type.keys():
                if tag in tags:
                    by_type[tag].append(uni)
        
        for tag, unis in by_type.items():
            if unis:
                filepath = os.path.join(self.base_dir, "universities", "by_type", f"{tag}.json")
                self._save_json(filepath, {
                    "type": tag,
                    "count": len(unis),
                    "universities": unis
                })
        
        logger.info(f"保存院校数据完成：{len(universities)} 所，{len(by_province)} 个省份")
    
    def update_stats(self, universities_count=0, majors_count=0):
        """更新统计信息"""
        stats = {
            "last_crawl": datetime.now().isoformat(),
            "universities": {
                "total": universities_count
            },
            "majors": {
                "total": majors_count
            }
        }
        
        self._save_json(self.stats_file, stats)
        logger.info(f"统计信息已更新")


def main():
    """主函数"""
    crawler = GaokaoCrawler()
    print("爬虫脚本已加载")
    print("请使用 Puppeteer MCP 工具来爬取数据")


if __name__ == "__main__":
    main()
