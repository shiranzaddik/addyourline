"""FastAPI application entrypoint for Add Your Line."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import init_db
from .frontend import register_frontend
from .routers import matchmaking, stories, websocket_router
from .services.story_service import GameError


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Add Your Line API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(GameError)
async def game_error_handler(request: Request, exc: GameError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code})


@app.get("/api/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config", tags=["config"])
async def public_config() -> dict:
    return {
        "allowed_turn_counts": sorted(settings.allowed_turn_count_set),
        "min_turns": settings.min_turns,
        "max_turns": settings.max_turns,
        "max_name_length": settings.max_name_length,
        "max_turn_length": settings.max_turn_length,
        "min_words": settings.min_words,
        "public_base_url": settings.public_base_url,
    }


app.include_router(stories.router)
app.include_router(matchmaking.router)
app.include_router(websocket_router.router)

# Serve the built frontend in production (no-op in dev when dist/ is absent).
register_frontend(app)
