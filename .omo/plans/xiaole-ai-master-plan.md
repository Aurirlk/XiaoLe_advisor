# 小乐AI 项目全面审查与总体开发计划

> 审查日期: 2026-06-16
> 审查范围: 全项目代码、架构、数据流、知识库、前端组件、测试覆盖
> 计划版本: v1.0

---

## TL;DR

> **Summary**: 小乐AI项目架构优秀，但在前端样式、数据基础和RAG能力方面存在明显短板，需要系统性改进
> **Deliverables**: 完整的知识库、多维RAG检索、Multi-Agent协作、前端修复
> **Effort**: XL（约15周）
> **Parallel**: YES - 5个阶段可部分并行
> **Critical Path**: Phase 0（前端修复）→ Phase 1（知识库）→ Phase 2（RAG增强）

---

## 一、项目架构总览

### 1.1 系统架构

```
用户输入（文字/语音/图片）
    │
    ▼
┌──────────────────────────────────────────────┐
│          Supervisor Agent (路由中枢)           │
│   ├─ LLM 结构化意图识别                        │
│   ├─ 家长/学生角色分流                         │
│   └─ _fallback_route (确定性关键词兜底)         │
└───┬───┬───┬───┬───┬───┬───┬───┬──────────────┘
    │   │   │   │   │   │   │   │
    ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼
 Profile Parent Family Match Career Web  SQL  Synthesis
 Agent   Agent  Agent  Agent Agent  Search Agent Agent
    │   │   │   │   │   │   │
    └───┴───┴───┴───┴───┴───┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Synthesis Agent      │
    │   + SynthesisGuard     │
    │   (防端水硬约束引擎)     │
    └────────────────────────┘
                 │
                 ▼
         SSE/WebSocket → Vue 3 前端
```

### 1.2 数据存储架构

| 存储层 | 技术 | 用途 | 数据量 |
|--------|------|------|--------|
| 关系型数据库 | SQLite | 院校/分数线/用户画像/对话/反馈 | 15所种子院校 + 24条种子分数线 + 283,653条原始数据 |
| 向量数据库 | ChromaDB | 经验库语义检索 | 383条文档 |
| 知识图谱 | Neo4j | 院校-专业-职业-城市-政策关系 | 需Docker部署 |
| 缓存 | Redis | 会话管理/分布式缓存 | 7天TTL |
| 全文检索 | SQLite FTS5 | RAG全文检索 | 随文档同步 |
| JSON文件 | 本地文件 | 经验库索引/配置 | ~120KB |

### 1.3 数据流向

```
用户输入
  ↓
Supervisor Agent (意图识别)
  ↓
Worker Agent (数据采集)
  ├─ match_agent → SQLTools → SQLite (四级降级链)
  ├─ career_agent → RAGTools → ChromaDB + FTS5 + 关键词 (RRF融合)
  ├─ web_search_agent → WebSearchTools → DuckDuckGo/Metaso/Tavily
  ├─ sql_agent → Function Calling → Neo4j + SQLite
  ├─ profile_agent → 用户画像提取 → State
  ├─ parent_agent → 家长画像提取 → State
  └─ family_agent → 家庭融合 → State
  ↓
Synthesis Agent + SynthesisGuard
  ↓
SSE/WebSocket → Vue 3 前端
```

---

## 二、代码审查发现的问题

### 2.1 严重问题 (Critical)

#### 2.1.1 前端登录页CSS样式缺失

**问题描述**: 
- `LoginPage.js` 使用了12+个CSS类，但 `styles.css` 中完全没有定义
- 登录页面会显示为无样式的原始HTML元素，用户体验极差

**证据**:
```css
/* styles.css 中完全没有以下样式 */
.login-page { /* ❌ 无样式 */ }
.login-container { /* ❌ 无样式 */ }
.login-header { /* ❌ 无样式 */ }
.login-form { /* ❌ 无样式 */ }
.form-group { /* ❌ 无样式 */ }
.submit-btn { /* ❌ 无样式 */ }
```

**影响**: 用户首次访问看到的是无样式的原始HTML，严重影响第一印象

#### 2.1.2 知识图谱和排名页面无后端API

**问题描述**:
- `KnowledgeGraph.js` 使用硬编码的示例数据（16个节点+18条边）
- `UniversityRanking.js` 使用硬编码的示例数据（QS排名前20）
- 没有对应的后端API端点

