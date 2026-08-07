"""
web_search_agent — 混合搜索机制
1. embedding 语义分类 → 识别搜索平台（知乎/微博/贴吧/小红书/全网）
2. LLM 提取搜索关键词 → 去掉语气词，保留实体
3. 组装搜索 query → 调搜索引擎 → 返回结果
"""
from __future__ import annotations
import asyncio
import math
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

from core.state_schema import GraphState

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # LLM 关键词提取降级为规则

if TYPE_CHECKING:
    from core.web_search_service import WebSearchService
    from tools.web_search_tools import WebSearchTools

# ======== 平台模板 ========
SEARCH_TEMPLATES = [
    {"name": "知乎",   "site": "",                              "desc": "知乎搜索",     "prompt_hint": "知乎"},
    {"name": "微博",   "site": "site:weibo.com",                "desc": "微博搜索",     "prompt_hint": "微博"},
    {"name": "贴吧",   "site": "site:tieba.baidu.com",          "desc": "贴吧搜索",     "prompt_hint": "贴吧"},
    {"name": "小红书", "site": "site:xiaohongshu.com",          "desc": "小红书搜索",    "prompt_hint": "小红书"},
    {"name": "全网",   "site": "",                              "desc": "通用搜索",     "prompt_hint": "全网搜索"},
]

TEMPLATE_TEXTS = [
    "在知乎上搜索关于这个话题的内容",
    "在微博上搜一下大家对这件事的看法",
    "贴吧里有人讨论这个吗",
    "小红书上有相关的信息吗",
    "上网查一下这个信息",
]

KEYWORD_EXTRACT_PROMPT = """你是一个搜索关键词提取器。从用户的问题中提取 2-5 个核心搜索关键词。

规则：
- 只返回关键词，用空格分隔，不要任何解释
- 去掉语气词、问候语、连接词
- 如果是问"XX 怎么样/评价/如何"→提取核心名词
- 如果用户指定了平台（知乎/微博/贴吧/小红书），不要包含平台名

示例：
用户：帮我搜一下清华大学的计算机专业怎么样
关键词：清华大学 计算机专业

用户：大家觉得张雪峰老师推荐的计算机专业到底好不好
关键词：张雪峰 计算机专业

用户：微博上对人工智能就业前景的评价
关键词：人工智能 就业前景

用户：{query}
关键词："""


@lru_cache(maxsize=1)
def _build_embedding_model():
    """懒加载 embedding 模型（进程级单例——每次请求重新构造会阻塞事件循环并重复加载 ~420MB 模型）"""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    return model


@lru_cache(maxsize=1)
def _template_embeddings():
    """平台模板向量只需计算一次"""
    model = _build_embedding_model()
    return model.encode(TEMPLATE_TEXTS)


def _cosine_sim(a: list, b: list) -> float:
    """纯 Python 余弦相似度，无 numpy 依赖"""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-10)


def _classify_platform(query: str, model) -> tuple:
    """embedding 语义分类 → 返回 (最佳平台, 置信度)

    注意：这是 CPU 密集的同步函数，async 上下文中必须经 asyncio.to_thread 调用。
    """
    query_emb = model.encode([query])[0].tolist()
    template_embs = _template_embeddings()

    best_idx = 0
    best_score = -1.0
    for i, t in enumerate(template_embs):
        score = _cosine_sim(query_emb, t.tolist())
        if score > best_score:
            best_score = score
            best_idx = i

    return SEARCH_TEMPLATES[best_idx], round(best_score, 4)


async def _extract_keywords_llm(query: str, llm: Optional[ChatOpenAI] = None) -> str:
    """LLM 提取搜索关键词（async——在事件循环中禁止同步 invoke）"""
    if llm is None:
        # 无可用的 LLM 时，简单规则兜底
        import re
        cleaned = re.sub(r'帮我|搜一下|搜索|大家觉得|怎么样|如何|评价|关于|的|了|吗|呢|啊|哈|吧', '', query)
        return cleaned.strip()[:100]

    from langchain_core.messages import HumanMessage, SystemMessage
    try:
        resp = await llm.ainvoke([
            SystemMessage(content=KEYWORD_EXTRACT_PROMPT.format(query=query)),
            HumanMessage(content=query),
        ])
        keywords = resp.content.strip()
        return keywords if keywords else query[:100]
    except Exception:
        return query[:80]


def build_web_search_agent(
    web_search_service: "WebSearchService | None" = None,
    web_search: "WebSearchTools | None" = None,
    llm: Optional[ChatOpenAI] = None,
):
    async def web_search_agent(state: GraphState) -> GraphState:
        raw_query = state.get("user_query", "")
        session_id = state.get("session_id", "") or ""

        # ====== Step 1: embedding 平台分类（CPU 密集，丢线程池避免阻塞事件循环） ======
        platform = SEARCH_TEMPLATES[-1]  # 默认全网
        confidence = 0.0
        try:
            platform, confidence = await asyncio.to_thread(
                lambda: _classify_platform(raw_query, _build_embedding_model())
            )
        except Exception:
            pass

        # ====== Step 2: LLM 提取搜索关键词 ======
        keywords = await _extract_keywords_llm(raw_query, llm)

        # ====== Step 3: 组装搜索 query ======
        # 高置信度 → 加 site 限定；低置信度 → 不加 site，让搜索引擎自己处理
        if confidence > 0.3 and platform["site"]:
            search_query = f"{keywords} {platform['site']}"
            source_note = f"（平台：{platform['name']}，置信度：{confidence:.2f}）"
        else:
            search_query = keywords
            source_note = "（全网搜索）"

        # LangGraph 节点必须通过返回值提交 delta，禁止原地修改 state
        # （原地写入不会被 checkpointer 持久化，下游读不到）
        trace = {
            "web_search_platform": platform["name"],
            "web_search_keywords": keywords,
            "web_search_confidence": confidence,
        }

        # ====== Step 4: 执行搜索 ======
        if web_search_service is not None:
            bundle = await web_search_service.search_fetch_and_persist(
                search_query,
                chat_session_id=session_id,
            )
            formatted = bundle.formatted_text
            if not formatted:
                formatted = (
                    "【系统提示：外部搜索无结果/失败（可能网络不可用或超时），"
                    "请基于本地数据与经验回答】"
                )
            return {
                **trace,
                "web_search_results": formatted,
                "web_search_pages": bundle.pages,
                "next_node": "synthesis_agent",
            }
        else:
            from tools.web_search_tools import WebSearchTools
            tools = web_search or WebSearchTools()
            results = await tools.search(query=search_query, top_k=5)
            formatted = tools.format_results(results)
            if not formatted:
                formatted = (
                    "【系统提示：外部搜索无结果/失败（可能网络不可用或超时），"
                    "请基于本地数据与经验回答】"
                )
            return {
                **trace,
                "web_search_results": f"{source_note}\n{formatted}",
                "next_node": "synthesis_agent",
            }

    return web_search_agent
