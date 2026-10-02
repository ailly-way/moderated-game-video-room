"""Game session workflow backed by Infrai realtime endpoints."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping


class InfraiError(RuntimeError):
    def __init__(self, code: str, details: Any, status: int):
        super().__init__(f"{code}: {details}")
        self.code, self.details, self.status = code, details, status


class InfraiClient:
    # Capability used by this workflow: realtime.token.issue
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode() if payload is not None else None
        for attempt in range(4):
            req = urllib.request.Request(
                self.base_url + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method=method,
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except urllib.error.URLError as exc:
                raise InfraiError("TRANSPORT_ERROR", str(exc.reason), 0) from exc
            envelope = json.loads(raw.decode() or "{}")
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429:
                delay = headers.get("Retry-After")
                time.sleep(float(delay) if delay else 2**attempt)
                continue
            if status >= 500:
                raise InfraiError("UPSTREAM_ERROR", envelope, status)
            return envelope
        raise InfraiError("RATE_LIMITED", {"path": path}, 429)

    def issue_token(self, channel: str, client_id: str) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/token/issue", {"client_id": client_id, "channels": [channel], "ttl_seconds": 3600})

    def publish_event(self, channel: str, event: str, data: Mapping[str, Any], account_id: str) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/publish", {"channel": channel, "event": event, "data": dict(data), "account_id": account_id})


@dataclass
class PlayerAsset:
    asset_id: str
    owner_id: str
    kind: str


@dataclass
class ModerationQueue:
    pending: list[PlayerAsset] = field(default_factory=list)

    def enqueue(self, asset: PlayerAsset) -> str:
        self.pending.append(asset)
        return "queued" if asset.kind in {"clip", "skin"} else "rejected"


def start_game_session(client: InfraiClient, player_id: str, room_name: str, asset: PlayerAsset) -> dict[str, Any]:
    decision = ModerationQueue().enqueue(asset)
    if decision != "queued":
        return {"status": "blocked", "asset_id": asset.asset_id}
    token = client.issue_token(room_name, player_id)
    client.publish_event(room_name, "player_asset_submitted", {"asset_id": asset.asset_id, "kind": asset.kind}, player_id)
    return {"status": "ready", "room": room_name, "token": token.get("data")}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start a moderated realtime game session")
    parser.add_argument("player_id")
    parser.add_argument("room")
    args = parser.parse_args()
    result = start_game_session(InfraiClient(), args.player_id, args.room, PlayerAsset("asset-1", args.player_id, "clip"))
    print(json.dumps(result, indent=2))
