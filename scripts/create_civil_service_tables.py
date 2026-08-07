"""考公考编数据库建表 + 种子数据"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "zx_advisor.db"

SQL_STATEMENTS = [
    # 考公职位表
    """CREATE TABLE IF NOT EXISTS cs_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        exam_type TEXT NOT NULL,   -- 国考/省考
        province TEXT,             -- 省份（省考）
        department TEXT NOT NULL,  -- 招录部门
        position_name TEXT NOT NULL,
        position_code TEXT,
        recruitment_count INTEGER DEFAULT 1,
        education_required TEXT,   -- 学历要求
        major_required TEXT,       -- 专业要求
        min_score_entrance REAL,   -- 最低进面分
        max_score_entrance REAL,   -- 最高进面分
        applicant_count INTEGER,   -- 报名人数
        competition_ratio REAL,    -- 竞争比
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # 考公考试科目表
    """CREATE TABLE IF NOT EXISTS cs_exam_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_type TEXT NOT NULL,   -- 国考/省考
        subject_name TEXT NOT NULL,-- 行测/申论/专业科目
        question_type TEXT,        -- 题型
        question_count INTEGER,    -- 题量
        max_score REAL,            -- 满分
        time_minutes INTEGER,      -- 考试时间（分钟）
        notes TEXT
    )""",

    # 考编岗位表
    """CREATE TABLE IF NOT EXISTS pi_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        province TEXT,
        institution TEXT NOT NULL,  -- 招聘单位
        position_name TEXT NOT NULL,
        category TEXT,              -- A/B/C/D/E 类
        recruitment_count INTEGER DEFAULT 1,
        education_required TEXT,
        major_required TEXT,
        exam_subject_1 TEXT,        -- 考试科目1
        exam_subject_2 TEXT,        -- 考试科目2
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # 考编考试科目表
    """CREATE TABLE IF NOT EXISTS pi_exam_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,     -- A/B/C/D/E 类
        subject_name TEXT NOT NULL, -- 职测/综应/公基
        question_type TEXT,
        question_count INTEGER,
        max_score REAL,
        time_minutes INTEGER,
        notes TEXT
    )""",
]

SEED_CS_POSITIONS = [
    (2025, '国考', None, '国家税务总局', '一级行政执法员', '300110001001', 3, '本科及以上', '经济学类、财政学类', 128.5, 135.2, 856, 285.3, '工作地点：北京'),
    (2025, '国考', None, '外交部', '英语翻译', '102000001002', 5, '本科及以上', '英语、翻译', 125.0, 140.5, 4230, 846.0, '需要英语专业八级'),
    (2025, '国考', None, '国家统计局', '统计调查', '700100001001', 2, '本科及以上', '统计学、数学', 120.0, 128.5, 340, 170.0, None),
    (2025, '国考', None, '公安部', '网络安全技术', '109000001003', 4, '硕士及以上', '计算机科学与技术、网络安全', 115.0, 130.0, 890, 222.5, '需政审'),
    (2025, '省考', '广东', '广东省财政厅', '财务管理', '440000001001', 2, '本科及以上', '会计学、财务管理', 75.5, 82.0, 520, 260.0, None),
    (2025, '省考', '江苏', '江苏省发改委', '经济分析', '320000001001', 3, '硕士及以上', '经济学', 78.0, 85.5, 680, 226.7, None),
    (2025, '省考', '浙江', '浙江省人社厅', '综合管理', '330000001001', 2, '本科及以上', '不限', 82.0, 88.0, 2100, 1050.0, '不限专业'),
]

SEED_CS_SUBJECTS = [
    ('国考', '行测', '常识判断', 20, 100, 120, '政治/法律/经济/科技/文史'),
    ('国考', '行测', '言语理解', 40, 100, 120, '逻辑填空+阅读理解'),
    ('国考', '行测', '数量关系', 10, 100, 120, '数学运算'),
    ('国考', '行测', '判断推理', 40, 100, 120, '图形+定义+类比+逻辑'),
    ('国考', '行测', '资料分析', 20, 100, 120, '图表数据分析'),
    ('国考', '申论', '概括归纳', 1, 100, 180, '归纳材料要点'),
    ('国考', '申论', '综合分析', 1, 100, 180, '多角度分析问题'),
    ('国考', '申论', '提出对策', 1, 100, 180, '提出解决方案'),
    ('国考', '申论', '文章写作', 1, 100, 180, '议论文写作'),
]

SEED_PI_SUBJECTS = [
    ('A', '职测', '常识判断', 20, 100, 90, '综合管理类'),
    ('A', '职测', '言语理解', 40, 100, 90, '综合管理类'),
    ('A', '职测', '数量关系', 10, 100, 90, '综合管理类'),
    ('A', '综应', '案例分析', 4, 100, 120, '材料分析+对策'),
    ('A', '综应', '公文写作', 2, 100, 120, '通知/报告/函'),
    ('B', '职测', '常识判断', 20, 100, 90, '社会科学类'),
    ('B', '综应', '概念分析', 2, 100, 120, '社会科学类'),
    ('E', '职测', '医学基础知识', 30, 100, 90, '医疗卫生类'),
    ('E', '综应', '医学案例分析', 3, 100, 120, '医疗卫生类'),
]


def run():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    for sql in SQL_STATEMENTS:
        cursor.execute(sql)

    # 插入种子数据
    for row in SEED_CS_POSITIONS:
        cursor.execute(
            "INSERT OR IGNORE INTO cs_positions (year, exam_type, province, department, position_name, position_code, recruitment_count, education_required, major_required, min_score_entrance, max_score_entrance, applicant_count, competition_ratio, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            row
        )

    for row in SEED_CS_SUBJECTS:
        cursor.execute(
            "INSERT OR IGNORE INTO cs_exam_subjects (exam_type, subject_name, question_type, question_count, max_score, time_minutes, notes) VALUES (?,?,?,?,?,?,?)",
            row
        )

    for row in SEED_PI_SUBJECTS:
        cursor.execute(
            "INSERT OR IGNORE INTO pi_exam_subjects (category, subject_name, question_type, question_count, max_score, time_minutes, notes) VALUES (?,?,?,?,?,?,?)",
            row
        )

    conn.commit()
    conn.close()
    print(f"✓ 考公考编 4 张表创建/确认成功 ({DB_PATH})")


if __name__ == "__main__":
    run()