**证据**:
```javascript
// KnowledgeGraph.js 第213-217行
loadGraph() {
    // 使用示例数据（实际应从API获取）
    this.nodes = JSON.parse(JSON.stringify(this.sampleGraph.nodes));
    this.edges = JSON.parse(JSON.stringify(this.sampleGraph.edges));
},

// UniversityRanking.js 第237-258行
universities: [
    { rank: 1, name: '麻省理工学院', score: 100 },
    // ... 只有20条示例数据
],
```

**影响**: 知识图谱和排名页面显示的是假数据，无法满足用户需求

#### 2.1.3 RAG 知识库严重匮乏

**问题描述**: 
- `data/documents/` 目录下只有一个 `README.md`，没有任何实际文档
- `data/vector_store/zx_experience.json` 只有383条经验片段
- 缺少：专业详解、院校详情、就业数据、政策文件、报考指南

**影响**: RAG检索几乎无法返回有价值的结果

#### 2.1.4 种子数据严重不足

**问题描述**: 
- `init_sqlite.py` 只有15所院校 + 24条分数线（仅广东省物理类2025年）
- 原始数据 `data/raw/gaokao_data/` 有283,653条（2016-2020年），但未导入
- 缺少2021-2025年的最新数据和历史类数据

**影响**: 用户问非广东省或历史类的分数线时，系统无法回答

### 2.2 中等问题 (Medium)

#### 2.2.1 RAG 检索准确性问题

**问题描述**:
- `rag_tools.py` 的 `_dense_score` 方法使用简单的词频重叠，不是真正的语义相似度
- 嵌入模型 `paraphrase-multilingual-MiniLM-L12-v2` 只有384维
- 没有多维embedding（dense + sparse + colbert）

#### 2.2.2 GraphRAG 缺失

**问题描述**:
- Neo4j 和 ChromaDB 之间没有协同工作
- 缺少图嵌入、子图检索、图神经网络推理

#### 2.2.3 Multi-Agent 机制不完善

**问题描述**:
- Worker Agent 之间没有协作机制
- 缺乏自我反思和修正能力
- 缺乏记忆共享和循环推理

### 2.3 轻微问题 (Low)

#### 2.3.1 登出功能不完整

- 前端有 `removeToken()` 但没有登出按钮
- 没有用户信息显示

#### 2.3.2 Token刷新缺失

- 没有Token自动刷新机制
- Token过期后需要重新登录

#### 2.3.3 问卷结果可视化缺失

- 问卷系统功能完整，但缺少结果分析报告页面
- 缺少MBTI性格测试的详细分析

---

## 三、前端组件状态审查

### 3.1 组件完成度总览

| 组件 | 完成度 | 关键缺失 | 优先级 |
|------|--------|----------|--------|
| 登录注册 | 70% | CSS样式、登出按钮、Token刷新 | P0 |
| 对话系统 | 95% | 无 | - |
| 问卷系统 | 95% | 结果可视化、MBTI详细分析 | P1 |
| 知识图谱 | 60% | 后端API、真实数据 | P0 |
| 院校排名 | 60% | 后端API、真实数据 | P0 |
| B端管理后台 | 90% | 无 | - |

### 3.2 登录注册系统详情

**已完成**:
- ✅ 前端页面 (`LoginPage.js` - 135行)
- ✅ 后端API (`auth_router.py` - 120行)
- ✅ 认证模块 (`core/auth.py` - 88行)
- ✅ API客户端 (`apiClient.js` - 102行)
- ✅ 主页面整合 (`index.html`)

**缺失**:
- ❌ CSS样式（最紧急）
- ❌ 登出按钮
- ❌ Token自动刷新
- ❌ 密码找回功能

### 3.3 知识图谱可视化详情

**已完成**:
- ✅ Canvas渲染节点和关系
- ✅ 节点拖拽移动
- ✅ 滚轮缩放
- ✅ 节点详情面板

**缺失**:
- ❌ 后端API端点
- ❌ 真实Neo4j数据连接
- ❌ 图谱搜索API

### 3.4 院校排名页面详情

**已完成**:
- ✅ 6个排名来源切换
- ✅ 院校搜索和筛选
- ✅ 排名详情弹窗
- ✅ 排名体系对比说明

**缺失**:
- ❌ 后端API端点
- ❌ 真实排名数据
- ❌ 排名数据采集

---

## 四、总体开发计划

### Phase 0: 前端紧急修复 (1周) - 新增

**目标**: 修复前端关键缺失，让系统可用。

#### 0.1 登录页CSS样式 (1天)

**What to do**:
1. 在 `frontend/assets/styles.css` 中添加登录页样式
2. 实现全屏居中布局
3. 添加卡片容器、阴影、圆角
4. 添加表单样式（label、input、button）
5. 添加响应式布局
6. 添加动画效果

