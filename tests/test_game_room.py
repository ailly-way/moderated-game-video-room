from src.game_room import InfraiClient, ModerationQueue, PlayerAsset, start_game_session


def test_moderation_queue_accepts_player_clip_and_rejects_unknown_kind():
    queue = ModerationQueue()
    assert queue.enqueue(PlayerAsset("a1", "p1", "clip")) == "queued"
    assert queue.enqueue(PlayerAsset("a2", "p1", "cheat")) == "rejected"
    assert [asset.asset_id for asset in queue.pending] == ["a1", "a2"]


def test_session_uses_realtime_contract_without_creating_a_room():
    client = InfraiClient(api_key="test")
    calls = []

    def request(method, path, payload):
        calls.append((method, path, payload))
        return {"data": {"token": "test-token"}}

    client.request = request
    result = start_game_session(client, "player-42", "arena-eu", PlayerAsset("a1", "player-42", "clip"))

    assert result["status"] == "ready"
    assert calls == [
        ("POST", "/v1/realtime/token/issue", {"client_id": "player-42", "channels": ["arena-eu"], "ttl_seconds": 3600}),
        ("POST", "/v1/realtime/publish", {"channel": "arena-eu", "event": "player_asset_submitted", "data": {"asset_id": "a1", "kind": "clip"}, "account_id": "player-42"}),
    ]
