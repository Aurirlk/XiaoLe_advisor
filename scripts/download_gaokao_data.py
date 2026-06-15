"""
高考录取数据下载脚本

数据来源：
1. labolado/gaokao_2016-2020 - 2016-2020年全国高考录取分数线（xlsx格式）
2. EvanYao826/china-university-admission - 1167所高校+录取数据（SQLite）
"""
import os
import zipfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT / "data" / "raw" / "gaokao_data"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# GitHub仓库raw链接
GITHUB_REPOS = {
    "gaokao_2016-2020": "https://github.com/labolado/gaokao_2016-2020/archive/refs/heads/main.zip",
    "china_university_admission": "https://github.com/EvanYao826/china-university-admission/archive/refs/heads/main.zip",
}

# 需要下载的省份列表（优先热门省份）
PRIORITY_PROVINCES = [
    "广东", "北京", "上海", "江苏", "浙江", "山东", "河南", "四川",
    "湖北", "湖南", "福建", "安徽", "河北", "陕西", "重庆", "天津",
]


def download_file(url: str, dest: Path) -> bool:
    """下载文件"""
    if dest.exists():
        print(f"  ✓ 文件已存在: {dest.name}")
        return True
    
    try:
        print(f"  ↓ 下载中: {url}")
        urllib.request.urlretrieve(url, str(dest))
        print(f"  ✓ 下载完成: {dest.name}")
        return True
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return False


def extract_zip(zip_path: Path, dest_dir: Path) -> bool:
    """解压zip文件"""
    try:
        print(f"  📦 解压中: {zip_path.name}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        print(f"  ✓ 解压完成")
        return True
    except Exception as e:
        print(f"  ✗ 解压失败: {e}")
        return False


def download_gaokao_scores():
    """下载2016-2020年高考录取分数线数据"""
    print("\n" + "=" * 60)
    print("📥 下载2016-2020年高考录取分数线数据")
    print("=" * 60)
    
    dest_dir = RAW_DATA_DIR / "gaokao_2016-2020"
    zip_path = RAW_DATA_DIR / "gaokao_2016-2020.zip"
    
    url = GITHUB_REPOS["gaokao_2016-2020"]
    if download_file(url, zip_path):
        extract_zip(zip_path, dest_dir)
        # 列出解压后的文件
        extracted = list(dest_dir.glob("**/*.xlsx.zip"))
        print(f"\n  📊 找到 {len(extracted)} 个xlsx文件")
        return True
    return False


def download_china_university_data():
    """下载中国高校招生数据（SQLite数据库）"""
    print("\n" + "=" * 60)
    print("📥 下载中国高校招生数据")
    print("=" * 60)
    
    dest_dir = RAW_DATA_DIR / "china_university_admission"
    zip_path = RAW_DATA_DIR / "china_university_admission.zip"
    
    url = GITHUB_REPOS["china_university_admission"]
    if download_file(url, zip_path):
        extract_zip(zip_path, dest_dir)
        # 查找SQLite数据库
        db_files = list(dest_dir.glob("**/*.db"))
        if db_files:
            print(f"\n  🗄️ 找到SQLite数据库: {db_files[0]}")
        return True
    return False


def list_priority_files():
    """列出优先导入的省份文件"""
    print("\n" + "=" * 60)
    print("📋 优先导入的省份文件")
    print("=" * 60)
    
    gaokao_dir = RAW_DATA_DIR / "gaokao_2016-2020"
    if not gaokao_dir.exists():
        print("  ⚠️ 数据目录不存在")
        return
    
    priority_files = []
    for province in PRIORITY_PROVINCES:
        files = list(gaokao_dir.glob(f"**/{province}*.xlsx.zip"))
        for f in files:
            priority_files.append(f)
            print(f"  📁 {f.name}")
    
    print(f"\n  共找到 {len(priority_files)} 个优先文件")


def main():
    """主函数"""
    print("🎓 高考录取数据下载工具")
    print("=" * 60)
    
    # 1. 下载2016-2020年分数线数据
    download_gaokao_scores()
    
    # 2. 下载中国高校招生数据
    download_china_university_data()
    
    # 3. 列出优先文件
    list_priority_files()
    
    print("\n" + "=" * 60)
    print("✅ 下载完成！")
    print(f"📁 数据目录: {RAW_DATA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
