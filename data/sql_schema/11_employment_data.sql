-- ═══════════════════════════════════════════════════════════════
-- 就业薪资与地区数据表
-- 
-- 数据来源：
-- - 国家统计局年度数据
-- - 招聘平台薪资报告（BOSS直聘/猎聘/智联）
-- - 各省市统计公报
-- - 教育部就业质量报告
-- ═══════════════════════════════════════════════════════════════

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. 城市数据表
-- 包含：城市等级、生活成本、产业分布、政策倾向
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS city_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name TEXT NOT NULL UNIQUE,              -- 城市名称
    province TEXT NOT NULL,                       -- 所在省份
    
    -- 城市等级
    tier TEXT NOT NULL,                           -- 一线/新一线/二线/三线/四线/五线
    is_first_tier INTEGER DEFAULT 0,              -- 是否一线
    is_new_first_tier INTEGER DEFAULT 0,          -- 是否新一线
    
    -- 经济指标
    gdp REAL,                                     -- GDP（亿元）
    gdp_per_capita REAL,                          -- 人均GDP（万元）
    average_salary REAL,                          -- 平均工资（元/月）
    
    -- 生活成本
    housing_index REAL,                           -- 房价指数（100为基准）
    cost_of_living REAL,                          -- 生活成本指数
    
    -- 产业分布（JSON数组）
    top_industries TEXT DEFAULT '[]',             -- 主导产业
    tech_clusters TEXT DEFAULT '[]',              -- 科技园区/产业集群
    major_employers TEXT DEFAULT '[]',            -- 主要雇主
    
    -- 教育资源
    university_count INTEGER,                     -- 高校数量
    is_985_city INTEGER DEFAULT 0,                -- 是否有985高校
    is_211_city INTEGER DEFAULT 0,                -- 是否有211高校
    
    -- 政策倾向
    hukou_policy TEXT DEFAULT 'normal',           -- 落户政策：strict/moderate/loose
    talent_policy TEXT DEFAULT '',                -- 人才政策摘要
    employment_subsidy REAL,                      -- 就业补贴（元）
    
    -- 地理信息
    latitude REAL,                                -- 纬度
    longitude REAL,                               -- 经度
    climate TEXT DEFAULT '',                      -- 气候特征
    distance_to_capital REAL,                     -- 距省会距离（公里）
    
    created_at TEXT DEFAULT (datetime('now'))
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 2. 专业薪资数据表
-- 按专业×城市×经验的薪资分布
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS major_salary_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_name TEXT NOT NULL,                    -- 专业名称
    city_name TEXT NOT NULL,                      -- 城市名称
    year INTEGER NOT NULL,                        -- 数据年份
    
    -- 薪资分布（元/月）
    entry_salary_p25 REAL,                       -- 入门25分位
    entry_salary_p50 REAL,                       -- 入门中位数
    entry_salary_p75 REAL,                       -- 入门75分位
    
    mid_salary_p25 REAL,                         -- 3年经验25分位
    mid_salary_p50 REAL,                         -- 3年经验中位数
    mid_salary_p75 REAL,                         -- 3年经验75分位
    
    senior_salary_p25 REAL,                      -- 5年+经验25分位
    senior_salary_p50 REAL,                      -- 5年+经验中位数
    senior_salary_p75 REAL,                      -- 5年+经验75分位
    
    -- 就业指标
    job_availability TEXT DEFAULT 'medium',       -- 岗位供给：low/medium/high
    competition_index REAL,                      -- 竞争指数（1-10）
    growth_rate REAL,                             -- 薪资年增长率（%）
    
    -- 数据来源
    data_source TEXT DEFAULT 'mixed',             -- 统计局/招聘平台/学校报告
    sample_size INTEGER,                          -- 样本量
    
    created_at TEXT DEFAULT (datetime('now')),
    
    UNIQUE(major_name, city_name, year)
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 3. 企业招聘数据表
-- 校招信息、实习机会、行业分布
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS employer_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,                   -- 企业名称
    city_name TEXT NOT NULL,                      -- 所在城市
    industry TEXT NOT NULL,                       -- 所属行业
    
    -- 企业属性
    company_type TEXT DEFAULT 'private',          -- 国企/外企/民企/事业单位
    scale TEXT DEFAULT 'medium',                  -- 员工规模：small/medium/large/mega
    is_listed INTEGER DEFAULT 0,                  -- 是否上市
    is_fortune500 INTEGER DEFAULT 0,              -- 是否世界500强
    is_unicorn INTEGER DEFAULT 0,                 -- 是否独角兽
    
    -- 招聘信息
    hire_majors TEXT DEFAULT '[]',               -- 招聘专业（JSON数组）
    entry_salary_min REAL,                        -- 校招起薪下限
    entry_salary_max REAL,                        -- 校招起薪上限
    intern_ratio REAL,                            -- 实习转正率
    
    -- 评分
    overall_rating REAL,                          -- 综合评分（1-5）
    work_life_balance REAL,                       -- 工作生活平衡
    career_development REAL,                      -- 职业发展
    compensation_rating REAL,                     -- 薪酬竞争力
    
    -- 地理
    address TEXT DEFAULT '',                      -- 详细地址
    latitude REAL,
    longitude REAL,
    is_campus_nearby INTEGER DEFAULT 0,           -- 是否靠近大学城
    
    created_at TEXT DEFAULT (datetime('now'))
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 4. 就业政策数据表
-- 地方人才政策、补贴、落户条件
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS employment_policy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name TEXT NOT NULL,                      -- 城市名称
    policy_name TEXT NOT NULL,                    -- 政策名称
    policy_type TEXT NOT NULL,                    -- 类型：hukou/subsidy/housing/employment
    
    -- 政策内容
    description TEXT NOT NULL,                    -- 政策描述
    eligibility TEXT NOT NULL,                    -- 申请条件
    benefit TEXT NOT NULL,                        -- 补贴/优惠内容
    amount REAL,                                  -- 金额（元）
    duration TEXT DEFAULT '',                     -- 有效期
    
    -- 门槛条件
    min_degree TEXT DEFAULT '',                   -- 最低学历要求
    min_score REAL,                               -- 最低薪资要求
    required_majors TEXT DEFAULT '[]',            -- 限制专业
    
    -- 时效性
    effective_date TEXT,                          -- 生效日期
    expiry_date TEXT,                             -- 到期日期
    is_current INTEGER DEFAULT 1,                 -- 是否当前有效
    
    -- 搜索关键词（用于动态刷新）
    search_keyword TEXT DEFAULT '',               -- 搜索关键词
    
    created_at TEXT DEFAULT (datetime('now'))
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 5. 校区地理数据表
-- 防止学生误报偏远校区
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE IF NOT EXISTS campus_location (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    university_name TEXT NOT NULL,                -- 大学名称
    campus_name TEXT NOT NULL,                    -- 校区名称（主校区/分校区）
    
    -- 地理位置
    city TEXT NOT NULL,                           -- 所在城市
    district TEXT DEFAULT '',                     -- 区县
    address TEXT DEFAULT '',                      -- 详细地址
    latitude REAL,
    longitude REAL,
    
    -- 校区属性
    is_main_campus INTEGER DEFAULT 0,             -- 是否主校区
    is_new_campus INTEGER DEFAULT 0,              -- 是否新校区
    is_remote INTEGER DEFAULT 0,                  -- 是否偏远
    
    -- 交通便利度
    nearest_metro TEXT DEFAULT '',                -- 最近地铁站
    metro_distance_km REAL,                       -- 距地铁站距离
    nearest_train_station TEXT DEFAULT '',        -- 最近火车站
    distance_to_city_center REAL,                 -- 距市中心距离（公里）
    
    -- 周边配套
    has_hospital INTEGER DEFAULT 1,               -- 周边有医院
    has_commercial INTEGER DEFAULT 1,             -- 周边有商业
    has_internship_base INTEGER DEFAULT 0,        -- 周边有实习基地
    
    -- 周边产业集群
    nearby_clusters TEXT DEFAULT '[]',            -- JSON: 附近产业集群
    nearby_companies TEXT DEFAULT '[]',           -- JSON: 附近主要企业
    
    -- 风险提示
    risk_warning TEXT DEFAULT '',                 -- 风险提示（如：新校区配套不完善）
    
    created_at TEXT DEFAULT (datetime('now'))
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 索引
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE INDEX IF NOT EXISTS idx_city_province ON city_data(province);
CREATE INDEX IF NOT EXISTS idx_city_tier ON city_data(tier);
CREATE INDEX IF NOT EXISTS idx_salary_major ON major_salary_data(major_name);
CREATE INDEX IF NOT EXISTS idx_salary_city ON major_salary_data(city_name);
CREATE INDEX IF NOT EXISTS idx_employer_city ON employer_data(city_name);
CREATE INDEX IF NOT EXISTS idx_employer_industry ON employer_data(industry);
CREATE INDEX IF NOT EXISTS idx_policy_city ON employment_policy(city_name);
CREATE INDEX IF NOT EXISTS idx_campus_university ON campus_location(university_name);
CREATE INDEX IF NOT EXISTS idx_campus_city ON campus_location(city);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 种子数据（部分示例）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 一线城市数据
INSERT OR IGNORE INTO city_data (city_name, province, tier, is_first_tier, average_salary, top_industries, hukou_policy)
VALUES 
('北京', '北京市', '一线', 1, 12000, '["互联网", "金融", "教育", "科技"]', 'strict'),
('上海', '上海市', '一线', 1, 11500, '["金融", "贸易", "科技", "制造"]', 'strict'),
('广州', '广东省', '一线', 1, 10000, '["商贸", "汽车", "互联网", "医药"]', 'moderate'),
('深圳', '广东省', '一线', 1, 11000, '["科技", "金融", "互联网", "硬件"]', 'moderate');

-- 新一线城市数据
INSERT OR IGNORE INTO city_data (city_name, province, tier, is_new_first_tier, average_salary, top_industries, hukou_policy)
VALUES 
('杭州', '浙江省', '新一线', 1, 10500, '["互联网", "电商", "金融", "文创"]', 'loose'),
('成都', '四川省', '新一线', 1, 8500, '["科技", "游戏", "文创", "制造"]', 'loose'),
('武汉', '湖北省', '新一线', 1, 8000, '["光电", "汽车", "医药", "教育"]', 'loose'),
('南京', '江苏省', '新一线', 1, 9000, '["软件", "电子", "医药", "金融"]', 'moderate'),
('苏州', '江苏省', '新一线', 1, 9500, '["制造", "电子", "医药", "金融"]', 'moderate'),
('西安', '陕西省', '新一线', 1, 7500, '["军工", "航天", "软件", "教育"]', 'loose');

-- 计算机专业薪资数据（深圳示例）
INSERT OR IGNORE INTO major_salary_data (major_name, city_name, year, entry_salary_p50, mid_salary_p50, senior_salary_p50, job_availability)
VALUES 
('计算机科学与技术', '深圳', 2024, 12000, 22000, 35000, 'high'),
('软件工程', '深圳', 2024, 13000, 24000, 38000, 'high'),
('人工智能', '深圳', 2024, 15000, 28000, 45000, 'high'),
('数据科学与大数据技术', '深圳', 2024, 11000, 20000, 32000, 'high'),
('电子信息工程', '深圳', 2024, 10000, 18000, 28000, 'medium');

-- 校区地理数据示例
INSERT OR IGNORE INTO campus_location (university_name, campus_name, city, is_main_campus, is_new_campus, is_remote, risk_warning)
VALUES 
('中山大学', '广州校区南校园', '广州', 1, 0, 0, ''),
('中山大学', '深圳校区', '深圳', 0, 1, 0, '新校区，部分设施仍在建设中'),
('中山大学', '珠海校区', '珠海', 0, 0, 0, '与主校区有一定距离'),
('哈尔滨工业大学', '本部', '哈尔滨', 1, 0, 0, ''),
('哈尔滨工业大学', '深圳校区', '深圳', 0, 1, 0, '深圳校区就业资源丰富'),
('哈尔滨工业大学', '威海校区', '威海', 0, 0, 1, '地理位置相对偏远，实习资源较少');
