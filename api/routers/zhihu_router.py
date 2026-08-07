"""知乎搜索 API 代理路由（自 backend/app/routers 迁移，P1-20）

修复：ACCESS_SECRET 硬编码 → ZHIHU_ACCESS_SECRET 环境变量（P0-1 同类密钥问题）。
"""
from __future__ import annotations

import json
import os
import re

import httpx
from fastapi import APIRouter, Query

from api.crud_services import get_system_config  # noqa: F401  (兼容旧 import 形态)
from api.response import fail, ok

router = APIRouter(prefix="/api/zhihu", tags=["zhihu"])

SSE_URL = "https://developer.zhihu.com/api/mcp/zhihu_search/v1/sse"


def _get_headers() -> dict:
    secret = os.getenv("ZHIHU_ACCESS_SECRET", "").strip()
    if not secret:
        raise RuntimeError("ZHIHU_ACCESS_SECRET 环境变量未配置")
    return {
        "Authorization": f"Bearer {secret}",
        "Accept": "text/event-stream",
    }


def _parse_xml_items(text: str) -> list:
    """从 MCP 返回的 XML 中提取搜索结果"""
    items = []
    for item_block in text.split("</search_item>"):
        if "<search_item " not in item_block:
            continue
        title = ""
        url = ""
        author = ""
        for attr_match in re.finditer(r'(\w+)="([^"]*)"', item_block):
            key, val = attr_match.groups()
            if key == "title":
                title = val
            elif key == "url":
                url = val
            elif key == "author_name":
                author = val
        text_start = item_block.rfind(">")
        summary = item_block[text_start + 1:].strip() if text_start >= 0 else ""
        items.append({
            "title": title or summary[:60],
            "url": url,
            "author": author,
            "summary": summary[:300],
        })
    return items


@router.get("/search")
async def search_zhihu(
    query: str = Query(..., min_length=2, max_length=100),
    count: int = Query(8, ge=1, le=10),
):
    """代理知乎搜索 - 用户自主搜索，结果自行判断"""
    try:
        headers = _get_headers()
    except RuntimeError as e:
        return fail(message=str(e))

    mcp_result = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            # 1. SSE → 获取 session
            async with client.stream("GET", SSE_URL, headers=headers) as sse:
                message_url = None
                async for line in sse.aiter_lines():
                    if line.startswith("data: "):
                        message_url = line[6:].strip()
                        break
            if not message_url:
                return fail(message="无法获取知乎搜索会话")

            full_url = f"https://developer.zhihu.com{message_url}"

            # 2. initialize
            await client.post(full_url, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "xiaole-ai", "version": "1.0"},
                    "capabilities": {},
                },
            }, headers=headers)

            # 3. tools/call
            await client.post(full_url, json={
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "zhihu_search", "arguments": {"query": query, "count": count}},
            }, headers=headers)

            # 4. SSE 等待结果
            async with client.stream("GET", SSE_URL, headers=headers) as sse:
                async for line in sse.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "result" in data:
                                mcp_result = data["result"]
                                break
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        return fail(message=f"知乎搜索异常: {str(e)}")

    if not mcp_result:
        return fail(message="知乎搜索无返回结果")

    text = mcp_result.get("content", [{}])[0].get("text", "")
    items = _parse_xml_items(text)
    return ok(data={"items": items, "total": len(items)})
