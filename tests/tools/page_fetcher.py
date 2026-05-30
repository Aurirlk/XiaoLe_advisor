from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
import trafilatura


@dataclass
class PageFetchResult:
    status: str  # ok | timeout | blocked | empty | error
    text: str = ""
    chars: int = 0
    error: str = ""


_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
)


def _is_blocked_host(hostname: str) -> bool:
    if not hostname:
        return True
    host = hostname.strip().lower()
    if host in ("localhost", "0.0.0.0"):
        return True
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        pass
    if re.match(r"^127\.", host) or re.match(r"^10\.", host):
        return True
    return False


def is_safe_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        return False
    if _is_blocked_host(parsed.hostname or ""):
        return False
    return bool(parsed.netloc)


class PageFetcher:
    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (compatible; ZXAIAdvisor/1.0)",
        timeout_seconds: float = 8.0,
        max_content_bytes: int = 512_000,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_content_bytes = max_content_bytes

    async def fetch_page(self, url: str) -> PageFetchResult:
        if not is_safe_url(url):
            return PageFetchResult(status="blocked", error="URL not allowed")

        headers = {"User-Agent": self.user_agent}
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout_seconds,
            ) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code >= 400:
                    return PageFetchResult(
                        status="error",
                        error=f"HTTP {resp.status_code}",
                    )
                raw = resp.content[: self.max_content_bytes]
                html = raw.decode(resp.encoding or "utf-8", errors="ignore")
        except httpx.TimeoutException:
            return PageFetchResult(status="timeout", error="request timeout")
        except Exception as exc:
            return PageFetchResult(status="error", error=str(exc)[:200])

        text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return PageFetchResult(status="empty", error="no extractable text")

        return PageFetchResult(status="ok", text=text, chars=len(text))
