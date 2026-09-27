# The Oracle

A Claude-powered companion that lives in chat. Every message a kid types can be
seen by it; most of the time it stays quiet, but it can answer a question,
banter back, or hand out a quest.

This is the first feature built on the [event bus](EVENT_BUS.md) that talks
back in both directions — game to API to game on every single message, not
just game to API like every earlier feature. It is also the first real
implementation of the pluggable-writer shape [`api/epitaphs.py`](../api/epitaphs.py)
defines, aimed at a different job: `OracleResponder` in
[`api/oracle.py`](../api/oracle.py) is the same idea (something injectable that
turns game data into words), applied to a two-way conversation instead of a
one-line obituary.

## What it looks like

```text
<Jonah> oracle, how do I make a beacon?
Jonah, mine 3 obsidian-proof Nether stars from a Wither, place them in a
pyramid under a beacon block, and stand nearby!
```

```text
<Silas> hey Jonah want to go mining
```

(No reply — ordinary chat between the two of them isn't the Oracle's business.)

```text
<Jonah> oracle give me a quest
Quest: Diamond Dash -- Mine 5 diamonds before sundown.
```

The dashboard page at `/oracle` shows the current on/off state, the
allowlist and rate limit, and a running log of recent exchanges and quests.

## How it works

1. `api/events.py` already parses every chat line into a `chat` event — this
   shipped long before the Oracle did, so no new parsing was needed.
2. `Oracle.handle_event` in [`api/oracle.py`](../api/oracle.py) picks it up
   from the bus, checks the allowlist, and queues it. The allowlist check
   happens here rather than after dequeueing so that chat from anyone not on
   it — a griefer's, a visitor's — never enters the worker's backlog at all.
3. A worker thread takes it from the queue, re-checks the kill switch (so
   disabling the Oracle stops it from answering immediately rather than once
   the backlog drains), checks the rate limit, and calls Claude
   (`claude-haiku-4-5`) with a pinned system prompt, asking it to triage the
   message into exactly one of three outcomes: stay quiet, banter back, or
   generate a quest.
4. A `no_reply` outcome ends there. A `banter` outcome is sent straight back
   to the player with `tellraw`. A `quest_request` outcome triggers a second
   call, to `claude-sonnet-5`, that generates a structured quest — title,
   objective, difficulty, a flavor-text reward — which is delivered the same
   way and also saved.
5. Every outcome the worker actually considers (including a quiet one, a
   rate-limited one, or a disabled/no-key skip) is recorded and logged to the
   audit log — not just the ones that reached Claude.

### Why two models

Every surviving chat message costs one `claude-haiku-4-5` call — fast and
cheap, which matters because it runs on *every* allowlisted message, not just
ones clearly meant for the Oracle. `claude-sonnet-5` only runs on the rarer
path where a message is actually asking for a quest, and only needs to
produce one small structured object.

### Why the model chooses silence

There is no trigger word — the Oracle sees every chat message a kid types.
To keep that from being intrusive or expensive, the triage call itself
decides whether a reply is warranted, and the system prompt tells it to
choose quiet liberally: ordinary chatter between the two kids should almost
always come back `no_reply`.

### No conversation memory

Every message is triaged independently — there's no rolling context window,
so "wait, I just told you that" gets nothing. That's a deliberate v1
simplification, not an oversight: it keeps the design simple and the cost
predictable. A per-player rolling context is the natural next step if it
turns out to matter in practice.

## Guardrails

This talks directly to children, so every design choice here is a guardrail
first:

- **Off by default, twice over.** `config/oracle.conf`'s `ENABLED` defaults
  to `false`, and even when set to `true`, no `ANTHROPIC_API_KEY` means no
  responder is built at all — every message resolves to a logged-once skip
  rather than doing nothing silently over and over.
- **An exact-username allowlist.** A chat message from anyone not in
  `ALLOWLIST` is never sent to Claude, and isn't even logged — it's simply
  not the Oracle's business.
- **A per-player rate limit that gates the API call itself**, not just the
  reply. This is the actual cost control: `RATE_LIMIT_PER_MINUTE` (default 4)
  bounds worst-case spend per player to a trivial amount even on the
  chattiest day.
- **A pinned system prompt that treats chat as content, not instructions.**
  It explicitly tells the model that the quoted chat line is something to
  react to, never a command to it, even if it claims otherwise — the
  standard defense against a kid trying to jailbreak it.
