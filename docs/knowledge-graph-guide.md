# Neo4j 知识图谱指南

> 本文档介绍小乐AI系统中Neo4j知识图谱的部署、配置、数据模型和查询工具。

---

## 目录

- [概述](#概述)
- [Neo4j部署](#neo4j部署)
- [图模型设计](#图模型设计)
- [数据导入](#数据导入)
- [查询工具](#查询工具)
- [可视化页面](#可视化页面)
- [常见问题](#常见问题)

---

## 概述

小乐AI使用Neo4j知识图谱存储院校、专业、职业、产业集群、就业政策等实体之间的复杂关系。相比传统SQL的多表联查，图数据库天然支持多跳查询，能够快速回答类似"广东物理600分 → 能上哪些学校的计算机 → 这些学校在深圳有没有校区 → 深圳的就业政策是什么"的复杂问题。

### 核心优势

| 优势 | 说明 |
|------|------|
| 多跳查询 | 一次查询遍历多层关系，无需JOIN |
| 关系优先 | 关系是第一类公民，查询效率高 |
| 模板化Cypher | 禁止Text2Cypher，所有查询预定义，零幻觉 |
| 可视化 | 支持图谱可视化，直观展示实体关系 |

---

## Neo4j部署

### Docker部署（推荐）

```bash
# 启动Neo4j容器
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -v neo4j_data:/data \
  neo4j:5.15-community
```

### 访问Neo4j浏览器

- 地址：http://localhost:7474
- 用户名：`neo4j`
- 密码：`password`

### 配置文件

编辑 `configs/neo4j_config.yaml`：

```yaml
neo4j:
  uri: "bolt://localhost:7687"
  username: "neo4j"
  password: "password"
  database: "neo4j"
  max_connection_lifetime: 3600
  max_connection_pool_size: 50
```

---

## 图模型设计

### 节点类型

| 节点类型 | 属性 | 说明 |
|---------|------|------|
| `University` | name, level, city, tags | 大学院校 |
| `Province` | name | 省份 |
| `Major` | name | 专业 |
| `Career` | name, prospect | 职业（绿牌/红牌） |
| `City` | name | 城市 |
| `IndustryCluster` | name, city, industry, core_companies, avg_salary | 产业集群 |
| `Policy` | name, city, type, description, eligibility, amount, search_keyword | 就业政策 |

### 关系类型

| 关系类型 | 起点→终点 | 属性 | 说明 |
|---------|----------|------|------|
| `LOCATED_IN` | University→Province | - | 大学所在省份 |
| `OFFERS` | University→Major | year, subject_type, min_score, min_rank | 录取分数线 |
| `LEADS_TO` | Major→Career | - | 专业→职业路径 |
| `HAS_CLUSTER` | City→IndustryCluster | - | 城市→产业集群 |
| `HAS_POLICY` | City→Policy | - | 城市→就业政策 |

### 图谱示例

```
(清华大学)-[:LOCATED_IN]->(北京)
(清华大学)-[:OFFERS {year:2020, min_score:694}]->(计算机科学与技术)
(计算机科学与技术)-[:LEADS_TO]->(软件工程师)
(北京)-[:HAS_CLUSTER]->(中关村科技园)
(北京)-[:HAS_POLICY]->(北京人才引进政策)
```

---

## 数据导入

### 从SQLite导入

```bash
# 确保SQLite数据库已初始化
python scripts/init_sqlite.py

# 导入数据到Neo4j
python scripts/import_neo4j.py
```

### 导入内容

| 数据类型 | 来源 | 数量 |
|---------|------|------|
| 大学节点 | universities表 | 2,708所 |
| 省份节点 | admission_scores表 | 29个 |
| 专业节点 | admission_scores表 | ~100个 |
| 职业节点 | 预设数据 | 25个 |
| 城市节点 | 预设数据 | 14个 |
| 产业集群 | 预设数据 | 25个 |
| 就业政策 | 预设数据 | 15个 |

### 验证导入

在Neo4j浏览器中执行：

```cypher
// 统计节点数量
MATCH (n) RETURN labels(n) AS type, count(n) AS count

// 统计关系数量
MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count

// 查询广东的录取数据
MATCH (u:University)-[o:OFFERS]->(m:Major)
WHERE o.subject_type = "物理类" AND o.min_score >= 600 AND o.min_score <= 650
RETURN u.name, m.name, o.min_score
ORDER BY o.min_score DESC
LIMIT 10
```

---

## 查询工具

### 3个核心查询工具

#### 1. query_neo4j_admission_tool

查询符合分数的大学和专业推荐。

```python
from tools.neo4j_tools import query_neo4j_admission_tool

result = query_neo4j_admission_tool.invoke({
    "province": "广东",
    "subject_type": "物理类",
    "score": 600,
    "target_major": "计算机"
})
```

#### 2. query_career_path_tool

查询专业对应的职业路径和就业前景。

```python
from tools.neo4j_tools import query_career_path_tool

result = query_career_path_tool.invoke({
    "major_name": "计算机科学与技术"
})
```

#### 3. query_university_info_tool

查询大学详细信息。

```python
from tools.neo4j_tools import query_university_info_tool

result = query_university_info_tool.invoke({
    "university_name": "清华大学"
})
```

### 架构铁律

**禁止Text2Cypher！** 所有Cypher必须是预定义的模板。

```python
# ✅ 正确：模板化查询
cypher = """
MATCH (u:University)-[o:OFFERS]->(m:Major)
WHERE o.subject_type = $subject_type 
  AND o.min_score <= $max_score 
  AND o.min_score >= $min_score
RETURN u.name, m.name, o.min_score
"""

# ❌ 错误：让LLM生成Cypher
# 这会导致幻觉和安全风险
```

---

## 可视化页面

### 访问方式

1. 启动服务：`python -m api.main`
2. 访问前端：http://127.0.0.1:5000
3. 点击顶部导航栏的"知识图谱"按钮

### 功能说明

| 功能 | 说明 |
|------|------|
| 查询类型 | 按院校/专业/城市/职业查询 |
| 搜索 | 输入关键词过滤节点 |
| 深度选择 | 1跳/2跳/3跳 |
| 节点拖拽 | 鼠标拖拽移动节点 |
| 缩放 | 滚轮缩放图谱 |
| 节点详情 | 点击节点查看详情 |
| 关联展示 | 显示节点的所有关联关系 |

### 图例

| 节点类型 | 颜色 |
|---------|------|
| 院校 | 蓝色 |
| 专业 | 绿色 |
| 职业 | 橙色 |
| 城市 | 红色 |
| 产业集群 | 灰色 |
| 省份 | 紫色 |

---

## 常见问题

### Q: Neo4j连接失败怎么办？

检查：
1. Docker容器是否运行：`docker ps`
2. 端口是否开放：`telnet localhost 7687`
3. 配置文件是否正确：`configs/neo4j_config.yaml`

### Q: 如何添加新的节点和关系？

修改 `scripts/import_neo4j.py`，添加新的导入函数，然后重新运行：

```bash
python scripts/import_neo4j.py
```

### Q: 如何自定义查询模板？

在 `tools/neo4j_tools.py` 中添加新的工具函数，使用预定义的Cypher模板。

### Q: 图谱数据如何更新？

1. 更新SQLite数据
2. 重新运行导入脚本：`python scripts/import_neo4j.py`
3. 使用MERGE语句确保幂等性

---

## 相关文档

- [数据导入指南](data-import-guide.md)
- [问卷系统指南](questionnaire-guide.md)
- [API参考](api-reference.md)
- [版本历史](version-history.md)

---

*小乐AI · Neo4j知识图谱指南*
