"""
情感分析模块 — 从文本/语音识别结果中提取情绪标签

支持两种方案（用户在设置界面选择）：
- keyword: 关键词规则（默认，免费+快）
- llm: LLM 提取（准确，多一次 API 调用）
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmotionResult:
    """情绪分析结果"""
    label: str           # happy/anxious/disappointed/angry/neutral/sad/excited/confused
    intensity: float     # 0.0-1.0 情绪强度
    valence: float       # -1.0(负面) ~ +1.0(正面)
    confidence: float    # 0.0-1.0 置信度
    raw_tags: List[str]  # 命中的原始关键词

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "intensity": round(self.intensity, 2),
            "valence": round(self.valence, 2),
            "confidence": round(self.confidence, 2),
        }


# 情绪关键词词典
_EMOTION_KEYWORDS: Dict[str, Dict[str, Any]] = {
    "happy": {
        "keywords": ["开心", "高兴", "太好了", "棒", "厉害", "不错", "感谢", "谢谢", "赞",
                      "满意", "喜欢", "完美", "牛", "优秀", "可以啊", "真好", "挺好的",
                      "哈哈", "笑死", "太强了", "绝了"],
        "valence": 0.8,
        "base_intensity": 0.7,
    },
    "excited": {
        "keywords": ["激动", "期待", "太期待了", "好期待", "兴奋", "迫不及待", "冲冲冲",
                      "冲鸭", "太棒了", "梦想", "终于"],
        "valence": 0.9,
        "base_intensity": 0.8,
    },
    "anxious": {
        "keywords": ["焦虑", "担心", "害怕", "紧张", "不安", "慌", "怕", "担忧", "着急",
                      "急死了", "怎么办", "万一", "不确定", "心里没底", "没底", "忐忑",
                      "纠结", "犹豫", "好难选", "选不出来"],
        "valence": -0.5,
        "base_intensity": 0.7,
    },
    "confused": {
        "keywords": ["不懂", "不明白", "啥意思", "什么意思", "搞不懂", "看不懂", "听不懂",
                      "一头雾水", "懵", "迷惑", "不理解", "为什么", "怎么回事"],
        "valence": -0.2,
        "base_intensity": 0.5,
    },
    "disappointed": {
        "keywords": ["失望", "没用", "不行", "差", "太差了", "垃圾", "废了", "完了",
                      "白搭", "没希望", "没戏", "上不了", "够呛", "可惜", "遗憾",
                      "不甘心", "唉", "算了"],
        "valence": -0.7,
        "base_intensity": 0.7,
    },
    "angry": {
        "keywords": ["生气", "愤怒", "气死", "烦死了", "烦", "讨厌", "受不了", "崩溃",
                      "离谱", "过分", "坑", "坑人", "坑爹", "什么鬼", "服了",
                      "无语", "醉了", "去你的"],
        "valence": -0.8,
        "base_intensity": 0.8,
    },
    "sad": {
        "keywords": ["难过", "伤心", "哭", "想哭", "心酸", "心痛", "痛苦", "无奈",
                      "没办法", "就这样吧", "认命", "接受现实", "凉了"],
        "valence": -0.6,
        "base_intensity": 0.7,
    },
}

# 强度修饰词
_INTENSIFIERS = {
    "very_high": ["非常", "特别", "极其", "太", "超级", "贼", "巨", "爆"],
    "high": ["很", "挺", "相当", "真", "确实"],
    "low": ["有点", "稍微", "略微", "一点", "一点点"],
}

# 否定词（翻转情绪极性）
_NEGATION_WORDS = ["不", "没", "没有", "别", "不要", "不会", "不是", "并非"]


class EmotionAnalyzer:
    """情感分析器"""

    def __init__(self, method: str = "keyword", llm=None):
        self.method = method
        self.llm = llm

    async def analyze(self, text: str) -> EmotionResult:
        """分析文本情绪"""
        if not text or not text.strip():
            return EmotionResult("neutral", 0.0, 0.0, 1.0, [])

        if self.method == "llm" and self.llm:
            try:
                return await self._analyze_with_llm(text)
            except Exception as e:
                logger.warning("LLM 情感分析失败，回退到关键词: %s", e)

        return self._analyze_with_keywords(text)

    def _analyze_with_keywords(self, text: str) -> EmotionResult:
        """关键词规则情感分析"""
        scores: Dict[str, float] = {}
        matched_tags: Dict[str, List[str]] = {}

        for emotion, cfg in _EMOTION_KEYWORDS.items():
            hit_count = 0
            hits = []
            for kw in cfg["keywords"]:
                if kw in text:
                    hit_count += 1
                    hits.append(kw)
            if hit_count > 0:
                # 基础分 = 命中数 × 基础强度
                base = cfg["base_intensity"] * min(hit_count / 3, 1.0)

                # 强度修饰
                intensifier = 1.0
                for level, words in _INTENSIFIERS.items():
                    if any(w in text for w in words):
                        if level == "very_high":
                            intensifier = 1.3
                        elif level == "high":
                            intensifier = 1.15
                        elif level == "low":
                            intensifier = 0.7
                        break

                # 否定翻转
                has_negation = any(neg in text for neg in _NEGATION_WORDS)
                if has_negation:
                    intensifier *= 0.5  # 否定减弱情绪

                scores[emotion] = min(base * intensifier, 1.0)
                matched_tags[emotion] = hits

        if not scores:
            return EmotionResult("neutral", 0.1, 0.0, 0.5, [])

        # 选择得分最高的情绪
        best_emotion = max(scores, key=scores.get)
        best_score = scores[best_emotion]

        return EmotionResult(
            label=best_emotion,
            intensity=round(min(best_score, 1.0), 2),
            valence=_EMOTION_KEYWORDS[best_emotion]["valence"],
            confidence=round(min(best_score * 1.2, 1.0), 2),
            raw_tags=matched_tags.get(best_emotion, []),
        )

    async def _analyze_with_llm(self, text: str) -> EmotionResult:
        """LLM 情感分析"""
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            "分析以下文本的情绪，返回 JSON 格式：\n"
            '{"label": "<happy|anxious|disappointed|angry|neutral|sad|excited|confused>", '
            '"intensity": <0.0-1.0>, "valence": <-1.0到1.0>}\n\n'
            f"文本：{text[:200]}"
        )
        resp = await self.llm.ainvoke([
            SystemMessage(content="你是情绪分析专家。只返回 JSON，不要解释。"),
            HumanMessage(content=prompt),
        ])

        import json
        content = str(resp.content).strip()
        # 提取 JSON
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            data = json.loads(content[start:end + 1])
            return EmotionResult(
                label=data.get("label", "neutral"),
                intensity=float(data.get("intensity", 0.5)),
                valence=float(data.get("valence", 0.0)),
                confidence=0.8,
                raw_tags=[],
            )

        return EmotionResult("neutral", 0.3, 0.0, 0.3, [])


def get_emotion_tts_params(emotion: EmotionResult, tts_type: str) -> dict:
    """根据情绪结果返回 TTS 参数

    Args:
        emotion: 情绪分析结果
        tts_type: TTS 供应商类型 (edge/siliconflow/aliyun_stream)

    Returns:
        TTS 参数 dict（voice/speed/pitch/emotion 等）
    """
    params: Dict[str, Any] = {}

    if tts_type == "edge":
        # Edge TTS 不支持情绪参数，仅可通过 rate 微调语速
        if emotion.label in ("excited", "happy"):
            params["rate"] = "+10%"
        elif emotion.label in ("sad", "disappointed"):
            params["rate"] = "-10%"
        elif emotion.label == "anxious":
            params["rate"] = "+5%"
        return params

    if tts_type in ("siliconflow", "aliyun_stream"):
        # CosyVoice 支持 style 参数
        style_map = {
            "happy": "happy",
            "excited": "excited",
            "anxious": "gentle",
            "sad": "sad",
            "angry": "serious",
            "disappointed": "gentle",
            "confused": "gentle",
            "neutral": "neutral",
        }
        params["style"] = style_map.get(emotion.label, "neutral")
        params["style_weight"] = min(emotion.intensity * 1.5, 1.0)
        return params

    return params


# 全局实例（默认关键词分析）
_default_analyzer: Optional[EmotionAnalyzer] = None


def get_emotion_analyzer(method: str = "keyword", llm=None) -> EmotionAnalyzer:
    """获取情感分析器实例"""
    global _default_analyzer
    if _default_analyzer is None or _default_analyzer.method != method:
        _default_analyzer = EmotionAnalyzer(method=method, llm=llm)
    return _default_analyzer
