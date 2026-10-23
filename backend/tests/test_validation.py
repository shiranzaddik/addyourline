"""Unit tests for sentence validation (English and Hebrew)."""
import pytest

from app.utils.validation import ValidationError, count_sentences, validate_contribution


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Hello world. This is fun!", 2),
        ("One sentence only.", 1),
        ("Three. Little. Sentences.", 3),
        ("No punctuation here", -1),  # unterminated
        ("First one. Second without end", -1),
        ("   ", 0),
        ("What a day! Really?", 2),
        ("היום יום יפה. השמש זורחת בחוץ!", 2),  # Hebrew, two sentences
        ("שלום לכולם.", 1),  # Hebrew, one sentence
        ("Wait... Then go!", 2),  # ellipsis counts as one terminator
    ],
)
def test_count_sentences(text, expected):
    assert count_sentences(text) == expected


def test_validate_contribution_ok_english():
    out = validate_contribution("The sun rose. Birds began to sing.", 600)
    assert out == "The sun rose. Birds began to sing."


def test_validate_contribution_ok_hebrew():
    out = validate_contribution("הסיפור מתחיל כאן. הגיבור יוצא לדרך.", 600)
    assert "הסיפור" in out


def test_validate_contribution_rejects_one_sentence():
    with pytest.raises(ValidationError) as exc:
        validate_contribution("Only one sentence here.", 600)
    assert str(exc.value) == "needs_two_sentences"


def test_validate_contribution_rejects_three_sentences():
    with pytest.raises(ValidationError):
        validate_contribution("One. Two. Three.", 600)


def test_validate_contribution_rejects_empty():
    with pytest.raises(ValidationError):
        validate_contribution("   ", 600)


def test_validate_contribution_rejects_too_long():
    with pytest.raises(ValidationError) as exc:
        validate_contribution("A. B.", 3)
    assert str(exc.value) == "too_long"
