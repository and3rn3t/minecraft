# Updating the Game Server Image

How the game server's Docker image stays current, how to see which one is
running, and how to switch to a prebuilt registry image if you would rather pull
than build.

## How it is updated by default

`docker-compose.yml` has a `build:` section, so the Pi **builds the image itself**
from the `Dockerfile`. There is no registry image to pull. Two things keep it
current, and neither restarts the server while someone is playing:

| What | When | What it does |
| --- | --- | --- |
| Deploy agent (`minecraft-deploy.timer`) | Every 5 minutes | After a green commit on `main` changes the `Dockerfile`, a compose file, `scripts/start.sh` or `scripts/download-server.sh`, rebuilds the image and restarts the server once nobody is online. See [AUTO_DEPLOYMENT_SETUP.md](AUTO_DEPLOYMENT_SETUP.md) |
| `minecraft-update.timer`, which runs `scripts/auto-update.sh run` | 5 minutes after boot, then hourly | Compares the image the container is running with the image its tag points at now, and restarts the server only if they differ **and** nobody is online. A server that was stopped on purpose is left stopped. With `build:` there is nothing to pull, so in practice this picks up an image the deploy agent rebuilt while players were on |

Install the timer once (the other units are in
[RPI5_FULL_DEPLOYMENT.md](RPI5_FULL_DEPLOYMENT.md)):

```bash
sudo cp systemd/minecraft-update.service systemd/minecraft-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft-update.timer

# When it last ran and when it runs next
systemctl list-timers minecraft-update.timer
```

## What is running

```bash
# Which image the container was started from
docker inspect minecraft-server --format '{{.Config.Image}}'

# When that image was built
docker inspect minecraft-server --format '{{.Image}}' | xargs docker image inspect --format '{{.Created}}'

# Is a newer one waiting? Changes nothing.
./scripts/auto-update.sh check
```

## Update now

```bash
# What the timer does, on demand: restarts only if the image changed and nobody is online
./scripts/auto-update.sh run

# Rebuild by hand. This restarts the server, so check that nobody is online first
docker compose build
docker compose up -d
```

## Pulling a prebuilt image instead of building

CI publishes images to GitHub Container Registry, `ghcr.io/and3rn3t/minecraft-server`:

| Published by | Tags |
| --- | --- |
| A push to `main` (ARM64 only) | `latest`, `main`, `main-<short sha>` |
| A release (ARM64 and AMD64) | `X.Y.Z`, `X.Y`, `X` |

The default compose file does not use them. To pull instead of build, replace the
`build:` block with an `image:` line:

```yaml
services:
  minecraft:
    image: ghcr.io/and3rn3t/minecraft-server:latest
```

`scripts/auto-update.sh` then runs `docker compose pull` each hour and restarts
the server only when the pulled image differs and nobody is online. To follow a
specific release, use its tag (`:1.6.0`) instead of `latest`.

If the package is private, log in once on the Pi with a personal access token that
has only `read:packages`:

```bash
echo "$TOKEN" | docker login ghcr.io -u and3rn3t --password-stdin
```

Docker keeps the credential in `~/.docker/config.json`. Do not put the token in a
systemd unit.

## Troubleshooting

### The update never happens

`auto-update.sh` writes to the journal, and the unit adds a "finished" line to
`logs/minecraft-update.log`:

```bash
sudo systemctl status minecraft-update.service
sudo journalctl -u minecraft-update.service --since "1 day ago"
tail logs/minecraft-update.log
```

The usual reasons are in its messages:

- **"Server is not running; leaving it stopped"**: it never starts a server that was stopped.
- **"New image found, but N player(s) online"**: it restarts once the server is empty.
- **"A deploy is changing the server right now"**: the deploy agent holds the lock; it tries again next run.
- **"Already up to date"**: the running container already uses the current image.

### The pull fails with 403 or "not found"

Only applies when you use a registry image. Check that CI's `main` run passed and
pushed the tag, that the package is visible to you, and that the token has
`read:packages` and has not expired.

### The container will not start with the new image

```bash
docker logs minecraft-server --tail 50
docker compose up -d --force-recreate
```

If it still fails, go back to the previous image with its `main-<short sha>` or
release tag, or rebuild from the last known-good commit.
