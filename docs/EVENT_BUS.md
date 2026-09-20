# Game Event Bus

The event bus turns the Minecraft server's log into typed, persisted events that
features can subscribe to. It is the foundation the gameplay features in
[ROADMAP.md](ROADMAP.md) are built on.

## Why it exists

The server log is the only real-time signal Minecraft produces. Before the bus,
the API followed that log purely to stream raw text to the browser, so anything
reactive had to re-parse raw lines for itself, and nothing was captured at all
unless somebody had the dashboard open.

The bus changes three things:

- The follower runs from API startup, not from the first browser connection.
  Events that happen while nobody is watching are exactly the ones worth keeping.
- Lines are parsed once into typed events and recorded once, so counts do not
  drift. Statistics the game keeps for itself are not duplicated here at all:
  [PLAYER_STATS.md](PLAYER_STATS.md) reads those from the world's own files.
- Anything can subscribe. A new feature is a handler function, not another log
  parser.

## Event types

| Type | Fired when | Extra fields in `data` |
| --- | --- | --- |
| `chat` | A player sends a chat message | `message` |
| `connect` | A player's client authenticates and connects | `address` |
| `join` | A player enters the world | |
| `leave` | A player disconnects | |
| `death` | A player dies | `cause`, `message` |
| `advancement` | An advancement, challenge or goal is earned | `advancement` |
| `command` | A player runs a slash command | `command` |
| `server_ready` | The server finishes starting | `startup_time` |
| `server_stopping` | The server begins shutting down | |

Every event also carries `log_time`, the `HH:MM:SS` the server itself printed.

A player session logs two lines, the `connect` carrying the network address and
the `join` a moment later. They are separate types so that counting joins does
not double-count every session. Use `join` for "who arrived"; `connect` exists
so a future "a new device connected" alert has the address it needs.

### Event shape

```json
{
  "type": "death",
  "timestamp": "2026-09-19T21:14:07.418233+00:00",
  "player": "Silas",
  "data": {
    "log_time": "16:14:07",
    "cause": "was slain by Zombie",
    "message": "Silas was slain by Zombie"
  },
  "raw": "[16:14:07] [Server thread/INFO]: Silas was slain by Zombie"
}
```

`timestamp` is when the line was ingested, in UTC. Log lines carry only a time
of day with no date, so building a full timestamp from them breaks across
midnight. The server's own reading is kept in `data.log_time` instead.

## Death detection

Vanilla death messages have no marker of their own. They are bare sentences
beginning with a player name, so they are matched against the opening phrases of
Minecraft's `death.attack.*` strings, listed in `_DEATH_PHRASES` in
[`api/events.py`](../api/events.py).

Chat is matched first and deliberately. A player can type a sentence that looks
exactly like a death message, and the `<name>` form has to win before any other
pattern is tried. A message the phrase list does not cover is simply not treated
as a death, which is the safe direction to fail. Add phrases to that tuple as
new ones appear.

## Writing a handler

```python
from api import events, rcon

def announce_death(event):
    if event.type != events.EVENT_DEATH:
        return
    rcon.get_client().command(f'tellraw @a {{"text":"RIP {event.player}","color":"red"}}')

events.get_bus().subscribe(announce_death)
```

Handlers run synchronously, in registration order, on the follower thread.
Two consequences:

- Keep them fast. Anything slow, such as an API call to a language model, should
  hand off to a queue or a background task rather than blocking the reader.
- A handler that raises is logged and skipped. One broken feature cannot silence
  the bus or stop the others.

## Storage

Events are appended to `data/events/YYYY-MM-DD.jsonl`, one JSON object per line.

Writes are buffered, flushing after 20 events or 30 seconds, whichever comes
first. The Pi boots from an SD card with finite write endurance, so a continuous
stream of one-line appends is batched rather than written per event. Files older
than 30 days are pruned automatically on the first flush of each day.

`data/` is gitignored and lives only on the Pi.

### Moving the files onto an SSD

This is the one directory the server writes to continuously, so it is the one
worth moving off the SD card when an SSD is attached. Two environment
variables, both read at import:

| Variable | Default | Effect |
| --- | --- | --- |
| `MC_EVENTS_DIR` | `data/events` under the project | Where the daily files are written. `~` is expanded |
| `MC_EVENTS_RETENTION_DAYS` | `30` | Days of history to keep. `0` or negative disables pruning |

```bash
# /etc/systemd/system/minecraft-api.service, or the API's environment
MC_EVENTS_DIR=/mnt/ssd/minecraft/events
MC_EVENTS_RETENTION_DAYS=365
```

Move the existing files first, or the history starts over:

```bash
sudo mkdir -p /mnt/ssd/minecraft/events
sudo mv data/events/*.jsonl /mnt/ssd/minecraft/events/ 2>/dev/null || true
sudo chown -R "$USER" /mnt/ssd/minecraft/events
```

The 30-day retention exists to bound what the card absorbs. Once the files are
on an SSD that reason is gone, and the history is what the Gazette and the
leaderboards read from, so raising it is the point of moving them.

A malformed `MC_EVENTS_RETENTION_DAYS` falls back to 30 rather than being read
as zero, so a typo cannot silently turn pruning off.

## REST API

Both endpoints require the `logs.view` permission.

```text
GET /api/events?limit=100&type=death&player=Silas
GET /api/events/types
```

`limit` defaults to 100 and is capped at 500. `type` must be one of the types
above; anything else returns 400 with the valid list. Events come back newest
first.

```bash
curl -H "X-API-Key: $API_KEY" "http://localhost:8080/api/events?type=death&limit=10"
```

## WebSocket

Clients already connected to the log stream also receive a `game_event` message
for every parsed event, carrying the same JSON shape as the REST endpoint.

```javascript
socket.on('game_event', (event) => {
  if (event.type === 'death') {
    console.log(`${event.player}: ${event.data.cause}`);
  }
});
```

Raw `logs` messages continue unchanged, so the existing Logs page is unaffected.

## Operational notes

- **The follower attaches with `--tail 0`, on purpose.** Every line it reads is
  persisted as an event, so replaying a backlog would record the same deaths and
  advancements again on every API restart and every re-attach, and the counts
  would climb with each one. New clients still get their scrollback: the
  WebSocket sends it separately on connect, and that path does not touch the bus.
  The trade is that events occurring while the API is down are not captured,
  which is far better than recording some of them repeatedly.
- The follower re-attaches by itself. `docker logs -f` exits when the container
  stops, and the reader waits two seconds and tries again, so a server restart
  resumes streaming without intervention.
- If Docker is not installed the reader reports it once and stops, rather than
  retrying forever.
- `stop_log_reader()` in [`api/server.py`](../api/server.py) brings the follower
  down deliberately. It kills the `docker logs` process to break the blocking
  read, because a quiet server would otherwise leave the reader parked in it.
- Buffered events are also flushed on a timer, so the last few on a quiet server
  are not left in memory waiting for the next one.

## Related

- [`api/events.py`](../api/events.py) — the parser, bus and storage
- [`api/rcon.py`](../api/rcon.py) — how handlers talk back to the server
- [RCON.md](RCON.md) — RCON setup
- [ROADMAP.md](ROADMAP.md) — what this is for
