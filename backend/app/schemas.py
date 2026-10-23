"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ---- Requests ---------------------------------------------------------------

class CreateStoryRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=80)
    language: str = Field(..., pattern="^(en|he)$")
    total_turns: int
    mode: str = Field(..., pattern="^(random|friend)$")

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()


class JoinStoryRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()


class MatchmakingRequest(BaseModel):
    # Random mode: the server chooses the length, so no total_turns here.
    display_name: str = Field(..., min_length=1, max_length=80)
    language: str = Field(..., pattern="^(en|he)$")

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()


class SubmitTurnRequest(BaseModel):
    token: str = Field(..., min_length=8)
    text: str = Field(..., min_length=1)


class CancelMatchmakingRequest(BaseModel):
    token: str = Field(..., min_length=8)


class UpdateSettingsRequest(BaseModel):
    token: str = Field(..., min_length=8)
    total_turns: int


# ---- Responses --------------------------------------------------------------

class PlayerPublic(BaseModel):
    id: str
    display_name: str
    player_number: int


class SentencePublic(BaseModel):
    id: int
    player_id: str
    player_number: int
    position: int
    turn_number: int
    text: str


class StoryState(BaseModel):
    id: str
    language: str
    mode: str
    total_turns: int
    current_turn: int
    status: str
    active_player_number: int | None
    players: list[PlayerPublic]
    sentences: list[SentencePublic]
    created_at: datetime
    completed_at: datetime | None
    invite_url: str
    share_url: str
    # The last 2 words of the previous turn, shown to the active writer as a
    # handoff hint (empty on turn 1, while waiting, or once completed).
    continuation_hint: str = ""


class JoinResponse(BaseModel):
    """Returned when a player creates or joins a story. Includes the secret token."""
    token: str
    player: PlayerPublic
    story: StoryState


class StoryStateResponse(BaseModel):
    story: StoryState
    # Echoes the viewer's player number if a valid token was supplied.
    you: PlayerPublic | None = None
