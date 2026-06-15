-- ═══════════════════════════════════════════════════════════════
-- 投研级专业数据表（去水分版）
-- 
-- 设计理念：
-- - 放弃高校官方注水的"98%就业率"
-- - 建立四张真实反映就业质量的投研表
-- - 数据缺失时返回NULL触发风险提示
-- ═══════════════════════════════════════════════════════════════

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. 就业去向表（去向表）
-- 剔除灵活就业水分，反映真实就业质量
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS major_destination_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_name TEXT NOT NULL,                    -- 专业名称
    year INTEGER NOT NULL,                       -- 数据年份
    university_tier TEXT DEFAULT '',             -- 院校层次（985/211/普通）
    
    -- 就业去向（剔除灵活就业）
    employed_rate REAL,                          -- 实际就业率（剔除灵活就业后）
    postgraduate_rate REAL,                      -- 国内升学率
    abroad_rate REAL,                            -- 出国深造率
    civil_servant_rate REAL,                     -- 考公上岸率
    state_owned_rate REAL,                       -- 国企就业率
    
    -- 行业流向
    industry_top3 TEXT DEFAULT '[]',             -- JSON: 前三大就业行业
    city_top3 TEXT DEFAULT '[]',                 -- JSON: 前三大就业城市
    position_top3 TEXT DEFAULT '[]',             -- JSON: 前三大岗位类型
    
    -- 薪资（中位数）
    avg_start_salary REAL,                       -- 起薪中位数
    
    created_at TEXT DEFAULT (datetime('now')),
    
    UNIQUE(major_name, year, university_tier)
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 2. 收入证据表（收入表）
-- 结合统计局+招聘平台+学校报告三重验证
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS major_salary_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_name TEXT NOT NULL,                    -- 专业名称
    year INTEGER NOT NULL,                       -- 数据年份
    
    -- 薪资分布（分位数）
    salary_p25 REAL,                             -- 25分位薪资（低收入端）
    salary_p50 REAL,                             -- 中位数薪资
    salary_p75 REAL,                             -- 75分位薪资（高收入端）
    
    -- 分城市薪资
    salary_by_city TEXT DEFAULT '{}',            -- JSON: {"北京": 12000, "上海": 11000, ...}
    
    -- 数据来源标记
    data_source TEXT DEFAULT 'mixed',            -- mixed/stats_bureau/recruitment/school
    
    created_at TEXT DEFAULT (datetime('now')),
    
    UNIQUE(major_name, year)
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 3. 稳定性线索表（稳定性表）
-- 评估就业稳定性和行业周期性
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS major_stability_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_name TEXT NOT NULL,                    -- 专业名称
    year INTEGER NOT NULL,                       -- 数据年份
    
    -- 离职率
    turnover_rate_1y REAL,                       -- 一年内离职率
    turnover_rate_3y REAL,                       -- 三年内离职率
    
    -- 合同与编制
    contract_ratio REAL,                         -- 合同制比例
    permanent_ratio REAL,                        -- 正式编制比例
    
    -- 行业依赖度
    exam_dependency TEXT DEFAULT 'low',          -- 考公/考证依赖度: high/medium/low
    industry_cyclicality TEXT DEFAULT 'low',     -- 行业周期性: high/medium/low
    
    -- 考证需求
    required_certs TEXT DEFAULT '[]',            -- JSON: 必需证书列表
    
    created_at TEXT DEFAULT (datetime('now')),
    
    UNIQUE(major_name, year)
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 4. 发展路径表（路径表）
-- 职业发展天花板和成长路径
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS major_career_path (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_name TEXT NOT NULL,                    -- 专业名称
    
    -- 职业路径
    entry_position TEXT DEFAULT '',              -- 入门岗位（0-2年）
    mid_career_position TEXT DEFAULT '',         -- 中期岗位（3-5年）
    ceiling_position TEXT DEFAULT '',            -- 天花板岗位（10年+）
    
    -- 发展维度
    salary_growth_rate REAL,                     -- 年薪增长率（%）
    promotion_speed TEXT DEFAULT 'medium',       -- 晋升速度: fast/medium/slow
    
    -- AI替代风险
    ai_replacement_risk REAL,                    -- AI替代风险 0.0-1.0
    ai_enhancement_potential REAL,               -- AI增强潜力 0.0-1.0
    
    -- 技能要求
    core_skills TEXT DEFAULT '[]',               -- JSON: 核心技能列表
    emerging_skills TEXT DEFAULT '[]',           -- JSON: 新兴技能列表
    
    created_at TEXT DEFAULT (datetime('now')),
    
    UNIQUE(major_name)
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 索引
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE INDEX IF NOT EXISTS idx_destination_major ON major_destination_stats(major_name);
CREATE INDEX IF NOT EXISTS idx_destination_year ON major_destination_stats(year);
CREATE INDEX IF NOT EXISTS idx_salary_major ON major_salary_stats(major_name);
CREATE INDEX IF NOT EXISTS idx_stability_major ON major_stability_stats(major_name);
CREATE INDEX IF NOT EXISTS idx_career_major ON major_career_path(major_name);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 种子数据（示例）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 计算机科学与技术
INSERT OR IGNORE INTO major_destination_stats (major_name, year, university_tier, employed_rate, postgraduate_rate, civil_servant_rate, industry_top3, avg_start_salary)
VALUES ('计算机科学与技术', 2024, '985', 0.85, 0.35, 0.05, '["互联网", "软件", "金融"]', 15000);

INSERT OR IGNORE INTO major_salary_stats (major_name, year, salary_p25, salary_p50, salary_p75, salary_by_city)
VALUES ('计算机科学与技术', 2024, 8000, 12000, 18000, '{"北京": 15000, "上海": 14000, "深圳": 14500, "杭州": 12000}');

INSERT OR IGNORE INTO major_stability_stats (major_name, year, turnover_rate_1y, turnover_rate_3y, exam_dependency, industry_cyclicality)
VALUES ('计算机科学与技术', 2024, 0.15, 0.35, 'low', 'medium');

INSERT OR IGNORE INTO major_career_path (major_name, entry_position, mid_career_position, ceiling_position, ai_replacement_risk, ai_enhancement_potential, core_skills)
VALUES ('计算机科学与技术', '初级开发工程师', '高级工程师/架构师', '技术总监/CTO', 0.3, 0.8, '["编程", "算法", "系统设计"]');

-- 土木工程
INSERT OR IGNORE INTO major_destination_stats (major_name, year, university_tier, employed_rate, postgraduate_rate, civil_servant_rate, industry_top3, avg_start_salary)
VALUES ('土木工程', 2024, '普通', 0.65, 0.15, 0.15, '["建筑", "房地产", "政府"]', 6000);

INSERT OR IGNORE INTO major_salary_stats (major_name, year, salary_p25, salary_p50, salary_p75, salary_by_city)
VALUES ('土木工程', 2024, 4500, 6500, 9000, '{"北京": 7500, "上海": 7000, "广州": 6500}');

INSERT OR IGNORE INTO major_stability_stats (major_name, year, turnover_rate_1y, turnover_rate_3y, exam_dependency, industry_cyclicality)
VALUES ('土木工程', 2024, 0.20, 0.45, 'medium', 'high');

INSERT OR IGNORE INTO major_career_path (major_name, entry_position, mid_career_position, ceiling_position, ai_replacement_risk, ai_enhancement_potential, core_skills)
VALUES ('土木工程', '施工员/技术员', '项目经理', '总工程师', 0.2, 0.4, '["CAD", "施工管理", "结构计算"]');

-- 法学
INSERT OR IGNORE INTO major_destination_stats (major_name, year, university_tier, employed_rate, postgraduate_rate, civil_servant_rate, industry_top3, avg_start_salary)
VALUES ('法学', 2024, '985', 0.70, 0.25, 0.20, '["律所", "政府", "企业法务"]', 10000);

INSERT OR IGNORE INTO major_salary_stats (major_name, year, salary_p25, salary_p50, salary_p75, salary_by_city)
VALUES ('法学', 2024, 6000, 10000, 18000, '{"北京": 12000, "上海": 11000, "广州": 9000}');

INSERT OR IGNORE INTO major_stability_stats (major_name, year, turnover_rate_1y, turnover_rate_3y, exam_dependency, industry_cyclicality, required_certs)
VALUES ('法学', 2024, 0.12, 0.30, 'high', 'low', '["法律职业资格证"]');

INSERT OR IGNORE INTO major_career_path (major_name, entry_position, mid_career_position, ceiling_position, ai_replacement_risk, ai_enhancement_potential, core_skills)
VALUES ('法学', '律师助理/实习律师', '执业律师', '合伙人', 0.25, 0.6, '["法律研究", "诉讼技巧", "谈判"]');
