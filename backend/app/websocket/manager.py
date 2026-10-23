"""In-memory WebSocket connection manager.

Connections are grouped per story. Each story can have multiple live sockets
(e.g. a player with two tabs), tracked per player number so we can tell whether
a given player is currently connected.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # story_id -> set of (player_number, websocket)
        self._rooms: dict[str, set[tuple[int, WebSocket]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, story_id: str, player_number: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[story_id].add((player_number, websocket))

    async def disconnect(self, story_id: str, player_number: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(story_id)
            if room:
                room.discard((player_number, websocket))
                if not room:
                    self._rooms.pop(story_id, None)

    async def connected_players(self, story_id: str) -> set[int]:
        async with self._lock:
            return {pn for pn, _ in self._rooms.get(story_id, set())}

    async def is_player_connected(self, story_id: str, player_number: int) -> bool:
        async with self._lock:
            return any(pn == player_number for pn, _ in self._rooms.get(story_id, set()))

    async def broadcast(self, story_id: str, message: dict) -> None:
        """Send a JSON message to every socket in the room."""
        async with self._lock:
            targets = list(self._rooms.get(story_id, set()))
        dead: list[tuple[int, WebSocket]] = []
        for player_number, ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append((player_number, ws))
        if dead:
            async with self._lock:
                room = self._rooms.get(story_id)
                if room:
                    for item in dead:
                        room.discard(item)


manager = ConnectionManager()
