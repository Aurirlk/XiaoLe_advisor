"""
下载所有省份的高考录取数据

数据来源：labolado/gaokao_2016-2020
格式：xlsx.zip（每个省份一个文件）
"""
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT / "data" / "raw" / "gaokao_data"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 所有省份列表
ALL_PROVINCES = [
    "北京", "天津", "河北", "山西", "内蒙古",
    "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆",
]

# GitHub仓库raw链接模板
URL_TEMPLATE = "https://github.com/labolado/gaokao_2016-2020/raw/main/{filename}"

# 科类
SUBJECT_TYPES = ["理科", "文科"]


def download_province(province: str, subject_type: str) -> bool:
    """下载单个省份的数据"""
    filename = f"{province}-{subject_type}.xlsx.zip"
    url = URL_TEMPLATE.format(filename=urllib.request.quote(filename))
    dest_dir = RAW_DATA_DIR / f"{province}_{subject_type}"
    zip_path = RAW_DATA_DIR / filename
    
    # 如果目录已存在，跳过
    if dest_dir.exists() and list(dest_dir.glob("*.xlsx")):
        print(f"  ✓ 已存在: {province}-{subject_type}")
        return True
    
    # 下载
    try:
        print(f"  ↓ 下载: {filename}")
        urllib.request.urlretrieve(url, str(zip_path))
        
        # 解压
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        
        # 删除zip文件
        zip_path.unlink(missing_ok=True)
        
        print(f"  ✓ 完成: {province}-{subject_type}")
        return True
    except Exception as e:
        print(f"  ✗ 失败: {province}-{subject_type} - {e}")
        # 清理失败的文件
        if zip_path.exists():
            zip_path.unlink()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("📥 下载所有省份高考录取数据")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for province in ALL_PROVINCES:
        for subject_type in SUBJECT_TYPES:
            if download_province(province, subject_type):
                success_count += 1
            else:
                fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ 下载完成: 成功 {success_count}, 失败 {fail_count}")
    print(f"📁 数据目录: {RAW_DATA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