- **Structured output, not free text.** Every response is validated against
  a fixed schema (`OracleTriage`, `QuestSpec`). A jailbreak attempt is bounded
  to a short text field with no tool access — there's no path from a clever
  chat message to an RCON command or a file write.
- **Output length caps.** A banter reply is capped and truncated
  (`MAX_TELLRAW_LENGTH`) before it ever reaches `tellraw`, since Minecraft
  truncates long commands anyway.
- **Every exchange is audit-logged**, including ones that produced no reply.
- **A live kill switch on the dashboard**, gated by a dedicated `oracle.manage`
  permission that is admin-only by default — not inherited by the `operator`
  or `user` roles.

## Configuration

Copy `config/oracle.conf.example` to `config/oracle.conf`. The real file is
gitignored.

| Setting | Default | Meaning |
| --- | --- | --- |
| `ENABLED` | `false` | The kill switch. |
| `ALLOWLIST` | `Jonah,Silas` | Comma-separated exact Minecraft usernames. |
| `RATE_LIMIT_PER_MINUTE` | `4` | Per player, per minute. Gates the Claude call itself. |
| `COLOR` | `aqua` | Chat text color for the Oracle's replies. |
| `RETENTION_DAYS` | `90` | How long exchange logs are kept. |
| `HAIKU_MODEL` | `claude-haiku-4-5` | The triage model. |
| `SONNET_MODEL` | `claude-sonnet-5` | The quest-generation model. |

**`ANTHROPIC_API_KEY` does not go in this file.** It's a secret, and
`config/oracle.conf` sits alongside every other config the dashboard's Config
Files page can read. Set it as a real environment variable instead — in the
systemd unit's `Environment=` line on the Pi, or your shell profile for local
dev. The Anthropic SDK resolves it automatically; nothing in this repo reads
a `.env` file.

Records are stored under `data/oracle/`, gitignored and living only on the
Pi: `exchanges/YYYY-MM-DD.jsonl` (day-sharded, like Hall of Deaths) and a
single `quests.jsonl` — not day-sharded, since quest volume is low and a
future bounty board ([P11](ROADMAP.md)) wants one file to scan forward
through. Each quest carries a stable `id` (a UUID) and a `claimed` flag,
reserved and unused until P11 exists to set it.

## Cost

Ballpark numbers at current pricing ($1/$5 per MTok for haiku, $2/$10 per
MTok for sonnet):

- **Triage**: roughly $0.0003 per chat message. Even an implausibly chatty
  day — 2,000 messages between two kids — is well under $1.
- **Quest generation**: roughly $0.005 per quest. Trivial at any realistic
  volume.

The real cost risk isn't the per-message price, it's an unbounded loop — a
kid (or a misbehaving bot) spamming chat. `RATE_LIMIT_PER_MINUTE` is what
actually caps that, since it gates the Claude call itself rather than just
the reply.

## REST API

`GET /api/oracle`, `GET /api/oracle/exchanges`, and `GET /api/oracle/quests`
require `oracle.view`. `PUT /api/oracle/enable`, `PUT /api/oracle/disable`,
and `PUT /api/oracle/settings` require `oracle.manage`. Both permissions are
admin-only by default.

```text
GET  /api/oracle
GET  /api/oracle/exchanges?limit=50
GET  /api/oracle/quests?limit=50
PUT  /api/oracle/enable
PUT  /api/oracle/disable
PUT  /api/oracle/settings   {"allowlist": ["Jonah", "Silas"], "rate_limit_per_minute": 4}
```

```bash
curl -H "X-API-Key: $API_KEY" "http://localhost:8080/api/oracle"
```

## Notes

- **A non-allowlisted player's chat never touches the network.** The
  allowlist check runs before the rate limit and before any Claude call.
- **Reply text is JSON-encoded, not interpolated**, so a model response
  containing a quote or backslash cannot break the command.
- **The target player name is validated too**, not just the reply text —
  `tellraw <player> ...` puts the player into the command itself, not just
  JSON-escaped text. In practice the name always comes from `api/events.py`'s
  already-anchored chat regex, so this is defense-in-depth.
- **A refusal from Claude's own safety classifiers is treated as silence**,
  not an error — the triage call maps it to `no_reply`.

## Related

- [EVENT_BUS.md](EVENT_BUS.md) — where chat events come from
- [ROADMAP.md](ROADMAP.md) — W1 shipped here; W2 (the Invention Forge) and
  P11 (the bounty board, which will eventually read `data/oracle/quests.jsonl`)
  are next
