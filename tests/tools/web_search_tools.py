from __future__ import annotations

import html
import json
import re
from typing import Dict, List
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


class WebSearchTools:
    """
    极简外部搜索工具：
    - 默认走 DuckDuckGo 的 html 结果页（无需 key）
    - 只提取标题与跳转链接（不抓全文），用于“有/无外部信息”的补强
    - 失败时返回空列表，由上游优雅降级
    """

    def __init__(self, user_agent: str | None = None, timeout_seconds: float = 4.0) -> None:
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; ZXAIAdvisor/0.1)"
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        q = (query or "").strip()
        if not q:
            return []

        url = f"https://duckduckgo.com/html/?q={quote_plus(q)}"
        request = Request(url=url, headers={"User-Agent": self.user_agent}, method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
        except (URLError, TimeoutError, ValueError):
            return []

        # 结果页里常见结构：<a class="result__a" href="...">title</a>
        matches = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body)
        items: List[Dict[str, str]] = []
        for href, title_html in matches[: max(top_k, 1)]:
            title = re.sub(r"<.*?>", "", title_html)
            title = html.unescape(title).strip()
            href = html.unescape(href).strip()
            if not title or not href:
                continue
            items.append({"title": title, "url": href})
        return items[:top_k]

    @staticmethod
    def format_results(results: List[Dict[str, str]]) -> str:
        if not results:
            return ""
        lines = []
        for i, item in enumerate(results, start=1):
            lines.append(f"{i}. {item.get('title','').strip()} | {item.get('url','').strip()}")
        return "\n".join(lines).strip()

    @staticmethod
    def to_json(results: List[Dict[str, str]]) -> str:
        return json.dumps(results, ensure_ascii=False, indent=2)

