# Documentation Index

Every guide in this project, grouped by what you are trying to do.

- [Getting Started](#getting-started)
- [Deployment & Operations](#deployment--operations)
- [Server Features](#server-features)
- [API & Web Panel](#api--web-panel)
- [Performance & Raspberry Pi](#performance--raspberry-pi)
- [Development](#development)
- [Reference & Troubleshooting](#reference--troubleshooting)

---

## Getting Started

| Guide | What it covers |
| --- | --- |
| [INSTALL.md](INSTALL.md) | Full installation on a Raspberry Pi 5, start to finish, including starting at boot |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | One-page command cheat sheet |
| [CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md) | Worked examples for every config file |

New here? Read `INSTALL.md`, then keep `QUICK_REFERENCE.md` open.

---

## Deployment & Operations

| Guide | What it covers |
| --- | --- |
| [RPI5_FULL_DEPLOYMENT.md](RPI5_FULL_DEPLOYMENT.md) | Installing the API, web panel and every systemd unit, so all of it starts at boot |
| [AUTO_DEPLOYMENT_SETUP.md](AUTO_DEPLOYMENT_SETUP.md) | How a push to `main` reaches the Pi: the deploy agent, CI gating and rollback |
| [UPDATE_DOCKER_IMAGE.md](UPDATE_DOCKER_IMAGE.md) | How the server image is updated, how to see which one is running, and switching to a registry image |
| [UPDATE_CODEBASE.md](UPDATE_CODEBASE.md) | Updating the repository checkout on the Pi |
| [UPDATE_MANAGEMENT.md](UPDATE_MANAGEMENT.md) | Minecraft version updates and compatibility checks |
| [MULTI_ARCHITECTURE.md](MULTI_ARCHITECTURE.md) | Building images for arm64 and amd64 |
| [BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md) | Backup scheduling, retention, health checks, metrics |
| [CLOUD_BACKUP.md](CLOUD_BACKUP.md) | Offsite backups to Cloudflare R2, S3 or Backblaze B2 |
| [LOG_MANAGEMENT.md](LOG_MANAGEMENT.md) | Log rotation, search and analysis |
| [PLAYIT.md](PLAYIT.md) | How players reach the server through CGNAT: the playit.gg tunnel and its SRV record |
| [DYNAMIC_DNS.md](DYNAMIC_DNS.md) | Keeping a hostname pointed at a changing home IP |
| [CLOUDFLARE_SETUP.md](CLOUDFLARE_SETUP.md) | Cloudflare DDNS configuration specifics |

---

## Server Features

| Guide | What it covers |
| --- | --- |
| [MINECRAFT_MANAGEMENT.md](MINECRAFT_MANAGEMENT.md) | Whitelist, bans, ops, server properties, announcements |
| [MULTI_WORLD.md](MULTI_WORLD.md) | Creating, switching and backing up multiple worlds |
| [PLUGIN_MANAGEMENT.md](PLUGIN_MANAGEMENT.md) | Installing and configuring Bukkit/Spigot/Paper plugins |
| [MOD_SUPPORT.md](MOD_SUPPORT.md) | Mod loader detection and mod pack installation |
| [RCON.md](RCON.md) | Remote console setup and usage |
| [EVENT_BUS.md](EVENT_BUS.md) | Typed game events parsed from the server log |
| [HALL_OF_DEATHS.md](HALL_OF_DEATHS.md) | Epitaphs for every death, in game and on the dashboard |
| [BEDTIME.md](BEDTIME.md) | Scheduled, warned end to the evening |
| [PLAYER_STATS.md](PLAYER_STATS.md) | Player counters read from the world's own stats files |
| [ANALYTICS.md](ANALYTICS.md) | Player and server analytics collection and reports |
| [DATAPACKS.md](DATAPACKS.md) | Installing, enabling and reloading vanilla datapacks |
| [ADVANCEMENTS.md](ADVANCEMENTS.md) | The family advancement tree and how each achievement is triggered |
| [LUCKY_BLOCKS.md](LUCKY_BLOCKS.md) | Craft a player head, break it, roll a loot table |
| [GRAVES.md](GRAVES.md) | Dropped items collected into a labeled chest, not scattered |
| [PET_CEMETERY.md](PET_CEMETERY.md) | Gentle obituaries and gravestones for named pets |
| [ORACLE.md](ORACLE.md) | A Claude-powered companion that lives in chat |

---

## API & Web Panel

| Guide | What it covers |
| --- | --- |
| [API.md](API.md) | Complete REST API reference (mirrors `api/openapi.yaml`) |
| [API_VENV_SETUP.md](API_VENV_SETUP.md) | Python virtual environment for the API server |
| [API_KEYS.md](API_KEYS.md) | Creating, scoping and rotating API keys |
| [RBAC.md](RBAC.md) | Roles and permissions |
| [OAUTH_SETUP.md](OAUTH_SETUP.md) | Google / Apple sign-in |
| [WEB_INTERFACE.md](WEB_INTERFACE.md) | Using the React admin panel |
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | Tokens, primitives and conventions for the web panel's UI |
| [SECURITY_HARDENING.md](SECURITY_HARDENING.md) | Hardening the API and the host |

---

## Performance & Raspberry Pi

| Guide | What it covers |
| --- | --- |
| [RASPBERRY_PI_COMPATIBILITY.md](RASPBERRY_PI_COMPATIBILITY.md) | What works on which Pi, and how to verify |
| [RASPBERRY_PI_OPTIMIZATIONS.md](RASPBERRY_PI_OPTIMIZATIONS.md) | Pi-specific tuning (memory, JVM, thermals) |
| [SYSTEM_OPTIMIZATIONS.md](SYSTEM_OPTIMIZATIONS.md) | Filesystem, kernel, swap and log tuning, and what `optimize-system.sh` applies |
| [DOCKER_OPTIMIZATION.md](DOCKER_OPTIMIZATION.md) | Image size, build caching, layer strategy |
| [PERFORMANCE_BENCHMARKING.md](PERFORMANCE_BENCHMARKING.md) | Measuring and comparing performance |

---

## Development

| Guide | What it covers |
| --- | --- |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local setup and day-to-day workflow |
| [LOCAL_TESTING.md](LOCAL_TESTING.md) | Running a real server in Docker locally to test game features |
| [TESTING.md](TESTING.md) | Test layout, how to run each suite, coverage |
| [WEB_UI_TESTING.md](WEB_UI_TESTING.md) | Vitest, MSW and Playwright specifics for `web/` |
| [LINTING.md](LINTING.md) | ShellCheck, ESLint, flake8, yamllint |
| [CI_CD.md](CI_CD.md) | GitHub Actions pipeline and release process |
| [CURSOR_CONFIGURATION.md](CURSOR_CONFIGURATION.md) | Cursor IDE setup |
| [ROADMAP.md](ROADMAP.md) | Everything planned, in order — the only roadmap |

AI assistants read [`../AGENTS.md`](../AGENTS.md) — the single source of truth for
conventions. See also [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

---

## Reference & Troubleshooting

| Guide | What it covers |
| --- | --- |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Installation, startup, restart loops, connectivity, Docker, system issues |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Command cheat sheet |
| [CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md) | Config file examples |
| [../CHANGELOG.md](../CHANGELOG.md) | Version history |

---

## Adding a Document

Add the file to `docs/`, then add a row to the right table above — an unlisted
document will not be found. Historical "summary" or "implementation complete"
write-ups do not belong here; that record lives in `CHANGELOG.md` and git history.
