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
dropped item within 3 blocks and moves its stack into the chest. Getting
this right took three attempts against a real running server — the first
two looked reasonable on paper and both turned out to be wrong in ways that
only showed up by actually running them:

1. `item replace block <pos> container.N from entity <item> contents` — the
   command the Minecraft Wiki's `/item` page describes for exactly this —
   fails on this server with `Unknown slot 'contents'`. That slot name
   appears to be a later addition than 1.20.4.
2. `data modify block <pos> Items append from entity <item> Item` (no
   explicit slot) *looks* like it works for one item, but doesn't actually
   accumulate: a chest's `Items` list is re-derived from its live,
   slot-indexed inventory on every access, and an entry with no `Slot`
   field defaults to slot 0 — so a second append silently overwrites the
   first instead of adding a second entry. Confirmed reproducible, not a
   timing fluke: setting `Items[-1].Slot` in a *separate* follow-up command
   doesn't fix it either, because the same revalidation already dropped the
   previous entry the moment anything else touched the container.

The fix: build the complete entry — `id`, `Count` and `Slot` all present at
once — in a scratch NBT storage location first (`storage family:temp`,
which has no such revalidation semantics), then commit it to the chest in
one atomic `Items append from storage ...`. Chests need each `Items` entry
to carry an explicit slot number, and 1.20.4 has no macros to compute one
dynamically from a stored score, so which slot gets used is a **fixed
27-way branch** (one `execute if score ... matches N run ...` per chest
slot) rather than a computed index — verbose, but every line is obviously
correct standing alone. `vacuum_grave_step.mcfunction`'s own comments carry
this full story for the next time something here needs to change.

**The sign** hit a similar surprise: `front_text.messages[N] set value
"plain text"` silently does nothing for any index beyond the first — the
value has to be a JSON text component, `'{"text":"plain text"}'`, or it
doesn't persist at all despite the command reporting success.

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

## Verified against a real server

Every mechanic above — death detection, chest placement, the item vacuum
(multiple items, distinct slots), the sign (all three lines), and expiry
(chest and sign destroyed, contents dropped, marker removed) — was run
against a real vanilla 1.20.4 server in Docker, not just reasoned through.
That's what caught both bugs described above: neither one was visible from
reading the code, only from running it. See
[`LOCAL_TESTING.md`](LOCAL_TESTING.md) for how to stand up the same setup.

The one thing not exercised end to end is a *real player* dying —
verification used a stand-in entity (`execute as <entity> at <entity> run
function family:tick/make_grave`) rather than an actual connected client,
since this environment has no Minecraft client available. The death
*detection* (the stat-comparison in `check_deaths.mcfunction`) is unverified
against a real death for the same reason, though it reuses the exact
technique already proven for Ten Thousand Blocks.

## Related

- [`DATAPACKS.md`](DATAPACKS.md) — the pipeline this ships through
- [`ADVANCEMENTS.md`](ADVANCEMENTS.md) — Sibling Rivalry's dawn-detection,
  reused here for grave aging
- [`PET_CEMETERY.md`](PET_CEMETERY.md) — the Python-side counterpart, which
  can put real names on its signs because it runs outside the datapack
- [`ROADMAP.md`](ROADMAP.md) — W8, the roadmap item this implements
