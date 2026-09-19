# Family Server Roadmap — The Wow Factor

Audience: Matt, planning what to build next on the Pi 5 server for Jonah and Silas.

Every other roadmap in this repo (`ROADMAP.md`, `TASKS.md`,
`MINECRAFT_GAMEPLAY_ENHANCEMENTS.md`) plans the *server management product*: more
endpoints, more admin pages, more ops polish. This one plans the *experience the
kids actually see*. It assumes the management layer is good enough already and
asks a different question: what could this server do that no other Minecraft
server does?

Ratings used below:

- **Green** — works on the Pi 5, on vanilla 1.20.4, with what's already in the repo.
- **Yellow** — works, but with a real constraint (extra RAM, extra hardware, a
  server-type change, or the work belongs on the Mac rather than the Pi).
- **Red** — don't, or not yet.

---

## Phase 0 — Foundations

Four pieces of plumbing. Almost everything in this document depends on at least
one of them, and several ideas collapse from "hard" to "an afternoon" once these
exist. Build these first.

### F1. A real RCON client inside the API — Green — **done**

Today every command shells out: `api/server.py` → `subprocess` →
`scripts/rcon-client.sh` → a brand new TCP connection and auth handshake per
command. That is roughly 50–100ms of overhead per command, and the pure-Python
fallback in `scripts/rcon-client.sh` has two defects worth knowing about before
you build on it: it does a single `sock.recv(4096)` with no length-prefix
framing, so long responses are truncated or split, and it treats any 4+ byte
reply as a successful auth rather than checking for a request id of `-1`.

Shipped as [`api/rcon.py`](../api/rcon.py): a persistent, pooled, properly
framed client with `command()` and a `commands(list)` batch call, multi-packet
reassembly and automatic reconnection. `api/server.py` reaches it through
`run_rcon_command()`, which falls back to the shell script when RCON is
unconfigured or unreachable. `scripts/rcon-client.sh` is unchanged for CLI use.

This is what makes the pixel-art placer, the event responders and the control
room viable instead of sluggish.

### F2. The Event Bus — Green — **done**

This is the backbone. `_log_reader` at `api/server.py:3657` already follows
`docker logs -f` in a single well-written thread and fans raw lines out over
Socket.IO. Two changes turn it into an event bus:

1. **Run it always.** It currently starts only when a browser subscribes and
   returns as soon as `active_log_streams` is empty. Start it at app boot and keep
   it running, so events are captured when nobody is watching the dashboard.
2. **Parse and persist.** Match each line into a typed event and append to
   `data/events/YYYY-MM-DD.jsonl`, then emit both the raw line (back-compat with
   the Logs page) and the typed event on a new Socket.IO channel.

Event types to start with: `chat`, `join`, `leave`, `death`, `advancement`,
`command`, `server_start`, `server_stop`. Vanilla log lines carry all of these.

Shipped as [`api/events.py`](../api/events.py) with the always-on follower in
`api/server.py`, the `GET /api/events` endpoints and a `game_event` WebSocket
message. Features subscribe with a handler function; see
[EVENT_BUS.md](EVENT_BUS.md). An "on death, do X" hook is what makes a dozen
features below into ten lines of code each.

Still outstanding: the stats rewrite below.

**While you're in there:** `scripts/player-stats-tracker.sh` re-parses the entire
log file on every invocation and adds to the existing counts, so every run
inflates the numbers. It also only matches three crude patterns. Vanilla already
writes authoritative per-player data to `data/<world>/stats/<uuid>.json` and
`data/<world>/advancements/<uuid>.json`. Read those files instead. They have
every statistic Minecraft tracks: blocks mined by type, distance walked, damage
taken, time played, every death cause.

### F3. A datapack pipeline — Green

Datapacks are the cheat code for this whole document. They are plain JSON in
`data/<world>/datapacks/`, they work on **vanilla**, they hot-reload with
`/reload`, and they give you custom advancements, recipes, loot tables,
predicates and functions without a single plugin.

Build `scripts/datapack-manager.sh` (`create`, `list`, `enable`, `disable`,
`validate`, `reload`) — `docs/MINECRAFT_ENHANCEMENTS.md` already proposes it.
Keep the family datapack in git so every change is revertible.

### F4. Resource pack hosting — Green

Set `resource-pack=` and `resource-pack-sha1=` in `server.properties` and host
the zip from Cloudflare R2, which is already wired up for backups in
`scripts/cloud-backup-r2.sh`. Clients download it automatically on join. This
unlocks custom sounds, custom music discs, custom item textures and custom
fonts, again on vanilla.

---

## Tier 1 — Highest wow per hour of work

