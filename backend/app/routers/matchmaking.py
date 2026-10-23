"""Explicit matchmaking endpoint (alias of creating a story in random mode)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..ratelimit import rate_limit
from ..schemas import JoinResponse, MatchmakingRequest, PlayerPublic
from ..services import matchmaking
from ..services.story_service import serialize_story
from ..websocket import events

router = APIRouter(prefix="/api/matchmaking", tags=["matchmaking"])


@router.post("", response_model=JoinResponse, dependencies=[Depends(rate_limit)])
async def join_random(req: MatchmakingRequest, db: AsyncSession = Depends(get_db)) -> JoinResponse:
    story, player, token, matched = await matchmaking.request_match(
        db, req.display_name, req.language
    )
    if matched:
        await events.broadcast_state(story, events.GAME_STARTED)
    return JoinResponse(
        token=token,
        player=PlayerPublic(
            id=player.id, display_name=player.display_name, player_number=player.player_number
        ),
        story=serialize_story(story),
    )
