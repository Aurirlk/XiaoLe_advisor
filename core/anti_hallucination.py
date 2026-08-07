"""
反幻觉与数据引导技能 (Anti-Hallucination Skill)

设计理念：
- 不依赖LLM判断数据充足性，用硬规则检测
- 对每个工具返回结果进行"数据充分性"评分
- 分级处理：致命缺失→阻断+引导 / 部分缺失→警告+建议 / 充足→放行
- 输出标准化的数据引导建议，注入SynthesisAgent

架构位置：
Worker Nodes 返回 tool_result → DataSufficiencyCheck (评分) → SynthesisAgent (注入警告)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
# 数据充分性分级（硬规则，不由LLM判断）
# ═══════════════════════════════════════════════════════════

class DataSufficiencyGrade:
    """数据充分性等级"""
    SUFFICIENT = "sufficient"       # 数据充足，正常回答
    PARTIAL = "partial"              # 数据部分缺失，需标注
    OUTDATED = "outdated"            # 有数据但已过时
    MISSING = "missing"              # 完全查不到
    CONFLICT = "conflict"            # 多条数据矛盾


# ═══════════════════════════════════════════════════════════
# 可靠信息源（按领域分类，优先级从高到低）
# ═══════════════════════════════════════════════════════════

TRUSTED_SOURCES: Dict[str, List[Dict]] = {
    "admission": [
        {"name": "各省教育考试院官网", "url": "各省考试院", "desc": "批次线、投档线、一分一段表", "priority": 1},
        {"name": "阳光高考网", "url": "https://gaokao.chsi.com.cn", "desc": "院校库、专业库、分数线", "priority": 2},
        {"name": "掌上高考", "url": "https://www.gaokao.cn", "desc": "院校对比、专业解读、位次查询", "priority": 3},
    ],
    "employment": [
        {"name": "各校就业质量报告", "url": "院校官网就业栏目", "desc": "官方就业率、薪资、行业去向", "priority": 1},
        {"name": "麦可思研究院", "url": "https://www.mycos.com.cn", "desc": "大学生就业质量年度研究", "priority": 2},
        {"name": "BOSS直聘研究院", "url": "https://www.zhipin.com", "desc": "招聘市场实时薪资数据", "priority": 3},
    ],
    "policy": [
        {"name": "教育部官网", "url": "https://www.moe.gov.cn", "desc": "国家教育政策原文", "priority": 1},
        {"name": "各省教育考试院", "url": "各省考试院官网", "desc": "省招考政策、录取办法", "priority": 2},
        {"name": "阳光高考网政策频道", "url": "https://gaokao.chsi.com.cn/news/zszc.do", "desc": "招生政策汇总", "priority": 3},
    ],
    "ranking": [
        {"name": "软科排名", "url": "https://www.shanghairanking.cn", "desc": "中国大学排名", "priority": 1},
        {"name": "QS排名", "url": "https://www.topuniversities.com", "desc": "世界大学排名", "priority": 2},
        {"name": "US News排名", "url": "https://www.usnews.com", "desc": "美国大学排名", "priority": 3},
    ],
}

# ═══════════════════════════════════════════════════════════
# 数据分级规则（硬编码检测规则）
# ═══════════════════════════════════════════════════════════

# 检测信号：工具返回结果中的"数据不足"关键词
NO_DATA_SIGNALS = [
    "未找到", "不存在", "暂无数据", "查询失败",
    "未收录", "没有找到", "未在数据库中找到",
]

# 检测信号：数据时间过旧
OUTDATED_SIGNALS = {
    "admission": {"max_year": 2022, "current_year": 2024},  # 录取数据超过2年算过时
    "employment": {"max_year": 2023, "current_year": 2024},
    "policy": {"max_year": 2023, "current_year": 2024},
}

# 数据类型 → 信息源类别 映射
TOPIC_TO_SOURCE = {
    "admission": "admission",
    "score": "admission",
    "rank": "admission",
    "cutoff": "admission",
    "employment": "employment",
    "salary": "employment",
    "job": "employment",
    "policy": "policy",
    "reform": "policy",
    "ranking": "ranking",
    "university": "admission",
    "major": "admission",
}


class DataSufficiencyCheck:
    """
    数据充分性检测器（硬约束层，不调用LLM）

    用法：
        check = DataSufficiencyCheck()
        result = check.evaluate(tool_name="query_scores", tool_output="未在数据库中找到匹配数据")
        # → grade=DataSufficiencyGrade.MISSING, sources=[...], guidance="..."
    """

    def __init__(self):
        pass

    # ── 主入口：评估单个工具返回的数据充分性 ──

    def evaluate(self, tool_name: str, tool_output: str, query_context: str = "") -> Dict:
        """
        评估工具返回结果的充分性

        Args:
            tool_name: 工具名称，如 query_admission_scores_tool
            tool_output: 工具返回的文本结果
            query_context: 用户原始查询

        Returns:
            {
                "grade": "sufficient" | "partial" | "outdated" | "missing",
                "topic": "admission" | "employment" | ...,
                "sources": [{"name": ..., "url": ..., "desc": ...}],
                "guidance": "引导话术",
                "should_warn": True/False,
                "should_block": True/False,
                "prompt_injection": "注入SynthesisAgent的警告文本",
            }
        """
        # 1. 检测是否命中"无数据"信号
        is_missing = any(sig in tool_output for sig in NO_DATA_SIGNALS)

        # 2. 检测是否数据过时
        is_outdated = self._check_outdated(tool_name, tool_output, query_context)

        # 3. 确定主题
        topic = self._infer_topic(tool_name, query_context)

        # 4. 获取信息源
        sources = TRUSTED_SOURCES.get(topic, TRUSTED_SOURCES["admission"])

        # 5. 评级
        if is_missing:
            grade = DataSufficiencyGrade.MISSING
        elif is_outdated:
            grade = DataSufficiencyGrade.OUTDATED
        elif len(tool_output.strip()) < 20:
            grade = DataSufficiencyGrade.PARTIAL
        else:
            grade = DataSufficiencyGrade.SUFFICIENT

        # 6. 生成引导话术
        guidance = self._build_guidance(grade, topic, sources)

        # 7. 生成注入 SynthesisAgent 的提示
        prompt_injection = self._build_prompt_injection(grade, topic, sources)

        return {
            "grade": grade,
            "topic": topic,
            "sources": sources[:3],
            "guidance": guidance,
            "should_warn": grade in (DataSufficiencyGrade.PARTIAL, DataSufficiencyGrade.OUTDATED),
            "should_block": grade == DataSufficiencyGrade.MISSING,
            "prompt_injection": prompt_injection,
        }

    # ── 批量评估 ──

    def evaluate_all(self, tool_results: List[Dict], query_context: str = "") -> Dict:
        """
        评估所有工具返回结果，返回汇总评估

        Args:
            tool_results: [{"name": "tool_name", "output": "...", "query": "..."}]
        """
        grades = []
        all_sources = {}
        injections = []

        for tr in tool_results:
            result = self.evaluate(
                tool_name=tr.get("name", ""),
                tool_output=tr.get("output", ""),
                query_context=tr.get("query", query_context),
            )
            grades.append(result["grade"])

            # 收集信息源（去重）
            for s in result["sources"]:
                if s["name"] not in all_sources:
                    all_sources[s["name"]] = s

            if result.get("prompt_injection"):
                injections.append(result["prompt_injection"])

        # 取最严重等级
        severity_order = [DataSufficiencyGrade.MISSING, DataSufficiencyGrade.CONFLICT,
                          DataSufficiencyGrade.OUTDATED, DataSufficiencyGrade.PARTIAL,
                          DataSufficiencyGrade.SUFFICIENT]

        worst_grade = DataSufficiencyGrade.SUFFICIENT
        for g in severity_order:
            if g in grades:
                worst_grade = g
                break

        should_block = DataSufficiencyGrade.MISSING in grades
        should_warn = any(g not in (DataSufficiencyGrade.SUFFICIENT,) for g in grades)

        return {
            "overall_grade": worst_grade,
            "per_tool_grades": grades,
            "should_block": should_block,
            "should_warn": should_warn,
            "sources": list(all_sources.values()),
            "prompt_injections": injections,
            "guidance": self._build_batch_guidance(worst_grade, list(all_sources.values())),
        }

    # ── 私有方法 ──

    def _check_outdated(self, tool_name: str, tool_output: str, query_context: str) -> bool:
        """检查数据是否过时（基于年份关键词）"""
        import re

        # 提取工具输出中的年份
        years = re.findall(r"(19|20)\d{2}(?=\s*年|\s*$|\s*-)", tool_output)
        if not years:
            years = re.findall(r"(19|20)\d{2}(?!\s*月)", tool_output)

        if not years:
            return False

        # 取最大年份
        try:
            latest_year = max(int(y) for y in years if y.isdigit())
        except ValueError:
            # 处理可能的不完整年份匹配
            extracted = []
            for y in years:
                try:
                    extracted.append(int(y))
                except ValueError:
                    pass
            if not extracted:
                return False
            latest_year = max(extracted)

        # 从上下文提取查询的年份
        year_from_context = 2024
        context_years = re.findall(r"(19|20)\d{2}(?=\s*年)", query_context)
        if context_years:
            try:
                year_from_context = int(context_years[0])
            except ValueError:
                pass

        topic = self._infer_topic(tool_name, query_context)
        threshold = OUTDATED_SIGNALS.get(topic, {}).get("max_year", 2022)
        return latest_year < threshold or latest_year < year_from_context - 1

    def _infer_topic(self, tool_name: str, query_context: str) -> str:
        """根据工具名称和查询内容推断数据类型"""
        tool_topic_map = {
            "query_admission_scores_tool": "admission",
            "query_major_admission_tool": "admission",
            "search_experience_tool": "employment",
            "query_policy_tool": "policy",
            "query_news_tool": "employment",
            "query_major_info_tool": "admission",
            "query_university_info_tool": "admission",
            "query_city_info_tool": "admission",
        }

        if tool_name in tool_topic_map:
            return tool_topic_map[tool_name]

        # 从查询中推断
        for keyword, topic in TOPIC_TO_SOURCE.items():
            if keyword in query_context:
                return topic

        return "admission"

    def _build_guidance(self, grade: str, topic: str, sources: List[Dict]) -> str:
        """生成用户可见的引导话术"""
        if grade == DataSufficiencyGrade.SUFFICIENT:
            return ""

        source_list = "\n".join(
            f"  {s['priority']}. {s['name']}: {s['desc']}（{s['url']}）"
            for s in sorted(sources, key=lambda x: x.get("priority", 99))[:3]
        )

        if grade == DataSufficiencyGrade.MISSING:
            return (
                f"系统目前没有这方面的数据。建议通过以下官方渠道查询：\n"
                f"{source_list}\n\n"
                f"如果你手头有相关数据（截图/PDF/Excel），可以上传给我们，系统会自动解析入库。"
            )

        if grade == DataSufficiencyGrade.OUTDATED:
            return (
                f"以下分析基于系统现有数据，可能不是最新版本。\n"
                f"建议通过以下渠道核实最新数据：\n"
                f"{source_list}"
            )

        return (
            f"部分数据可能不完整，建议参考以下渠道：\n"
            f"{source_list}"
        )

    def _build_prompt_injection(self, grade: str, topic: str, sources: List[Dict]) -> str:
        """
        生成注入 SynthesisAgent 的提示文本

        这段文字会被插入到系统提示词中，告诉LLM如何处理当前情况
        """
        if grade == DataSufficiencyGrade.SUFFICIENT:
            return ""

        source_text = "、".join(s["name"] for s in sorted(sources, key=lambda x: x.get("priority", 99))[:2])

        injections = {
            DataSufficiencyGrade.MISSING: (
                "[硬约束: 数据缺失] 你查询的数据在系统中完全没有。"
                "不要猜测或编造任何数字、排名、分数线。"
                "必须在回复开头明确说明'系统没有这个数据'，然后引导用户去{source_text}查询。"
                "鼓励用户找到数据后上传到系统。"
            ).format(source_text=source_text),

            DataSufficiencyGrade.OUTDATED: (
                "[硬约束: 数据过时] 系统有相关数据但可能已过时。"
                "可以引用数据做参考分析，但必须在回复中明确标注'以上数据基于20XX年，最新情况请查询{source_text}'。"
                "不要用过时数据做确定性结论。"
            ).format(source_text=source_text),

            DataSufficiencyGrade.PARTIAL: (
                "[硬约束: 数据不完整] 系统只有部分数据。"
                "可以引用已有数据，但必须标注'以下分析基于部分数据，完整信息请查询{source_text}'。"
            ).format(source_text=source_text),
        }

        return injections.get(grade, "")

    def _build_batch_guidance(self, grade: str, sources: List[Dict]) -> str:
        """生成批量评估的汇总引导话术"""
        if grade == DataSufficiencyGrade.SUFFICIENT:
            return ""

        unique_sources = {s["name"]: s for s in sources}
        source_list = "\n".join(
            f"  {s['priority']}. {s['name']}: {s['desc']}（{s['url']}）"
            for s in sorted(unique_sources.values(), key=lambda x: x.get("priority", 99))[:5]
        )

        if grade == DataSufficiencyGrade.MISSING:
            return (
                f"系统在多个维度上缺少数据，无法给出准确分析。\n\n"
                f"建议通过以下官方渠道查询：\n{source_list}\n\n"
                f"如果你手头有相关数据，可以上传给我们，系统会自动解析入库。"
            )

        return (
            f"部分分析基于系统现有数据，可能不够完整或最新。\n"
            f"建议参考以下渠道核实：\n{source_list}"
        )


# ═══════════════════════════════════════════════════════════
# SynthesisAgent 系统提示词注入
# ═══════════════════════════════════════════════════════════

ANTI_HALLUCINATION_PROMPT = """
## 反幻觉约束 (Anti-Hallucination Rules)