**需要添加的CSS类**:
```css
.login-page { /* 全屏居中布局 */ }
.login-container { /* 卡片容器，阴影，圆角 */ }
.login-header { /* 标题样式 */ }
.login-tabs { /* 登录/注册切换Tab */ }
.tab-btn { /* Tab按钮样式 */ }
.login-form { /* 表单布局 */ }
.form-group { /* 表单项，label+input */ }
.role-select { /* 角色选择布局 */ }
.role-option { /* 角色选项样式 */ }
.error-message { /* 错误提示样式 */ }
.submit-btn { /* 提交按钮，渐变背景 */ }
.login-footer { /* 底部协议链接 */ }
```

**Acceptance Criteria**:
- [ ] 登录页显示正常，有完整的样式
- [ ] 响应式布局在移动端正常显示
- [ ] 登录/注册Tab切换正常
- [ ] 角色选择显示正常
- [ ] 错误提示样式正确

#### 0.2 登出功能 (0.5天)

**What to do**:
1. 在 `AppLayout.js` 的 header 中添加用户信息显示
2. 添加登出按钮
3. 实现登出逻辑（清除Token，跳转登录页）

**Acceptance Criteria**:
- [ ] 登出按钮显示在header右侧
- [ ] 点击登出后清除Token
- [ ] 登出后跳转到登录页

#### 0.3 图谱查询API (1天)

**What to do**:
1. 创建 `api/routers/graph_router.py`
2. 实现 `/api/graph/query` 端点
3. 连接 Neo4j 数据库
4. 实现图谱查询逻辑
5. 修改 `KnowledgeGraph.js` 调用真实API

**API设计**:
```python
@router.get("/graph/query")
async def query_graph(
    query_type: str,  # university/major/city/career
    keyword: str,
    depth: int = 2
):
    """查询知识图谱"""
    # 连接Neo4j
    # 执行Cypher查询
    # 返回节点和边
```

**Acceptance Criteria**:
- [ ] API端点正常响应
- [ ] 前端调用API显示真实数据
- [ ] 支持按类型查询
- [ ] 支持深度控制

#### 0.4 排名数据API (1天)

**What to do**:
1. 创建 `api/routers/ranking_router.py`
2. 准备排名数据（JSON格式）
3. 实现 `/api/ranking/{source}` 端点
4. 修改 `UniversityRanking.js` 调用真实API

**API设计**:
```python
@router.get("/ranking/{source}")
async def get_ranking(
    source: str,  # qs/usnews/times/nature/arwu/cuhk
    country: Optional[str] = None,
    keyword: Optional[str] = None
):
    """获取院校排名"""
    # 加载排名数据
    # 筛选和搜索
    # 返回排名列表
```

**Acceptance Criteria**:
- [ ] 6个排名来源都有数据
- [ ] 搜索和筛选功能正常
- [ ] 前端调用API显示真实数据

#### 0.5 Token自动刷新 (0.5天)

**What to do**:
1. 在 `apiClient.js` 中添加Token过期检测
2. 实现Token自动刷新逻辑
3. 处理刷新失败情况

**Acceptance Criteria**:
- [ ] Token过期前自动刷新
- [ ] 刷新失败后跳转登录页
- [ ] 不影响正常请求

---

### Phase 1: 知识库基础建设 (2-3周)

**目标**: 建立完整的数据基础，让系统能够回答基本问题。

#### 1.1 数据导入 (1周)

**What to do**:
1. 完善 `import_gaokao_from_xlsx.py`
   - 修复文件名解析逻辑
   - 添加数据校验和去重
   - 添加导入进度显示
2. 运行数据导入
   ```bash
   python scripts/init_sqlite.py
   python scripts/import_gaokao_from_xlsx.py
   python scripts/import_neo4j.py
   ```
3. 数据质量验证

**Acceptance Criteria**:
- [ ] 导入283,653条录取数据
- [ ] 覆盖全国29个省份
- [ ] 数据完整性和准确性验证通过

#### 1.2 知识库文档建设 (1-2周)

**What to do**:
1. 编写专业详解文档（100+专业）
2. 编写院校详情文档（985/211/双一流）
3. 编写就业数据文档（薪资、就业率、行业趋势）
4. 编写政策文件文档（各省招生政策）
5. 编写报考指南文档（张雪峰风格）

**文档结构**:
```
data/documents/
├── majors/                    # 专业详解
├── universities/              # 院校详情
├── employment/                # 就业数据
├── policies/                  # 政策文件
└── guides/                    # 报考指南
```

