# Player Statistics

Minecraft keeps a complete set of per-player counters itself. This reads them
rather than reconstructing them.

## Where the numbers come from

| File | What it holds |
| --- | --- |
| `<world>/stats/<uuid>.json` | Every counter the game tracks: blocks mined by type, distance travelled, damage taken and dealt, time played, deaths, kills |
| `<world>/advancements/<uuid>.json` | Which advancements are complete |
| `usercache.json` | UUID to player name |

The world is `data/<level-name>`, with `level-name` read from
`data/server.properties`. `MC_WORLD_DIR` overrides the whole path for a server
whose files live elsewhere.

## Why not parse the log

`scripts/player-stats-tracker.sh` used to scrape the server log with three
regular expressions and **add** what it found to the previous totals. The same
unchanged log therefore reported different numbers each time it ran:

```text
run 1: Jonah login_count=1
run 2: Jonah login_count=2
run 3: Jonah login_count=3
```

Jonah joined once. A restart replayed the whole file, and the death pattern
matched the literal word `etc`.

Reading the game's own counters cannot drift, because there is nothing to
accumulate: the number in the file is the answer. It is also far more complete —
the log knows about joins, leaves and deaths, while the stats file knows how
many diamonds were mined and how far each player has walked.

## What is exposed

| Field | Derived from |
| --- | --- |
| `play_time_minutes` | `minecraft:play_time` ticks, at 20 per second, floored to whole minutes. Falls back to `play_one_minute`, the pre-1.17 name |
| `deaths`, `mob_kills`, `player_kills` | the matching `minecraft:custom` counters |
| `blocks_mined` | `minecraft:mined`, summed across every block type |
| `items_crafted` | `minecraft:crafted`, summed |
| `damage_taken`, `damage_dealt` | the counters, in tenths of a heart, converted to hearts and kept to one decimal — half a heart matters to a player who has three |
| `jumps` | `minecraft:jump` |
| `distance_walked_m` | `minecraft:walk_one_cm`, converted to metres |
| `advancements` | completed advancements, **excluding** `minecraft:recipes/...` — those are how recipes unlock, not achievements, and counting them makes the number meaningless |

The complete stats block is available with `?raw=true` for anything not
summarised above.

## Endpoints

All require the `players.view` permission.

- `GET /api/players/stats` — every player with a statistics file
- `GET /api/players/stats/<player>` — one player, by name; `?raw=true` adds the full block
- `GET /api/players/stats/leaderboard?metric=<m>&limit=<n>` — ranked, highest first; `limit` is clamped to 1-50
- `GET /api/players/stats/metrics` — the counters a leaderboard can use

`POST /api/players/stats/parse` is gone. It ran the log scrape, and there is no
collection step any more.

The metric names the old tracker invented (`login_count`, `blocks_broken`,
`play_time`) still resolve, onto the real counter nearest to what they meant, so
an existing caller gets a true answer rather than an empty leaderboard.

## Notes

- These files are written by a running server, so a read can land mid-write. An
  unreadable file is skipped rather than raising, and one bad file does not stop
  the rest being listed.
- A player who has never joined has no file and is reported as not found, which
  is different from a player with a file full of zeroes.
- Nothing here writes. Reading statistics does not touch the game's files, and a
  test asserts their modification times are unchanged.

## Related

- [EVENT_BUS.md](EVENT_BUS.md) — events for the things the game does not count
- [HALL_OF_DEATHS.md](HALL_OF_DEATHS.md) — death history, with epitaphs
