# CRM 用户画像系统

## 一、系统概述

AI CRM 是小乐AI 的核心模块之一，用于自动提取和管理用户画像信息。支持**学生画像 + 家长画像 + 家庭背景**三维度，实现跨会话断点续传。

### 核心功能

1. **学生画像提取** — 从对话中自动提取省份、选科、分数、位次、兴趣等
2. **家长画像提取** — 从家长对话中提取职业、行业、期望、担忧
3. **家庭背景融合** — 综合学生+家长画像，推断收入/决策人/一致性
4. **学科评分** — 九门学科自评+高考分数数组
5. **跨会话记忆** — 画像持久化存储，支持断点续传

---

## 二、数据模型

### 2.1 学生画像 (user_profiles)

| 字段 | 类型 | 说明 |
|------|------|------|
| phone_number | TEXT | 用户唯一标识 |
| province | TEXT | 高考省份 |
| subject_type | TEXT | 选科类别：物理类/历史类 |
| major_name | TEXT | 目标专业 |
| score | INTEGER | 分数 |
| rank | INTEGER | 位次 |
| budget | INTEGER | 预算（元） |
| target_city | TEXT | 目标城市 |
| postgraduate_plan | TEXT | 读研意愿 |
| gender | TEXT | 性别 |
| interests | TEXT | 兴趣爱好（JSON 数组） |
| personality | TEXT | 性格特点 |
| target_universities | TEXT | 目标院校（JSON 数组） |
| risk_tolerance | TEXT | 风险偏好 |
| subject_scores_json | TEXT | 学科评分（JSON） |
| extra_tags | TEXT | 扩展标签（JSON） |
| session_count | INTEGER | 累计会话数 |

### 2.2 学科评分 (SubjectScores)

```json
{
  "self_assessment": [85, 90, 78, 92, null, null, null, null, null],
  "gaokao_scores": [110, 135, 120, 85, null, null, null, null, null],
  "self_rank": ["good", "excellent", "good", "excellent", null, null, null, null, null],
  "strong_subjects": ["数学", "物理"],
  "weak_subjects": ["英语"]
}
```

索引顺序：语文(0) 数学(1) 英语(2) 物理(3) 化学(4) 生物(5) 政治(6) 历史(7) 地理(8)

### 2.3 家长画像 (parent_profiles)

| 字段 | 类型 | 说明 |
|------|------|------|
| student_phone | TEXT | 关联学生 |
| role | TEXT | father/mother/grandfather/other |
| name | TEXT | 姓名 |
| occupation | TEXT | 职业 |
| industry | TEXT | 行业（金融/医疗/教育/IT等） |
| education | TEXT | 学历 |
| expectation | TEXT | 对孩子期望 |
| concerns | TEXT | 担忧点（JSON 数组） |
| decision_weight | TEXT | dominant/consultative/independent |

### 2.4 家庭背景 (family_contexts)

| 字段 | 类型 | 说明 |
|------|------|------|
| student_phone | TEXT | 关联学生 |
| income_level | TEXT | low/medium/high |
| annual_budget | INTEGER | 年预算 |
| is_only_child | INTEGER | 独生子女（0/1/-1未知） |
| decision_maker | TEXT | student/parent/joint |
| location_preference | TEXT | local/nearby/anywhere |
| financial_urgency | TEXT | none/moderate/high |
| parent_consensus | TEXT | agree/disagree/partial |

---

## 三、工作流程

```
用户对话
    │
    ▼
┌─────────────────────────────────────────┐
│  profile_agent (学生画像提取)             │
│  - 正则匹配：分数/位次/省份/城市/专业     │
│  - 关键词匹配：兴趣/性别/风险偏好         │
│  - 学科评分：强势/弱势/具体分数           │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  parent_agent (家长画像提取)              │
│  - 行业/职业/学历/期望/担忧              │
│  - 决策风格识别                          │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  family_agent (家庭融合)                  │
│  - 推断收入水平                          │
│  - 推断决策人                            │
│  - 检查家校一致性                        │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  synthesis_agent (最终建议)               │
│  - 注入学生+家长+家庭数据               │
│  - 生成个性化报考建议                    │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  CRM 持久化                             │
│  - save_profile() 写入 SQLite           │
│  - 下次访问自动 load_profile()          │
└─────────────────────────────────────────┘
```

---

## 四、API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/stream/state/{session_id}` | 获取当前画像 |
| GET | `/stream/history/{session_id}` | 画像变更历史 |

---

## 五、使用示例

### 对话中自动提取

```
用户：我是广东的，选的物理，考了580分，想去深圳读计算机
系统：[自动提取] province=广东省, subject_type=物理类, score=580, target_city=深圳, major_name=计算机科学与技术

用户：我数学最好，物理也不错
系统：[自动提取] strong_subjects=["数学", "物理"]

用户：我爸是做IT的，家里预算一年15万
系统：[自动提取] parent.industry=IT, budget=150000
```

### 跨会话恢复

```
[一个月后]
用户：我上次说的那个计算机专业，如果是去西安呢？
系统：[从CRM加载画像] province=广东省, subject_type=物理类, score=580, major_name=计算机科学与技术
系统：根据你的情况，西安的西安电子科技大学计算机专业...
```
