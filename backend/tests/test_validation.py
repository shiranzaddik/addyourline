"""Unit tests for contribution validation (minimum word count, EN and HE)."""
import pytest

from app.utils.validation import ValidationError, count_words, validate_contribution


@pytest.mark.parametrize(
    "text,expected",
    [
        ("one two three four", 4),
        ("only three words", 3),
        ("   ", 0),
        ("Hello, world! Nice day.", 4),
        ("יום אחד הלך ילד לטייל בגינה ומצא חתול.", 8),  # Hebrew
        ("a b c", 3),
    ],
)
def test_count_words(text, expected):
    assert count_words(text) == expected


def test_validate_contribution_ok_english():
    out = validate_contribution("the sun rose over the hills", 600, 4)
    assert out == "the sun rose over the hills"


def test_validate_contribution_ok_hebrew():
    out = validate_contribution("יום אחד הלך ילד לטייל בגינה", 600, 4)
    assert "יום" in out


def test_validate_contribution_rejects_too_few_words():
    with pytest.raises(ValidationError) as exc:
        validate_contribution("only three words", 600, 4)
    assert str(exc.value) == "needs_min_words"


def test_validate_contribution_rejects_empty():
    with pytest.raises(ValidationError):
        validate_contribution("   ", 600, 4)


def test_validate_contribution_rejects_too_long():
    with pytest.raises(ValidationError) as exc:
        validate_contribution("one two three four", 5, 4)
    assert str(exc.value) == "too_long"
