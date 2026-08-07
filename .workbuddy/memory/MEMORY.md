
# 项目铁律（2026-08-06 立，用户明确要求）
1. **禁止随意删代码**：删除任何文件前必须：① 对照蓝图文档（.omo/plans/xiaole-ai-master-plan.md / docs/技术文档.md）确认不是蓝图组件；② 向用户确认。教训：agent_bus/reflexion_agent/evaluation 曾因"零引用"被删，实为蓝图"多智能体协作体系"核心，需重建。
2. **项目定位**：作品集（面试展示），非上线产品。架构决策标准 = 能否讲清楚/可 review/与简历叙事自洽。
3. **产品叙事主线**：多 Agent 协同（中枢-员工 Sisyphus 模式）+ RAG/Neo4j/GraphRAG 知识库 + Harness/multi-agent 学习协作机制的高考志愿决策系统。
4. **蓝图文档是真相源**：.omo/plans/xiaole-ai-master-plan.md（699行主计划）、docs/技术文档.md（12大体系）、docs/版本历史.md —— 修改代码前先查蓝图。
