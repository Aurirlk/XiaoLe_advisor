# -*- coding: utf-8 -*-
"""
蓝图 Phase 3.1/3.2 集成测试：Agent 通信总线 + 自我反思质量门接入 worker

覆盖：
1. bus 请求-响应：career_agent 向 match.admission 订阅者请求录取数据并并入上下文
2. bus 发布：match_agent 完成后 publish match.completed 事件
3. reflexion 质量门：match/career 输出写 reflexion_report（satisfied/issues/suggestions）
4. reflexion regenerate：career 空 RAG 时触发全库兜底重查（追加而非覆盖）
5. build_graph 开关组合编译（enable_agent_bus / enable_reflexion）

注：本测试用 mock（零 LLM、零 DB），pytest 收集阶段避免加载
sentence_transformers/chromadb 原生库（zxf 环境 segfault 规避）。
"""
import asyncio

import pytest


# ── mocks ─────────────────────────────────────────────────────

class _MockResult:
    tier = "ok"
    data = [{"university_name": "中山大学", "min_score": 630},
            {"university_name": "华南理工", "min_score": 620}]
    is_degraded = False
    diagnostics = []
    suggestions = []


class _MockSQLTools:
    async def query_scores(self, args):
        return _MockResult()


class _MockRAGTools:
    async def query_zx_experience_async(self, query, top_k=3, kb_scope=None):
        return "【经验库】医学就业：三甲医院就业率85%，薪资中位数1.2万"


class _EmptyRAGTools:
    async def query_zx_experience_async(self, query, top_k=3, kb_scope=None):
        return ""  # 空结果 → 触发 reflexion regenerate


_STATE = {
    "user_query": "临床医学在广东能上什么学校",
    "user_profile": {"province": "广东省", "subject_type": "物理类",
                     "major_name": "临床医学", "score": 600},
    "extracted_score": 600,
}


# ── 测试 ─────────────────────────────────────────────────────

class TestBusRequestReply:
    """career_agent 通过总线向 match 订阅者请求录取数据"""

    def test_career_merges_bus_admission(self):
        from core.agent_bus import AgentCommunicationBus
        from agents.workers.career_agent import build_career_agent

        bus = AgentCommunicationBus()
        sql_tools = _MockSQLTools()

        async def admission_handler(msg):
            payload = msg.payload or {}
            if not payload.get("major_name"):
                return None
            r = await sql_tools.query_scores(None)
            return {"universities": [x["university_name"] for x in r.data][:5]}

        bus.subscribe("match.admission", admission_handler)
        career_agent = build_career_agent(_MockRAGTools(), bus=bus, reflexion=None)

        async def _run():
            out = await career_agent(dict(_STATE))
            return out

        out = asyncio.run(_run())
        ctx = out.get("career_context", "")
        assert "可冲院校参考（Agent 总线协作）" in ctx, "bus 协作数据应并入 career_context"
        assert "中山大学" in ctx, "订阅者应答的院校应出现在上下文中"
        assert bus.get_stats()["requests"] == 1, "应记录一次 request"
        assert bus.get_stats()["replies"] == 1, "应收到一次 reply"

    def test_bus_unavailable_degrades_gracefully(self):
        """bus=None 时 career_agent 保持原行为（不报错）"""
        from agents.workers.career_agent import build_career_agent

        career_agent = build_career_agent(_MockRAGTools(), bus=None, reflexion=None)

        async def _run():
            out = await career_agent(dict(_STATE))
            return out

        out = asyncio.run(_run())
        assert "经验库" in out.get("career_context", "")
        assert "可冲院校参考" not in out.get("career_context", "")


class TestBusPublish:
    """match_agent 完成后发布 match.completed 事件"""

    def test_match_publishes_event(self):
        from core.agent_bus import AgentCommunicationBus
        from agents.workers.match_agent import build_match_agent

        bus = AgentCommunicationBus()
        received = []

        async def subscriber(msg):
            received.append(msg.payload)

        bus.subscribe("match.completed", subscriber)
        match_agent = build_match_agent(_MockSQLTools(), bus=bus, reflexion=None)

        async def _run():
            return await match_agent(dict(_STATE))

        out = asyncio.run(_run())
        assert out.get("sql_results"), "match 应返回院校结果"
        assert len(received) == 1, "应收到一次 match.completed 事件"
        assert received[0]["major_name"] == "临床医学"
        assert bus.get_stats()["published"] == 1


class TestReflexionGate:
    """reflexion 质量门：match/career 输出写 reflexion_report"""

    def test_match_writes_reflexion_report(self):
        from agents.workers.match_agent import build_match_agent
        from core.reflexion_agent import ReflexionAgent

        reflexion = ReflexionAgent(max_reflections=1)
        match_agent = build_match_agent(_MockSQLTools(), bus=None, reflexion=reflexion)

        async def _run():
            return await match_agent(dict(_STATE))

        out = asyncio.run(_run())
        report = out.get("reflexion_report", {})
        assert report.get("node") == "match_agent"
        assert "satisfied" in report and "issues" in report
        assert isinstance(report.get("suggestions"), list)

    def test_career_empty_rag_triggers_regenerate(self):
        """career RAG 空 → reflexion 触发 regenerate 全库重查，且不覆盖已有数据"""
        from agents.workers.career_agent import build_career_agent
        from core.reflexion_agent import ReflexionAgent

        class _FallbackRAG(_EmptyRAGTools):
            async def query_zx_experience_async(self, query, top_k=3, kb_scope=None):
                # 全库兜底（kb_scope=None）返回内容；分权查询（有 scope）返回空
                if kb_scope is None:
                    return "【全库兜底】医学就业：三甲医院就业率85%，薪资中位数1.2万"
                return ""

        reflexion = ReflexionAgent(max_reflections=1)
        career_agent = build_career_agent(_FallbackRAG(), bus=None, reflexion=reflexion)

        async def _run():
            return await career_agent(dict(_STATE))

        out = asyncio.run(_run())
        report = out.get("reflexion_report", {})
        assert report.get("node") == "career_agent"
        assert report.get("reflections", 0) >= 1, "空 RAG 应触发反思重试"
        assert "全库兜底" in out.get("career_context", ""), "反思补充内容应并入上下文"


class TestGraphCompile:
    """build_graph 开关组合编译（不依赖 DB/LLM 实际调用）"""

    @pytest.mark.parametrize("kwargs,expect_nodes", [
        (dict(), 15),
        (dict(enable_agent_bus=True, enable_reflexion=True), 15),
        (dict(enable_write_agent=True), 16),
        (dict(enable_result_fusion=True, enable_write_agent=True), 17),
        (dict(enable_result_fusion=True, enable_write_agent=True,
              enable_agent_bus=True, enable_reflexion=True), 17),
    ])
    def test_combos_compile(self, kwargs, expect_nodes):
        from langchain_openai import ChatOpenAI
        from core.graph_builder import build_graph

        class _MockEngine:
            async def connect(self):
                raise RuntimeError("not used")

        llm = ChatOpenAI(model="deepseek-v4-flash", api_key="sk-test", streaming=True)
        g = build_graph(_MockEngine(), llm, checkpointer=None, **kwargs)
        assert len(list(g.get_graph().nodes.keys())) == expect_nodes