**Acceptance Criteria**:
- [ ] 至少100篇专业详解文档
- [ ] 至少50篇院校详情文档
- [ ] 至少20篇就业数据文档
- [ ] RAG检索能够返回有价值的结果

#### 1.3 RAG 索引重建 (1天)

**What to do**:
1. 重建 RAG 索引
2. 重建 ChromaDB 向量库
3. 重建 FTS5 全文索引
4. 验证检索质量

**命令**:
```bash
python scripts/build_rag_index.py
curl -X POST http://127.0.0.1:8000/rag/scan-documents
```

**Acceptance Criteria**:
- [ ] RAG索引包含所有文档
- [ ] ChromaDB向量库同步完成
- [ ] 检索返回相关结果

---

### Phase 2: RAG 能力增强 (2-3周)

**目标**: 提升检索准确性，实现多维检索。

#### 2.1 多维 Embedding (1周)

**What to do**:
1. 安装依赖: `pip install FlagEmbedding`
2. 下载模型: `BAAI/bge-m3`
3. 实现 `MultiEmbeddingStore` 类
4. 修改 `rag_tools.py` 使用新的嵌入存储
5. 重建索引

**技术方案**:
```python
class MultiEmbeddingStore:
    """多维嵌入向量存储"""
    
    def __init__(self):
        # Dense embedding: BGE-M3 (1024维)
        self.dense_model = SentenceTransformer("BAAI/bge-m3")
        
        # Sparse embedding: BM25
        self.sparse_index = BM25Index()
        
        # ColBERT: 细粒度交互
        self.colbert_model = ColBERTEncoder()
```

**Acceptance Criteria**:
- [ ] 检索准确率提升20%以上
- [ ] 支持dense + sparse + colbert三路检索
- [ ] RRF融合正常工作

#### 2.2 GraphRAG 实现 (1-2周)

**What to do**:
1. 实现 `GraphRAG` 类
2. 在 `match_agent` 和 `career_agent` 中集成
3. 添加图谱检索缓存
4. 测试多跳查询

**Acceptance Criteria**:
- [ ] Neo4j和ChromaDB协同工作
- [ ] 支持多跳查询
- [ ] 检索结果包含图谱信息

#### 2.3 检索重排序 (3天)

**What to do**:
1. 安装依赖: `pip install FlagEmbedding`
2. 实现 `Reranker` 类
3. 在 `rag_tools.py` 中集成
4. 测试重排序效果

**Acceptance Criteria**:
- [ ] 重排序后相关性提升
- [ ] 响应时间可接受（<500ms）

---

### Phase 3: Multi-Agent 增强 (2-3周)

**目标**: 实现 Agent 协作和循环推理。

#### 3.1 Agent 协作机制 (1周)

**What to do**:
1. 实现 `AgentCommunicationBus` 类
2. 在 `graph_builder.py` 中集成通信总线
3. 修改 Worker Agent 支持消息订阅
4. 测试 Agent 间协作

**Acceptance Criteria**:
- [ ] Agent之间可以发送和接收消息
- [ ] 协作流程正常工作
- [ ] 性能影响可接受

#### 3.2 自我反思循环 (1周)

**What to do**:
1. 实现 `ReflexionAgent` 类
2. 在 `match_agent` 和 `career_agent` 中集成
3. 添加反思记忆
4. 测试反思效果

**Acceptance Criteria**:
- [ ] 结果不满意时可以重新推理
- [ ] 反思记忆正常工作
- [ ] 推理质量提升

#### 3.3 结果融合策略 (3天)

**What to do**:
1. 实现 `ResultFusion` 类
2. 在 `synthesis_agent` 前添加融合节点
3. 测试融合效果

**Acceptance Criteria**:
- [ ] 多个Agent结果正确融合
- [ ] 冲突检测正常工作
- [ ] 推荐结果更全面

---

### Phase 4: 工程闭环 (1-2周)

**目标**: 建立完整的评测和反馈体系。

#### 4.1 评测体系 (1周)

**What to do**:
1. 建立端到端评测框架
2. 创建评测数据集（100+用例）
3. 实现自动评测脚本
4. 建立评测报告生成

**评测维度**:
| 维度 | 指标 | 目标值 |
|------|------|--------|
| 路由准确率 | Supervisor 路由正确率 | ≥95% |
| 检索准确率 | RAG 检索相关性 | ≥80% |
| 回答质量 | 人工评分（1-5分） | ≥4.0 |
| 响应时间 | 首次响应时间 | ≤2s |
| 用户满意度 | 反馈评分 | ≥4.0 |

**Acceptance Criteria**:
- [ ] 评测框架正常工作
- [ ] 评测数据集覆盖全面
- [ ] 评测报告生成正常

