# Minecraft Server for Raspberry Pi 5

A self-hosted Minecraft server stack tuned for the Raspberry Pi 5 (ARM64): Docker
deployment, automated and offsite backups, plugin and mod management, multi-world
support, RCON, a REST API, and a React web admin panel.

Works on x86_64 too — the Pi is just what it is optimised for.

## Features

- 🎮 Tuned for Raspberry Pi 5 (ARM64), multi-arch images
- 🐳 Docker Compose deployment with systemd units for boot-time start
- 💾 Scheduled backups with retention, plus offsite backup to R2 / S3 / B2
- 🔌 Plugin and mod management (Paper, Spigot, Fabric, Forge)
- 🌍 Multi-world management, switching, and per-world backups
- 🖥️ REST API + React admin panel with RBAC, API keys and OAuth
- 📊 Analytics, metrics, log rotation and search
- 🔄 Version checking, compatibility checks and guided updates

## Requirements

- Raspberry Pi 5 (4GB minimum, 8GB recommended)
- MicroSD card, 32GB or larger
- Raspberry Pi OS (64-bit)
- Docker with the Compose v2 plugin (the setup script installs it)

## Quick Start

```bash
# On the Pi
git clone https://github.com/and3rn3t/minecraft.git ~/minecraft-server
cd ~/minecraft-server

./scripts/setup-rpi.sh      # installs Docker, dependencies, permissions
# log out and back in so the docker group takes effect

./scripts/manage.sh start   # start the server
./scripts/manage.sh logs    # watch it come up
```

Connect from Minecraft using the Pi's address on port `25565`.

Full walkthrough, including flashing the SD card: **[docs/INSTALL.md](docs/INSTALL.md)**.
Deploying the API and web panel as well: **[docs/RPI5_FULL_DEPLOYMENT.md](docs/RPI5_FULL_DEPLOYMENT.md)**.

## Managing the Server

`scripts/manage.sh` is the main entry point; `make` wraps the common ones.

```bash
./scripts/manage.sh start|stop|restart|status|logs|backup|console
./scripts/manage.sh update [version]      # update the server jar
./scripts/manage.sh check-version         # is there a newer release?
./scripts/manage.sh check-compatibility   # safe to update?
```

```bash
make help        # every target
make start       # same as ./scripts/manage.sh start
make status
make backup
make logs
```

### Other tools

```bash
# Server properties and presets
./scripts/server-properties-manager.sh set view-distance 10
./scripts/performance-presets.sh balanced

# Players
./scripts/whitelist-manager.sh add PlayerName
./scripts/ban-manager.sh ban PlayerName "Reason"
./scripts/op-manager.sh grant PlayerName 4

# Performance
./scripts/jvm-optimizer.sh generate 2G 4 aikar
./scripts/monitor-rpi5.sh
```

Everything is listed in **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)**.

## Configuration

### Server properties

Edit `server.properties`, then `./scripts/manage.sh restart`:

```properties
max-players=10
difficulty=normal
gamemode=survival
view-distance=10           # lower is faster
motd=My Minecraft Server
```

### Memory and version

Both come from environment variables read by `docker-compose.yml`, so set them in a
`.env` file next to it rather than editing the compose file:

```bash
MINECRAFT_VERSION=1.20.4
MEMORY_MIN=1G              # 2G on an 8GB Pi
MEMORY_MAX=2G              # 4G on an 8GB Pi
CONTAINER_MEMORY_LIMIT=3G  # must exceed MEMORY_MAX by ~1G
```