当你在回答用户问题时，必须遵守以下规则：

1. **数据边界**：只能基于 delivered 的 tool results 和 known data 回答问题。凡是没有数据支撑的结论，必须说"系统没有这个数据"，严禁编造。

2. **过时标注**：如果引用的数据年份比当前晚2年以上，必须在回复中标注："数据年份为20XX年，最新情况可能有变化"。

3. **数据引导**：当工具返回"未找到"或数据明显缺失时，不要继续尝试推理。转而告诉用户可以：
   - 访问官方渠道查询（阳光高考网、省教育考试院等，具体URL会由工具提供）
   - 用搜索引擎搜索相关关键词
   - 将找到的数据上传到系统（截图、PDF、Excel都支持）

4. **分级响应**：
   - 数据完全缺失 → 明确告知无法分析，提供查询渠道
   - 数据部分缺失 → 标注"以下分析基于部分数据"，可以给出参考意见
   - 数据过时 → 标注"数据为X年前"，可以给出趋势分析

5. **禁止行为**：
   - 禁止说"据我所知"、"根据经验"、"通常来说"来绕过数据不足
   - 禁止用通用建议代替具体数据（如"一般来说计算机专业就业不错"）
   - 禁止在不同工具都返回空结果时仍然输出"建议报考"
"""


class AntiHallucinationSkill:
    """
    反幻觉技能的完整包装

    在 GraphBuilder 中注册为中间节点，
    在 SynthesisAgent 之前对所有 tool results 进行充分性检查。
    """

    def __init__(self):
        self._checker = DataSufficiencyCheck()

    def check(self, tool_results: List[Dict], user_query: str) -> Dict:
        """
        对外接口：检查所有工具返回的数据充分性

        Args:
            tool_results: [{"name": "tool_name", "output": "...", "query": "..."}]
            user_query: 用户原始查询

        Returns:
            评估结果 + 应注入的提示词 + 用户可见引导
        """
        return self._checker.evaluate_all(tool_results, user_query)

    def inject_to_prompt(self, base_prompt: str, check_result: Dict) -> str:
        """
        将反幻觉约束注入到系统提示词中

        Args:
            base_prompt: 原始系统提示词
            check_result: check() 的返回结果

        Returns:
            注入后的提示词
        """
        injection = check_result.get("prompt_injections", [])
        if not injection:
            return base_prompt

        injection_text = "\n\n".join(injection)
        return f"{base_prompt}\n\n{ANTI_HALLUCINATION_PROMPT}\n\n{injection_text}"
