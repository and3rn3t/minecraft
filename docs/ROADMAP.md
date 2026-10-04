# Roadmap

The single source of truth for what is planned, in what order, and what has been
ruled out. **What shipped is not described here.** That record lives in [`../CHANGELOG.md`](../CHANGELOG.md) and in git history, and the guides are indexed in [INDEX.md](INDEX.md). Maintenance work lives in
[TECH_DEBT.md](TECH_DEBT.md).

Audience: Matt, planning what to build next on the Pi 5 server for Jonah and Silas.

## Legend

Every item carries a feasibility rating, which is about this hardware and this setup rather than about difficulty in general:

- **Green** — works on the Pi 5, on vanilla (26.3 today), with what is already in the repo. Datapack work stays Green on Paper too.
- **Yellow** — works, but with a real constraint: extra RAM, extra hardware, a server-type change (plugins mean Paper, mods mean Fabric), or the work belongs on the Mac rather than the Pi.
- **Red** — don't, or not yet. These live in [Ruled out](#ruled-out).

---

## Where this stands

**v1.6.0**, released 2026-09-28. The management product is finished: backups, monitoring, the API and admin panel, auth, plugin, mod and world management, and the move to Minecraft 26.3. So is the first layer of family content: the datapack pipeline and its advancement tree, Lucky Blocks, Graves, the Pet Cemetery, the Hall of Deaths, Bedtime mode and the Oracle.