#### 4.2 反馈闭环 (3天)

**What to do**:
1. 实现 `FeedbackLoop` 类
2. 在 `synthesis_agent` 结束后调用
3. 添加定时任务处理反馈
4. 测试优化效果

**Acceptance Criteria**:
- [ ] 用户反馈正确收集
- [ ] 反馈分析正常工作
- [ ] 优化建议生成正常

---

### Phase 5: 用户体验增强 (2-3周)

**目标**: 提升用户体验，增加核心功能。

#### 5.1 推荐理由解释 (1周)

**What to do**:
1. 在 `synthesis_agent` 中添加理由生成
2. 前端展示推荐理由
3. 测试理由生成质量

**Acceptance Criteria**:
- [ ] 每个推荐都有理由说明
- [ ] 理由清晰易懂
- [ ] 理由基于数据

#### 5.2 对比分析 (1周)

**What to do**:
1. 实现 `ComparisonEngine` 类
2. 添加对比 API 端点
3. 前端添加对比页面
4. 测试对比功能

**Acceptance Criteria**:
- [ ] 支持多校对比
- [ ] 支持多专业对比
- [ ] 对比结果清晰展示

#### 5.3 志愿表生成 (1周)

**What to do**:
1. 实现 `ApplicationFormGenerator` 类
2. 添加志愿表 API 端点
3. 前端添加志愿表页面
4. 测试生成功能

**Acceptance Criteria**:
- [ ] 自动生成冲稳保志愿表
- [ ] 志愿表可导出
- [ ] 建议合理

---

## 五、开发时间表

| Phase | 时间 | 目标 | 关键交付物 |
|-------|------|------|-----------|
| **Phase 0** | **第0-1周** | **前端紧急修复** | **登录页样式、图谱API、排名API** |
| Phase 1 | 第2-4周 | 知识库基础建设 | 完整数据库 + 知识库文档 |
| Phase 2 | 第5-7周 | RAG 能力增强 | 多维Embedding + GraphRAG |
| Phase 3 | 第8-10周 | Multi-Agent 增强 | Agent协作 + 自我反思 |
| Phase 4 | 第11-12周 | 工程闭环 | 评测体系 + 反馈闭环 |
| Phase 5 | 第13-15周 | 用户体验增强 | 推荐理由 + 对比分析 + 志愿表 |

**总工期**: 约15周（3.75个月）

---

## 六、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 数据采集困难 | 高 | 中 | 使用公开数据源，与教育机构合作 |
| 模型性能不足 | 高 | 中 | 使用更强大的模型（GPT-4、Claude） |
| Neo4j 部署复杂 | 中 | 低 | 提供 Docker 一键部署 |
| 用户反馈不足 | 中 | 中 | 建立激励机制，收集早期用户反馈 |
| 技术债务积累 | 中 | 高 | 定期重构，保持代码质量 |
| 前端样式问题 | 高 | 低 | 优先修复CSS样式 |

---

## 七、总结

小乐AI 项目架构设计优秀，核心理念清晰（Supervisor-Worker-Skills 三层架构），但在**前端样式**、**数据基础**和 **RAG 能力**方面存在明显短板。

### 关键发现

| 类别 | 问题 | 严重程度 |
|------|------|----------|
| 前端样式 | 登录页无CSS样式 | 🔴 严重 |
| 前端API | 知识图谱和排名页面无后端API | 🔴 严重 |
| 数据库 | 种子数据不足（15所院校+24条分数线） | 🔴 严重 |
| 知识库 | RAG文档库为空 | 🔴 严重 |
| RAG准确性 | 嵌入模型维度低，无多维检索 | 🟡 中等 |
| Multi-Agent | 缺乏协作和反思机制 | 🟡 中等 |

### 最关键的三个改进

1. **前端紧急修复**: 登录页样式、图谱API、排名API（第0-1周）
2. **知识库建设**: 没有数据，一切都是空谈（第2-4周）
3. **RAG 准确性**: 检索质量直接决定回答质量（第5-7周）

### 立即可做的事情

```bash
# 1. 修复登录页样式（最紧急）
# 在 frontend/assets/styles.css 中添加 .login-* 样式

# 2. 导入283,653条数据
python scripts/init_sqlite.py
python scripts/import_gaokao_from_xlsx.py

# 3. 重建RAG索引
python scripts/build_rag_index.py
curl -X POST http://127.0.0.1:8000/rag/scan-documents

# 4. 部署Neo4j并导入数据
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.15-community
python scripts/import_neo4j.py
```

---

*审查完成 · 小乐AI 项目审计报告 · 版本: v1.0*
