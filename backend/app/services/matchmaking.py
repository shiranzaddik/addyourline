"""In-memory matchmaking queue for the 'random person' mode.

Players who pick the same (language, total_turns) are paired. A waiting story is
created for the first player; the next compatible player joins it and the game
starts. A single asyncio lock serializes queue access to avoid races such as
two players grabbing the same waiting story.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import MODE_RANDOM, STATUS_WAITING, Player, Story
from ..utils.security import generate_token, hash_token
from ..utils.validation import validate_name
from .story_service import GameError, join_story, load_story

# (language, total_turns) -> queue of waiting story ids
_queue: dict[tuple[str, int], deque[str]] = defaultdict(deque)
_lock = asyncio.Lock()


async def _create_random_story(
    db: AsyncSession, display_name: str, language: str, total_turns: int
) -> tuple[Story, Player, str]:
    token = generate_token()
    story = Story(
        language=language,
        mode=MODE_RANDOM,
        total_turns=total_turns,
        current_turn=1,
        status=STATUS_WAITING,
    )
    player = Player(display_name=display_name, player_number=1, player_token_hash=hash_token(token))
    story.players.append(player)
    db.add(story)
    await db.commit()
    await db.refresh(story, attribute_names=["players", "sentences"])
    return story, player, token


async def request_match(
    db: AsyncSession, display_name: str, language: str, total_turns: int
) -> tuple[Story, Player, str, bool]:
    """Return (story, player, token, matched).

    matched=True means the player joined an existing waiting story and the game
    is now active; matched=False means they are waiting in a freshly created one.
    """
    name = validate_name(display_name, settings.max_name_length)
    if total_turns not in settings.allowed_turn_count_set:
        raise GameError("invalid_turn_count")

    key = (language, total_turns)
    async with _lock:
        q = _queue[key]
        while q:
            waiting_id = q.popleft()
            waiting = await load_story(db, waiting_id)
            # Skip stale entries (cancelled, already full, or no longer waiting).
            if waiting is None or waiting.status != STATUS_WAITING or len(waiting.players) != 1:
                continue
            # Found a valid partner — join as player 2.
            story, player, token = await join_story(db, waiting_id, name)
            return story, player, token, True

        # No partner available: create a new waiting story and enqueue it.
        story, player, token = await _create_random_story(db, name, language, total_turns)
        _queue[key].append(story.id)
        return story, player, token, False


async def cancel_match(story_id: str, language: str, total_turns: int) -> None:
    """Remove a waiting story from the queue (player left the waiting room)."""
    key = (language, total_turns)
    async with _lock:
        q = _queue.get(key)
        if q and story_id in q:
            # deque has no direct remove-by-value that is cheap, but queues are small.
            try:
                q.remove(story_id)
            except ValueError:
                pass
