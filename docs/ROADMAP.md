# Roadmap

The single source of truth for what is planned, in what order, and what has been
ruled out. It replaces the four documents this repo used to keep in parallel
(`TASKS.md`, `FAMILY_SERVER_ROADMAP.md`, `MINECRAFT_ENHANCEMENTS.md` and
`MINECRAFT_GAMEPLAY_ENHANCEMENTS.md`), which duplicated and contradicted each
other.

**What shipped is not described here.** That record lives in
[`../CHANGELOG.md`](../CHANGELOG.md) and in git history. The table under
[Where this stands](#where-this-stands) names the finished areas so the
unfinished work has context, and points at each area's guide; everything after
it is work that is not done.

Audience: Matt, planning what to build next on the Pi 5 server for Jonah and
Silas.

## Legend

Every item carries a feasibility rating, which is about this hardware and this
setup rather than about difficulty in general:

- **Green** — works on the Pi 5, on vanilla (1.20.4 today; see F7), with what
  is already in the repo.
- **Yellow** — works, but with a real constraint: extra RAM, extra hardware, a
  server-type change, or the work belongs on the Mac rather than the Pi.
- **Red** — don't, or not yet. These live in [Ruled out](#ruled-out).

---

## Where this stands

**v1.5.0**, released 2026-09-19.

The management product is effectively finished. Every version milestone the old
roadmap projected out to mid-2026 has already shipped, several of them years
ahead of the dates written down:

| Area | State | Guide |
| --- | --- | --- |
| Backups, retention, verification, scheduling | Done | [BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md) |
| Offsite backup (R2, S3, B2) | Done | [CLOUD_BACKUP.md](CLOUD_BACKUP.md) |
| Monitoring, TPS, metrics, Prometheus | Done | [BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md) |
| Analytics, trends, anomalies, predictions | Done | [ANALYTICS.md](ANALYTICS.md) |
| Version checking and one-command updates | Done | [UPDATE_MANAGEMENT.md](UPDATE_MANAGEMENT.md) |
| Paper / Spigot / Fabric server types | Done | [MINECRAFT_SERVER_SETUP.md](MINECRAFT_SERVER_SETUP.md) |
| Plugin and mod management | Done | [PLUGIN_MANAGEMENT.md](PLUGIN_MANAGEMENT.md), [MOD_SUPPORT.md](MOD_SUPPORT.md) |
| Multi-world management | Done | [MULTI_WORLD.md](MULTI_WORLD.md) |
| REST API, OpenAPI spec | Done | [API.md](API.md) |
| Web admin panel (21 pages) | Done | [WEB_INTERFACE.md](WEB_INTERFACE.md) |
| Auth, RBAC, OAuth, 2FA, API keys, audit log | Done | [RBAC.md](RBAC.md), [API_KEYS.md](API_KEYS.md), [OAUTH_SETUP.md](OAUTH_SETUP.md) |
| Dynamic DNS (DuckDNS, No-IP, Cloudflare) | Done | [DYNAMIC_DNS.md](DYNAMIC_DNS.md) |
| CI/CD, multi-arch images, test suites | Done | [CI_CD.md](CI_CD.md), [TESTING.md](TESTING.md) |
| Pooled RCON client | Done | [RCON.md](RCON.md) |
| Game event bus | Done | [EVENT_BUS.md](EVENT_BUS.md) |
| Hall of Deaths | Done | [HALL_OF_DEATHS.md](HALL_OF_DEATHS.md) |
| Bedtime mode | Done | [BEDTIME.md](BEDTIME.md) |
| Player statistics from the game's own files | Done | [PLAYER_STATS.md](PLAYER_STATS.md) |

So the question this roadmap answers is no longer "what else should the admin
panel do". It is: **what could this server do that no other Minecraft server
does?** The management layer is good enough, the defects that were sitting
underneath it are fixed, and what remains is the experience the kids actually
see.

---

## Build order

Roughly the next year of evenings, ordered so that each step makes the next one
cheaper. Every open item appears in exactly one row; rows are grouped by the
plumbing they share, so each row is mostly content on top of the row before.

| Order | Items | Why here |
| --- | --- | --- |
| 1 | W6 | Hours of work, immediate payoff, no new infrastructure |
| 2 | F7 | The biggest visible change for the least code — happy ghasts, trial chambers — and it must come before any datapack, because pack formats and item syntax change across it. R1 wants it too |
| 3 | W1 | First real "whoa"; proves the event bus end to end in both directions |
| 4 | F3, P2, W7, W8, M6 | The datapack pipeline, then the first packs. W8 and M6 both extend the Hall of Deaths' death handling, so build them together |
| 5 | F8, P8, P7, P3, P10 | Scoreboard, team and bossbar tooling, then the games that run on it. P10 is P3's reward track, so they ship as one |
| 6 | F6, W4, T3, M5, H5, P11, R3 | Items and delivery: F6 builds items and queues them for the next join, and everything else in the row hands a player something. R3's weekly digest is the Gazette's parent edition |
| 7 | M2, M1, M7, T6 | Spectacle from data that already exists: map and time-lapse rendered on the Mac, statues from the `advancement` event, the server list from the stats |
| 8 | W2, P9, P4, M4, P1, P5, P6 | Content on the pipelines above. W2 once the datapack validator can be trusted; P9 and P4 share a template-world reset and both feed M4's Museum; P1 and P5 are datapack content; P6 is scheduler content |
| 9 | H1, H2, H3 | House and game wired to each other |
| 10 | R1 | Geyser — but see the gate below |
| 11 | F4, T1, M3, H4, T4, T2, T5, T7 | The big projects: new hardware, Mac-side rendering or a resource pack. F4 comes first in this row: T1 serves its pack through it |

**One decision gate: do the boys play on iPads?** If yes, R1 moves to order 3,
straight after F7. Cross-play changes when and where they can play at all,
which outranks anything else here, and Geyser tracks current Java releases, so
it needs F7 first regardless.

---

## Foundations

Plumbing that several features below depend on. Three are done and described in
[EVENT_BUS.md](EVENT_BUS.md), [RCON.md](RCON.md) and
[PLAYER_STATS.md](PLAYER_STATS.md) rather than repeated here.

### F7. Catch up to current Minecraft — Yellow, and decide it early

The server defaults to **1.20.4**, which is now a long way behind the game the
boys see on YouTube. Everything added since is missing from their world:

- **Trial chambers, the breeze and the mace** (1.21) — a new dungeon type built
  for exactly this age, with a weapon whose whole point is falling on things.
- **Bundles** (1.21.2) and **the Pale Garden with the creaking** (1.21.4).
- **The happy ghast** (1.21.6) — a giant friendly ghast you can put a harness
  on and fly with four players riding it. On its own this is a reason to
  upgrade.
- **Copper golems** (1.21.9) that sort chests for you.

It matters for this roadmap as much as for the game. 1.20.5 moved items to
components, 1.21 made **enchantments data-driven**, and 1.21.4 lets a datapack
point any item at a custom model. Together they turn W2 (the Invention Forge)
from "a recipe that renames a vanilla item" into genuinely new items with new
enchantments, and T1's textures stop needing the CustomModelData workaround.
The Java side is already done: the image runs Temurin 25.

Yellow because upgrading a world is one-way. The procedure:

1. Take a verified backup and push it offsite.
2. Boot a copy of that backup on the new version on the Mac first (the same
   trick as M4's rewind), walk around, check the bases.
3. Bump `MINECRAFT_VERSION`, pre-generate a ring around spawn so the new
   biomes and structures exist where they will actually be found, and upgrade.

Do it **before F3**, and before R1. Datapacks carry a `pack_format` that changes almost every
release, and item syntax changed at 1.20.5, so every datapack and every F6 book
written against 1.20.4 would need rewriting afterwards. Pick the newest release
that has been out a couple of weeks when the work starts, not whatever is
named here.

### F3. A datapack pipeline — Green

Datapacks are the cheat code for this whole document. They are plain JSON in
`data/<world>/datapacks/`, they work on **vanilla**, they hot-reload with
`/reload`, and they give you custom advancements, recipes, loot tables,
predicates and functions without a single plugin.

Build `scripts/datapack-manager.sh` with `create`, `list`, `enable`, `disable`,
`validate` and `reload`, plus the matching endpoints:

- `GET /api/datapacks` — list
- `POST /api/datapacks/install` — install from URL or file
- `PUT /api/datapacks/<name>/enable` / `disable`
- `DELETE /api/datapacks/<name>`

Keep the family datapack in git so every change is revertible. F3 unblocks P1,
P2, P5, P7, P8, W2, W7, W8, T7 and most of T1.

### F8. Scoreboards, teams and bossbars — Green

Six features run a game with a score, a side or a timer: co-op goals (P3),
Raid Night (P5), Manhunt (P7), the Arcade (P8), Build Battles (P9) and the
expanding world (P10). Build one module for objectives, sidebar display, teams
(colours, prefixes, friendly fire), bossbars and titles, with endpoints the
dashboard can drive, before the second of those games rather than after the
fifth.

Bedtime mode already drives a bossbar, so factor that code out rather than
writing a second. Titles are partly covered by
`scripts/announcement-manager.sh`; extend it rather than replace it. This
replaces the scoreboard, team, bossbar and title rows the management backlog
used to carry.

### F6. Items and delivery — Green, build it with W4

Six features hand a player something: the Gazette book (W4), mail (T3), the
time capsule (M5), chore pay (H5), bounty rewards (P11) and anything the
Oracle (W1) awards. All of them need two things, and should share both.

**Building the item.** `/give` with the contents attached, and **1.20.5
replaced item NBT with components**, so the syntax differs by server version:

```text
1.20.4   /give @p written_book{title:"...",author:"...",pages:['...']}
1.20.5+  /give @p written_book[written_book_content={title:"...",author:"...",pages:['...']}]
```

If F7 has landed, only the second form is needed and version detection can be
skipped. If it hasn't, detect the version rather than assuming it.

**Delivering it.** The recipient is usually offline when the item is created —
a Sunday-morning Gazette, a letter from Mom, a chore paid during school. Keep
a small persistent queue per player and drain it on the `join` event, with a
title and a sound so arriving mail feels like an event. A full inventory
leaves the item queued rather than dropping it on the floor.

**Build it as the first commit of W4, not before.** Nothing constructs items
today, so a module written now would be guessing at what the callers need,
and would be wrong in the way abstractions written without a caller usually
are. The constraint is recorded here so W4 starts with it rather than
discovering it.

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

### W1. The Oracle — a Claude-powered companion in chat — Green

Kids type in chat, something answers. The event bus catches `chat`, the API
calls the Claude API, the reply goes back via `tellraw` with coloured JSON text.

Use `claude-haiku-4-5` for banter (fast and cheap) and `claude-sonnet-5` for
anything that generates structure, like quests. Round trip lands around 2–4
seconds, which reads as "the wizard is thinking" rather than as lag.

**Do not call the model from the handler.** `EventBus.publish()` runs every
handler synchronously, in registration order, on the log follower thread
(`api/events.py:347`). A 2–4 second round trip inline would stall the bus for
that long on every message, and with it the Hall of Deaths, bedtime enforcement
and anything else subscribed. Push the chat event onto a queue and answer from a
worker, the way `api/hall_of_deaths.py` already announces from a worker thread.

Give it a personality and a job: it knows the server's history from the event
log, it remembers what each kid was building last week, it posts a daily
quest to P11's bounty board rather than keeping a quest system of its own, it
answers "how do I make a beacon" without either of them alt-tabbing to
a wiki.

**Guardrails, because this is aimed at children.** Pin a system prompt that
scopes it to Minecraft and kid-appropriate content, allowlist the player names
that may invoke it, rate limit per player per minute, cap output tokens so a
reply always fits a chat line, log every exchange through the existing
`log_audit_event()`, and put a kill switch on the dashboard.

The epitaph writer in `api/epitaphs.py` already defines the interface a
language-model-backed writer plugs into; W1 is the first real implementation of
it.

### W2. The Invention Forge — describe an item, the server creates it — Yellow

The one nobody else has. A kid types:

```text
!invent a pickaxe that leaves a trail of flowers
```

Claude generates the datapack JSON — an advancement, a recipe, a loot table, a
function — the API validates it against a strict schema, writes it into
`data/<world>/datapacks/family/`, runs `/reload`, and **the item exists in the
game seconds later.**

Yellow rather than Green because of the validator, and it is worth doing
properly: generated `function` files can contain arbitrary commands, so run
every generated command through an allowlist before it ever touches the disk.
`api/security.py` already has `ALLOWED_MINECRAFT_COMMANDS` and
`BLOCKED_COMMAND_PREFIXES` for exactly this shape of problem — extend that
pattern. Keep the family datapack in git so a bad generation is one `git revert`
away, and add `/undo-invention` to disable the last pack and reload.

A ten-year-old inventing a working item by describing it is the single most
"knock your socks off" thing on this list.

### W4. The Family Gazette — Green

A weekly newspaper, auto-generated every Sunday morning: player stats, the
funniest deaths of the week, whose base grew the most, who mined the most
diamonds, what is coming up next week, a picture of the map.

Delivered two ways — as an HTML page on the dashboard, and **in game as an
actual written book** placed in each player's inventory via `/give` with book
NBT. Receiving a physical newspaper in your inventory on a Sunday is a ritual.

Reads its numbers from [PLAYER_STATS.md](PLAYER_STATS.md) and its obituaries
from the Hall of Deaths, which already stores
the week's obituaries. Start with F6: the book writer is where item
construction is invented, and T3 and M5 both inherit it.

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

### W7. Lucky blocks — Green

The single most requested thing on any server kids run. A special block —
a player head with a gold "?" texture needs no resource pack at all — and
breaking it rolls a loot table: a diamond sword, a stack of cake, a pig
wearing a saddle, a lightning strike, an anvil falling from the sky, a
charged creeper named "Oops".

Pure datapack: a `minecraft.mined:minecraft.player_head` scoreboard stat
catches the break, a tick function finds the dropped head by its custom data
and swaps it for a roll of a weighted random loot table. Tune the
table so the good outcomes win about 70% of the time and the funny ones cover
most of the rest; nothing should wipe a base. Give it a crafting recipe so
lucky blocks are earned rather than spawned, and add a **Lucky Block Race**
to the P8 arcade.

Outcomes can be written by the boys themselves from a dashboard form, which
turns it into a thing they designed rather than a thing they downloaded.

### W8. Graves — Green

Losing a whole inventory to lava is the fastest way to end an evening in
tears. `keepInventory` fixes that but removes all tension; graves are the
middle ground. When a player dies, their items go into a grave marker at the
spot, only they can open it, and the Hall of Deaths announcement gains a
clickable line with the coordinates.

A datapack does this on vanilla. The event bus already knows about every
death, and the log line lacks coordinates, but
`data get entity <player> LastDeathLocation` over RCON supplies them, so the
API side is small: store the location alongside the obituary. Worth deciding
up front: after 30 real minutes the grave opens to everyone (so a sibling can
rescue it), and after a day the items drop normally. The epitaph from
`api/epitaphs.py` can go on a sign above the grave.

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
`Offers` NBT (or components after F7). Put the rare stuff — a mending book,
a saddle, the cool armour trim templates — behind that shop, so real-world
effort buys real in-game value.

Two details make it work. Payment must survive the player being offline, so
it goes through F6's delivery queue, the same one T3's mail uses.
And a parent approves each payment on the dashboard rather than it firing
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

### M6. The pet cemetery — Green

Kids grieve dogs. Vanilla logs the death of any **named** entity —
`Named entity Wolf['Biscuit'/…] died: Biscuit was slain by Skeleton` — so a
tamed wolf, cat, parrot or horse with a name tag already produces a log line
nobody reads.

Add a `pet_death` type to the event bus's parser, give it an obituary in the
Hall of Deaths with its own section, and build a small cemetery in game: each
pet gets a gravestone sign with the name, owner, date and epitaph. Announce it
gently rather than with the comedy tone the player obituaries use. This will
matter more to them than it looks like it should.

### M7. The Hall of Champions — Green

Statues at spawn. When someone earns a milestone advancement — kills the Ender
Dragon, beats the Wither, finds an ancient city — the API builds a statue: an
armour stand wearing that player's head (`player_head` with their name), the
armour they were wearing, holding the weapon they used, posed mid-swing, on a
plinth with a plaque.

The `advancement` event already carries everything needed. The statue spot
comes from a list of plinth coordinates the API fills in order. After a year,
spawn is a gallery of everything they have done, with their own faces on it.

---

## Tier 4 — Structured play

### P1. Treasure hunts — Green

Claude writes a chain of riddle clues. A script picks real coordinates, places a
loot chest at each, and delivers the first clue as a book. Each clue's answer is
the next location. Difficulty tuned per kid.

### P2. A family advancement tree — Green

A custom datapack advancement tab with its own icon, appearing in the real
advancements screen alongside the vanilla ones:

- "Sibling Rivalry" — survive three nights with your brother
- "Neighbors" — build within 50 blocks of Dad's house
- "First Diamond"
- "Ten Thousand Blocks"
- "Night Shift" — play past 9pm (they will find this hilarious)

Vanilla triggers cover most of it; location checks need a tick function. Because
it appears in the game's own UI it reads as official rather than bolted on.

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
trigger at health thresholds, and loot worth the fight. Scheduled for Friday
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
tower with checkpoints. Each is a command-block or datapack build with a
scoreboard timer.

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
through a no-login link with a one-time code that can do nothing but vote. The winner's build goes to the
Museum (M4) and on the front page of the Gazette.

### P10. The expanding world — Green

Start a new world with a small world border, say 500 blocks. It grows only
when the family hits co-op goals (P3): every thousand blocks mined together,
every boss beaten, every village saved. The border animates outwards with an
announcement and a firework show at spawn, and everyone rushes to see what
was just revealed.

It turns the whole world into a progression system with a single vanilla
command. Promotes the world border manager in the backlog from P3 to P2.

### P11. The bounty board — Green

Parents post challenges from the dashboard: "mine 64 iron", "tame a horse",
"reach the End", "build a bridge over the river". Each shows up in game on a
physical board at spawn and as a `/trigger bounties` list.

Most complete themselves — the stats files from
[PLAYER_STATS.md](PLAYER_STATS.md) and the `advancement` event already answer
"did he mine 64 iron" and "did he reach the End" — and pay out automatically,
in emeralds for H5's shop or a custom item, through F6's delivery queue.
Build challenges get a parent "approve" button. W1's daily quests post here
too, so there is one list of things to do rather than two. Lighter than the Oracle's daily quests, fully under parental
control, and needs no model at all.

---

## Tier 5 — Make it theirs

### T1. A resource pack the kids made — Yellow, enormous payoff

Record a sound on an iPad and it becomes a music disc they can play on a jukebox
in the game. Draw a 16×16 sprite in a web pixel editor on the dashboard and it
becomes an item texture via CustomModelData. The pack auto-builds, uploads to R2
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
The server icon manager in the backlog is half of it already. Minutes of work
once written, and it makes the server feel alive before they have even
joined.

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

## Tier 6 — Reach

### R1. Geyser and Floodgate for cross-play — Yellow

Let them join from an iPad, a phone or a Switch. Run Geyser standalone as a
separate container proxying into the vanilla server.

Cost is an additional JVM, roughly 300–500MB: Yellow on an 8GB Pi, Red on a 4GB
one. Tablets and phones connect easily; a Switch needs DNS redirection to work
at all.

**If the kids have iPads this may be the highest-value item in the entire
document,** because it changes when and where they can play. Weigh it against
everything above.

### R3. Push notifications and a weekly digest — Green

"Silas just got his first diamond." Event bus plus ntfy, Pushover or APNs. Cheap,
and it keeps the adults connected to what is happening without hovering.
The weekly digest is the Gazette (W4) rendered for parents, so build it from
the same data rather than as a second report.

---

## Management and tooling backlog

Smaller, well-understood pieces of the management product. None of them are
blocking anything; pick them up when one is in the way.

### Minecraft configuration

| Item | Priority | Notes |
| --- | --- | --- |
| Gamerule manager | P2 | `scripts/gamerule-manager.sh` plus `GET`/`PUT /api/gamerules/<rule>`; get, set, list, presets, validation |
| Entity management | P2 | Mob caps, tracking range, density; `GET /api/entities/stats`, `POST /api/entities/optimize` |
| Chunk management | P2 | Pre-generation for performance, loading radius, chunk stats and cleanup |
| World border manager | P2 | Centre, size, damage, knockback, animated changes; needed by P10 (the expanding world) |
| Spawn protection manager | P3 | Radius and behaviour |
| Server icon manager | P2 | Set from file, generate from image, validate 64×64 PNG; half of T6 |
| Structure generation control | P3 | Enable/disable structures, spawn rates, custom templates |

### Scoreboards and teams

Moved to [F8](#f8-scoreboards-teams-and-bossbars--green): six games on this
roadmap depend on it, so it is a foundation rather than backlog.

### Player and automation

| Item | Priority | Notes |
| --- | --- | --- |
| Advancement manager | P2 | List, grant, revoke, track progress; pairs with P2 (family tree) |
| Command chain manager | P2 | Named, reusable command sequences with variables and conditional branching |
| Player note system | P2 | Admin notes on a player, categorised and timestamped |
| Player teleport history | P2 | Saved locations, back/return, teleport requests |
| Automated world maintenance | P2 | Entity cleanup, chunk optimisation, lag-spike detection, backup before maintenance |
| Server event manager | P2 | Scheduled tournaments and contests with registration and reward distribution. Overlaps P4, P5 and P9 — build those first and generalise if a pattern emerges |
| Weather and time scheduling | P3 | Superseded in spirit by H3; build only the parts H3 doesn't cover |
| Recipe and loot table managers | P3 | Mostly free once F3 exists |

### Economy and rewards — P3, plugin-dependent

Balance checks, payments, transaction history and reward packages all require an
economy plugin (EssentialsX, Vault). That means leaving vanilla, which most of
this roadmap depends on. Revisit only if the server moves to Paper for another
reason.

---

## Infrastructure and technical debt

- **Web UI pages for what already exists.** The API has endpoints with no page:
  events, announcements, gamerules once they land. Check `api/openapi.yaml`
  against `web/src/pages/` before adding anything new.
- **Test coverage gaps.** Tracked in [TESTING.md](TESTING.md); close them
  alongside the feature that touches the gap, not as a separate project.
- **`api/server.py` is very large.** The recent features (`rcon.py`,
  `events.py`, `hall_of_deaths.py`, `bedtime.py`) each moved out cleanly. Keep
  doing that: new features get their own module, and blocks of `server.py`
  follow when they are touched anyway.
- **Architecture diagrams.** One diagram of log → event bus → feature handlers →
  RCON would save more explaining than any amount of prose.

---

## Ruled out

Recorded so they don't get proposed again. These were on earlier roadmaps.

| Item | Why not |
| --- | --- |
| Multi-server orchestration, clustering, load balancing | One Pi, two players. There is no second server to orchestrate |
| Kubernetes, Docker Swarm, HA, auto-scaling, multi-region | Same. Docker Compose is the right size for this |
| Enterprise auth (LDAP), compliance, SLA reporting | No enterprise |
| Intrusion detection, automated threat response, pen-testing tooling | [SECURITY_HARDENING.md](SECURITY_HARDENING.md) plus a LAN-only API is proportionate. Fix the blockers above instead |
| Marketplace, plugin/world sharing platform, community ratings | This is a family server, not a product with a community |
| Plugin SDK, GraphQL API, client SDKs for Python/Node/Go | The REST API and its OpenAPI spec are enough |
| Mobile app (iOS/Android) | W6 (Shortcuts and widgets) gets 90% of the value for 2% of the work |
| Discord, Slack and Telegram bots | R3 (push notifications) covers the actual need |
| Video tutorials, multi-language docs | Cancelled previously; nothing has changed |
| Simple Voice Chat | Needs Fabric or Paper plus a client mod for every player. Two brothers in the same house can shout |
| WASM plugins, GPU world generation, ML chunk optimisation | No |
| Blockchain world ownership, quantum optimisation, VR/AR | No |

---

## Keeping this current

- One roadmap. When something ships, delete its entry here and describe it in
  [`../CHANGELOG.md`](../CHANGELOG.md) — don't leave a checked box behind.
  Restating completed work in two places is what made the previous four
  documents disagree with each other.
- New ideas go in the tier they belong to with a feasibility rating, not at the
  end.
- Anything decided against goes in [Ruled out](#ruled-out) with a reason, rather
  than being silently deleted.
- No dates. The old roadmap's quarterly targets were wrong in both directions —
  work shipped a year early and a year late — and they made the document look
  stale faster than anything else in it.
