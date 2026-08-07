"""
普通聊天 Agent — 处理非高考/考研相关对话

功能：
- 情感交流、闲聊、日常问题
- 引导用户回到志愿填报话题
- 提供情感支持
"""
from __future__ import annotations

import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.state_schema import GraphState

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """
你是小乐AI，一个温暖、有耐心的高考志愿填报助手。

当前用户正在和你进行普通聊天，不是咨询高考志愿相关问题。

你的回复原则：
1. 保持温暖、友善的语气
2. 适当回应用户的情感需求
3. 如果合适，可以温和地引导用户回到志愿填报话题
4. 不要强迫用户，尊重他们想聊天的需求
5. 如果用户表达了焦虑或压力，给予情感支持

回复风格：
- 简洁、自然、像朋友聊天
- 不要过于正式
- 可以适当使用表情符号
""".strip()


def build_chat_agent(llm: ChatOpenAI):
    """构建普通聊天 Agent"""
    
    async def chat_agent(state: GraphState) -> Dict[str, Any]:
        query = (state.get("user_query") or "").strip()
        profile = state.get("user_profile") or {}
        emotion_label = state.get("emotion_label", "neutral")
        emotion_intensity = state.get("emotion_intensity", 0.0)
        
        # 构建上下文
        context_parts = []
        
        # 用户画像
        if profile.get("province"):
            context_parts.append(f"用户省份：{profile['province']}")
        if profile.get("score"):
            context_parts.append(f"用户分数：{profile['score']}")
        
        # 情绪状态
        if emotion_label != "neutral":
            context_parts.append(f"用户情绪：{emotion_label}（强度：{emotion_intensity:.1f}）")
        
        context = "\n".join(context_parts) if context_parts else "暂无用户画像"
        
        # 生成回复
        try:
            resp = await llm.ainvoke([
                SystemMessage(content=CHAT_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"用户画像：\n{context}\n\n"
                        f"用户消息：{query}\n\n"
                        "请回复用户，保持温暖友善的语气。如果合适，可以温和地引导用户回到志愿填报话题。"
                    )
                ),
            ])
            
            reply = (resp.content or "").strip()
            
            return {
                "messages": [{"role": "assistant", "content": reply}],
                "next_node": "END",
            }
            
        except Exception as e:
            logger.error(f"Chat agent 调用失败: {e}", exc_info=True)
            return {
                "messages": [{"role": "assistant", "content": "抱歉，我暂时无法回复。请稍后再试。"}],
                "next_node": "END",
            }
    
    return chat_agent