The question this roadmap answers is no longer "what else should the admin panel do". It is: **what could this server do that no other Minecraft server does?** What remains is the experience the kids actually see, once the [Pi checklist](#pi-checklist) is closed.

## Next up

1. Close the [Pi checklist](#pi-checklist). A backup that has never been restored or uploaded offsite is a hope.
2. **W6** (Siri and Shortcuts) and **I1** (Hearthstone, Tether, Whistle): hours of work, no new infrastructure.
3. **B2** (boss levels and scaling) on datapacks, alongside P5. F9 is decided: vanilla, so B1 waits.

## Build order

Roughly the next year of evenings, ordered so that each step makes the next one cheaper. Every open item except O1 and D1 appears in exactly one row; rows are grouped by the plumbing they share, so each row is mostly content on top of the row before.

| Order | Items | Why here |
| --- | --- | --- |
| 0 | Pi checklist | The Pi's backups have never been confirmed offsite or restored. Nothing below matters if the world is lost |
| 1 | W6, I1 | Hours of work, immediate payoff, no new infrastructure. I1 is three hand-built items, and doubles as the prototype for W2 |
| 2 | F8, F9, P8, P7, P3, P10 | Scoreboard, team and bossbar tooling, then the games that run on it. P10 is P3's reward track, so they ship as one. F9 is a decision, now made (stay vanilla), and stays here only so its revisit condition is not lost |
| 3 | F6, W4, T3, M5, R3, O6 | Delivery: F6 builds items and queues them for the next join, and everything else in the row hands a player something. O6 switches the scheduler back on as M5's first step. R3's weekly digest is the Gazette's parent edition |
| 4 | H5, P11, I2, I3, I4 | Rewards, paid out through row 3's queue. I2–I4 stock H5's trader and P11's prizes, so emeralds have something to buy |
| 5 | M2, M1, M7, T6 | Spectacle from data that already exists: map and time-lapse rendered on the Mac, statues from the `advancement` event, the server list from the stats |
| 6 | W2, P9, P4, M4, P1, P5, B2, B1, P6, I5 | Content on the pipelines above. W2 once the datapack validator can be trusted; P9 and P4 share a template-world reset and both feed M4's Museum; P1, P5 and I5 are datapack content; B2 (scaling) ships with P5, and B1 (MythicMobs) only once F9 is revisited and moves to Paper; P6 is scheduler content |
| 7 | H1, H2, H3 | House and game wired to each other |
| 8 | F4, T1, M3, H4, T4, T2, T5, T7 | The big projects: new hardware, Mac-side rendering or a resource pack. F4 comes first in this row: T1 serves its pack through it |

O1 is deferred until the player list settles (see its entry). D1 is blocked on
upstream. The small management pieces in
[Standalone management pieces](#standalone-management-pieces) have no row; take
one when it is in the way.

---

## Operations and reliability

### Pi checklist

All of this is built and shipped; what is left runs on the Pi, not in the repo.
Delete each line when it is done.

- [ ] **Backups.** Confirm the timer's first runs (`systemctl list-timers`,
      `logs/backup-scheduler.log`; a "Skipping backup" line means the time
      check is in the way). Set `AUTO_UPLOAD="true"` in
      `config/cloud-backup-r2.conf` (or s3/b2) and confirm an object lands
      (`cloud-backup-r2.sh list`). Until then every backup sits on the same SD
      card as the world.
- [ ] **Secrets.** Install `age`, generate a keypair with the private key kept
      off the Pi, and set `AGE_RECIPIENT` in `config/backup-secrets.conf`
      ([CLOUD_BACKUP.md](CLOUD_BACKUP.md#secrets-backup)). Find the path of the
      `minecraft-api.service` override that sets `ALLOWED_ORIGINS`
      (`systemctl cat minecraft-api.service`) and add it to `backup-secrets.sh`,
      which does not cover it yet.
- [ ] **One real restore.** Download a real backup from the Pi, run
      `manage.sh restore` against it and join with
      [LOCAL_TESTING.md](LOCAL_TESTING.md#restoring-a-real-backup)'s local
      server.
- [ ] **Notifications.** Set `NTFY_URL` in `config/notify.conf`, then force each
      failure path once (backup, unhealthy container, deploy refusal) and
      confirm exactly one notification fires, not a flood.

### O1. Close the game server to strangers — Green, deferred

**Deferred (2026-09-28).** The server is new, and which of the boys' friends
will join isn't known yet, so the whitelist stays off until that list
settles. The risk below still stands while it is open.

`server.properties` on the Pi has `white-list=false` and
`enforce-whitelist=false`, and `mine.andernet.dev` reaches the server from
anywhere through the playit.gg tunnel ([PLAYIT.md](PLAYIT.md)). Anyone with a
Java account and the address can join and talk to the kids.
`online-mode=true` only means they need a real account, not an invitation.

Add every account first — the boys and each friend who plays — with
`whitelist add <name>` over RCON (the admin panel's Console page), then
`whitelist on` and set `enforce-whitelist=true` so anyone already connected
who isn't on the list gets kicked. Adding the accounts first is the part that matters: a whitelist
switched on empty locks the kids out. A new friend then needs a
`whitelist add` before their first visit, which is what W6's Shortcuts or a
dashboard button should make a one-tap job for a parent. Don't use
`scripts/whitelist-manager.sh` for this yet: its RCON call is a stub, so it
only edits `whitelist.json`, which the running server doesn't reread.

### O6. Re-check what the scheduler is for — Green

`minecraft-scheduler.timer` is disabled on the Pi, so
`scripts/command-scheduler.py` runs nothing. That is harmless today, but P6
(birthdays and holidays) and M5 (the time capsule) are both written as
scheduler content. Enable it as the first step of whichever of those ships
first, after reviewing what schedules are already configured, rather than
switching on a timer that fires every minute with unknown contents.

---

## Foundations

Plumbing that several features below depend on.

### F8. Scoreboards, teams and bossbars — Green

Six features run a game with a score, a side or a timer: co-op goals (P3),
Raid Night (P5), Manhunt (P7), the Arcade (P8), Build Battles (P9) and the
expanding world (P10). Build one module for objectives, sidebar display, teams
(colours, prefixes, friendly fire), bossbars and titles, with endpoints the
dashboard can drive, before the second of those games rather than after the
fifth.

Bedtime mode already drives a bossbar, so factor that code out rather than
writing a second. Titles are partly covered by
`scripts/announcement-manager.sh`; extend it rather than replace it.

### F9. Paper or vanilla — decided: stay vanilla, revisit for B1 — Yellow

The server runs `SERVER_TYPE=vanilla` on 26.3. Plugins such as MythicMobs
(B1) only load on Paper, so this is the gate for everything plugin-shaped.
Paper is already supported by `scripts/switch-server-type.sh` and
`SERVER_TYPE=paper`, so the switch itself is small; the cost is elsewhere.

**What Paper keeps.** Datapacks, the event bus's log matching, RCON and the
backup and restore paths all work unchanged, so nearly every item on this
roadmap stays Green. Paper is also faster than vanilla on a Pi.

**What it costs.**

- **Version lag.** Paper and each plugin follow Minecraft's releases late. A
  plugin that lists 26.2 is not a promise about 26.3. Check the plugin's own
  page for the exact version *before* switching, and expect to hold the
  Minecraft version back when a plugin is behind.
- **RAM.** Plugins add heap on a box already capped by `MEMORY_MAX`. Measure
  with the Pi's own metrics ([BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md)),
  not by estimate, before adding a second large plugin.
- **Behaviour differences** the kids can notice: Paper changes some redstone,
  mob-spawn and item-despawn defaults. Test with a world copy first, using
  [LOCAL_TESTING.md](LOCAL_TESTING.md).
- **Chat and log formats.** Re-verify the event bus patterns against a live
  Paper server, as was needed after the 26.3 upgrade; vanilla's log lines are
  not guaranteed to match.

**Decision: stay on vanilla 26.3.** B2 gets most of what MythicMobs would give,
works today, and keeps the server as the lowest-maintenance version of itself.
The newest MythicMobs build found listed 26.2, so moving now would mean either
holding Minecraft back or waiting on the plugin, for a benefit B2 mostly
delivers anyway.

**Revisit when** B2 has run for a while and its limits show (hand-written phase
and ability functions getting unwieldy, or a boss design that needs skills a
datapack can't express) **and** MythicMobs lists the exact Minecraft version in
use. Then: take a backup, switch on a copy of the world, run the event-bus and
datapack checks, and switch the Pi last. Until then `SERVER_TYPE` stays
`vanilla`.

### F6. Items and delivery — Green, build it with W4

Every feature that hands a player something shares this: the Gazette book (W4),
mail (T3), the time capsule (M5), chore pay (H5), bounty rewards (P11) and
whatever the Oracle ([ORACLE.md](ORACLE.md)) awards. Those items refer back
here instead of repeating it.

**Building the item.** `/give` with the contents attached as components, not
the NBT tags older guides still show (1.20.5 replaced item NBT, and the server
is on 26.3):

```text
/give @p written_book[written_book_content={title:"...",author:"...",pages:['...']}]
```

**Delivering it.** The recipient is usually offline when the item is created.
Keep a small persistent queue per player and drain it on the `join` event, with
a title and a sound so arriving mail feels like an event. A full inventory
leaves the item queued rather than dropping it on the floor. The queue is also
the record of what was paid out.

**Build it as the first commit of W4, not before.** Nothing constructs items
today, so a module written now would be guessing at what its callers need.

### F4. Resource pack hosting — Green

Set `resource-pack=` and `resource-pack-sha1=` in `server.properties` and host
the zip from Cloudflare R2, which is already wired up for backups in
`scripts/cloud-backup-r2.sh`. Clients download it on join. This unlocks custom
sounds, custom music discs, custom item textures and custom fonts, again on
vanilla.

Wants `scripts/resource-pack-manager.sh` (set URL, upload, compute hash,
enable/disable) and `GET`/`POST`/`DELETE /api/resourcepack`.

---

## Tier 1 — Highest wow per hour

### W2. The Invention Forge — describe an item, the server creates it — Yellow

The one nobody else has. A kid types:

```text
!invent a pickaxe that leaves a trail of flowers
```

Claude generates the datapack JSON — an advancement, a recipe, a loot table, a
function — the API validates it against a strict schema, writes it into
`data/<world>/datapacks/family/`, runs `/reload`, and **the item exists in the
game seconds later.**

The 26.3 upgrade already unlocked what this needs: items moved to components
at 1.20.5, enchantments became data-driven at 1.21, and a datapack can point
any item at a custom model since 1.21.4. Together they turn this from "a
recipe that renames a vanilla item" into genuinely new items with new
enchantments, and T1's textures stop needing the CustomModelData workaround.

Yellow rather than Green because of the validator, and it is worth doing
properly: generated `function` files can contain arbitrary commands, so run
every generated command through an allowlist before it ever touches the disk.
`api/security.py` already has `ALLOWED_MINECRAFT_COMMANDS` and
`BLOCKED_COMMAND_PREFIXES` for exactly this shape of problem — extend that
pattern. Keep the family datapack in git so a bad generation is one `git revert`
away, and add `/undo-invention` to disable the last pack and reload. The
recipe and loot-table managers fall out of the same pipeline
([DATAPACKS.md](DATAPACKS.md)) rather than needing their own.

A ten-year-old inventing a working item by describing it is the single most
"knock your socks off" thing on this list.

### W4. The Family Gazette — Green

A weekly newspaper, auto-generated every Sunday morning: player stats, the
funniest deaths of the week, whose base grew the most, who mined the most
diamonds, what is coming up next week, a picture of the map.

Delivered two ways — as an HTML page on the dashboard, and **in game as an
actual written book** placed in each player's inventory through
[F6](#f6-items-and-delivery--green-build-it-with-w4). Receiving a physical
newspaper in your inventory on a Sunday is a ritual.

Reads its numbers from [PLAYER_STATS.md](PLAYER_STATS.md) and its obituaries
from the Hall of Deaths, which already stores the week's obituaries. Start with
F6: the book writer is where item construction is invented, and T3 and M5 both
inherit it.

### W6. Siri, Shortcuts and HomeKit — Green

The cheapest big win in the document. The API already exists, already takes an
`X-API-Key` header, and already has start, stop, status and player endpoints. An
iOS Shortcut that makes an HTTP request is all that stands between you and:

- "Hey Siri, start Minecraft."
- "Hey Siri, is Jonah online?"
- "Hey Siri, Minecraft bedtime." — `POST /api/bedtime/now` already does this.
- A Home Screen widget showing who is online.

Almost no new server code: ship a documented Shortcuts bundle and a few
convenience endpoints. Hours of work, not days. The `homekit-automator` repo can
take it further and expose the server as a real HomeKit accessory.

**Give the Shortcut its own narrowly scoped key.** Keys carry a role now, so a
Shortcut that starts the server and reads status wants `server.control` and
`server.view` and nothing else — not the `admin` role, and not a key shared with
the dashboard.

---

## Tier 2 — The house and the game talk to each other

Genuinely rare, and rare only because most people don't run their server on a Pi
in their own house with a smart-home stack next to it.

### H1. Minecraft controls the real house — Green

A lever in the game turns on the real lamp in the bedroom.

Simplest implementation: a sign or command block in game runs a chat command the
event bus recognises, the API fires a webhook at `homehub` or HomeKit, the light
changes. A cleaner version uses a datapack tick function writing to a scoreboard
the API polls.

Build a small control-panel room in the world: one lever per light, a button for
the kitchen speaker, a redstone lamp mirroring whether the front door is locked.
For a kid this crosses a line they didn't know could be crossed.

### H2. The Control Room — Green

The inverse. An in-game room whose signs and scoreboard sidebar show real-world
data, refreshed by RCON once a minute: house temperature, tomorrow's forecast
(from the `weather-app` repo), chores due today (from the `family` repo), the
server's own TPS and the Pi's CPU temperature, both already collected by
`scripts/analytics-collector.sh`.

### H3. Real-world sync — Green, with a caveat

- Real local weather drives in-game weather.
- Real sunrise and sunset drive in-game time.
- Real moon phase matches the in-game moon.
- A meteor shower tonight — the `sky` and `telescope` repos know — means an
  automatic firework show at the real peak time.

Weather and time scheduling beyond this belong here too, not in a separate
manager.

**Caveat:** hard-syncing time breaks sleeping in beds and scrambles mob-spawn
expectations, which kids notice fast. Make it a per-world toggle, sync on a slow
cadence, and consider syncing weather and moon only. The meteor-shower fireworks
are the best part anyway and carry no downside.

### H4. Status hardware on the Pi — Yellow

Physical presence for an invisible thing:

- An LED strip whose colour is server health, that pulses when someone joins,
  and whose brightness follows in-game day and night.
- A small e-ink panel on the shelf showing who is online.
- A big arcade button that starts the server.

**Two Pi 5 specific gotchas, because both will waste an evening otherwise.** The
Pi 5 moved GPIO behind the RP1 I/O controller, so `RPi.GPIO` does not work — use
`gpiozero` with the `lgpio` pin factory. And the classic `rpi_ws281x` NeoPixel
driver relies on PWM/DMA behaviour the Pi 5 doesn't provide, so drive
addressable pixels over SPI or hang them off a cheap microcontroller over USB.
E-ink over SPI is fine.

This is also the repo's one completely untouched area: nothing here drives
anything physical today.

### H5. Chores for emeralds — Green

The `family` repo already knows which chores are done. When a parent ticks one
off, the player gets paid in game: emeralds to spend at a family trader
villager at spawn, whose offers are set with `/summon villager` and custom
`Offers` entity data. Put the rare stuff — a mending book,
a saddle, the cool armour trim templates — behind that shop, so real-world
effort buys real in-game value. The items in [Tier 5](#tier-5--things-worth-owning)
are its top shelf: things that exist only on this server.

Two details make it work. Payment goes through F6's delivery queue, so it
survives the player being offline. And a parent approves each payment on the dashboard rather than it firing
automatically, so it stays a reward and never becomes something to negotiate
with a script.

---

## Tier 3 — Memory and spectacle

### M1. Build time-lapse — Green, on the Mac

Render the same region from each nightly backup, stitch the frames with ffmpeg.
"Watch your base grow over a year" in ninety seconds. Run it on the Mac against
`backups/` — there is no reason to spend the Pi's thermal budget on rendering,
and the backups are already there.

### M2. A 3D web map — Yellow on the Pi, Green on the Mac

BlueMap gives a genuinely beautiful browsable 3D map. The initial full render of
a mature world is CPU-hours and will run the Pi hot.

The sharp version: run BlueMap's standalone CLI **on the Mac** against last
night's backup, publish the static output to Cloudflare Pages or R2, and link it
from the dashboard. Free hosting, no server load, updates every morning, works
against a vanilla world directory with no plugin required.

### M3. 3D-print your build — Green, and a showstopper

Select a region, export it with Mineways or jmc2obj on the Mac, convert to STL,
hand it to the `Printer` repo and the Anycubic.

A child holding a physical model of the house they built in Minecraft is an
all-timer. A weekend project with an enormous payoff, connecting two repos you
already maintain.

### M4. World rewind and the Museum — Yellow / Green

**Rewind:** boot a backup from any date as a second, read-only server on port
25566 and walk around the past. Two JVMs on an 8GB Pi is tight and on a 4GB Pi
it won't fit, so run the rewind instance on the Mac and have the dashboard hand
out the connection address.

**Museum:** a permanent showcase world where the best builds get copied in with
structure blocks, each with a sign giving the builder and the date. Green, and
`scripts/world-manager.sh` already has `create-template` and `from-template` to
build on.

### M5. The Time Capsule — Green

Write a book in game, seal it in the capsule, and the server delivers it back to
you on a real date a year from now.

No datapack needed: store the book's contents as JSON and schedule the `/give`
through the existing command scheduler. Technically the smallest item in this
document, and probably the one that matters most in five years.

### M7. The Hall of Champions — Green

Statues at spawn. When someone earns a milestone advancement — kills the Ender
Dragon, beats the Wither, finds an ancient city — the API builds a statue: an
armour stand wearing that player's head (`player_head` with their name), the
armour they were wearing, holding the weapon they used, posed mid-swing, on a
plinth with a plaque.

The `advancement` event says who and what, but not what they were wearing
or holding: it carries only the player and the advancement name. The handler
has to capture the rest itself, over RCON, as soon as the event arrives —
`data get entity <player> Inventory` for the armour slots and
`SelectedItem` for the weapon (1.21.5 moved player armour into an
`equipment` compound, and the server is now on 26.3 — check the exact field
names live rather than assuming either the 1.20.4 or 1.21.5 shape still
applies) — before they change gear. The statue spot comes from a list of plinth
coordinates the API fills in order. After a year,
spawn is a gallery of everything they have done, with their own faces on it.

---

## Tier 4 — Structured play

### P1. Treasure hunts — Green

Claude writes a chain of riddle clues. A script picks real coordinates, places a
loot chest at each, and delivers the first clue as a book. Each clue's answer is
the next location. Difficulty tuned per kid.

### P3. Sibling co-op goals — Green

Shared, server-wide objectives on a scoreboard that only complete if both
brothers contribute. Completing one unlocks a reward for both. Escalate toward
real-world prizes: finish the tier, get pizza night. Cooperation with a payout
beats competition for siblings.

Runs on F8. P10 is its reward track: build the two together.

### P4. The Expedition World — Green

Every week a temporary world from a template: skyblock, parkour, hardcore, the
floor is lava, a Claude-generated challenge. Results go in the Gazette, the best
build gets copied into the Museum, then the world resets.

`scripts/world-manager.sh` already supports templates, so this is mostly
scheduling and ceremony.

### P5. Raid Night — Green

Scripted boss encounters via datapack functions: a summoned mob with custom
attributes, equipment and a name, a bossbar tracking its health, phases that
trigger at health thresholds, and loot worth the fight. Difficulty scaling is
[B2](#b2-boss-levels-and-scaling--green-datapack); [B1](#b1-mythicmobs-bosses-and-mobs--yellow-deferred-by-f9)
is the plugin route, deferred until F9 is revisited. Scheduled for Friday
evenings and announced in the Gazette all week.

### P6. Birthdays and holidays — Green

Automatic firework shows, cake, custom titles and themed loot on birthdays and
holidays. `scripts/command-scheduler.py` already handles date-based scheduling,
so this is content, not engineering.

### P7. Manhunt — Dad versus the boys — Green

The format they already watch on YouTube: one speedrunner tries to beat the
Ender Dragon, the hunters chase them with a compass that always points at
their target. Here it is two brothers against Dad, or Dad as the runner and
both of them hunting.

A datapack gives each hunter a lodestone compass whose target a tick function
updates to the runner's position every second; the dashboard picks the teams,
resets a fresh world from a template and runs the timer. Results go in the
Gazette. Runs on F8, and the reset is P4's template-world machinery.

### P8. The Arcade — Green

A permanent minigame hub, next to spawn rather than in a temporary world: a
boat race with lap timers, spleef, TNT run, an elytra ring course, a parkour
tower with checkpoints, a **Lucky Block Race** (see
[`docs/LUCKY_BLOCKS.md`](LUCKY_BLOCKS.md) for the block itself, already
shipped). Each is a command-block or datapack build with a scoreboard timer.

The admin-portal half is what makes it last: every run is recorded, the
dashboard keeps a **records board** per game with each kid's personal best,
and a new record gets a server-wide title and a line in the Gazette. Beating
your brother's lap time by 0.4 seconds is a reason to play for weeks.

### P9. Build Battles with family voting — Green

Every Saturday a theme — from a list or from the Oracle: "a treehouse", "a
volcano lair", "the Pi's home as a castle". Each builder gets an identical
plot, a timer on the bossbar, and creative mode inside the plot boundary.

When time is up the dashboard shows a screenshot or map render of each plot
and **the grown-ups vote from their phones** — Mom and grandparents included,
through a no-login link with a one-time code that can do nothing but vote.
Scheduled contests with sign-up and prizes (P4, P5, P9) are the case for a
generic event manager; build those three first and generalise only if a
pattern emerges. The winner's build goes to the
Museum (M4) and on the front page of the Gazette.

### P10. The expanding world — Green

Start a new world with a small world border, say 500 blocks. It grows only
when the family hits co-op goals (P3): every thousand blocks mined together,
every boss beaten, every village saved. The border animates outwards with an
announcement and a firework show at spawn, and everyone rushes to see what
was just revealed.

It turns the whole world into a progression system with a single vanilla
command. Its dashboard half is a world border manager (centre, size, damage,
knockback, animated changes); build that first, as a small module of its own.

### P11. The bounty board — Green

Parents post challenges from the dashboard: "mine 64 iron", "tame a horse",
"reach the End", "build a bridge over the river". Each shows up in game on a
physical board at spawn and as a `/trigger bounties` list.

Most complete themselves — the stats files from
[PLAYER_STATS.md](PLAYER_STATS.md) and the `advancement` event already answer
"did he mine 64 iron" and "did he reach the End" — and pay out automatically,
in emeralds for H5's shop or a custom item, through F6's delivery queue.
Build challenges get a parent "approve" button. The board itself is fully
under parental control and needs no model at all.

The Oracle ([ORACLE.md](ORACLE.md), shipped) already generates quests
on request and persists them to `data/oracle/quests.jsonl` — there is
nowhere else for them to go yet. Once this board exists, it should read from
that file rather than the Oracle keeping its own separate list, so there is
one list of things to do rather than two.

---

## Tier 4b — Bosses, levels and dungeons

Raid Night (P5) is the event; this tier is what makes its fights worth
repeating. Two ways to build it: B2 on plain datapacks, which works today, and
B1 on MythicMobs, which needs Paper and so waits on F9's revisit condition. They are not rivals.
B2's design (what scales with what) carries over to B1 unchanged.

### B2. Boss levels and scaling — Green, datapack

A boss that is fair for one ten-year-old and one adult is neither. Tune it from
what is actually in the world when it spawns:

- **By players present.** On spawn, a function counts the players within range
  and applies attribute modifiers to the boss (`max_health`, `attack_damage`,
  `armor`), then sets its health to the new maximum. One kid gets a boss they
  can beat; three people get a harder one.
- **By tier.** Bosses come in levels (1 to 5 is plenty) held in a scoreboard
  objective and shown in the name and bossbar (F8). Level comes from the
  family's progress, e.g. advancements from the family tree
  ([ADVANCEMENTS.md](ADVANCEMENTS.md)) or P10's border size, so the same Friday
  boss gets tougher as they do, and loot improves with the level.
- **Safety rails for this audience.** A damage cap per hit, a hard `Difficulty`
  floor and ceiling per boss, no environment kills, and the graves system
  ([GRAVES.md](GRAVES.md)) so a loss costs time, not a build. Each fight also
  takes a parent-set maximum level on the dashboard.

Attribute names and the modifier format changed across 1.21.x releases, so
confirm them against 26.3 before writing the functions (the same warning as
[Tier 5](#tier-5--things-worth-owning)). The dashboard half is a levels table
and a "next raid" level override through F8's endpoints.

### B1. MythicMobs bosses and mobs — Yellow, deferred by F9

[MythicMobs](https://www.spigotmc.org/resources/5702/) defines custom mobs,
skills, phases and drops in YAML, with built-in level modifiers. It replaces
the hand-written phase and ability functions P5 would otherwise need with
config files you can keep in git. Use it for:

- P5's bosses: phases at health thresholds, summons, telegraphed attacks.
- Scaling by level and by distance from spawn, so B2's design is a config
  rather than functions.
- Drops that feed I4's cards, with a unique drop per boss.

**Before starting.**

- Confirm the plugin lists the exact Minecraft version the Pi runs. It listed
  26.2 as the newest when this was written; 26.3 was unconfirmed.
- Check the free version covers it. Free is reported to cover most needs; the
  premium build adds a few features (check which of them the bosses need).
- **Budget the Pi.** Cap concurrent custom mobs and keep skill ticking light.
  A boss fight that drops TPS below ~15 on the Pi is a failed design, and
  `analytics-collector.sh` already records TPS to prove it.
- Plugin configs live in `plugins/`, so add them to the backups, and add the
  API's plugin management ([PLUGIN_MANAGEMENT.md](PLUGIN_MANAGEMENT.md)) to
  the install path rather than hand-copying jars.

### D1. When Dungeons Arise — Red for now, blocked upstream

Not workable today. When Dungeons Arise is a **mod** (Fabric, Forge or
NeoForge), not a plugin, and as of this writing it supports up to 1.21.1 while
the server is on 26.3. It also cannot run beside MythicMobs: that needs Paper,
this needs a mod loader. The server can be one or the other.

Revisit only if WDA publishes a build for the Minecraft version in use. Until
then, I5 (family dungeons) covers "structures worth exploring" with
datapack structures, which work on vanilla and on Paper. To get WDA's feel
sooner, evaluate a worldgen **datapack** that adds dungeons and check that it
supports 26.x before trusting it, running it through
[DATAPACKS.md](DATAPACKS.md)'s validator. Moving the server to Fabric to run
WDA would also mean holding Minecraft back to 1.21.1 and giving up the whole
26.3 upgrade, which is not worth it.

---

## Tier 5 — Things worth owning

Everything above is an event or a system: a game on Friday, a board at spawn, a
grave when you die. What is missing is the ordinary Tuesday — nothing in a
kid's inventory exists only on this server. The family datapack's one custom
item is the Lucky Block recipe, and W2 is the only other plan for items.

These items also give the reward track a purpose. H5, P11, P3 and the lucky
blocks all hand out emeralds and prizes, but H5's trader only stocks vanilla
items, so there is little worth saving for. The items below are its top shelf.

All of them are vanilla datapack work. The common trick for "right-click to do
something" is an item with the `consumable` component plus an advancement on
the `consume_item` trigger that runs a function and revokes itself. Confirm the
component names against 26.3 before building: several changed between 1.21.x
releases.

### I1. Hearthstone, Sibling Tether and Pet Whistle — Green

Three items built the same way, so they ship together:

- **Hearthstone** — use it to return to your bed or spawn, with a long
  `use_cooldown`. Getting lost far from home is the most likely real
  complaint, and this answers it.
- **Sibling Tether** — one charge, teleports you to your brother. It is the
  item most likely to push the two of them into co-op play, and the one worth
  doing chores for.
- **Pet Whistle** — teleports every pet you own to you. The Pet Cemetery
  ([PET_CEMETERY.md](PET_CEMETERY.md)) shows the pets matter; lost dogs are how
  they usually end up there.

Build these by hand before W2. Three hand-made items show what the Invention
Forge's validator actually has to allow, which is W2's open question.

### I2. Leaf Cape — Green

A chestplate with the `glider` component: weak, slow flight long before an
elytra. Elytra come at the very end of the game, so this gives the kids flight
months earlier. Sold by H5's trader or paid out as a bounty prize.

### I3. The Magnet enchantment — Green

Enchantments have been data-driven since 1.21. A custom enchantment with a
`tick` effect that runs a function can pull nearby dropped items towards the
wearer. It is the prize at the top of H5's shop, and the first real test of
custom enchantments before W2 starts generating them.

### I4. Collectible cards — Green

A set of named trophy items with lore and, once F4 exists, their own textures
via `item_model`: one per mob type, biome, family in-joke or boss. They drop
rarely from lucky blocks, P5's bosses and P11's bounties, and go in item frames
at home. Having something to collect keeps kids playing between events. A
complete set earns a place in the Hall of Champions (M7), and the dashboard
can show each kid's progress.

Unique boss drops belong here too: P5's "loot worth the fight" should include
at least one card or item you can get nowhere else.

### I5. Family dungeons in the world — Green

Custom worldgen structures from the datapack: small ruins, towers or vaults,
built once in a creative world, saved with structure blocks, and scattered
across new chunks with loot tables written for this server. P1's treasure hunts
reward turning up on a certain day; these reward wandering around on any day.
P10's expanding border shows them off well: every time it grows, there is new
ground to explore.

Needs a new world or unexplored chunks to appear in, so pair it with P10's
fresh world or push the border outwards. Enabling, disabling and re-spacing
vanilla structures is the same datapack work. This is also the working answer to
[D1](#d1-when-dungeons-arise--red-for-now-blocked-upstream) until upstream
catches up.

---

## Tier 6 — Make it theirs

### T1. A resource pack the kids made — Yellow, enormous payoff

Record a sound on an iPad and it becomes a music disc they can play on a jukebox
in the game. Draw a 16×16 sprite in a web pixel editor on the dashboard and it
becomes an item texture via the `item_model` component (1.21.4+, no
CustomModelData workaround needed). The pack auto-builds, uploads to R2
and serves through F4.

Real effort, but the result is their drawings and their voices inside Minecraft.

### T2. Pixel-art uploader — Yellow, Green with one trick

Upload a PNG, get it built in blocks in game. The naive approach of one
`setblock` per pixel is far too slow: a 128×128 image is 16,384 commands.

Two ways to fix it. Run-length encode each row into `/fill` commands, which
typically cuts the command count by 10–50× on real images. Or generate an `.nbt`
structure file directly and place it with a structure block, which is one
command total. Cap the input at 128×128 either way.

### T3. Mail — Green

Send a letter from the dashboard, or from a phone, and it arrives as a written
book in the player's inventory. A note from Mom waiting for you when you log in.
Trivial once the Gazette's book builder exists.

### T4. NFC portal cards — Yellow

A PN532 reader on the Pi, or the tooling already in the `amiibo` and `flipper`
repos. Tap a physical card and the game responds: teleport to a saved location,
switch worlds, grant a kit, trigger an event.

Physical objects that do things in a video game is a category of magic that
lands extremely well at this age.

### T5. Real photos on the walls — Yellow

Upload a family photo on the dashboard and it appears in game as map art in
item frames: the dog on the wall of their base, a holiday snapshot in the
Museum. Resize to a grid of 128×128 tiles, quantise each tile to the map
colour palette with dithering, write each as a `map_<n>.dat`, then `/give`
the filled maps.

Yellow because the server holds the map counter in memory: write map files
only while the server is stopped (the nightly backup window works), or claim
IDs by having RCON create blank maps first and overwrite those files. Cheaper
than T2's pixel art in blocks and much prettier, but fixed to the size of an
item frame wall.

### T6. The server list talks — Green

The first thing they see is the multiplayer screen, and it can say something.
Regenerate `motd` and `server-icon.png` on every restart: "Silas is 3
diamonds ahead", "7 days since anyone fell in lava", "Build Battle tomorrow:
volcano lair", with the icon swapped for a holiday version or the latest
champion's face.

Both are read only at startup, so this rides the existing restart schedule.
The icon half is a small manager: set from a file or generate from an image,
and validate a 64×64 PNG. Minutes of work once written, and it makes the server
feel alive before they have even joined.

### T7. Design-a-world — Yellow

Datapacks can define world generation: taller mountains, floating islands,
oceans of lava, a world that is all mushroom fields. Give the dashboard a
page of friendly sliders and presets — "how tall are mountains", "how much
ocean", "which biomes" — that writes a worldgen datapack, then hands it to
`scripts/world-manager.sh` to create the world.

Yellow for the Pi: exotic terrain is expensive to generate, so pre-generate a
modest area on the Mac, copy it across and cap the world border (P10 fits
naturally). The result is a world whose shape they chose, which is a
different feeling from any seed.

---

## Tier 7 — Reach

### R3. Push notifications and a weekly digest — Green

"Silas just got his first diamond." Event bus plus ntfy, Pushover or APNs. Cheap,
and it keeps the adults connected to what is happening without hovering.
The weekly digest is the Gazette (W4) rendered for parents, so build it from
the same data rather than as a second report.

---

---

## Standalone management pieces

Small, well-understood pieces of the management product that nothing on the
roadmap depends on. Pick one up when it is in the way.

| Item | Notes |
| --- | --- |
| Gamerule manager | `scripts/gamerule-manager.sh` plus `GET`/`PUT /api/gamerules/<rule>`: get, set, list, presets, validation |
| Entity management | Mob caps, tracking range, density; `GET /api/entities/stats`. Gives B1 its concurrent-mob budget |
| Chunk management | Pre-generation, loading radius, chunk stats and cleanup |
| Automated world maintenance | Entity cleanup, lag-spike detection, a backup before maintenance |
| Advancement manager | List, grant, revoke, track progress; pairs with [ADVANCEMENTS.md](ADVANCEMENTS.md), and makes B2's level tiers testable |
| Command chain manager | Named, reusable command sequences with variables and conditional branches |
| Player teleport history | Saved locations, back/return, teleport requests |
| Player notes | Admin notes on a player, categorised and timestamped |
| Spawn protection manager | Radius and behaviour |
| Web UI pages for what exists | The API has endpoints with no page (events, announcements). Check `api/openapi.yaml` against `web/src/pages/` before adding anything |

Folded into the items they serve: the world border manager into P10, the server
icon manager into T6, structure generation control into I5, weather and time
scheduling into H3, the recipe and loot table managers into W2, and the server
event manager into P9. Scoreboards and teams are F8.

---

## Ruled out

Recorded so they don't get proposed again. These were on earlier roadmaps.

| Item | Why not |
| --- | --- |
| Multi-server orchestration, clustering, load balancing | One Pi, two players. There is no second server to orchestrate |
| Kubernetes, Docker Swarm, HA, auto-scaling, multi-region | Same. Docker Compose is the right size for this |
| Enterprise auth (LDAP), compliance, SLA reporting | No enterprise |
| Intrusion detection, automated threat response, pen-testing tooling | The admin panel is public through Cloudflare Tunnel, not LAN-only, so the proportionate answer is Cloudflare's own controls (Access in front of the tunnel, WAF rate limits) plus [SECURITY_HARDENING.md](SECURITY_HARDENING.md) — not running a security stack on the Pi |
| Marketplace, plugin/world sharing platform, community ratings | This is a family server, not a product with a community |
| Plugin SDK, GraphQL API, client SDKs for Python/Node/Go | The REST API and its OpenAPI spec are enough |
| Mobile app (iOS/Android) | W6 (Shortcuts and widgets) gets 90% of the value for 2% of the work |
| Discord, Slack and Telegram bots | R3 (push notifications) covers the actual need |
| Video tutorials, multi-language docs | Cancelled previously; nothing has changed |
| Geyser and Floodgate cross-play (was R1) | Everyone who plays, the boys and their friends, is on a PC with Java Edition. It would cost a second JVM (300–500MB) for players who don't exist. Revisit if a tablet, phone or console player turns up |
| Simple Voice Chat | Needs Fabric or Paper plus a client mod for every player. Two brothers in the same house can shout |
| When Dungeons Arise (as a mod) | Supports up to 1.21.1; the server is on 26.3, and a mod loader excludes Paper plugins such as MythicMobs. Tracked as [D1](#d1-when-dungeons-arise--red-for-now-blocked-upstream) with a revisit condition. I5 covers the need meanwhile |
| Plugin economy (EssentialsX, Vault) | Emeralds, H5's trader and F6's queue already are the economy, and a balance and `/pay` add nothing for two kids. Revisit only if F9 chooses Paper for another reason |
| WASM plugins, GPU world generation, ML chunk optimisation | No |
| Blockchain world ownership, quantum optimisation, VR/AR | No |

---

## Keeping this current

- One roadmap. When something ships, delete its entry here and describe it in
  [`../CHANGELOG.md`](../CHANGELOG.md) — don't leave a checked box behind.
- New ideas go in the tier they belong to with a feasibility rating, not at the
  end.
- IDs are never reused. The gaps in the numbering (O2–O5, O7, W1, P2, M6, R1, R2
  and so on) are items that shipped or were ruled out; renumbering would break
  links in the changelog and in commit messages.
- Anything decided against goes in [Ruled out](#ruled-out) with a reason, rather
  than being silently deleted.
- No dates. The old roadmap's quarterly targets were wrong in both directions —
  work shipped a year early and a year late — and they made the document look
  stale faster than anything else in it.
