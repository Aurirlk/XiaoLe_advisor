"""
反馈闭环 - 收集用户反馈并优化系统

支持:
1. 反馈收集
2. 反馈分析
3. 优化建议生成
4. 自动调优
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class FeedbackRecord:
    """反馈记录"""
    turn_id: str
    session_id: str
    rating: int  # 1-5
    tags: List[str] = field(default_factory=list)
    comment: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    category: str  # routing, retrieval, answer, etc.
    suggestion: str
    priority: str  # high, medium, low
    evidence: List[str] = field(default_factory=list)


class FeedbackLoop:
    """
    反馈闭环系统
    
    收集用户反馈，分析问题，生成优化建议
    """
    
    def __init__(self, feedback_store=None):
        self._feedback_store = feedback_store
        self._feedback_history: List[FeedbackRecord] = []
    
    async def collect_feedback(
        self,
        turn_id: str,
        session_id: str,
        rating: int,
        tags: List[str] = None,
        comment: str = "",
    ) -> bool:
        """收集反馈"""
        feedback = FeedbackRecord(
            turn_id=turn_id,
            session_id=session_id,
            rating=rating,
            tags=tags or [],
            comment=comment,
        )
        
        self._feedback_history.append(feedback)
        
        # 持久化到存储
        if self._feedback_store:
            try:
                await self._feedback_store.save_feedback(feedback)
            except Exception as e:
                print(f"[WARN] 保存反馈失败: {e}")
        
        return True
    
    async def analyze_feedback(
        self,
        time_range_days: int = 30,
    ) -> Dict[str, Any]:
        """分析反馈数据"""
        # 获取反馈数据
        feedbacks = self._get_feedbacks(time_range_days)
        
        if not feedbacks:
            return {"message": "暂无反馈数据"}
        
        # 统计评分分布
        rating_dist = Counter(f.rating for f in feedbacks)
        
        # 统计标签
        tag_dist = Counter()
        for f in feedbacks:
            tag_dist.update(f.tags)
        
        # 计算平均评分
        avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
        
        # 识别低分反馈
        low_ratings = [f for f in feedbacks if f.rating <= 2]
        
        return {
            "total_feedbacks": len(feedbacks),
            "average_rating": avg_rating,
            "rating_distribution": dict(rating_dist),
            "top_tags": tag_dist.most_common(10),
            "low_rating_count": len(low_ratings),
            "low_rating_comments": [f.comment for f in low_ratings if f.comment][:10],
        }
    
    def _get_feedbacks(self, days: int) -> List[FeedbackRecord]:
        """获取指定时间范围内的反馈"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        return [f for f in self._feedback_history if f.created_at >= cutoff]
    
    async def generate_suggestions(
        self,
        analysis: Dict[str, Any],
    ) -> List[OptimizationSuggestion]:
        """生成优化建议"""
        suggestions = []
        
        # 检查平均评分
        avg_rating = analysis.get("average_rating", 5.0)
        if avg_rating < 3.5:
            suggestions.append(OptimizationSuggestion(
                category="overall",
                suggestion="整体评分偏低，需要全面提升系统质量",
                priority="high",
                evidence=[f"平均评分: {avg_rating:.2f}"],
            ))
        
        # 检查低分反馈
        low_count = analysis.get("low_rating_count", 0)
        if low_count > 5:
            suggestions.append(OptimizationSuggestion(
                category="quality",
                suggestion="低分反馈较多，需要重点改进回答质量",
                priority="high",
                evidence=[f"低分反馈数: {low_count}"],
            ))
        
        # 分析标签
        top_tags = analysis.get("top_tags", [])
        negative_tags = ["不准确", "不相关", "太慢", "错误"]
        for tag, count in top_tags:
            if tag in negative_tags and count > 3:
                suggestions.append(OptimizationSuggestion(
                    category="specific",
                    suggestion=f"用户反馈 '{tag}' 问题较多，需要针对性改进",
                    priority="medium",
                    evidence=[f"标签 '{tag}' 出现 {count} 次"],
                ))
        
        return suggestions
    
    async def auto_optimize(
        self,
        suggestions: List[OptimizationSuggestion],
    ) -> Dict[str, Any]:
        """自动优化（基于反馈）"""
        optimizations = []
        
        for suggestion in suggestions:
            if suggestion.priority == "high":
                # 记录高优先级优化
                optimizations.append({
                    "category": suggestion.category,
                    "action": suggestion.suggestion,
                    "status": "pending",
                })
        
        return {
            "optimizations": optimizations,
            "total_suggestions": len(suggestions),
            "high_priority": len([s for s in suggestions if s.priority == "high"]),
        }
