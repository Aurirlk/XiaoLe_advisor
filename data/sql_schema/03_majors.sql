-- 专业库：辅助风险评估与考公友好判断
CREATE TABLE IF NOT EXISTS majors (
    id SERIAL PRIMARY KEY,
    major_code VARCHAR(20) UNIQUE,
    major_name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    is_pitfall BOOLEAN DEFAULT FALSE,
    civil_service_friendly BOOLEAN DEFAULT FALSE,
    base_salary_tier INT DEFAULT 3,
    description TEXT
);

INSERT INTO majors (major_code, major_name, category, is_pitfall, civil_service_friendly, base_salary_tier, description) VALUES
('080901', '计算机科学与技术', '工学', FALSE, TRUE, 5, '万金油专业，就业面广，互联网/国企/考公均可，起薪高但内卷严重，存在35岁中年危机。'),
('080902', '软件工程', '工学', FALSE, FALSE, 5, '与计算机高度重合，更偏向工程实践和代码落地，学费通常较贵，是拿高薪的最短路径。'),
('030101k', '法学', '法学', FALSE, TRUE, 3, '考公之王，但也是红牌专业。如果不考公、不过法考、进不了红圈所，底层法务薪资极低，典型方差极大的专业。'),
('070301', '化学', '理学', TRUE, FALSE, 2, '四大天坑之一。本科学历极难找高薪对口工作，进厂或做实验员有毒有害危险性高，必须读研读博。'),
('083001', '生物工程', '工学', TRUE, FALSE, 2, '四大天坑之一。投资周期长，国内产业环境不成熟，普通本科毕业大概率转行或做低薪销售。'),
('100201k', '临床医学', '医学', FALSE, FALSE, 4, '先苦后甜的精英专业。必须5+3起步，普通家庭慎报，规培期间收入极低，但35岁以后是越老越吃香的铁饭碗。'),
('050301', '新闻学', '文学', FALSE, TRUE, 2, '传统媒体式微，自媒体不需要新闻学本科学历。考公有一定岗位，但竞争极其惨烈，性价比很低。'),
('020101', '经济学', '经济学', FALSE, TRUE, 3, '看似高大上，实则极看重第一学历（清北复交）和家庭人脉。普通二本学经济学大概率去做柜员或卖保险。')
ON CONFLICT (major_name) DO NOTHING;