> `CONTAINER_MEMORY_LIMIT` has to leave the JVM roughly 0.5–1G of headroom beyond
> `MEMORY_MAX`. Setting it equal to `MEMORY_MAX` is the classic cause of a restart
> loop — see [Troubleshooting](docs/TROUBLESHOOTING.md#server-restart-loop).

More examples: **[docs/CONFIGURATION_EXAMPLES.md](docs/CONFIGURATION_EXAMPLES.md)**.

## Backups

```bash
./scripts/manage.sh backup                   # one-off, into backups/
./scripts/install-backup-timer.sh            # scheduled via systemd timer
./scripts/cloud-backup-r2.sh upload          # offsite (also -s3 and -b2 variants)
```

To restore, stop the server, extract the archive into `data/`, and start again.
Details and retention policy: **[docs/BACKUP_AND_MONITORING.md](docs/BACKUP_AND_MONITORING.md)**
and **[docs/CLOUD_BACKUP.md](docs/CLOUD_BACKUP.md)**.

## Starting on Boot

systemd units ship in `systemd/`. They use `docker compose` and pull the latest
image before starting:

```bash
sudo cp systemd/minecraft.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft.service
```

`minecraft-api.service`, `minecraft-web.service`, the backup timer and the update
timer install the same way. See **[docs/DOCKER_BOOT_SETUP.md](docs/DOCKER_BOOT_SETUP.md)**.

## Remote Access

To let friends connect from outside your network, forward TCP `25565` to the Pi.
For a stable hostname on a changing home IP, use the DDNS updater —
**[docs/DYNAMIC_DNS.md](docs/DYNAMIC_DNS.md)**.

## Web Panel & API

```bash
./scripts/setup-api-venv.sh     # Python venv for the API
./scripts/api-server.sh start   # REST API
./scripts/build-web.sh          # build the React panel
```

The panel covers server control, players, worlds, backups, plugins, logs, the
console, analytics, config editing, users and API keys. See
**[docs/WEB_INTERFACE.md](docs/WEB_INTERFACE.md)** and **[docs/API.md](docs/API.md)**
(the OpenAPI spec is `api/openapi.yaml`).

## Development

```bash
git clone https://github.com/and3rn3t/minecraft.git
cd minecraft

make lint     # shellcheck, eslint, python, yaml, compose validation
make test     # pytest + vitest + syntax checks
make coverage # coverage report
```

- **[AGENTS.md](AGENTS.md)** — conventions, stack, commands (also what AI assistants read)
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** — setup and workflow
- **[docs/TESTING.md](docs/TESTING.md)** — test layout and how to run each suite
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — contribution guidelines

## Documentation

📚 **[docs/INDEX.md](docs/INDEX.md) lists every guide**, grouped by task. Common ones:

| Topic | Guide |
| --- | --- |
| Install from scratch | [docs/INSTALL.md](docs/INSTALL.md) |
| Command cheat sheet | [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) |
| Something is broken | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Backups & monitoring | [docs/BACKUP_AND_MONITORING.md](docs/BACKUP_AND_MONITORING.md) |
| Plugins | [docs/PLUGIN_MANAGEMENT.md](docs/PLUGIN_MANAGEMENT.md) |
| Multiple worlds | [docs/MULTI_WORLD.md](docs/MULTI_WORLD.md) |
| REST API | [docs/API.md](docs/API.md) |
| Pi tuning | [docs/RASPBERRY_PI_OPTIMIZATIONS.md](docs/RASPBERRY_PI_OPTIMIZATIONS.md) |
| Roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) |
| Version history | [CHANGELOG.md](CHANGELOG.md) |

## Troubleshooting

Start with **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — it covers
installation failures, startup problems, restart loops, connectivity, performance,
Docker and system-level issues.

Quick checks:

```bash
./scripts/manage.sh status
./scripts/health-check.sh
docker logs --tail 100 minecraft-server
free -h && df -h
vcgencmd measure_temp       # should stay below 80°C
```

## Performance Tips

1. Use Ethernet rather than WiFi
2. Give the Pi 5 active cooling — it throttles under sustained load
3. Use the official Pi 5 power supply
4. Use a fast A2-rated card, or better, an NVMe drive
5. Lower `view-distance` and `simulation-distance` before lowering memory

See **[docs/RASPBERRY_PI_OPTIMIZATIONS.md](docs/RASPBERRY_PI_OPTIMIZATIONS.md)**.

## Resources

- [Minecraft server documentation](https://minecraft.wiki/w/Server)
- [server.properties reference](https://minecraft.wiki/w/Server.properties)
- [Raspberry Pi documentation](https://www.raspberrypi.com/documentation/)
- [Docker documentation](https://docs.docker.com/)

## License

See [LICENSE](LICENSE). Security reports: [SECURITY.md](SECURITY.md).
