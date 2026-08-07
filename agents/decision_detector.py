"""
决心度检测 Agent — 检测用户犹豫状态并生成回退引导

功能：
- 检测用户是否犹豫/迷茫
- 生成渐进式引导问题
- 集成信息差弥合、决策框架、情感支持
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.state_schema import GraphState
from skills.decision_heuristics import build_soul_questions, generate_progressive_questions
from skills.info_gap_bridger import InfoGapBridger
from skills.decision_framework import DecisionFramework
from skills.emotional_support import EmotionalSupport
from tools.rag_tools import RAGTools

logger = logging.getLogger(__name__)

DECISION_DETECTOR_PROMPT = """
你是决心度检测系统，负责帮助犹豫不决的用户做出决定。

用户当前状态：{decision_state}
犹豫信号：{hesitation_signals}
场景：{scene_type}
路径：{path_type}

你的任务：
1. 理解用户为什么犹豫
2. 提供有针对性的引导
3. 帮助用户理清思路
4. 不要强迫用户，给他们空间

回复风格：
- 温暖、理解、有耐心
- 提供具体的建议，而不是空洞的安慰
- 引导用户思考，而不是替他们做决定
""".strip()


def build_decision_detector(llm: ChatOpenAI, rag_tools: RAGTools):
    """构建决心度检测 Agent"""
    
    info_gap_bridger = InfoGapBridger(rag_tools)
    decision_framework = DecisionFramework()
    emotional_support = EmotionalSupport()
    
    async def decision_detector(state: GraphState) -> Dict[str, Any]:
        query = (state.get("user_query") or "").strip()
        profile = state.get("user_profile") or {}
        decision_state = state.get("decision_state", "firm")
        hesitation_signals = state.get("hesitation_signals", [])
        scene_type = state.get("scene_type", "gaokao")
        path_type = state.get("path_type")
        emotion_label = state.get("emotion_label", "neutral")
        emotion_intensity = state.get("emotion_intensity", 0.0)
        
        # 如果用户决心度很高，直接跳过
        if decision_state == "firm":
            return {
                "next_node": "synthesis_agent",
            }
        
        # 生成各模块内容
        info_gap_content = ""
        decision_framework_content = ""
        emotional_support_content = ""
        progressive_questions = []
        
        # 1. 信息差弥合
        try:
            info_gap_content = await info_gap_bridger.bridge_info_gap(query, profile, scene_type)
        except Exception as e:
            logger.warning(f"信息差弥合失败: {e}")
        
        # 2. 决策框架
        try:
            decision_framework_content = decision_framework.generate_framework(scene_type, path_type, profile)
        except Exception as e:
            logger.warning(f"决策框架生成失败: {e}")
        
        # 3. 情感支持
        try:
            emotional_support_content = emotional_support.provide_support(
                emotion_label, emotion_intensity, decision_state, query
            )
        except Exception as e:
            logger.warning(f"情感支持生成失败: {e}")
        
        # 4. 渐进询问
        try:
            progressive_questions = await generate_progressive_questions(
                profile, scene_type, path_type
            )
        except Exception as e:
            logger.warning(f"渐进询问生成失败: {e}")
        
        # 5. 生成综合回复
        context_parts = []
        if info_gap_content:
            context_parts.append(f"[信息差弥合]\n{info_gap_content}")
        if decision_framework_content:
            context_parts.append(f"[决策框架]\n{decision_framework_content}")
        if emotional_support_content:
            context_parts.append(f"[情感支持]\n{emotional_support_content}")
        
        context = "\n\n".join(context_parts) if context_parts else "暂无额外信息"

        # 构建灵魂追问
        soul_questions = build_soul_questions(profile)
        soul_text = "\n".join([f"- {q}" for q in soul_questions[:3]]) if soul_questions else "暂无追问"

        # P1-2：不再在此生成 LLM 回复 —— graph_builder 对 decision_detector 是硬边
        # （add_edge → synthesis_agent），next_node 会被覆盖，LLM 调用纯属浪费。
        # 只产出结构化 hints，由 synthesis_agent 统一生成最终回复。
        return {
            "info_gap_content": info_gap_content,
            "decision_framework": decision_framework_content,
            "emotional_support": emotional_support_content,
            "progressive_questions": progressive_questions,
            "next_node": "synthesis_agent",
        }

    return decision_detector
