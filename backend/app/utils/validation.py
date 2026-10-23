"""Sentence-count validation for English and Hebrew.

A turn must contain exactly two sentences. We use a lightweight, punctuation-based
heuristic (no heavy NLP): a sentence is a run of text terminated by one or more
terminal punctuation marks. This works for both English and Hebrew, which share
the same Latin/Arabic-numeral punctuation (. ! ?) plus the ellipsis character.
"""
import re

# Terminal punctuation that ends a sentence (ASCII + ellipsis + fullwidth variants).
_TERMINALS = ".!?…！？。"
# A sentence = some non-terminal characters, then one or more terminals.
_SENTENCE_RE = re.compile(rf"[^{re.escape(_TERMINALS)}]*[{re.escape(_TERMINALS)}]+")
# At least one letter or digit (any script) must be present in a sentence body.
_HAS_WORD_RE = re.compile(r"[^\W\d_]|\d", re.UNICODE)


class ValidationError(ValueError):
    """Raised when a contribution fails validation."""


def count_sentences(text: str) -> int:
    """Count terminated sentences in the given text."""
    stripped = text.strip()
    if not stripped:
        return 0
    matches = _SENTENCE_RE.findall(stripped)
    # Remove whitespace-only matches.
    sentences = [m for m in matches if m.strip() and _HAS_WORD_RE.search(m)]
    # Reject trailing text that is not terminated by punctuation.
    consumed = "".join(matches)
    if consumed.strip() != stripped:
        # There is leftover (unterminated) content after the last terminal mark.
        return -1
    return len(sentences)


def validate_contribution(text: str, max_length: int) -> str:
    """Validate a two-sentence contribution and return the normalized text.

    Raises ValidationError with a machine-readable code when invalid.
    """
    if text is None:
        raise ValidationError("empty")
    normalized = text.strip()
    if not normalized:
        raise ValidationError("empty")
    if len(normalized) > max_length:
        raise ValidationError("too_long")

    count = count_sentences(normalized)
    if count == -1:
        # Unterminated trailing sentence (missing final punctuation).
        raise ValidationError("needs_two_sentences")
    if count != 2:
        raise ValidationError("needs_two_sentences")
    return normalized


def validate_name(name: str, max_length: int) -> str:
    if name is None:
        raise ValidationError("name_required")
    normalized = " ".join(name.split())  # collapse whitespace
    if not normalized:
        raise ValidationError("name_required")
    if len(normalized) > max_length:
        raise ValidationError("name_too_long")
    return normalized
