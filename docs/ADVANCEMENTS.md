# The Family Advancement Tree

A custom datapack advancement tab — `Family` — with five advancements that
appear in the game's own advancements screen next to the vanilla ones. Built
and shipped through [the datapack pipeline](DATAPACKS.md) as its first real
content. See [`ROADMAP.md`](ROADMAP.md#p2-a-family-advancement-tree--green)
for the original idea.

The source lives at `config/datapacks/family/`. Deploy it with:

```bash
./scripts/datapack-manager.sh enable family
```

## The five advancements

| Advancement | Unlocks when | Mechanism |
| --- | --- | --- |
| **First Diamond** | You pick up a diamond | A real vanilla trigger (`minecraft:inventory_changed`) — no function needed |
| **Neighbors** | You build within 50 blocks of Dad's house | A tick function checking distance against a hardcoded coordinate |
| **Ten Thousand Blocks** | You've mined ~10,000 blocks (a curated common set, not literally every block) | A tick function summing per-block mined stats |
| **Sibling Rivalry** | You and your brother are both online at dawn, three separate in-game days | A tick function detecting the daily dawn transition |
| **Night Shift** | You're online at 9pm real time | Granted by RCON from a scheduled command, not by the datapack itself |

Four of the five are granted explicitly by a datapack function calling
`advancement grant @s only family:<name>`, using `minecraft:impossible` as
the advancement's trigger — the standard pattern for a function-driven
advancement: that trigger never fires on its own, so only the function's
explicit grant can unlock it.

This isn't a stylistic choice — it's what 1.20.4 actually allows. Two
limitations shape every mechanism above:

- **No macros.** Function macros (reading a value out of `$(...)`
  substitution) arrived in 1.20.5. On 1.20.4, a function can't be handed a
  parameter at all — anything that looks configurable (a coordinate, a
  threshold) has to be a literal written into the `.mcfunction` file.
- **No aggregate stats.** Vanilla tracks "blocks of stone mined" and "blocks
  of dirt mined" as separate counters; there's no single stat for "blocks
  mined, any type." Same story for real-world time — a function has no way
  to ask what time it actually is outside the game.

### Neighbors: edit the coordinates once

`config/datapacks/family/data/family/function/tick/check_neighbors.mcfunction`
has:

```mcfunction
execute as @a at @s if entity @s[x=100,y=64,z=100,distance=..50] run advancement grant @s only family:neighbors
```

`x=100,y=64,z=100` is a placeholder. Stand at the real house location, run
`/tp @s ~ ~ ~` or check the F3 key coordinate display, and put the real
numbers in. Re-run `enable family` (or just `/reload` if you edited the
deployed copy directly for testing) to pick up the change. `distance=..50`
against literal coordinates is a true radial check — no macro needed for
this one, since the comparison point is the one thing that has to be
hardcoded anyway.

### Ten Thousand Blocks: the curated block list

There's no vanilla way to ask "how many blocks, total, has this player
mined" — only "how many `stone` has this player mined," repeated per block.
`sum_blocks_mined.mcfunction` tracks a curated set of common blocks (stone,
deepslate, dirt, cobblestone, sand, gravel, oak log, coal ore, iron ore,
copper ore, diorite, andesite) and sums them into one scoreboard value each
tick. It's an honest approximation, not a complete count — a kid who mines
almost nothing but, say, andesite variants or nether blocks outside this
list will take longer to hit 10,000 than the number suggests. Add more
objectives to `family_blocks_mined`'s inputs (in both
`function/load/init.mcfunction` and `function/tick/sum_blocks_mined.mcfunction`)
if a particular block turns out to matter.

### Night Shift: the one that isn't pure datapack

A vanilla function has no access to the real-world clock, so "still playing
at 9pm" can't be checked from inside the datapack at all. Instead it's
granted the same way [P6 birthday/holiday events](ROADMAP.md#p6-birthdays-and-holidays--green)
are meant to be: a scheduled command, via the existing
`scripts/command-scheduler.py` / `/api/scheduler/schedules` infrastructure
(see [`API.md`](API.md)), running once a day:

```mcfunction
execute as @a run advancement grant @s only family:night_shift
```

Set this up once — either through the web panel's scheduler page, or:

```bash
curl -X POST http://localhost:5000/api/scheduler/schedules \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{
        "command": "execute as @a run advancement grant @s only family:night_shift",
        "type": "daily",
        "run_time": "21:00"
      }'
```

Nothing new was written for this — it reuses the scheduler that already
exists rather than teaching the datapack pipeline about wall-clock time.

## Sibling Rivalry: how "a night" is detected

1.20.4 functions can't be told "the day just changed" directly. Instead,
`check_sibling_rivalry.mcfunction` stores the current `time query daytime`
value into a scoreboard score every tick and watches for it crossing back
down near 0 — that's dawn. A `#counted_today` flag stops the multi-tick
window right around 0 from being counted more than once. When dawn is
detected, `count_night.mcfunction` counts how many real players are
currently online (by iterating `@a` into a scoreboard counter — a selector's
`limit=` bounds how many entities a command *acts on*, it isn't a count
test, so the count has to be built explicitly) and, if at least 2 were
online to see the night end, increments a shared `family_nights_together`
counter. The advancement is granted to `@a` every tick once that counter
reaches 3, so a sibling who logs in after the third night still gets it.

## Related

- [`DATAPACKS.md`](DATAPACKS.md) — the pipeline this datapack is built and
  deployed through
- [`ROADMAP.md`](ROADMAP.md) — P2, the roadmap item this implements
