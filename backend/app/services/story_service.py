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
    # Exquisite-corpse rule: the written text stays hidden until the story is
    # completed, so players write blind and the full story is revealed only at
    # the end. We still expose counts/positions so the UI can show progress.
    reveal = story.status == STATUS_COMPLETED
    sentences = [
        SentencePublic(
            id=s.id,
            player_id=s.player_id,
            player_number=players_by_id[s.player_id].player_number
            if s.player_id in players_by_id
            else 0,
            position=s.position,
            turn_number=s.turn_number,
            text=s.text if reveal else "",
        )
        for s in sorted(story.sentences, key=lambda x: x.position)
    ]
    active = story.active_player_number if story.status == STATUS_ACTIVE else None
    base = settings.public_base_url.rstrip("/")

    # Handoff hint: the last two words of the most recent line, revealed to the
    # active writer so they can continue. (The previous writer already knows
    # these words, so this leaks nothing hidden.)
    continuation_hint = ""
    if story.status == STATUS_ACTIVE and story.sentences:
        last = max(story.sentences, key=lambda s: s.position)
        words = last.text.split()
        continuation_hint = " ".join(words[-2:]) if words else ""
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
        continuation_hint=continuation_hint,
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
    """Submit the active player's two sentences. Returns (story, submitted_turn).

    Enforces: valid token, correct active player, game active, exactly two
    sentences, no duplicate/past-turn submission. Runs atomically.
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
        normalized = validate_contribution(text, settings.max_turn_length)
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

    # Split the contribution into its two sentences for separate storage.
    first_text, second_text = _split_two_sentences(normalized)
    base_position = (submitted_turn - 1) * 2

    db.add_all(
        [
            Sentence(
                story_id=story.id,
                player_id=player.id,
                position=base_position,
                turn_number=submitted_turn,
                text=first_text,
            ),
            Sentence(
                story_id=story.id,
                player_id=player.id,
                position=base_position + 1,
                turn_number=submitted_turn,
                text=second_text,
            ),
        ]
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


def _split_two_sentences(text: str) -> tuple[str, str]:
    """Split a validated two-sentence string into its two sentences."""
    from ..utils.validation import _SENTENCE_RE  # local import to avoid cycle at top

    matches = [m.strip() for m in _SENTENCE_RE.findall(text) if m.strip()]
    if len(matches) >= 2:
        # Everything from the 2nd match onward goes into sentence two (defensive).
        first = matches[0]
        second = " ".join(matches[1:])
        return first, second
    # Fallback (should not happen after validation): keep whole text as one.
    return text, ""
