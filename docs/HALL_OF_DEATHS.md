# Hall of Deaths

Every death on the server gets an obituary. It is announced in game to everyone
online and kept on a dashboard page with a leaderboard.

This is the first feature built on the [event bus](EVENT_BUS.md), and it is
deliberately a complete vertical slice: an event arrives, something visible
happens in the game, and a record survives for later. Anything else that reacts
to play follows the same shape.

## What it looks like

A death happens. Moments later, in chat:

```
Here lies Jonah, who met Zombie and did not come to an arrangement.
```

```
Silas lost an argument with foliage and did not take it well.
```

```
Jonah went out with a bang, as they had always quietly hoped to.
```

The dashboard page at `/deaths` shows the same lines with totals, the most
common way to die, and a leaderboard of who has died most and how they usually
manage it.

## How it works

1. `api/events.py` parses a death line from the server log into a `death` event.
2. `HallOfDeaths.handle_event` in [`api/hall_of_deaths.py`](../api/hall_of_deaths.py)
   picks it up from the bus.
3. [`api/epitaphs.py`](../api/epitaphs.py) classifies the cause and writes a line.
4. The record is persisted, then announced with `tellraw`.

Persisting happens before announcing on purpose. Announcing needs the game
server to be reachable, and a death is worth keeping even when the announcement
cannot be delivered. A record carries `announced` so you can tell the difference.

## Epitaphs

Deaths are classified into categories, each with several lines so the same death
does not read the same way twice in an evening. The categories are `combat`,
`explosion`, `lava`, `fire`, `fall`, `void`, `drowning`, `starvation`,
`dehydration`, `freezing`, `lightning`, `crushing`, `spikes`, `prickly`,
`magic`, `sonic`, `kinetic` and `unknown`.

Order of matching matters. `was blown up by Creeper` is an explosion, not a mob
kill, and `walked into a cactus while trying to escape Creeper` is a cactus
death even though it names a mob. Both are covered by tests.

Where the message names a culprit, it is extracted and used: `was slain by Silas
using Netherite Sword` yields `Silas`. The weapon is dropped, because the lines
read better naming the culprit alone.

Selection is seeded by player, cause and timestamp, so a given death always
produces the same epitaph while different deaths vary.

### Writing epitaphs some other way

`write_epitaph()` takes an optional writer. Anything with a `write(death) -> str`
method works:

```python
from api.epitaphs import Death, write_epitaph

class MyWriter:
    def write(self, death):
        return f"{death.player} is no longer with us."

write_epitaph(Death(player="Jonah", cause="drowned"), MyWriter())
```

The default is `TemplateEpitaphWriter`, which runs offline, costs nothing,
returns instantly and needs no API key. That is the right default for a server
running on a Pi in a family's house.

A writer backed by a language model is the obvious upgrade and slots in here
without anything else moving. It would need an API key, a per-death cost, a
timeout that does not stall the event bus thread, and the kid-safety guardrails
described under W1 in [FAMILY_SERVER_ROADMAP.md](FAMILY_SERVER_ROADMAP.md).
Handlers run synchronously on the follower thread, so a network call belongs on
a queue rather than inline.

## Configuration

Copy `config/deaths.conf.example` to `config/deaths.conf`. The real file is
gitignored.

| Setting | Default | Meaning |
| --- | --- | --- |
| `ANNOUNCE_IN_GAME` | `true` | Announce each epitaph with `tellraw`. Set false to keep the Hall dashboard-only. |
| `ANNOUNCE_COLOR` | `gray` | Any Minecraft colour name. |
| `RETENTION_DAYS` | `365` | How long to keep records. `0` disables pruning. |

Records are stored in `data/deaths/YYYY-MM-DD.jsonl`, which is gitignored and
lives only on the Pi. They are written immediately rather than batched like log
events, because deaths are rare and losing a good epitaph to a crash would be a
worse trade than a few extra writes.

## REST API

Both endpoints require the `players.view` permission.

```
GET /api/deaths?limit=50&player=Silas&category=fall
GET /api/deaths/leaderboard?limit=10
```

`limit` on `/api/deaths` defaults to 50 and is capped at 200. Deaths come back
newest first, alongside a `stats` object with the totals.

Leaderboard entries carry `favourite_cause_count` as well as `favourite_cause`,
because a favourite only means something once it has happened more than once.
Three deaths in three different ways have no mode, and saying "mostly drowning"
on the strength of a single drowning is a small lie. The dashboard checks the
count and falls back to `last_category` when there is no real pattern.

```bash
curl -H "X-API-Key: $API_KEY" "http://localhost:8080/api/deaths?limit=5"
```

## Notes

- **A player typing a fake death message in chat does not create an entry.** The
  event bus matches chat before any other pattern, so `<Silas> Jonah was slain by
  Zombie` stays chat. There is a test for exactly this.
- **Announcement text is JSON-encoded, not interpolated**, so an epitaph
  containing a quote cannot break the command or inject extra components.
- **Long lines are truncated deliberately**, because the server would otherwise
  truncate them silently.

## Related

- [EVENT_BUS.md](EVENT_BUS.md) — where death events come from
- [FAMILY_SERVER_ROADMAP.md](FAMILY_SERVER_ROADMAP.md) — W3, and what comes next
