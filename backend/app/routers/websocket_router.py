"""WebSocket endpoint that streams live game state to both players."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..database import AsyncSessionLocal
from ..services.story_service import find_player_by_token, load_story, serialize_story
from ..websocket import events
from ..websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/stories/{story_id}")
async def story_socket(websocket: WebSocket, story_id: str, token: str | None = None) -> None:
    # Resolve the story and (optionally) the player from the token.
    async with AsyncSessionLocal() as db:
        story = await load_story(db, story_id)
        if story is None:
            await websocket.close(code=4404)
            return
        player = find_player_by_token(story, token) if token else None
        player_number = player.player_number if player else 0
        initial = {
            "type": "state",
            "event": "connected",
            "story": serialize_story(story).model_dump(mode="json"),
        }

    was_connected = await manager.is_player_connected(story_id, player_number) if player_number else False
    await manager.connect(story_id, player_number, websocket)

    try:
        await websocket.send_json(initial)
        # Tell the other side this player (re)connected.
        if player_number and not was_connected:
            await manager.broadcast(
                story_id,
                {"type": "presence", "event": events.PLAYER_RECONNECTED, "player_number": player_number},
            )

        while True:
            try:
                # We mainly listen to detect disconnects; respond to keepalive pings.
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.CancelledError:
                raise
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(story_id, player_number, websocket)
        # If this player has no remaining sockets, announce the disconnect.
        if player_number and not await manager.is_player_connected(story_id, player_number):
            await manager.broadcast(
                story_id,
                {"type": "presence", "event": events.PLAYER_DISCONNECTED, "player_number": player_number},
            )
