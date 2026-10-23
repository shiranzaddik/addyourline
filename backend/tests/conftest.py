"""Pytest fixtures: isolated temp-file SQLite database per test session."""
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

# Configure environment BEFORE importing the app (settings are cached).
_tmp_db = Path(tempfile.gettempdir()) / "addyourline_test.db"
if _tmp_db.exists():
    _tmp_db.unlink()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp_db.as_posix()}"
os.environ["PUBLIC_BASE_URL"] = "https://addyourline.com"
os.environ["RATE_LIMIT_REQUESTS"] = "1000"
os.environ["ALLOWED_TURN_COUNTS"] = "2,10,20,30"  # allow short games in tests

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    # Fresh schema for each test.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
