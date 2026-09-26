# Datapack Pipeline

How to install, enable, disable and reload Minecraft datapacks on this server,
via `scripts/datapack-manager.sh` and the matching `/api/datapacks` endpoints.

## Overview

Datapacks are plain JSON. They work on **vanilla** Minecraft, hot-reload with
`/reload`, and give you custom advancements, recipes, loot tables, predicates
and functions — no plugin required. Originally roadmap item F3; see
[`ROADMAP.md`](ROADMAP.md#where-this-stands) for where it now lives among the
shipped work.

The pipeline separates two locations on purpose:

- **`config/datapacks/<name>/`** — the tracked source. This is committed to
  git, so a bad change to a datapack is one `git revert` away.
- **`data/<world>/datapacks/<name>/`** — the deployed copy. This is where the
  running server actually reads datapacks from. It's gitignored, because
  `data/` is the Pi's runtime state.

`enable` copies from the first location to the second and runs `/reload`.
`disable` removes the deployed copy and runs `/reload`; it never touches the
tracked source. `delete` removes the deployed copy too (if enabled) before
deleting the tracked source. Nothing writes to `data/<world>/datapacks/`
except `enable`, `disable` and `delete` — don't edit a datapack there, edit
it under `config/datapacks/` and re-run `enable`.

## Quick Start

```bash
# Scaffold a new datapack (pack.mcmeta + empty advancements/functions/loot_tables/recipes dirs)
./scripts/datapack-manager.sh create mydatapack

# See what's tracked and what's currently deployed in the active world
./scripts/datapack-manager.sh list

# Check pack.mcmeta and JSON syntax before deploying
./scripts/datapack-manager.sh validate mydatapack

# Deploy into the current world and /reload
./scripts/datapack-manager.sh enable mydatapack
```

## Commands

| Command | What it does |
| --- | --- |
| `create <name>` | Scaffold a new datapack under `config/datapacks/<name>/` |
| `list` | Human-readable listing: enabled vs. available |
| `list-json` | Machine-readable listing, used by `GET /api/datapacks` |
| `install <name> --url <url>` | Download a zip and extract it into `config/datapacks/<name>/`, then enable it |
| `install <name> --file <path>` | Same, from a local zip file |
| `enable <name>` | Copy the tracked source into the current world's `datapacks/` dir and `/reload` |
| `disable <name>` | Remove the deployed copy (tracked source untouched) and `/reload` |
| `validate <name>` | Check `pack.mcmeta` exists and every `.json` file under the pack parses |
| `delete <name> [--yes]` | Back up to `backups/`, disable if deployed, then delete the tracked source |
| `reload` | Just run `/reload` |

`install` and `delete` ask for confirmation before overwriting or deleting an
existing datapack; pass `--yes` to skip the prompt (this is what the API does
for you — an HTTP call to a permission-gated route is its own confirmation).

## API

All routes require an API key with the `datapacks.view` permission for reads
and `datapacks.manage` for writes — see [`RBAC.md`](RBAC.md). The `user` and
`operator` roles get `.view`; `.manage` is admin-only, matching
`plugins.manage` and `worlds.manage`.

| Route | Permission | Does |
| --- | --- | --- |
| `GET /api/datapacks` | `datapacks.view` | List, with enabled state for the current world |
| `POST /api/datapacks/install` | `datapacks.manage` | Install from a `url` form field or a `file` upload, then enable |
| `PUT /api/datapacks/<name>/enable` | `datapacks.manage` | Deploy and reload |
| `PUT /api/datapacks/<name>/disable` | `datapacks.manage` | Remove from the current world and reload |
| `DELETE /api/datapacks/<name>` | `datapacks.manage` | Back up and delete the tracked source |

Full request/response shapes are in [`api/openapi.yaml`](../api/openapi.yaml)
under the `Datapacks` tag.

## Troubleshooting

**`enable` succeeds but nothing changed in game.** Check `validate <name>`
first — a datapack with invalid JSON gets copied in but Minecraft silently
ignores the broken file(s) on `/reload`. Also confirm you're editing the
right world: `enable`/`disable`/`reload` all act on whatever `level-name` is
set to in `server.properties`, not necessarily the world you're standing in
if you've been switching worlds.

**A zip installed via `--url`/`--file` fails with "no pack.mcmeta at its
root".** The zip needs `pack.mcmeta` at its top level, not nested inside a
folder. Re-zip it, or extract manually into `config/datapacks/<name>/`.

**Datapack works after `enable` but disappears after a server restart.**
It shouldn't — `enable` writes into `data/<world>/datapacks/`, which is
part of the world save and persists across restarts like any other world
data. If it did disappear, check that whatever restarted the container
didn't also reset `data/` (see [`BACKUP_AND_MONITORING.md`](BACKUP_AND_MONITORING.md)).

## Related

- [`ROADMAP.md`](ROADMAP.md) — F3, the roadmap item this implements
- [`ADVANCEMENTS.md`](ADVANCEMENTS.md) — the family advancement tree, the
  first datapack built through this pipeline
- [`RBAC.md`](RBAC.md) — roles and permissions