### W1. The Oracle — a Claude-powered companion in chat — Green

Kids type in chat, something answers. Event bus catches `chat`, the API calls
the Claude API, the reply goes back via `tellraw` with colored JSON text.

Use `claude-haiku-4-5` for banter (fast and cheap) and `claude-sonnet-5` for
anything that needs to generate structure, like quests. Round-trip lands around
2–4 seconds, which reads as "the wizard is thinking" rather than as lag.

Give it a personality and a job: it knows the server's history from the event
log, it remembers what each kid was building last week, it hands out a daily
quest, it answers "how do I make a beacon" without either of them alt-tabbing to
a wiki.

**Guardrails, because this is aimed at children.** Pin a system prompt that
scopes it to Minecraft and kid-appropriate content, allowlist the player names
that may invoke it, rate limit per player per minute, cap output tokens so a
reply always fits a chat line, log every exchange through the existing
`log_audit_event()`, and put a kill switch on the dashboard.

### W2. The Invention Forge — describe an item, the server creates it — Green/Yellow

This is the one nobody else has. A kid types:

```
!invent a pickaxe that leaves a trail of flowers
```

Claude generates the datapack JSON — an advancement, a recipe, a loot table, a
function — the API validates it against a strict schema, writes it into
`data/<world>/datapacks/family/`, runs `/reload`, and **the item exists in the
game seconds later.**

The reason this is Yellow rather than Green is the validator, and it is worth
doing properly: generated `function` files can contain arbitrary commands, so
run every generated command through an allowlist before it ever touches the
disk. `api/security.py` already has `ALLOWED_MINECRAFT_COMMANDS` and
`BLOCKED_COMMAND_PREFIXES` for exactly this shape of problem — extend that
pattern. Keep the family datapack in git so a bad generation is one `git revert`
away, and add a `/undo-invention` that disables the last pack and reloads.

A ten-year-old inventing a working item by describing it is the single most
"knock your socks off" thing on this list.

### W3. Obituaries and the Hall of Deaths — Green

Death event fires. Claude writes a one-line epitaph in the voice of a Victorian
newspaper obituary. It gets `tellraw`'d to everyone online, and it lands on a
Hall of Deaths page on the dashboard with a leaderboard of most creative demises.

Nearly free once F2 and W1 exist, and it will be the thing they quote at dinner.

### W4. The Family Gazette — Green

A weekly newspaper, auto-generated every Sunday morning. Player stats, the
funniest deaths of the week, whose base grew the most, who mined the most
diamonds, what's coming up next week, a photo of the map.

Delivered two ways: as an HTML page on the dashboard, and **in-game as an actual
written book** placed in each player's inventory via `/give` with book NBT.
Receiving a physical newspaper in your inventory on a Sunday is a ritual.

**Version caution:** 1.20.4 uses the old `written_book{pages:[...]}` NBT syntax.
1.20.5 replaced item NBT with components and this syntax breaks. Put all book
construction behind one function so a Minecraft upgrade is a one-file change.

### W5. Bedtime Mode — Green

Scheduled shutdown that doesn't start a fight. Thirty minutes out, a bossbar
countdown appears. At ten, five and one minute, a title flashes. Then autosave,
a graceful stop, and a "goodnight" message.

Add a "five more minutes" button on the dashboard, and a Siri Shortcut for it.
Build on `scripts/command-scheduler.py` (it already does daily schedules and
conditional execution) and `scripts/announcement-manager.sh` (it already does
say, title and actionbar).

This is the most useful thing on the list for the adults in the house.

### W6. Siri, Shortcuts and HomeKit — Green

The cheapest big win in the document. The API already exists, already takes an
`X-API-Key` header, and already has start/stop/status/players endpoints. An iOS
Shortcut that makes an HTTP request is all that stands between you and:

- "Hey Siri, start Minecraft."
- "Hey Siri, is Jonah online?"
- "Hey Siri, Minecraft bedtime." (triggers W5)
- A Home Screen widget showing who's online.

Zero new server code. Ship a documented Shortcuts bundle and a few convenience
endpoints. Hours of work, not days. The `homekit-automator` repo can take it
further and expose the server as a real HomeKit accessory.

---

## Tier 2 — The house and the game talk to each other

This is the category that is genuinely rare, and it is rare only because most
people don't run their server on a Pi in their own house with a smart-home stack
next to it. You do.

### H1. Minecraft controls the real house — Green

A lever in the game turns on the real lamp in the bedroom.

Simplest implementation: a command block or sign in-game runs a chat command the
event bus recognizes, the API fires a webhook at `homehub` or HomeKit, the light
changes. A slightly cleaner version uses a datapack tick function writing to a
scoreboard the API polls.

