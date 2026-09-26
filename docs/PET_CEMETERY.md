# The Pet Cemetery

A named (tamed) pet's death gets a gentle obituary and a real gravestone,
instead of the console log line nobody reads. A Python module
(`api/pet_cemetery.py`), not a datapack feature — see
[Why not the datapack?](#why-not-the-datapack) Originally roadmap item M6;
see [`ROADMAP.md`](ROADMAP.md#where-this-stands) for where it now lives
among the shipped work.

## How it works

Vanilla logs the death of any **named** entity to the console — never
broadcast to chat, which is why nobody notices it today. The log line is
built around Java's `Entity.toString()`:

```text
Named entity EntityWolf['Biscuit'/99, uuid='...', l='ServerLevel[...]',
x=..., y=..., z=..., cpos=[...], tl=..., v=true, rR=null] died: Biscuit was
slain by Skeleton
```

`api/events.py` gains a `pet_death` event type and a regex for this
(`_PET_DEATH_RE`), matched non-greedily through the diagnostic fields
between the name and `died:` so version-to-version changes there don't
break it. The death sentence after `died:` reads exactly like a player death
sentence, so `api.epitaphs.classify_cause`/`extract_culprit` are reused
unchanged for cause classification — only the *epitaph templates* are new
(`GENTLE_EPITAPHS` in `api/pet_cemetery.py`), because
[the tone is deliberately different](#why-gentle).

`api/pet_cemetery.py` mirrors `api/hall_of_deaths.py`'s shape closely (the
same handler → worker thread → record → JSONL-append → prune pattern), but
is a separate module rather than "a section within the Hall of Deaths" as
the roadmap's original wording put it. `HallOfDeaths` and its `DeathRecord`
are built specifically around player deaths (`culprit` parsed the same way,
`leaderboard()` and `stats()` shaped for player names) and around the
comedic tone; bolting a second, gentler record type and a second tone onto
that class would have meant branching most of its methods on "is this a
player or a pet" rather than just... not sharing the class. Same reasoning
as keeping player and pet epitaph templates in separate dicts instead of
one dict with a "tone" parameter threaded through every call site.

## Why gentle

The Hall of Deaths writes player obituaries in the voice of a Victorian
newspaper, and deliberately so — deaths are the most reliably funny thing
that happens on a survival server. A kid's tamed dog dying is not that kind
of moment. `GENTLE_EPITAPHS` is a separate, understated template set, keyed
by the same cause categories `classify_cause` already produces, so the
"what happened" logic is shared but the "how it reads" is not.

## The gravestone

Placed over RCON, not from the datapack — which means, unlike
[Graves](GRAVES.md)' signs, **this one can say the pet's actual name**: a
vanilla function has no macros to put a stored string into a sign in
1.20.4, but Python already has the name as a plain string from parsing the
log line, so it can just write the command directly.

Plots are laid out in a row from a placeholder origin coordinate
(`CEMETERY_ORIGIN` in `api/pet_cemetery.py`) — same pattern as
[Neighbors](ADVANCEMENTS.md#the-five-advancements)' house coordinates: edit
it once to a real spot near the house. The next free plot is tracked in a
small state file (`data/pet_cemetery/state.json`), the same way
`scripts/command-scheduler.py` owns its own schedule file rather than
round-tripping through the game to ask.

## Why not the datapack?

Two reasons this isn't built into the `family` datapack the way
[Lucky Blocks](LUCKY_BLOCKS.md) and [Graves](GRAVES.md) are:

1. **No owner.** The vanilla log line names the pet, but never who tamed
   it — there's nothing in the event to attribute a death to a person with,
   so this doesn't try to. (An earlier draft of this doc assumed ownership
   would be on the gravestone; it isn't, for exactly this reason.)
2. **The gravestone needs the pet's real name on it**, which — as above —
   needs Python's string handling, not a macro-less vanilla function.

## Known limitations

- **The species mapping is a best guess.** `FRIENDLY_SPECIES` maps a Java
  entity class name (e.g. `EntityWolf`) to a friendly word (`dog`). Only
  `EntityBlaze` was confirmed against a real captured server log; the rest
  follow the same "Entity" + capitalized-name pattern by inference. Getting
  one wrong just shows "pet" instead of the specific species — a cosmetic
  miss, not a broken feature.
- **A pet's name containing an apostrophe may not parse cleanly.** The regex
  captures the name between single quotes; a name like `Rex's Buddy` would
  truncate at the embedded apostrophe. Low-severity and not worth the
  complexity to handle for a pet-naming edge case.

## Related

- [`GRAVES.md`](GRAVES.md) — the datapack-side counterpart for player
  deaths, and why *its* signs can't say a name
- [`HALL_OF_DEATHS.md`](HALL_OF_DEATHS.md) — the player obituary system this
  deliberately does not share a tone with
- [`ROADMAP.md`](ROADMAP.md) — M6, the roadmap item this implements
