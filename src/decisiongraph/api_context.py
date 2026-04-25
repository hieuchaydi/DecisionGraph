from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from decisiongraph.config import (
    api_token,
    cors_origins,
    rate_limit_per_minute,
    resolve_data_path,
    validate_runtime_configuration,
)
from decisiongraph.service import DecisionGraphService
from decisiongraph.store import DecisionStore


def build_service() -> DecisionGraphService:
    validate_runtime_configuration()
    return DecisionGraphService(DecisionStore(path=resolve_data_path()))


def _is_public_path(path: str) -> bool:
    if path in {"/", "/health"}:
        return True
    return path.startswith("/docs") or path.startswith("/openapi.json") or path.startswith("/redoc")


def configure_cors(app: FastAPI) -> None:
    origins = cors_origins()
    if not origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )


def configure_auth_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        token = api_token()
        if not token or _is_public_path(request.url.path):
            return await call_next(request)

        supplied = request.headers.get("x-api-key", "").strip()
        if supplied != token:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        return await call_next(request)


def configure_rate_limit_middleware(app: FastAPI) -> None:
    limit = rate_limit_per_minute()
    if limit <= 0:
        return

    lock = Lock()
    counters: dict[tuple[str, int], int] = defaultdict(int)

    def _client_id(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").strip()
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
        return request.client.host if request.client else "unknown"

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if _is_public_path(request.url.path):
            return await call_next(request)

        bucket = int(time() // 60)
        client = _client_id(request)
        key = (client, bucket)

        with lock:
            counters[key] += 1
            current = counters[key]
            stale = [k for k in counters if k[1] < bucket - 1]
            for item in stale:
                counters.pop(item, None)

        if current > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests", "limit_per_minute": limit},
            )
        return await call_next(request)
