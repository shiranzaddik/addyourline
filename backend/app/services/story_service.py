"""Core game logic: creating stories, joining, submitting turns, serialization.

All turn mutations are authoritative on the server and run inside a single
database transaction so that both sentences are stored and the turn advances
atomically.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..models import (
    MODE_FRIEND,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    STATUS_WAITING,
    Player,
    Sentence,
    Story,
)
from ..schemas import PlayerPublic, SentencePublic, StoryState
from ..utils.security import generate_token, hash_token, verify_token
from ..utils.validation import ValidationError, validate_contribution, validate_name


class GameError(Exception):
    """Domain error with a machine-readable code and HTTP status."""

    def __init__(self, code: str, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def validate_turn_count(total_turns: int) -> None:
    """Allow any story length within the configured inclusive range."""
    if not (settings.min_turns <= total_turns <= settings.max_turns):
        raise GameError("invalid_turn_count")


async def load_story(db: AsyncSession, story_id: str) -> Story | None:
    result = await db.execute(
        select(Story)
        .where(Story.id == story_id)
        .options(selectinload(Story.players), selectinload(Story.sentences))
    )
    return result.scalar_one_or_none()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- Serialization ----------------------------------------------------------

def serialize_story(story: Story) -> StoryState:
    players_by_id = {p.id: p for p in story.players}
    # The full story so far is visible to both players during the game.
    sentences = [
        SentencePublic(
            id=s.id,
            player_id=s.player_id,
            player_number=players_by_id[s.player_id].player_number
            if s.player_id in players_by_id
            else 0,
            position=s.position,
            turn_number=s.turn_number,
            text=s.text,
        )
        for s in sorted(story.sentences, key=lambda x: x.position)
    ]
    active = story.active_player_number if story.status == STATUS_ACTIVE else None
    base = settings.public_base_url.rstrip("/")
    return StoryState(
        id=story.id,
        language=story.language,
        mode=story.mode,
        total_turns=story.total_turns,
        current_turn=story.current_turn,
        status=story.status,
        active_player_number=active,
        players=[
            PlayerPublic(id=p.id, display_name=p.display_name, player_number=p.player_number)
            for p in sorted(story.players, key=lambda x: x.player_number)
        ],
        sentences=sentences,
        created_at=story.created_at,
        completed_at=story.completed_at,
        invite_url=f"{base}/{story.id}",
        share_url=f"{base}/story/{story.id}",
    )


def find_player_by_token(story: Story, token: str) -> Player | None:
    for p in story.players:
        if verify_token(token, p.player_token_hash):
            return p
    return None


# ---- Creation & joining -----------------------------------------------------

async def create_friend_story(
    db: AsyncSession, display_name: str, language: str, total_turns: int
) -> tuple[Story, Player, str]:
    name = validate_name(display_name, settings.max_name_length)
    validate_turn_count(total_turns)

    token = generate_token()
    story = Story(
        language=language,
        mode=MODE_FRIEND,
        total_turns=total_turns,
        current_turn=1,
        status=STATUS_WAITING,
    )
    player = Player(
        display_name=name,
        player_number=1,
        player_token_hash=hash_token(token),
    )
    story.players.append(player)
    db.add(story)
    await db.commit()
    await db.refresh(story, attribute_names=["players", "sentences"])
    return story, player, token


async def update_turn_count(
    db: AsyncSession, story_id: str, token: str, total_turns: int
) -> Story:
    """Let the creator change a friend story's length while still waiting."""
    story = await load_story(db, story_id)
    if story is None:
        raise GameError("story_not_found", status_code=404)
    if story.status != STATUS_WAITING:
        raise GameError("story_already_started")
    player = find_player_by_token(story, token)
    if player is None or player.player_number != 1:
        raise GameError("invalid_token", status_code=403)
    validate_turn_count(total_turns)
    story.total_turns = total_turns
    story.updated_at = _now()
    await db.commit()
    await db.refresh(story, attribute_names=["players", "sentences"])
    return story


async def join_story(
    db: AsyncSession, story_id: str, display_name: str
) -> tuple[Story, Player, str]:
    name = validate_name(display_name, settings.max_name_length)
    story = await load_story(db, story_id)
    if story is None:
        raise GameError("story_not_found", status_code=404)
    if story.status != STATUS_WAITING:
        raise GameError("story_not_joinable")
    if len(story.players) >= 2:
        raise GameError("story_full")

    token = generate_token()
    player = Player(
        story_id=story.id,
        display_name=name,
        player_number=2,
        player_token_hash=hash_token(token),
    )
    story.players.append(player)
    story.status = STATUS_ACTIVE
    story.updated_at = _now()
    db.add(player)
    await db.commit()
    await db.refresh(story, attribute_names=["players", "sentences"])
    return story, player, token


# ---- Turn submission --------------------------------------------------------

async def submit_turn(
    db: AsyncSession, story_id: str, token: str, text: str
) -> tuple[Story, int]:
    """Submit the active player's contribution. Returns (story, submitted_turn).

    Enforces: valid token, correct active player, game active, minimum word
    count, no duplicate/past-turn submission. Runs atomically.
    """
    story = await load_story(db, story_id)
    if story is None:
        raise GameError("story_not_found", status_code=404)
    if story.status == STATUS_COMPLETED:
        raise GameError("story_completed")
    if story.status != STATUS_ACTIVE:
        raise GameError("story_not_active")

    player = find_player_by_token(story, token)
    if player is None:
        raise GameError("invalid_token", status_code=403)
    if player.player_number != story.active_player_number:
        raise GameError("not_your_turn", status_code=409)

    try:
        normalized = validate_contribution(text, settings.max_turn_length, settings.min_words)
    except ValidationError as exc:
        raise GameError(str(exc)) from exc

    submitted_turn = story.current_turn

    # Guard against duplicate submissions for this turn (idempotency on turn number).
    existing = await db.execute(
        select(Sentence).where(
            Sentence.story_id == story.id, Sentence.turn_number == submitted_turn
        )
    )
    if existing.first() is not None:
        raise GameError("turn_already_submitted", status_code=409)

    # Store the whole contribution as one entry for this turn.
    db.add(
        Sentence(
            story_id=story.id,
            player_id=player.id,
            position=submitted_turn - 1,
            turn_number=submitted_turn,
            text=normalized,
        )
    )

    # Advance the turn, or complete the story.
    if submitted_turn >= story.total_turns:
        story.status = STATUS_COMPLETED
        story.completed_at = _now()
    else:
        story.current_turn = submitted_turn + 1
    story.updated_at = _now()

    await db.commit()
    await db.refresh(story, attribute_names=["players", "sentences"])
    return story, submitted_turn
