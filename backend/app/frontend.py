"""Optionally serve the built React frontend from FastAPI (single-domain deploy).

When ``frontend/dist`` exists (i.e. the frontend was built), this module:
  * serves the static assets,
  * serves ``index.html`` for any non-API route so client-side routing and page
    refreshes work on deep links like ``/<story-id>`` and ``/story/<story-id>``,
  * injects Open Graph meta tags for completed-story share links so social
    previews render without running JavaScript.

In local development the frontend is served by Vite instead, so ``dist`` is
absent and these routes are simply not registered.
"""
from __future__ import annotations

import html
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import AsyncSessionLocal
from .models import STATUS_COMPLETED
from .services.story_service import load_story

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _render_index_with_og(index_html: str, title: str, description: str, url: str) -> str:
    og = (
        f'<meta property="og:type" content="website" />'
        f'<meta property="og:title" content="{html.escape(title)}" />'
        f'<meta property="og:description" content="{html.escape(description)}" />'
        f'<meta property="og:url" content="{html.escape(url)}" />'
        f'<meta name="twitter:card" content="summary" />'
        f'<meta name="twitter:title" content="{html.escape(title)}" />'
        f'<meta name="twitter:description" content="{html.escape(description)}" />'
    )
    # Inject right before </head>; fall back to appending.
    if "</head>" in index_html:
        return index_html.replace("</head>", og + "</head>", 1)
    return index_html + og


def register_frontend(app: FastAPI) -> None:
    if not DIST_DIR.exists():
        return

    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_path = DIST_DIR / "index.html"
    base = settings.public_base_url.rstrip("/")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str, request: Request):  # noqa: ANN202
        # Never hijack API or WebSocket paths.
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return HTMLResponse("Not found", status_code=404)

        # Serve a real static file if one matches (e.g. favicon, robots.txt).
        candidate = (DIST_DIR / full_path).resolve()
        if candidate.is_file() and str(candidate).startswith(str(DIST_DIR)):
            return FileResponse(candidate)

        index_html = index_path.read_text(encoding="utf-8")

        # Add OG tags for completed-story share links: /story/<id>
        parts = full_path.strip("/").split("/")
        story_id = None
        if len(parts) == 2 and parts[0] == "story":
            story_id = parts[1]
        if story_id:
            async with AsyncSessionLocal() as db:
                story = await load_story(db, story_id)
            if story and story.status == STATUS_COMPLETED:
                excerpt = " ".join(s.text for s in sorted(story.sentences, key=lambda x: x.position))
                excerpt = (excerpt[:157] + "...") if len(excerpt) > 160 else excerpt
                names = " & ".join(p.display_name for p in story.players)
                title = f"A story by {names} — Add Your Line"
                index_html = _render_index_with_og(
                    index_html, title, excerpt or "Read our collaborative story.", f"{base}/story/{story_id}"
                )

        return HTMLResponse(index_html)
