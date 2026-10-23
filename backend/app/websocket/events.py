"""Helpers for constructing and broadcasting WebSocket messages."""
from __future__ import annotations

from ..models import Story
from ..services.story_service import serialize_story
from .manager import manager

# Event names (mirrored on the frontend).
PLAYER_JOINED = "player_joined"
GAME_STARTED = "game_started"
TURN_SUBMITTED = "turn_submitted"
TURN_CHANGED = "turn_changed"
PLAYER_DISCONNECTED = "player_disconnected"
PLAYER_RECONNECTED = "player_reconnected"
STORY_COMPLETED = "story_completed"


def build_state_message(story: Story, event: str, extra: dict | None = None) -> dict:
    message = {
        "type": "state",
        "event": event,
        "story": serialize_story(story).model_dump(mode="json"),
    }
    if extra:
        message.update(extra)
    return message


async def broadcast_state(story: Story, event: str, extra: dict | None = None) -> None:
    await manager.broadcast(story.id, build_state_message(story, event, extra))