Build a small "control panel" room in the world: one lever per light, a button
for the kitchen speaker, a redstone lamp that mirrors whether the front door is
locked. For a kid, this crosses a line they didn't know could be crossed.

### H2. The Control Room — Green

The inverse. An in-game room whose signs and scoreboard sidebar show real-world
data, refreshed by RCON once a minute: house temperature, tomorrow's forecast
(from the `weather-app` repo), chores due today (from the `family` repo), the
server's own TPS and the Pi's CPU temperature (already collected by
`scripts/analytics-collector.sh`).

### H3. Real-world sync — Green, with a caveat

- Real local weather drives in-game weather.
- Real sunrise and sunset drive in-game time.
- Real moon phase matches the in-game moon.
- Meteor shower tonight (the `sky` and `telescope` repos know) means an automatic
  firework show at the real peak time.

**Caveat:** hard-syncing time breaks sleeping in beds and scrambles mob-spawn
expectations, which kids notice fast. Make it a per-world toggle, sync on a slow
cadence, and consider syncing weather and moon only. The meteor shower fireworks
are the best part anyway and carry no downside.

### H4. Status hardware on the Pi — Yellow

Physical presence for an invisible thing:

- An LED strip whose color is server health, that pulses when someone joins, and
  whose brightness follows in-game day and night.
- A small e-ink panel on the shelf showing who is online right now.
- A big arcade button that starts the server.

**Two Pi 5 specific gotchas, because both will waste your evening otherwise.**
The Pi 5 moved GPIO behind the RP1 I/O controller, so `RPi.GPIO` does not work —
use `gpiozero` with the `lgpio` pin factory. And the classic `rpi_ws281x`
NeoPixel driver relies on PWM/DMA behavior the Pi 5 doesn't provide, so drive
addressable pixels over SPI or hang them off a cheap microcontroller over USB.
E-ink over SPI is fine.

This is also the repo's one completely untouched area: nothing in the project
drives anything physical today.

---

## Tier 3 — Memory and spectacle

### M1. Build time-lapse — Green, on the Mac

Render the same region from each nightly backup, stitch the frames with ffmpeg.
"Watch your base grow over a year" in ninety seconds.

Run it on the Mac against `backups/`, not on the Pi. There is no reason to spend
the Pi's thermal budget on rendering, and the backups are already there.

### M2. A 3D web map — Yellow on the Pi, Green on the Mac

BlueMap gives a genuinely beautiful browsable 3D map. The initial full render of
a mature world is CPU-hours and will run the Pi hot.

The sharp version: run BlueMap's standalone CLI **on the Mac** against last
night's backup, publish the static output to Cloudflare Pages or R2, and link it
from the dashboard. Free hosting, no server load, updates every morning, and it
works against a vanilla world directory with no plugin required.

### M3. 3D-print your build — Green, and a showstopper

Select a region, export it with Mineways or jmc2obj on the Mac, convert to STL,
hand it to the `Printer` repo and the Anycubic.

A child holding a physical model of the house they built in Minecraft is an
all-timer. This is a weekend project with an enormous payoff, and it connects
two repos you already maintain.

### M4. World rewind and the Museum — Yellow / Green

**Rewind:** boot a backup from any date as a second, read-only server on port
25566 and walk around the past. Two JVMs on an 8GB Pi is tight and on a 4GB Pi
it won't fit, so run the rewind instance on the Mac and have the dashboard hand
out the connection address.

**Museum:** a permanent showcase world where the best builds get copied in with
structure blocks, with a sign giving the builder and the date. Green, and
`scripts/world-manager.sh` already has `create-template` and `from-template` to
build on.

### M5. The Time Capsule — Green

Write a book in-game, seal it in the capsule, and the server delivers it back to
you on a real date a year from now.

No datapack needed. Store the book's contents as JSON, schedule the `/give`
through the existing command scheduler, deliver on the day. Technically the
smallest item in this document, and probably the one that matters most in five
years.

---

## Tier 4 — Structured play

### P1. Treasure hunts — Green

Claude writes a chain of riddle clues. A script picks real coordinates, places a
loot chest at each, and delivers the first clue as a book. Each clue's answer is
the next location. Difficulty tuned per kid.

### P2. A family advancement tree — Green

A custom datapack advancement tab with a custom icon, appearing in the real
advancements screen alongside the vanilla ones:

- "Sibling Rivalry" — survive three nights with your brother
- "Neighbors" — build within 50 blocks of Dad's house
- "First Diamond"
- "Ten Thousand Blocks"
- "Night Shift" — play past 9pm (they will find this hilarious)

