# Graves

When a player dies, their dropped items are gathered into a chest at the
death spot instead of scattering across the ground, with a sign marking
whose it is. Part of the `family` datapack — see
[`DATAPACKS.md`](DATAPACKS.md) for the pipeline this ships through.
Originally roadmap item W8; see
[`ROADMAP.md`](ROADMAP.md#where-this-stands) for where it now lives among
the shipped work.

## The honor system, not a lock

**Vanilla has no per-player container lock.** A chest's `Lock` NBT tag
restricts who can open it by requiring the opener to hold an item with a
specific custom name — it has no concept of player identity. "Only the dead
player can open their grave" is therefore not something a vanilla datapack
can actually enforce, no matter how the roadmap's original wording reads.

Graves ships as an **unlocked chest with a sign asking nicely** —
"Please don't loot it." — relying on the honor system between two siblings
rather than any technical restriction. This was a deliberate call, not an
oversight: real per-player access control would need a plugin, which would
mean leaving vanilla, which the rest of this roadmap depends on staying on.

What *is* enforced is the part that doesn't need player identity: **after
24 in-game days, the grave expires.** The chest (and whatever's still in it)
and the sign are destroyed — `destroy` mode, so the contents drop loose
rather than vanishing — clearing old graves out automatically instead of
letting them accumulate forever.

## How it works

Detected the same way as [Lucky Blocks](LUCKY_BLOCKS.md): the real vanilla
stat `minecraft.custom:minecraft.deaths`, watched tick-to-tick rather than
through the event bus. This means it fires the same tick as the death —
before the brief respawn-screen delay — while the dying player's entity is
still sitting at the death position, which
`functions/tick/make_grave.mcfunction` needs.

**Placing the chest and finding it later.** A `minecraft:marker` entity is
summoned at the death spot and tagged `family_grave_marker`. It's not a
bookkeeping convenience — it *is* the only record of where that grave is.
`functions/tick/age_graves.mcfunction` (run once per in-game day, piggybacking
on the dawn-detection already built for
[Sibling Rivalry](ADVANCEMENTS.md#sibling-rivalry-how-a-night-is-detected))
finds every outstanding grave by looking for that tag, decrements its
countdown, and expires anything that reaches zero.

**Collecting the dropped items.**
`functions/tick/vacuum_grave_step.mcfunction` repeatedly finds the nearest
dropped item within 3 blocks and runs
`item replace block <pos> container.N from entity <item> contents` — the
vanilla command built for "take this entity's single held stack and put it
in this container slot." Chests need each `Items` entry to carry an explicit
slot number, and 1.20.4 has no macros to compute one dynamically from a
stored score, so which slot gets used is a **fixed 27-way branch** (one
`execute if score ... matches N run ...` per chest slot) rather than a
computed index. Verbose, but every line is obviously correct standing alone,
which was judged worth more here than a cleverer branch that's harder to
verify without a live server.

## Known limitations

- **Caps at 27 items.** A chest has 27 slots; a very full inventory's
  overflow stays on the ground. Same honest trade-off as Ten Thousand
  Blocks' curated block list — a documented simplification, not a silent
  one.
- **The sign can't say who died.** 1.20.4 has no macros to put a stored
  player name into sign text from a function — the same "no macros"
  constraint [`ADVANCEMENTS.md`](ADVANCEMENTS.md#the-five-advancements)
  describes for Neighbors' coordinates. The chest is what actually matters;
  the sign just marks the spot generically. (Contrast with the
  [Pet Cemetery](PET_CEMETERY.md), which places its signs from Python over
  RCON and *can* put a real name on them.)
- **The Hall of Deaths announcement doesn't link to the grave.** The
  original idea was a clickable coordinate in the in-game death
  announcement; `api/hall_of_deaths.py` wasn't touched to add this. A
  follow-up, not a gap in what shipped.
- **Not verified against a live server.** The item-vacuum command chain in
  particular (`item replace ... contents`, the 27-way slot branch, the
  marker-based position anchoring) was researched and reasoned through
  carefully — including confirming the exact commands against the Minecraft
  Wiki — but this environment has no way to run a real Minecraft client
  against it. This is the highest-risk-of-a-subtle-bug piece in this batch
  of features; test it for real before trusting it in an actual game night.

## Related

- [`DATAPACKS.md`](DATAPACKS.md) — the pipeline this ships through
- [`ADVANCEMENTS.md`](ADVANCEMENTS.md) — Sibling Rivalry's dawn-detection,
  reused here for grave aging
- [`PET_CEMETERY.md`](PET_CEMETERY.md) — the Python-side counterpart, which
  can put real names on its signs because it runs outside the datapack
- [`ROADMAP.md`](ROADMAP.md) — W8, the roadmap item this implements
