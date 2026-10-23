"""Very small in-memory per-IP rate limiter for write endpoints.

Not a replacement for a production limiter (e.g. Redis-backed), but enough to
blunt abusive bursts for the MVP. Uses a fixed window per client IP.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from .config import settings

_hits: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    # Respect a reverse proxy if present.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = time.time()
    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_requests
    bucket = _hits[ip]
    # Drop timestamps outside the window.
    cutoff = now - window
    bucket[:] = [t for t in bucket if t > cutoff]
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited"},
        )
    bucket.append(now)