Vanilla triggers cover most of it; location checks need a tick function. Because
it shows up in the game's own UI it reads as official rather than bolted on.

### P3. Sibling co-op goals — Green

Shared, server-wide objectives on a scoreboard that only complete if both
brothers contribute. Completing one unlocks a reward for both. Escalate toward
real-world prizes: finish the tier, get pizza night. Cooperation with a payout
beats competition for siblings.

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

Record a sound on an iPad, it becomes a music disc they can play on a jukebox in
the game. Draw a 16x16 sprite in a web pixel editor on the dashboard, it becomes
an item texture via CustomModelData. The pack auto-builds, uploads to R2 and
serves through F4.

Real effort, but the result is their drawings and their voices inside Minecraft.

### T2. Pixel-art uploader — Yellow, Green with one trick

Upload a PNG, get it built in blocks in-game. The naive approach of one
`setblock` per pixel is far too slow: a 128x128 image is 16,384 commands.

Two ways to fix it. Run-length encode each row into `/fill` commands, which
typically cuts command count by 10–50x on real images. Or generate an `.nbt`
structure file directly and place it with a structure block, which is one
command total. Cap the input at 128x128 either way.

### T3. Mail — Green

Send a letter from the dashboard, or from a phone, and it arrives as a written
book in the player's inventory. A note from Mom in your inventory when you log
in. Trivial once F1 and the Gazette's book builder exist.

### T4. NFC portal cards — Yellow

A PN532 reader on the Pi, or the tooling already in the `amiibo` and `flipper`
repos. Tap a physical card and the game responds: teleport to a saved location,
switch worlds, grant a kit, trigger an event.

Physical objects that do things in a video game is a category of magic that lands
extremely well at this age.

---

## Tier 6 — Reach

### R1. Geyser and Floodgate for cross-play — Yellow

Let them join from an iPad, a phone or a Switch. Run Geyser standalone as a
separate container proxying into the vanilla server.

Cost is an additional JVM, roughly 300–500MB. That's Yellow on an 8GB Pi and Red
on a 4GB one. Tablets and phones connect easily; a Switch needs DNS redirection
to work at all.

**If the kids have iPads, this may be the highest-value item in the entire
document,** because it changes when and where they can play at all. Weigh it
first against everything above.

### R2. Simple Voice Chat — Yellow, deprioritize

Needs Fabric or Paper server-side and a client mod installed for every player.
For two brothers in the same house who can simply shout, the value is low. Park
it.

### R3. Push notifications and a weekly digest — Green

"Silas just got his first diamond." Event bus plus ntfy, Pushover or APNs. Cheap,
and it keeps the adults connected to what's happening without hovering.

---

## Suggested sequence

| Order | Items | Why here |
|---|---|---|
| 1 | F1, F2 | Nothing good happens without the RCON client and the event bus |
| 2 | W6, W5 | Days of work, immediate daily payoff, no new infrastructure |
| 3 | W3, W1 | First "whoa" moments; W3 proves the event bus end to end |
| 4 | F3, P2 | Datapack pipeline plus family advancements, visible in-game |
| 5 | M2, M1 | Map and time-lapse, rendered on the Mac, zero Pi cost |
| 6 | W4, T3, M5 | The book pipeline: Gazette, mail, time capsule all share it |
| 7 | W2 | The Invention Forge, once the datapack validator can be trusted |
| 8 | H1, H2, H3 | House and game wired together |
| 9 | R1 | Geyser, if tablets matter — consider pulling this much earlier |
| 10 | M3, T1, H4, T4 | The big physical projects |

---

## Known issues to fix before any of this ships

These are real and they sit in the path of the work above.

- **`api/server.py:723` hardcodes `"role": "admin"` for every registered user**,
  despite a comment claiming otherwise. Open registration currently mints
  administrators. Fix before anything is exposed beyond the LAN.
- **API keys bypass permissions entirely** — `has_permission` returns `True`
  unconditionally for API-key callers (`api/server.py:605`). The Socket.IO stream
  accepts only API keys, so any key living in a kid's browser is a full admin
  credential. Tighten before handing out keys.
- **`scripts/player-stats-tracker.sh` inflates counts** on every run by
  re-parsing the whole log and adding to existing totals. Superseded by F2.
- **`apply_server_preset()` (`api/server.py:2673`) has no route decorator** and is
  unreachable. Either wire it up or delete it.
- **1.20.4 to 1.20.5 changes item NBT to components.** Every `/give` with NBT in
  this document breaks on that upgrade. Isolate item construction in one module.
- **SD-card write endurance.** The event bus appends JSONL continuously. Put
  `data/events/` on an SSD if there is one, batch the flushes, and rotate hard.
