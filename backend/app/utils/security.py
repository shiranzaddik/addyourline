"""Player token generation and verification.

A player receives a random opaque token once, stored client-side in localStorage.
We persist only the SHA-256 hash, so a leaked database cannot impersonate players.
"""
import hashlib
import hmac
import secrets


def generate_token() -> str:
    """Return a new random URL-safe token for a player."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), token_hash)
