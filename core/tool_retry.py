"""
统一工具重试、模糊降级与诊断框架

解决 sql_tools / rag_tools 中"查不到就抛错"的粗粒度问题。
提供:
- with_retry: 指数退避重试
- with_degradation: 多策略降级链
- ToolResult: 结构化返回值（含状态等级/诊断/建议）
"""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional


ResultTier = Literal["exact", "fuzzy", "degraded", "empty", "error"]


@dataclass
class ToolResult:
    """统一工具返回值，携带结果等级与诊断信息"""
    tier: ResultTier
    data: Any
    diagnostics: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.tier not in ("empty", "error")

    @property
    def is_degraded(self) -> bool:
        return self.tier in ("fuzzy", "degraded")

    @classmethod
    def exact(cls, data: Any) -> "ToolResult":
        return cls(tier="exact", data=data)

    @classmethod
    def fuzzy(cls, data: Any, diag: str = "") -> "ToolResult":
        diags = [diag] if diag else []
        return cls(tier="fuzzy", data=data, diagnostics=diags)

    @classmethod
    def degraded(cls, data: Any, diag: str = "", suggestions: List[str] | None = None) -> "ToolResult":
        diags = [diag] if diag else []
        sug = suggestions or []
        return cls(tier="degraded", data=data, diagnostics=diags, suggestions=sug)

    @classmethod
    def empty(cls, diag: str = "", suggestions: List[str] | None = None) -> "ToolResult":
        return cls(tier="empty", data=[], diagnostics=[diag] if diag else [], suggestions=suggestions or [])

    @classmethod
    def error(cls, error_msg: str) -> "ToolResult":
        return cls(tier="error", data=[], diagnostics=[error_msg])

    def merge_diagnostics(self, other: "ToolResult") -> "ToolResult":
        """合并两个结果的诊断信息（降级链叠加）"""
        self.diagnostics.extend(other.diagnostics)
        self.suggestions.extend(other.suggestions)
        return self


async def with_retry(
    fn: Callable,
    *args: Any,
    max_retries: int = 2,
    base_delay: float = 0.5,
    **kwargs: Any,
) -> tuple[Any, int, Optional[Exception]]:
    """带指数退避的异步重试"""
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result, attempt, None
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
    return None, max_retries, last_exc


# 省名标准化映射
PROVINCE_ALIASES: Dict[str, str] = {
    "广东": "广东省", "粤": "广东省",
    "河北": "河北省", "冀": "河北省",
    "河南": "河南省", "豫": "河南省",
    "山东": "山东省", "鲁": "山东省",
    "江苏": "江苏省", "苏": "江苏省",
    "浙江": "浙江省", "浙": "浙江省",
    "四川": "四川省", "川": "四川省",
    "湖北": "湖北省", "鄂": "湖北省",
    "湖南": "湖南省", "湘": "湖南省",
    "福建": "福建省", "闽": "福建省",
    "安徽": "安徽省", "皖": "安徽省",
    "江西": "江西省", "赣": "江西省",
    "辽宁": "辽宁省", "辽": "辽宁省",
    "吉林": "吉林省", "吉": "吉林省",
    "黑龙江": "黑龙江省", "黑": "黑龙江省",
    "陕西": "陕西省", "陕": "陕西省",
    "山西": "山西省", "晋": "山西省",
    "甘肃": "甘肃省", "甘": "甘肃省",
    "云南": "云南省", "滇": "云南省",
    "贵州": "贵州省", "黔": "贵州省",
    "海南": "海南省", "琼": "海南省",
    "青海": "青海省", "青": "青海省",
    "台湾": "台湾省", "台": "台湾省",
    "广西": "广西壮族自治区", "桂": "广西壮族自治区",
    "内蒙古": "内蒙古自治区",
    "西藏": "西藏自治区", "藏": "西藏自治区",
    "新疆": "新疆维吾尔自治区", "新": "新疆维吾尔自治区",
    "宁夏": "宁夏回族自治区", "宁": "宁夏回族自治区",
    "北京": "北京市", "京": "北京市",
    "上海": "上海市", "沪": "上海市",
    "天津": "天津市", "津": "天津市",
    "重庆": "重庆市", "渝": "重庆市",
}


def normalize_province(raw: str) -> str:
    """省名标准化：简称→全称，带'省'→不带'省'都归一化"""
    raw = raw.strip()
    if raw in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[raw]
    if raw.endswith("省") or raw.endswith("市") or raw.endswith("区"):
        return raw
    if raw + "省" in PROVINCE_ALIASES.values():
        return raw + "省"
    return raw


def normalize_subject(raw: str) -> str:
    """选科标准化"""
    raw = raw.strip()
    if "物理" in raw:
        return "物理类"
    if "历史" in raw:
        return "历史类"
    return raw
