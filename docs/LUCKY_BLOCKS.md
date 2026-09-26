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

Produces one plain `minecraft:player_head`. It isn't named or textured —
see [Known limitations](#known-limitations) for why.

## How it's detected

There is **no vanilla advancement trigger for "a specific block type was
mined."** (`minecraft:mine_block` does not exist, despite how it reads —
confirmed against the current advancement trigger list before building
this.) Detection instead watches the real vanilla stat
`minecraft.mined:minecraft.player_head` tick-to-tick, the same technique
[`ADVANCEMENTS.md`](ADVANCEMENTS.md) uses for Ten Thousand Blocks:
`config/datapacks/family/data/family/functions/tick/check_lucky_blocks.mcfunction`.

When a player's count goes up, `functions/tick/roll_lucky_block.mcfunction`
runs `/loot spawn ~ ~ ~ loot family:lucky_block` at roughly their position.

## Known limitations

- **Fires on *any* player-head break**, not just a crafted lucky block — a
  decorative head statue would trigger it too. There's no way to tell them
  apart from a stat change alone, and position-tracking which specific head
  this was would be significantly more code for a two-kid home server where
  a stray triggered roll from a decorative head isn't really a problem.
- **No custom name or texture.** A "gold `?`" look needs either a custom
  skin texture (a base64 `SkullOwner` hash that would have had to be guessed
  and shipped unverified) or a custom model via a resource pack (T1/F4,
  which the roadmap already scopes separately). Both were judged not worth
  the risk of silently shipping a wrong or broken-looking head for a purely
  cosmetic win.

## The loot table

`config/datapacks/family/data/family/loot_tables/lucky_block.json` — one
pool, weighted roughly 70% good outcomes (diamonds, emeralds, an enchanted
sword, a golden apple, a saddle, cake, XP bottles) and 30% funny/chaotic but
non-destructive ones (TNT as an item, rotten flesh, gunpowder, a poisonous
potato, and one troll: a `minecraft:barrier`, which can't normally be
obtained any other way in survival). Nothing in the table can wipe a base.

## Related

- [`DATAPACKS.md`](DATAPACKS.md) — the pipeline this ships through
- [`ADVANCEMENTS.md`](ADVANCEMENTS.md) — Ten Thousand Blocks uses the same
  tick-to-tick stat-watching technique
- [`ROADMAP.md`](ROADMAP.md) — W7, the roadmap item this implements
