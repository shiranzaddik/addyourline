"""REST endpoints for stories: create, join, get state, submit turn, cancel."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import MODE_FRIEND, STATUS_WAITING
from ..ratelimit import rate_limit
from ..schemas import (
    CancelMatchmakingRequest,
    CreateStoryRequest,
    JoinResponse,
    JoinStoryRequest,
    PlayerPublic,
    StoryStateResponse,
    SubmitTurnRequest,
    UpdateSettingsRequest,
)
from ..services import matchmaking
from ..services.story_service import (
    GameError,
    create_friend_story,
    find_player_by_token,
    join_story,
    load_story,
    serialize_story,
    submit_turn,
    update_turn_count,
)
from ..websocket import events

router = APIRouter(prefix="/api/stories", tags=["stories"])


def _player_public(player) -> PlayerPublic:
    return PlayerPublic(
        id=player.id, display_name=player.display_name, player_number=player.player_number
    )


@router.post("", response_model=JoinResponse, dependencies=[Depends(rate_limit)])
async def create_story(req: CreateStoryRequest, db: AsyncSession = Depends(get_db)) -> JoinResponse:
    if req.mode == MODE_FRIEND:
        story, player, token = await create_friend_story(
            db, req.display_name, req.language, req.total_turns
        )
    else:  # random -> matchmaking (length is chosen randomly by the server)
        story, player, token, matched = await matchmaking.request_match(
            db, req.display_name, req.language
        )
        if matched:
            # Notify the player who was already waiting that the game has started.
            await events.broadcast_state(story, events.GAME_STARTED)
    return JoinResponse(token=token, player=_player_public(player), story=serialize_story(story))


@router.post("/{story_id}/join", response_model=JoinResponse, dependencies=[Depends(rate_limit)])
async def join_existing_story(
    story_id: str, req: JoinStoryRequest, db: AsyncSession = Depends(get_db)
) -> JoinResponse:
    story, player, token = await join_story(db, story_id, req.display_name)
    # Both players are now in; the game is active.
    await events.broadcast_state(story, events.PLAYER_JOINED)
    await events.broadcast_state(story, events.GAME_STARTED)
    return JoinResponse(token=token, player=_player_public(player), story=serialize_story(story))


@router.post("/{story_id}/settings", response_model=StoryStateResponse, dependencies=[Depends(rate_limit)])
async def update_story_settings(
    story_id: str, req: UpdateSettingsRequest, db: AsyncSession = Depends(get_db)
) -> StoryStateResponse:
    story = await update_turn_count(db, story_id, req.token, req.total_turns)
    player = find_player_by_token(story, req.token)
    return StoryStateResponse(
        story=serialize_story(story), you=_player_public(player) if player else None
    )


@router.get("/{story_id}", response_model=StoryStateResponse)
async def get_story(
    story_id: str,
    token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> StoryStateResponse:
    story = await load_story(db, story_id)
    if story is None:
        raise GameError("story_not_found", status_code=404)
    you = None
    if token:
        player = find_player_by_token(story, token)
        if player is not None:
            you = _player_public(player)
    return StoryStateResponse(story=serialize_story(story), you=you)


@router.post("/{story_id}/turns", response_model=StoryStateResponse, dependencies=[Depends(rate_limit)])
async def submit_story_turn(
    story_id: str, req: SubmitTurnRequest, db: AsyncSession = Depends(get_db)
) -> StoryStateResponse:
    story, submitted_turn = await submit_turn(db, story_id, req.token, req.text)
    # Broadcast that a turn was submitted, then the resulting state change.
    await events.broadcast_state(story, events.TURN_SUBMITTED, {"submitted_turn": submitted_turn})
    if story.status == "completed":
        await events.broadcast_state(story, events.STORY_COMPLETED)
    else:
        await events.broadcast_state(story, events.TURN_CHANGED)
    player = find_player_by_token(story, req.token)
    return StoryStateResponse(
        story=serialize_story(story), you=_player_public(player) if player else None
    )


@router.post("/{story_id}/cancel", dependencies=[Depends(rate_limit)])
async def cancel_waiting_story(
    story_id: str, req: CancelMatchmakingRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    story = await load_story(db, story_id)
    if story is None:
        return {"ok": True}
    player = find_player_by_token(story, req.token)
    if player is None:
        raise GameError("invalid_token", status_code=403)
    if story.status != STATUS_WAITING:
        # Game already started; cannot cancel.
        raise GameError("story_not_cancelable")
    await matchmaking.cancel_match(story.id, story.language, story.total_turns)
    await db.delete(story)
    await db.commit()
    return {"ok": True}
