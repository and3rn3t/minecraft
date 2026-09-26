# Local Testing

How to run a real Minecraft server on your own machine — not the Pi — for
testing game features (datapacks, advancements, RCON-driven code) before
they ship. Everything here runs in Docker, using the same image and compose
file the Pi uses.

This exists because `scripts/datapack-manager.sh validate` only checks JSON
syntax — it can't catch a bad `.mcfunction` command, a wrong NBT slot name,
or a command that silently does nothing. Those only show up by actually
running the server. See [`GRAVES.md`](GRAVES.md#verified-against-a-real-server)
for what this setup caught that reading the code didn't.

## Prerequisites

- Docker Desktop (or another Docker daemon) running
- Nothing else — the image builds locally; `MINECRAFT_VERSION` in
  `docker-compose.yml` defaults to 1.20.4, matching the Pi

## First-time setup

```bash
cp .env.example .env      # defaults are fine for local testing
make build                 # builds the image; a couple of minutes the first time
make start                 # docker compose up -d
make logs                  # watch for "Done (...)! For help, type "help""
```

Ctrl-C out of `make logs` once you see `Done`; the server keeps running
detached.

**Enable RCON** — needed for everything below, and for the API server:

```bash
./scripts/rcon-setup.sh enable
./scripts/manage.sh restart
```

This writes a random password to `config/rcon.conf` (gitignored) and to
`data/server.properties`, then the restart picks it up. Confirm it worked:

```bash
./scripts/rcon-client.sh command "list"
# There are 0 of a max of 20 players online:
```

## Testing a datapack

```bash
./scripts/datapack-manager.sh enable family
docker compose logs --tail=20 minecraft
```

Watch the reload output for `Failed to load function ...` or `Failed to
load advancement ...` — that's a real syntax error the JSON/mcfunction
parser caught, not something `validate` would have shown you. A clean
reload just shows `Loaded N recipes` / `Loaded N advancements` with no
`ERROR` lines.

### Exercising a mechanic without a real player

Most of what you'll want to test happens "as a player" (breaking a block,
dying, taming a pet) and this environment has no Minecraft client. Two
ways around that:

**Call the function directly**, standing in for the player with any entity
you can summon (an armor stand works well — it won't wander off):

```bash
python3 -c "
from api.rcon import execute, reset_client
reset_client()
execute('summon minecraft:armor_stand 0 100 0 {Tags:[\"test_dummy\"]}')
print(execute('execute as @e[tag=test_dummy,limit=1] at @s run function family:tick/make_grave'))
print(execute('data get block 0 100 0'))       # the chest that should now exist
print(execute('data get block 0 101 0'))       # and the sign above it
"
```

This is exactly how [Graves](GRAVES.md) and [Lucky Blocks](LUCKY_BLOCKS.md)
were verified: summon some dropped items, run the function as a stand-in,
check the result with `data get`.

**Directly manipulate a scoreboard** to simulate a stat changing, then run
the tick-check function that watches it:

```bash
python3 -c "
from api.rcon import execute, reset_client
reset_client()
execute('scoreboard players set @e[tag=test_dummy] family_grave_age 1')
print(execute('function family:tick/age_graves'))
"
```

Note: tick-check functions like `check_lucky_blocks` and `check_deaths` loop
over `@a` (players only) — an armor stand won't trigger them. Call the
*downstream* function they'd have called instead (`roll_lucky_block`,
`make_grave`), as shown above.

**Use `forceload`** if you're testing away from spawn — without a player
nearby, chunks can unload between commands and reads won't reflect what you
just wrote:

```bash
python3 -c "
from api.rcon import execute, reset_client
reset_client()
execute('forceload add 100 100 100 100')
# ... your test ...
execute('forceload remove 100 100 100 100')
"
```

## Testing the API + RCON together

```bash
source .venv/bin/activate  # or: python3 -m venv .venv && pip install -r api/requirements.txt
ALLOWED_ORIGINS="http://localhost:5173" python3 api/server.py
```

There's already a dev API key in `config/api-keys.json` (gitignored, role
`user`). Bump it to `admin` locally if you need to exercise `.manage`
endpoints:

```bash
curl -H "X-API-Key: <key from config/api-keys.json>" http://localhost:8080/api/datapacks
```

For the web panel: `cd web && npm run dev`, then open <http://localhost:5173>
and put the same API key in via the login page (or `localStorage.setItem
('api_key', '...')` in the browser console).

## Connecting a real client

The one thing this whole setup can't do is actually play. If you want to
see something render — a sign's text, a lucky block's loot, an advancement
toast — connect a real Minecraft Java Edition 1.20.4 client to
`localhost:25565`. Everything built through RCON above will already be
there waiting.

## Cleaning up

```bash
./scripts/manage.sh stop     # or: docker compose down
rm -rf data/ backups/ .env   # full reset -- these are gitignored, safe to delete
```

`data/` holds the world; deleting it means the next `make start` generates
a fresh one.

## Related

- [`DATAPACKS.md`](DATAPACKS.md) — the datapack pipeline this is testing
- [`GRAVES.md`](GRAVES.md) — what this exact setup found and fixed
- [`RCON.md`](RCON.md) — more on `scripts/rcon-setup.sh` and the RCON client
- [`API_VENV_SETUP.md`](API_VENV_SETUP.md) — the Python virtual environment
  for the API server, in more detail
