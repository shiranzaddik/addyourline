"""SQLAlchemy ORM models for stories, players and sentences."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Status values
STATUS_WAITING = "waiting"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"

# Mode values
MODE_RANDOM = "random"
MODE_FRIEND = "friend"


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    language: Mapped[str] = mapped_column(String(8), nullable=False)  # "en" | "he"
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # random | friend
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False)
    current_turn: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_WAITING, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    players: Mapped[list[Player]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="Player.player_number",
    )
    sentences: Mapped[list[Sentence]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="Sentence.position",
    )

    # Whose turn is it (player_number). Turn 1 -> player 1, turn 2 -> player 2, ...
    @property
    def active_player_number(self) -> int:
        return 1 if self.current_turn % 2 == 1 else 2


class Player(Base):
    __tablename__ = "story_players"
    __table_args__ = (
        UniqueConstraint("story_id", "player_number", name="uq_story_player_number"),
        Index("ix_player_story", "story_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    player_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    player_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    story: Mapped[Story] = relationship(back_populates="players")
    sentences: Mapped[list[Sentence]] = relationship(back_populates="player")


class Sentence(Base):
    __tablename__ = "sentences"
    __table_args__ = (
        UniqueConstraint("story_id", "position", name="uq_story_sentence_position"),
        Index("ix_sentence_story_position", "story_id", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    player_id: Mapped[str] = mapped_column(ForeignKey("story_players.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-based order in the story
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    story: Mapped[Story] = relationship(back_populates="sentences")
    player: Mapped[Player] = relationship(back_populates="sentences")
