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
async def test_sentence_text_hidden_until_completed(client):
    a = await _create_friend(client, turns=2)
    story_id = a["story"]["id"]
    b = await _join(client, story_id)

    # After turn 1 the story is still active -> text must be redacted.
    await _submit(client, story_id, a["token"], "Secret one. Secret two.")
    mid = await client.get(f"/api/stories/{story_id}")
    assert mid.json()["story"]["status"] == "active"
    assert all(s["text"] == "" for s in mid.json()["story"]["sentences"])
    # Positions/turns are still exposed for progress.
    assert len(mid.json()["story"]["sentences"]) == 2

    # Completing the story reveals the full text.
    await _submit(client, story_id, b["token"], "Reveal three. Reveal four.")
    done = await client.get(f"/api/stories/{story_id}")
    assert done.json()["story"]["status"] == "completed"
    texts = [s["text"] for s in done.json()["story"]["sentences"]]
    assert "Secret one." in texts and "Reveal three." in texts


@pytest.mark.asyncio
async def test_continuation_hint_shows_last_two_words(client):
    a = await _create_friend(client, turns=10)
    sid = a["story"]["id"]
    b = await _join(client, sid)
    # Turn 1: nothing written yet, so no handoff hint.
    assert b["story"]["continuation_hint"] == ""

    await _submit(client, sid, a["token"], "The sun rose high. Birds sang loudly.")
    state = (await client.get(f"/api/stories/{sid}")).json()["story"]
    # The next writer sees only the last two words of the previous line.
    assert state["continuation_hint"] == "sang loudly."
    # The body text itself stays hidden until completion.
    assert all(s["text"] == "" for s in state["sentences"])


@pytest.mark.asyncio
async def test_update_friend_length_while_waiting(client):
    a = await _create_friend(client, turns=10)
    sid = a["story"]["id"]
    r = await client.post(
        f"/api/stories/{sid}/settings", json={"token": a["token"], "total_turns": 20}
    )
    assert r.status_code == 200, r.text
    assert r.json()["story"]["total_turns"] == 20

    # Once a friend joins (game started), the length can no longer change.
    await _join(client, sid)
    r2 = await client.post(
        f"/api/stories/{sid}/settings", json={"token": a["token"], "total_turns": 30}
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "story_already_started"


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
        "/api/matchmaking", json={"display_name": "P1", "language": "en"}
    )
    assert r1.status_code == 200
    assert r1.json()["story"]["status"] == "waiting"
    story_id = r1.json()["story"]["id"]
    # Length is chosen randomly by the server from the configured pool.
    assert r1.json()["story"]["total_turns"] in (10, 20, 30)

    r2 = await client.post(
        "/api/matchmaking", json={"display_name": "P2", "language": "en"}
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["story"]["id"] == story_id  # matched into the same story
    assert body2["story"]["status"] == "active"
    assert body2["player"]["player_number"] == 2


@pytest.mark.asyncio
async def test_matchmaking_random_length_is_server_chosen(client):
    # Players send no length; the server assigns one from its random pool and
    # both players share it.
    r1 = await client.post("/api/matchmaking", json={"display_name": "P1", "language": "en"})
    story_id = r1.json()["story"]["id"]
    assigned = r1.json()["story"]["total_turns"]
    assert assigned in (10, 20, 30)
    r2 = await client.post("/api/matchmaking", json={"display_name": "P2", "language": "en"})
    body2 = r2.json()
    assert body2["story"]["id"] == story_id
    assert body2["story"]["status"] == "active"
    assert body2["story"]["total_turns"] == assigned  # joiner inherits it


@pytest.mark.asyncio
async def test_matchmaking_requires_same_language(client):
    r1 = await client.post("/api/matchmaking", json={"display_name": "P1", "language": "en"})
    # Different language should NOT match the waiting player.
    r2 = await client.post("/api/matchmaking", json={"display_name": "P2", "language": "he"})
    assert r1.json()["story"]["id"] != r2.json()["story"]["id"]
    assert r2.json()["story"]["status"] == "waiting"


@pytest.mark.asyncio
async def test_custom_turn_count_within_range_allowed(client):
    # 7 is not a preset but is within the allowed 2..50 range.
    resp = await client.post(
        "/api/stories",
        json={"display_name": "Alice", "language": "en", "total_turns": 7, "mode": "friend"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["story"]["total_turns"] == 7


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [1, 0, 51, 999])
async def test_turn_count_out_of_range_rejected(client, bad):
    resp = await client.post(
        "/api/stories",
        json={"display_name": "Alice", "language": "en", "total_turns": bad, "mode": "friend"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_turn_count"


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
