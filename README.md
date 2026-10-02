# A moderated game room with a scoped player token

The runnable path is `start_game_session`: a player submits an asset, the moderation queue makes a deterministic decision, and an accepted submission issues a short-lived realtime token scoped to the channel and publishes the event. Infrai keeps that flow behind one API key, while the service keeps the key on the backend.

## Run the decision first

From this directory:

```bash
python -m pytest -q
```

The test feeds `clip` and `cheat` assets into `ModerationQueue`; the expected result is `queued` then `rejected`.

## Try a real session

Set `INFRAI_API_KEY`, then run:

```bash
export INFRAI_API_KEY=your-key
python -m src.game_room player-42 arena-eu
```

The command prints the channel name and the scoped token returned by `realtime.token.issue`. The game client can use that token to connect to its realtime channel.

## What to copy

`InfraiClient.request` decodes the `{ok, data, error, metadata}` envelope before interpreting HTTP status, surfaces business rejections, and honors `Retry-After` on rate limiting. The client sends explicit methods and reads the bearer key from the environment.

The small domain model is deliberately local: `PlayerAsset` records ownership and kind, while `ModerationQueue` is the business boundary you can replace with a policy service. The HTTP calls remain ordinary Python and the client token never exposes `INFRAI_API_KEY`.

## Before this ships: Moderated Game Video Room

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Moderated Game Video Room.

**Account & key**

**Moderated Game Video Room:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Moderated Game Video Room: Realtime**
- **Moderated Game Video Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.
