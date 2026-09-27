# Lucky Blocks

Craft a special player head, break it, and roll a loot table: something
good, something silly, occasionally something chaotic. Part of the `family`
datapack — see [`DATAPACKS.md`](DATAPACKS.md) for the pipeline this ships
through. Originally roadmap item W7; see
[`ROADMAP.md`](ROADMAP.md#where-this-stands) for where it now lives among
the shipped work.

## Crafting one

```text
[Gold Block] [Diamond]    [Gold Block]
[Diamond]    [Redstone Block] [Diamond]
[Gold Block] [Diamond]    [Gold Block]
```

Produces one `minecraft:player_head` named "Lucky Block" — the name is what
lets `roll_lucky_block.mcfunction` tell a crafted head apart from an
unrelated one when it consumes it (see below). It isn't textured — see
[Known limitations](#known-limitations) for why.

## How it's detected

There is **no vanilla advancement trigger for "a specific block type was
mined."** (`minecraft:mine_block` does not exist, despite how it reads —
confirmed against the current advancement trigger list before building
this.) Detection instead watches the real vanilla stat
`minecraft.mined:minecraft.player_head` tick-to-tick, the same technique
[`ADVANCEMENTS.md`](ADVANCEMENTS.md) uses for Ten Thousand Blocks:
`config/datapacks/family/data/family/function/tick/check_lucky_blocks.mcfunction`.

When a player's count goes up, `function/tick/roll_lucky_block.mcfunction`
runs `/loot spawn ~ ~ ~ loot family:lucky_block` at roughly their position,
then consumes one "Lucky Block"-named head — from their inventory if
they've already picked it up (the usual case, a tick after the break), or
from the ground nearby if not. Breaking a player head also drops that same
head as an item; without consuming it, placing it back down and breaking it
again would roll again for free, forever, off a single craft.

## Known limitations

- **Fires on *any* player-head break**, not just a crafted lucky block — a
  decorative head statue would trigger it too. There's no way to tell them
  apart from a stat change alone, and position-tracking which specific head
  this was would be significantly more code for a two-kid home server where
  a stray triggered roll from a decorative head isn't really a problem.
- **No custom texture.** A "gold `?`" look needs either a custom skin
  texture (a base64 `SkullOwner` hash that would have had to be guessed and
  shipped unverified) or a custom model via a resource pack (T1/F4, which
  the roadmap already scopes separately). Both were judged not worth the
  risk of silently shipping a wrong or broken-looking head for a purely
  cosmetic win.

## The loot table

`config/datapacks/family/data/family/loot_table/lucky_block.json` — one
pool, weighted 70 (diamonds, emeralds, an enchanted sword, a golden apple, a
saddle, cake, XP bottles) to 30 (TNT as an item, rotten flesh, gunpowder, a
poisonous potato, and one troll: a `minecraft:barrier`, which can't normally
be obtained any other way in survival) for a roughly 70/30 good-to-chaotic
split. Nothing in the table can wipe a base.

## Related

- [`DATAPACKS.md`](DATAPACKS.md) — the pipeline this ships through
- [`ADVANCEMENTS.md`](ADVANCEMENTS.md) — Ten Thousand Blocks uses the same
  tick-to-tick stat-watching technique
- [`ROADMAP.md`](ROADMAP.md) — W7, the roadmap item this implements
