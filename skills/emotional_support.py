"""
情感支持引擎 — 承认焦虑，提供支持

功能：
- 检测用户情绪状态
- 提供针对性的情感支持
- 缓解焦虑和压力
"""
from __future__ import annotations

from typing import Dict, Any


class EmotionalSupport:
    """情感支持引擎"""
    
    def provide_support(self, emotion_label: str, emotion_intensity: float,
                        decision_state: str, query: str) -> str:
        """提供情感支持"""
        
        # 基于情绪类型提供支持
        if emotion_label in ("anxious", "confused"):
            return self._support_anxious(decision_state, query)
        elif emotion_label in ("disappointed", "sad"):
            return self._support_disappointed(query)
        elif emotion_label == "angry":
            return self._support_angry(query)
        
        # 基于决心度提供支持
        if decision_state in ("hesitant", "lost"):
            return self._support_hesitant(decision_state, query)
        
        return ""
    
    def _support_anxious(self, decision_state: str, query: str) -> str:
        """支持焦虑"""
        return """
😌 **我理解你的焦虑**：

18 岁就要做这个决定，确实很难。但你不需要现在就确定一辈子的方向。

很多人后来都转行了，人生不是一条直线。

我们一步步来，不着急。
"""
    
    def _support_disappointed(self, query: str) -> str:
        """支持失望"""
        return """
😔 **我理解你的失望**：

分数不理想，感觉对不起自己和家人。

但分数只是人生的一个节点，不是终点。

很多人高考不理想，后来照样活得很好。

我们看看还有什么选择，好吗？
"""
    
    def _support_angry(self, query: str) -> str:
        """支持愤怒"""
        return """
😤 **我理解你的愤怒**：

可能觉得不公平，可能觉得被误解。

但愤怒不能解决问题，我们冷静下来，看看怎么把损失降到最低。

你愿意告诉我发生了什么吗？
"""
    
    def _support_hesitant(self, decision_state: str, query: str) -> str:
        """支持犹豫"""
        if decision_state == "lost":
            return """
迷茫是正常的，18 岁就要做这个决定确实很难。

你不需要现在就确定一辈子的方向，很多人后来都转行了。

我们一步步来：
1. 先排除你绝对不想做的
2. 再看你能接受什么
3. 最后在里面选最不差的

你先告诉我，有没有什么你绝对不想做的？
"""
        else:
            return """
犹豫是正常的，说明你在认真思考。

我们一起来分析一下，看看哪个选择更适合你。
"""
