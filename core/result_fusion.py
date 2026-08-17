"""
结果融合器 - 融合多个Agent的输出结果

支持多种融合策略:
1. 合并融合: 将多个结果合并为一个综合回答
2. 投票融合: 基于多数投票选择最佳结果
3. 加权融合: 基于置信度加权合并
4. 专家融合: 根据问题类型选择最合适的Agent结果

⚠️ 状态标注（2026-08-06 架构拷打，2026-08-17 更新）：
本模块已被 `core/graph_builder.py::build_graph(enable_result_fusion=True)` 可选接入
（synthesis 前节点，收集 sql/career/web 多源输出融合写入 fusion_context），
生产默认关闭（api/dependencies.py 未开启）。非"零调用方"，勿删。
候选方向：生产开启前需评估 vs 现状 prompt 合成（career_agent asyncio.gather 四路并行）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import Counter


@dataclass
class AgentResult:
    """Agent结果"""
    agent_name: str
    content: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResultFusion:
    """
    结果融合器
    
    将多个Agent的输出融合为一个连贯的回答
    """
    
    def __init__(self, llm=None):
        self._llm = llm
        self._fusion_strategies = {
            "merge": self._merge_fusion,
            "vote": self._vote_fusion,
            "weighted": self._weighted_fusion,
            "expert": self._expert_fusion,
        }
    
    async def fuse(
        self,
        results: List[AgentResult],
        query: str,
        strategy: str = "merge",
    ) -> str:
        """
        融合多个Agent结果
        
        Args:
            results: Agent结果列表
            query: 用户查询
            strategy: 融合策略
        
        Returns:
            融合后的回答
        """
        if not results:
            return "抱歉，我没有找到相关信息。"
        
        if len(results) == 1:
            return results[0].content
        
        fusion_func = self._fusion_strategies.get(strategy, self._merge_fusion)
        return await fusion_func(results, query)
    
    async def _merge_fusion(
        self,
        results: List[AgentResult],
        query: str,
    ) -> str:
        """合并融合 - 将多个结果合并为一个综合回答"""
        if not self._llm:
            # 无LLM时简单拼接
            return self._simple_merge(results)
        
        # 准备输入
        results_text = []
        for i, result in enumerate(results, 1):
            results_text.append(f"[来源{i}: {result.agent_name}]\n{result.content}")
        
        results_combined = "\n\n---\n\n".join(results_text)
        
        prompt = f"""请将以下多个来源的信息融合为一个连贯的回答:

用户查询: {query}

多个来源的信息:
{results_combined}

要求:
1. 保持张雪峰风格（直接、务实、数据驱动）
2. 去除重复信息
3. 保留最有价值的内容
4. 如果有冲突信息，选择更可靠的数据
5. 结构清晰，逻辑连贯

融合后的回答:"""
        
        try:
            response = await self._llm.ainvoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            print(f"[WARN] LLM融合失败: {e}")
            return self._simple_merge(results)
    
    def _simple_merge(self, results: List[AgentResult]) -> str:
        """简单合并（无LLM时使用）"""
        contents = [r.content for r in results if r.content]
        
        if not contents:
            return "抱歉，我没有找到相关信息。"
        
        # 去重
        unique_contents = list(dict.fromkeys(contents))
        
        # 拼接
        if len(unique_contents) == 1:
            return unique_contents[0]
        
        return "\n\n".join([f"**信息{i+1}**: {content}" for i, content in enumerate(unique_contents)])
    
    async def _vote_fusion(
        self,
        results: List[AgentResult],
        query: str,
    ) -> str:
        """投票融合 - 基于多数投票选择最佳结果"""
        if not results:
            return "抱歉，我没有找到相关信息。"
        
        # 统计投票
        votes = Counter()
        for result in results:
            # 使用内容的前100字符作为投票键（简化处理）
            key = result.content[:100]
            votes[key] += 1
        
        # 选择得票最多的结果
        if votes:
            best_key = votes.most_common(1)[0][0]
            for result in results:
                if result.content[:100] == best_key:
                    return result.content
        
        # 默认返回置信度最高的结果
        best_result = max(results, key=lambda r: r.confidence)
        return best_result.content
    
    async def _weighted_fusion(
        self,
        results: List[AgentResult],
        query: str,
    ) -> str:
        """加权融合 - 基于置信度加权合并"""
        if not results:
            return "抱歉，我没有找到相关信息。"
        
        # 计算权重
        total_confidence = sum(r.confidence for r in results)
        if total_confidence == 0:
            return await self._merge_fusion(results, query)
        
        # 按权重排序
        weighted_results = sorted(results, key=lambda r: r.confidence, reverse=True)
        
        # 选择置信度最高的结果作为主结果
        primary_result = weighted_results[0]
        
        # 如果有其他高置信度结果，尝试融合
        high_confidence_results = [r for r in weighted_results if r.confidence > 0.7]
        if len(high_confidence_results) > 1:
            return await self._merge_fusion(high_confidence_results, query)
        
        return primary_result.content
    
    async def _expert_fusion(
        self,
        results: List[AgentResult],
        query: str,
    ) -> str:
        """专家融合 - 根据问题类型选择最合适的Agent结果"""
        if not results:
            return "抱歉，我没有找到相关信息。"
        
        # 问题类型到Agent的映射
        expert_mapping = {
            "match_agent": ["分数", "位次", "录取", "分数线", "投档"],
            "career_agent": ["就业", "薪资", "前景", "考公", "考研"],
            "web_search_agent": ["最新", "政策", "新闻", "官网"],
            "sql_agent": ["查询", "数据", "统计"],
        }
        
        # 识别问题类型
        query_lower = query.lower()
        best_agent = None
        best_score = 0
        
        for agent_name, keywords in expert_mapping.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > best_score:
                best_score = score
                best_agent = agent_name
        
        # 如果找到合适的专家Agent，优先使用其结果
        if best_agent:
            for result in results:
                if result.agent_name == best_agent:
                    return result.content
        
        # 否则使用加权融合
        return await self._weighted_fusion(results, query)
