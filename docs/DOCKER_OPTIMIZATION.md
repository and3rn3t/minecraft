# Docker Image Optimization Guide

How the [Dockerfile](../Dockerfile) and CI build are set up for small images, good
layer caching, and fast builds on the Raspberry Pi 5 (ARM64).

## Current design

- **Base image**: `eclipse-temurin:25-jre-noble`, pinned by digest. It is the JRE
  variant because nothing in the image compiles Java. Renovate bumps the tag and
  digest together, so builds stay reproducible without going stale.
- **Single stage**: there is nothing to compile, so multi-stage builds add nothing.
- **Platforms**: `linux/arm64` and `linux/amd64`. Temurin 25 publishes no
  `linux/arm/v7` image, so 32-bit ARM is not supported.
- **Server jar is not baked in**: `scripts/download-server.sh` fetches it at first
  boot for `MINECRAFT_VERSION`, so one image serves any version and server type.
  Downloads retry on transient failures.
- **Image size**: about 405 MB (arm64).

## Layer caching

Layers run from least to most frequently changed:

1. Base image
2. `apt-get install` (with BuildKit cache mounts for apt)
3. Non-root user and directories
4. `download-server.sh`, then `start.sh`

`server.properties` and `eula.txt` are deliberately **not** copied into the image.
`/minecraft/server` is a volume (bind-mounted `./data` in Compose), which hides
anything baked into that path, and `start.sh` writes `eula.txt` itself. Copying them
only invalidated the layers below them whenever they were edited.

`.dockerignore` keeps docs, tests, CI config, `data/`, and `backups/` out of the
build context.

## Build arguments

`MINECRAFT_VERSION` is the only build argument. It sets the default `ENV` and image
labels; it can be overridden at runtime. It is defined in the Dockerfile, both
Compose files, `.env.example`, and `scripts/build-multiarch.sh`. CI relies on the
Dockerfile default rather than repeating it.

```bash
docker build --build-arg MINECRAFT_VERSION=26.3 -t minecraft-server .
```

## CI

- The `build-docker` job runs on `ubuntu-24.04-arm`, so the arm64 image builds
  natively instead of under QEMU.
- Layers are cached with the GitHub Actions cache (`type=gha`); release builds also
  use a registry cache.

## Security

- Runs as the unprivileged `minecraft` user.
- `--no-install-recommends` and cleanup keep installed packages to
  `ca-certificates`, `curl`, and `procps`.
- The healthcheck probes the game port, so "healthy" means the server accepts
  connections rather than "a java process exists".

## Checking size and layers

```bash
docker images minecraft-server
docker history minecraft-server
dive minecraft-server   # optional, interactive layer explorer
```

## Further options (not used)

- **Distroless / Alpine**: the start scripts need bash and `pgrep`, and Alpine's
  musl libc can cause JVM issues. The savings would not justify the changes.
- **Baking in the server jar**: makes first boot offline-safe but ties each image to
  one version and server type.

## See also

- [MULTI_ARCHITECTURE.md](MULTI_ARCHITECTURE.md)
- [UPDATE_DOCKER_IMAGE.md](UPDATE_DOCKER_IMAGE.md)
- [CI_CD.md](CI_CD.md)
