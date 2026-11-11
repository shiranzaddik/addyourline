"""Computer-opponent ("play vs the computer") mode.

A bot story is created already ``active`` with two players: the human (player 1)
and the computer (player 2). The human always writes first. After each human
turn the backend plays the computer's turn automatically, inside the same
request, so no second human (and no second WebSocket) is ever required.

The line generator is intentionally **self-contained**: it composes a
contribution from a curated pool of evocative, context-free story lines in the
story's language. That keeps the feature fully offline — no API key, no network
call, no extra dependency — and guarantees every computer line is grammatical
and always satisfies the minimum-word rule.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from ..config import settings
from ..models import (
    MODE_BOT,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    Player,
    Sentence,
    Story,
)
from ..utils.security import generate_token, hash_token
from ..utils.validation import validate_name
from .story_service import load_story, validate_turn_count

# Display name shown for the computer player, per language.
BOT_NAMES = {"en": "Computer 🤖", "he": "המחשב 🤖"}

# Curated continuation lines. Each is a complete sentence ending in terminal
# punctuation and contains enough words that any pair easily clears the
# minimum-word rule. They are deliberately generic so they fit any story.
_LINES = {
    "en": [
        "Then everything changed in an instant.",
        "But no one expected what came next.",
        "A strange silence filled the room.",
        "Suddenly the lights flickered and died.",
        "Nobody knew where the sound came from.",
        "The air grew colder by the second.",
        "Something moved quietly in the dark.",
        "A single question hung in the air.",
        "Far away, a dog began to bark.",
        "The old floorboards creaked under slow steps.",
        "Nothing would ever be the same again.",
        "A letter arrived with no return address.",
        "The clock on the wall stopped ticking.",
        "She held her breath and listened carefully.",
        "Then came a knock at the door.",
        "The map led somewhere it should not have.",
        "Rain started falling without any warning.",
        "He opened his eyes to a different world.",
        "Everyone turned to look at once.",
        "The secret had been there all along.",
        "A warm light spilled across the floor.",
        "Deep down, they all knew the truth.",
        "The last train pulled away far too soon.",
        "A small door appeared where none had been.",
        "They followed the footprints into the fog.",
        "The last candle burned down to nothing.",
        "Something glittered at the bottom of the well.",
        "No one dared to say a word.",
        "The garden looked different in the moonlight.",
        "A faint melody drifted through the hallway.",
        "The photograph showed a face they knew.",
        "Time seemed to slow almost to a stop.",
        "A quiet promise was made that night.",
        "The river carried the little boat onward.",
        "Then, against all odds, it finally worked.",
        "The key fit the old lock perfectly.",
        "A shadow slipped around the corner.",
        "The whole town held its breath.",
        "And just like that, she was gone.",
        "The real journey was only beginning.",
    ],
    "he": [
        "ואז הכול השתנה ברגע אחד.",
        "אבל איש לא ציפה למה שקרה אחר כך.",
        "שקט מוזר השתרר בחדר.",
        "לפתע האורות הבהבו וכבו.",
        "אף אחד לא ידע מאיפה בא הקול.",
        "האוויר הלך והתקרר משנייה לשנייה.",
        "משהו זז בשקט בתוך החשכה.",
        "שאלה אחת נותרה תלויה באוויר.",
        "הרחק משם כלב התחיל לנבוח.",
        "הרצפה הישנה חרקה תחת צעדים איטיים.",
        "שום דבר כבר לא יהיה אותו דבר.",
        "מכתב הגיע בלי כתובת שולח.",
        "השעון על הקיר הפסיק לתקתק.",
        "היא עצרה את נשימתה והקשיבה בתשומת לב.",
        "ואז נשמעה דפיקה בדלת.",
        "המפה הובילה למקום לא צפוי.",
        "גשם התחיל לרדת בלי שום אזהרה.",
        "הוא פקח את עיניו לעולם אחר.",
        "כולם הסתובבו להביט בבת אחת.",
        "הסוד היה שם כל הזמן.",
        "אור חמים נשפך על הרצפה.",
        "עמוק בפנים כולם ידעו את האמת.",
        "הרכבת האחרונה יצאה מוקדם מדי.",
        "דלת קטנה הופיעה היכן שלא הייתה.",
        "הם עקבו אחר העקבות אל תוך הערפל.",
        "הנר האחרון דעך עד כלות.",
        "משהו נצץ בתחתית הבאר.",
        "אף אחד לא העז לומר מילה.",
        "הגינה נראתה אחרת לאור הירח.",
        "מנגינה קלושה נישאה לאורך המסדרון.",
        "בתצלום הופיע פרצוף מוכר.",
        "הזמן כמעט עצר מלכת.",
        "באותו לילה ניתנה הבטחה חרישית.",
        "הנהר נשא את הסירה הקטנה הלאה.",
        "ואז, בניגוד לכל הסיכויים, זה עבד.",
        "המפתח התאים למנעול הישן בדיוק.",
        "צל חמק מעבר לפינה.",
        "כל העיירה עצרה את נשימתה.",
        "וכך פשוט, היא נעלמה.",
        "המסע האמיתי רק התחיל.",
    ],
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bot_name(language: str) -> str:
    return BOT_NAMES.get(language, BOT_NAMES["en"])


def generate_line(language: str, used_texts: set[str] | None = None) -> str:
    """Compose a computer contribution of two distinct lines.

    ``used_texts`` holds lines the computer already played in this story so it
    avoids repeating itself when the pool still has fresh options.
    """
    pool = _LINES.get(language, _LINES["en"])
    used = used_texts or set()
    fresh = [ln for ln in pool if ln not in used]
    source = fresh if len(fresh) >= 2 else pool
    first, second = random.sample(source, 2)
    text = f"{first} {second}"
    # Safety net: never exceed the configured contribution length.
    if len(text) > settings.max_turn_length:
        text = first
    return text


async def create_bot_story(
    db, display_name: str, language: str, total_turns: int
) -> tuple[Story, Player, str]:
    """Create a story that is immediately active: human (1) + computer (2)."""
    name = validate_name(display_name, settings.max_name_length)
    validate_turn_count(total_turns)

    human_token = generate_token()
    story = Story(
        language=language,
        mode=MODE_BOT,
        total_turns=total_turns,
        current_turn=1,
        status=STATUS_ACTIVE,  # no waiting room — the opponent is already here
    )
    human = Player(
        display_name=name,
        player_number=1,
        player_token_hash=hash_token(human_token),
    )
    bot = Player(
        display_name=_bot_name(language),
        player_number=2,
        # The computer never authenticates, but the column is required.
        player_token_hash=hash_token(generate_token()),
    )
    story.players.append(human)
    story.players.append(bot)
    db.add(story)
    await db.commit()
    await db.refresh(story, attribute_names=["players", "sentences"])
    return story, human, human_token


async def play_pending_bot_turns(db, story_id: str) -> Story | None:
    """If it's the computer's turn, play it (and keep playing while it still is).

    Returns the refreshed story, or ``None`` if the story vanished. Safe to call
    after any human submission; it no-ops when it isn't the computer's turn.
    """
    story = await load_story(db, story_id)
    if story is None or story.mode != MODE_BOT:
        return story

    played = False
    # Turns alternate, so this normally runs at most once, but the loop keeps the
    # logic correct regardless of who holds the final turn.
    while story.status == STATUS_ACTIVE and story.active_player_number == 2:
        bot_player = next((p for p in story.players if p.player_number == 2), None)
        if bot_player is None:
            break

        # A short, natural pause so it feels like the computer is writing.
        await asyncio.sleep(random.uniform(0.4, 0.9))

        used = {s.text for s in story.sentences if s.player_id == bot_player.id}
        text = generate_line(story.language, used)
        turn = story.current_turn

        story.sentences.append(
            Sentence(
                story_id=story.id,
                player_id=bot_player.id,
                position=turn - 1,
                turn_number=turn,
                text=text,
            )
        )
        if turn >= story.total_turns:
            story.status = STATUS_COMPLETED
            story.completed_at = _now()
        else:
            story.current_turn = turn + 1
        story.updated_at = _now()
        played = True

    if played:
        await db.commit()
        await db.refresh(story, attribute_names=["players", "sentences"])
    return story
