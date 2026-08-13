import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request

from app.core.errors import AppError


class InMemoryRateLimiter:
    """Per-process abuse protection; production proxies should add a shared outer limit."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        async with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= now - window_seconds:
                attempts.popleft()
            if len(attempts) >= limit:
                raise AppError("RATE_LIMITED", "Too many requests. Try again later.", 429)
            attempts.append(now)


limiter = InMemoryRateLimiter()


def sensitive_limit(
    name: str, limit: int, window_seconds: int
) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        await limiter.check(f"{name}:{client}", limit, window_seconds)

    return dependency
