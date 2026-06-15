"""
供应商基础抽象层：熔断器 + 指数退避重试 + BaseProvider
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    """熔断器打开时抛出的异常"""
    pass


class _State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """三态熔断器

    CLOSED  → 连续失败 >= failure_threshold → OPEN
    OPEN    → recovery_timeout 秒后 → HALF_OPEN
    HALF_OPEN → 放行 1 个请求：
        成功 → CLOSED
        失败 → OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "",
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = _State.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._success_count = 0

    @property
    def state(self) -> str:
        if self._state == _State.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = _State.HALF_OPEN
        return self._state.value

    def allow_request(self) -> bool:
        s = self.state
        if s == "closed":
            return True
        if s == "half_open":
            return True
        return False

    def record_success(self) -> None:
        if self._state == _State.HALF_OPEN:
            logger.info("[%s] 熔断器半开→关闭（恢复）", self.name)
        self._failure_count = 0
        self._state = _State.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            if self._state != _State.OPEN:
                logger.warning(
                    "[%s] 熔断器关闭→打开（连续失败 %d 次）",
                    self.name, self._failure_count,
                )
            self._state = _State.OPEN

    def reset(self) -> None:
        self._failure_count = 0
        self._state = _State.CLOSED


class RetryMixin:
    """指数退避重试混入

    delay = min(base_delay * 2^attempt + random_jitter, max_delay)
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0

    async def retry_with_backoff(
        self,
        fn: Callable,
        *args: Any,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> Any:
        retries = max_retries if max_retries is not None else self.max_retries
        last_exc: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                if asyncio.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    delay = min(
                        self.base_delay * (2 ** attempt) + random.uniform(0, 0.5),
                        self.max_delay,
                    )
                    logger.warning(
                        "[%s] 第 %d 次重试，%.1f 秒后: %s",
                        getattr(self, "name", "?"), attempt + 1, delay, exc,
                    )
                    await asyncio.sleep(delay)

        raise last_exc  # type: ignore[misc]


class BaseProvider(ABC, RetryMixin):
    """供应商基类：所有 ASR/LLM/TTS 供应商的父类"""

    name: str = ""
    provider_type: str = ""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        threshold = config.get("failure_threshold", 5)
        recovery = config.get("recovery_timeout", 60.0)
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=threshold,
            recovery_timeout=recovery,
            name=self.name,
        )
        self.max_retries = config.get("max_retries", 3)
        self.base_delay = config.get("base_delay", 1.0)
        self.max_delay = config.get("max_delay", 30.0)

    async def execute_with_resilience(
        self,
        fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """统一入口：熔断检查 → 重试 → 记录成功/失败"""
        cb = self._circuit_breaker
        if not cb.allow_request():
            raise CircuitBreakerOpen(
                f"供应商 {self.name} 已熔断，请等待 {cb.recovery_timeout} 秒后重试"
            )
        try:
            result = await self.retry_with_backoff(fn, *args, **kwargs)
            cb.record_success()
            return result
        except Exception:
            cb.record_failure()
            raise

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "type": self.provider_type,
            "circuit_state": self._circuit_breaker.state,
            "failure_count": self._circuit_breaker._failure_count,
        }
