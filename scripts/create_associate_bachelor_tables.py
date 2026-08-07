"""专升本数据库建表 + 种子数据"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "zx_advisor.db"

SQL_STATEMENTS = [
    # 专升本省份政策表
    """CREATE TABLE IF NOT EXISTS ab_provinces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        province TEXT NOT NULL UNIQUE,
        exam_name TEXT,              -- 考试名称
        exam_month TEXT,             -- 考试月份
        subjects_count INTEGER,      -- 考试科目数
        public_course TEXT,          -- 公共课
        major_course TEXT,           -- 专业课
        max_score REAL,              -- 满分
        eligible_condition TEXT,     -- 报考条件
        key_policy TEXT,             -- 关键政策
        official_site TEXT,          -- 官方网址
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # 专升本考试科目表
    """CREATE TABLE IF NOT EXISTS ab_exam_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        province TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        subject_type TEXT,           -- 公共课/专业课
        max_score REAL,
        time_minutes INTEGER,
        notes TEXT
    )""",

    # 专升本历史录取表
    """CREATE TABLE IF NOT EXISTS ab_admission (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        province TEXT NOT NULL,
        university_name TEXT NOT NULL,
        major_name TEXT NOT NULL,
        min_score REAL,              -- 最低录取分
        max_score REAL,              -- 最高录取分
        plan_count INTEGER,          -- 招生计划数
        applicant_count INTEGER,     -- 报考人数
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
]

# 31 省专升本政策种子数据
SEED_PROVINCES = [
    ("北京", "北京市专升本统考", "3-4月", 3, "英语", "专业课（2门）", 300, "北京高校应届专科生", "对口升本，不能跨专业大类", "www.bjeea.cn"),
    ("上海", "上海市专升本统考", "5月", 2, "英语", "计算机基础", 200, "需通过英语四级", "可跨专业，需加试", "www.shmeea.edu.cn"),
    ("广东", "广东省专插本考试", "3月", 4, "政治+英语", "专业基础+专业综合", 500, "广东户籍专科毕业生", "允许跨专业、允许跨校", "eea.gd.gov.cn"),
    ("江苏", "江苏省专转本考试", "3月", 3, "英语/日语", "高数/语文+专业课", 300, "江苏高校应届专科生", "仅限省内院校", "www.jseea.cn"),
    ("浙江", "浙江省专升本统考", "4月", 3, "英语", "高数/语文（按专业分文史/理工）", 300, "浙江高校应届专科生", "分文史类、理工类两线", "www.zjzs.net"),
    ("山东", "山东省专升本统考", "4月", 4, "英语+计算机", "高数/语文（按专业分）", 400, "山东高校应届专科生", "校荐+自荐双通道", "www.sdzk.cn"),
    ("河南", "河南省专升本统考", "6月", 2, "英语", "专业课", 300, "河南高校应届专科生", "专业对口，不允许跨专业大类", "www.heao.gov.cn"),
    ("湖北", "湖北省专升本统考", "5月", 3, "英语", "专业课（2门）", 300, "湖北高校应届专科生", "可跨校报考", "www.hbeea.edu.cn"),
    ("四川", "四川省专升本统考", "4月", 3, "英语+计算机", "高数/语文", 450, "四川高校应届专科生", "2024年起全省统考", "www.sceea.cn"),
    ("陕西", "陕西省专升本统考", "4月", 2, "英语", "高数/语文", 300, "陕西高校应届专科生", "专业对口", "www.sneea.cn"),
    ("安徽", "安徽省专升本统考", "4月", 4, "英语+计算机", "高数/语文+专业课", 500, "安徽高校应届专科生", "可参加多所院校考试", "www.ahzsks.cn"),
    ("福建", "福建省专升本统考", "3月", 3, "英语", "高数/语文+专业课", 300, "福建高校应届专科生", "专业大类对口", "www.eeafj.cn"),
    ("湖南", "湖南省专升本统考", "4月", 3, "英语", "高数/语文+专业课", 300, "湖南高校应届专科生", "可跨校报考", "jyt.hunan.gov.cn"),
    ("河北", "河北省专接本考试", "5月", 2, "英语", "高数/政治", 300, "河北高校应届专科生", "专业对口", "www.hebeea.edu.cn"),
    ("重庆", "重庆市专升本统考", "4月", 3, "英语+计算机", "高数/语文", 360, "重庆高校应届专科生", "统一划线", "www.cqksy.cn"),
    ("辽宁", "辽宁省专升本统考", "5月", 3, "英语+计算机", "专业课综合", 400, "辽宁高校应届专科生", "允许往届生报考", "www.lnzsks.com"),
    ("吉林", "吉林省专升本统考", "4月", 4, "英语+计算机", "高数/语文（分专业）+专业课", 300, "吉林高校应届专科生", "专业对口", "www.jleea.com.cn"),
    ("黑龙江", "黑龙江省专升本统考", "3月", 2, "公共英语", "高数/语文+专业课", 300, "黑龙江高校应届专科生", "专业对口", "www.lzk.hl.cn"),
    ("江西", "江西省专升本统考", "4月", 4, "英语+计算机", "高数/语文+专业课", 450, "江西高校应届专科生", "专业相关", "www.jxeea.cn"),
    ("贵州", "贵州省专升本统考", "4月", 2, "英语", "高数/语文+专业课", 300, "贵州高校应届专科生", "可跨校报考", "zsksy.guizhou.gov.cn"),
    ("云南", "云南省专升本统考", "4月", 2, "英语", "高数/语文+专业课", 300, "云南高校应届专科生", "专业对口", "www.ynzs.cn"),
    ("广西", "广西专升本统考", "4月", 3, "英语", "计算机+专业课", 300, "广西高校应届专科生", "专业对口", "www.gxeea.cn"),
    ("海南", "海南省专升本统考", "2月", 2, "英语", "专业课", 300, "海南高校应届专科生", "统一命题", "ea.hainan.gov.cn"),
    ("山西", "山西省专升本统考", "4月", 3, "英语", "高数/语文+专业课", 400, "山西高校应届专科生", "专业大类对口", "www.sxkszx.cn"),
    ("甘肃", "甘肃省专升本统考", "4月", 3, "英语+计算机", "专业课", 300, "甘肃高校应届专科生", "可跨校", "www.ganseea.cn"),
    ("内蒙古", "内蒙古专升本统考", "4月", 4, "英语+计算机+语文/高数", "专业课综合", 300, "内蒙古高校应届专科生", "专业对口", "www.nm.zsks.cn"),
    ("新疆", "新疆专升本统考", "4月", 2, "英语", "语文/高数", 300, "新疆高校应届专科生", "专业对口", "www.xjzk.gov.cn"),
    ("宁夏", "宁夏专升本统考", "4月", 2, "英语", "高数/语文+专业课", 300, "宁夏高校应届专科生", "专业对口", "www.nxjyks.cn"),
    ("青海", "青海专升本统考", "4月", 2, "英语", "高数/语文+专业课", 300, "青海高校应届专科生", "专业对口", "www.qhjyks.com"),
    ("西藏", "西藏专升本统考", "4月", 3, "英语+政治", "专业课", 300, "西藏高校应届专科生", "专业对口", "zsks.edu.xizang.gov.cn"),
    ("天津", "天津市专升本统考", "3月", 2, "英语", "专业课+计算机", 300, "天津高校应届专科生", "专业对口", "www.zhaokao.net"),
]

SEED_ADMISSION = [
    (2024, "广东", "广东工业大学", "计算机科学与技术", 365, 410, 60, 890, "专升本热门专业"),
    (2024, "广东", "广州大学", "软件工程", 380, 425, 40, 720, None),
    (2024, "广东", "广东财经大学", "会计学", 340, 395, 80, 1200, "不限专业大类"),
    (2024, "江苏", "南京信息工程大学", "计算机科学与技术", 280, 320, 50, 420, None),
    (2024, "江苏", "南京师范大学", "汉语言文学", 290, 335, 30, 380, None),
    (2024, "浙江", "浙江工业大学", "软件工程", 240, 285, 35, 450, None),
    (2024, "浙江", "杭州电子科技大学", "计算机科学与技术", 250, 300, 40, 680, "需加试"),
    (2024, "湖北", "武汉科技大学", "计算机科学与技术", 220, 270, 60, 550, None),
    (2024, "湖北", "湖北大学", "法学", 210, 255, 45, 410, None),
    (2024, "四川", "西南科技大学", "软件工程", 230, 280, 55, 380, None),
    (2024, "山东", "山东科技大学", "土木工程", 270, 310, 40, 340, None),
    (2024, "山东", "青岛大学", "会计学", 285, 330, 35, 520, None),
]


def run():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    for sql in SQL_STATEMENTS:
        cursor.execute(sql)

    for row in SEED_PROVINCES:
        cursor.execute(
            "INSERT OR IGNORE INTO ab_provinces (province, exam_name, exam_month, subjects_count, public_course, major_course, max_score, eligible_condition, key_policy, official_site) VALUES (?,?,?,?,?,?,?,?,?,?)",
            row
        )

    for row in SEED_ADMISSION:
        cursor.execute(
            "INSERT OR IGNORE INTO ab_admission (year, province, university_name, major_name, min_score, max_score, plan_count, applicant_count, notes) VALUES (?,?,?,?,?,?,?,?,?)",
            row
        )

    conn.commit()
    conn.close()
    print(f"✓ 专升本 3 张表创建/确认成功 ({DB_PATH})")


if __name__ == "__main__":
    run()
