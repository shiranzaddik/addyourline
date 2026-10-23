"""Integration tests for the REST game flow and rules."""
import pytest


async def _create_friend(client, turns=10, language="en", name="Alice"):
    resp = await client.post(
        "/api/stories",
        json={"display_name": name, "language": language, "total_turns": turns, "mode": "friend"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _join(client, story_id, name="Bob"):
    resp = await client.post(f"/api/stories/{story_id}/join", json={"display_name": name})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _submit(client, story_id, token, text):
    return await client.post(f"/api/stories/{story_id}/turns", json={"token": token, "text": text})


@pytest.mark.asyncio
async def test_friend_full_game(client):
    a = await _create_friend(client, turns=2)
    story_id = a["story"]["id"]
    assert a["story"]["status"] == "waiting"
    assert a["player"]["player_number"] == 1

    b = await _join(client, story_id)
    assert b["story"]["status"] == "active"
    assert b["player"]["player_number"] == 2

    token_a, token_b = a["token"], b["token"]

    # Turn 1: player A.
    r1 = await _submit(client, story_id, token_a, "The sun rose. Birds sang.")
    assert r1.status_code == 200, r1.text
    assert r1.json()["story"]["current_turn"] == 2
    assert r1.json()["story"]["active_player_number"] == 2

    # Turn 2: player B completes the 2-turn game.
    r2 = await _submit(client, story_id, token_b, "A storm came. Everyone ran home.")
    assert r2.status_code == 200, r2.text
    final = r2.json()["story"]
    assert final["status"] == "completed"
    # 2 turns * 2 sentences = 4 sentence records.
    assert len(final["sentences"]) == 4
    assert [s["position"] for s in final["sentences"]] == [0, 1, 2, 3]
    assert final["sentences"][0]["player_number"] == 1
    assert final["sentences"][2]["player_number"] == 2


@pytest.mark.asyncio
async def test_wrong_player_cannot_submit(client):
    a = await _create_friend(client, turns=10)
    story_id = a["story"]["id"]
    b = await _join(client, story_id)
    # It is player A's turn; player B tries to submit.
    r = await _submit(client, story_id, b["token"], "Nope nope. Not my turn.")
    assert r.status_code == 409
    assert r.json()["code"] == "not_your_turn"


@pytest.mark.asyncio
async def test_invalid_sentence_count_rejected(client):
    a = await _create_friend(client, turns=10)
    story_id = a["story"]["id"]
    await _join(client, story_id)
    r = await _submit(client, story_id, a["token"], "Only one sentence.")
    assert r.status_code == 400
    assert r.json()["code"] == "needs_two_sentences"


@pytest.mark.asyncio
async def test_duplicate_submission_blocked(client):
    a = await _create_friend(client, turns=10)
    story_id = a["story"]["id"]
    await _join(client, story_id)
    ok = await _submit(client, story_id, a["token"], "First sentence. Second sentence.")
    assert ok.status_code == 200
    # Same player tries to submit again for what is now player B's turn.
    again = await _submit(client, story_id, a["token"], "Trying again. Once more.")
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_third_player_cannot_join(client):
    a = await _create_friend(client, turns=10)
    story_id = a["story"]["id"]
    await _join(client, story_id, name="Bob")
    r = await client.post(f"/api/stories/{story_id}/join", json={"display_name": "Carol"})
    assert r.status_code == 400
    assert r.json()["code"] in ("story_full", "story_not_joinable")


@pytest.mark.asyncio
async def test_invalid_token_rejected(client):
    a = await _create_friend(client, turns=10)
    story_id = a["story"]["id"]
    await _join(client, story_id)
    r = await _submit(client, story_id, "not-a-real-token-xxxxxxxx", "Hello there. General Kenobi.")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_matchmaking_pairs_two_players(client):
    r1 = await client.post(
        "/api/matchmaking",
        json={"display_name": "P1", "language": "en", "total_turns": 10},
    )
    assert r1.status_code == 200
    assert r1.json()["story"]["status"] == "waiting"
    story_id = r1.json()["story"]["id"]

    r2 = await client.post(
        "/api/matchmaking",
        json={"display_name": "P2", "language": "en", "total_turns": 10},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["story"]["id"] == story_id  # matched into the same story
    assert body2["story"]["status"] == "active"
    assert body2["player"]["player_number"] == 2


@pytest.mark.asyncio
async def test_matchmaking_respects_settings(client):
    r1 = await client.post(
        "/api/matchmaking", json={"display_name": "P1", "language": "en", "total_turns": 10}
    )
    # Different turn count should NOT match the waiting player.
    r2 = await client.post(
        "/api/matchmaking", json={"display_name": "P2", "language": "en", "total_turns": 20}
    )
    assert r1.json()["story"]["id"] != r2.json()["story"]["id"]
    assert r2.json()["story"]["status"] == "waiting"


@pytest.mark.asyncio
async def test_get_story_state_with_token(client):
    a = await _create_friend(client, turns=10)
    story_id = a["story"]["id"]
    r = await client.get(f"/api/stories/{story_id}", params={"token": a["token"]})
    assert r.status_code == 200
    assert r.json()["you"]["player_number"] == 1
    # Links use the configured production base URL.
    assert r.json()["story"]["invite_url"] == f"https://addyourline.com/{story_id}"


@pytest.mark.asyncio
async def test_completed_story_is_public_and_immutable(client):
    a = await _create_friend(client, turns=2)
    story_id = a["story"]["id"]
    b = await _join(client, story_id)
    await _submit(client, story_id, a["token"], "One. Two.")
    await _submit(client, story_id, b["token"], "Three. Four.")
    # Public read without token.
    r = await client.get(f"/api/stories/{story_id}")
    assert r.status_code == 200
    assert r.json()["story"]["status"] == "completed"
    # Further submissions are rejected.
    r2 = await _submit(client, story_id, a["token"], "Five. Six.")
    assert r2.status_code == 400
    assert r2.json()["code"] == "story_completed"
