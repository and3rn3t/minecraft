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

- **Green** — works on the Pi 5, on vanilla 1.20.4, with what is already in the repo.
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

So the question this roadmap answers is no longer "what else should the admin
panel do". It is: **what could this server do that no other Minecraft server
does?** The management layer is good enough; the remaining work is the
experience the kids actually see, plus the handful of real defects sitting
underneath it.

---

## Blockers

These are defects, not features, and they sit in the path of everything below.
Line numbers were verified against the current `main`, and each tracked one
links to its issue.

- **`scripts/player-stats-tracker.sh` inflates its counts on every run**
  ([#28](https://github.com/and3rn3t/minecraft/issues/28)). It re-parses the
  whole log file and adds to the existing totals, so the numbers climb whether
  or not anything happened, and it only matches three crude patterns.
  Superseded by F5 below.
- **1.20.4 → 1.20.5 replaces item NBT with components.** Every `/give` carrying
  NBT in this document — the Gazette book, mail, the time capsule — breaks on
  that upgrade. Isolate item construction in one module before building three
  features on top of it.
- **SD-card write endurance.** The event bus appends JSONL continuously. Writes
  are already batched and pruned at 30 days; if an SSD is present, move
  `data/events/` onto it.

---

## Build order

Roughly the next year of evenings, ordered so that each step makes the next one
cheaper.

| Order | Items | Why here |
| --- | --- | --- |
| 1 | Blockers | What is left of them; the auth defects that gated W6 are fixed |
| 2 | W6, F5 | Days of work each, immediate payoff, no new infrastructure |
| 3 | W1 | First real "whoa"; proves the event bus end to end in both directions |
| 4 | F3, P2 | Datapack pipeline plus family advancements, visible in the game's own UI |
| 5 | M2, M1 | Map and time-lapse, rendered on the Mac, zero cost to the Pi |
| 6 | W4, T3, M5 | The book pipeline: Gazette, mail and time capsule all share it |
| 7 | W2 | The Invention Forge, once the datapack validator can be trusted |
| 8 | H1, H2, H3 | House and game wired to each other |
| 9 | R1 | Geyser, if tablets matter — consider pulling this much earlier |
| 10 | F4, M3, T1, H4, T4 | The big physical projects. F4 comes first in this row: T1 serves its pack through it |

**R1 (cross-play) is the one to reconsider first.** If the kids have iPads it
changes when and where they can play at all, which outranks anything else on
this list.

---

## Foundations

Plumbing that several features below depend on. Two of the four are done; those
are described in [EVENT_BUS.md](EVENT_BUS.md) and [RCON.md](RCON.md) rather
than repeated here.

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
P2, P5, W2 and most of T1.

### F4. Resource pack hosting — Green

Set `resource-pack=` and `resource-pack-sha1=` in `server.properties` and host
the zip from Cloudflare R2, which is already wired up for backups in
`scripts/cloud-backup-r2.sh`. Clients download it on join. This unlocks custom
sounds, custom music discs, custom item textures and custom fonts, again on
vanilla.

Wants `scripts/resource-pack-manager.sh` (set URL, upload, compute hash,
enable/disable) and `GET`/`POST`/`DELETE /api/resourcepack`.

### F5. Statistics from the game's own data — Green

Replace the log-scraping in `scripts/player-stats-tracker.sh`. Vanilla already
writes authoritative per-player data to `data/<world>/stats/<uuid>.json` and
`data/<world>/advancements/<uuid>.json`, covering every statistic Minecraft
tracks: blocks mined by type, distance walked, damage taken, time played, every
death cause. Read those files instead.

This fixes the inflating-counts defect and gives the Gazette, the leaderboards
and the advancement tree something true to read from.

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
log, it remembers what each kid was building last week, it hands out a daily
quest, it answers "how do I make a beacon" without either of them alt-tabbing to
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

Depends on F5 for real numbers and on the Hall of Deaths, which already stores
the week's obituaries. See the NBT-to-components blocker before building the
book writer.

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

Wants the scoreboard tooling in the [management backlog](#scoreboards-and-teams).

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
| World border manager | P3 | Centre, size, damage, knockback, animated changes |
| Spawn protection manager | P3 | Radius and behaviour |
| Server icon manager | P3 | Set from file, generate from image, validate 64×64 PNG |
| Structure generation control | P3 | Enable/disable structures, spawn rates, custom templates |

### Scoreboards and teams

| Item | Priority | Notes |
| --- | --- | --- |
| Scoreboard manager | P2 | Objectives, sidebar display, presets; needed by P3 (co-op goals) |
| Team manager | P2 | Colours, prefixes, friendly fire, collision, membership |
| Bossbar manager | P2 | Progress bars for events and timers; needed by P5 (Raid Night). Bedtime mode already drives one — factor that code out rather than writing a second |
| Title / actionbar manager | P2 | Partly covered by `scripts/announcement-manager.sh`; extend rather than replace |

### Player and automation

| Item | Priority | Notes |
| --- | --- | --- |
| Advancement manager | P2 | List, grant, revoke, track progress; pairs with P2 (family tree) |
| Command chain manager | P2 | Named, reusable command sequences with variables and conditional branching |
| Player note system | P2 | Admin notes on a player, categorised and timestamped |
| Player teleport history | P2 | Saved locations, back/return, teleport requests |
| Automated world maintenance | P2 | Entity cleanup, chunk optimisation, lag-spike detection, backup before maintenance |
| Server event manager | P2 | Scheduled tournaments and contests with registration and reward distribution. Overlaps P4/P5 — build those first and generalise if a pattern emerges |
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
