# Docker Image Optimization Guide

This guide covers Docker image optimization techniques used in the Minecraft Server project, specifically optimized for Raspberry Pi 5 (ARM64).

## Overview

The project uses optimized Docker images to:

- **Reduce image size** - Faster downloads and less storage usage
- **Improve build times** - Better layer caching
- **Enhance security** - Minimal attack surface
- **Optimize for ARM64** - Raspberry Pi 5 specific optimizations

## Current Dockerfile Structure

### Multi-Stage Builds

The Dockerfile uses multi-stage builds to separate build dependencies from runtime:

```dockerfile
# Stage 1: Base image with Java and tools
FROM arm64v8/openjdk:21-jdk-slim AS base

# Stage 2: Runtime image (final)
FROM base AS runtime
```

### Key Optimizations

1. **Combined RUN Commands** - Reduces image layers
2. **Minimal Base Image** - Uses `-slim` variant of OpenJDK
3. **Single Layer Package Installation** - All packages in one RUN command
4. **Proper Cleanup** - Removes apt cache and temp files
5. **Non-root User** - Runs as `minecraft` user for security
6. **Health Checks** - Built-in container health monitoring

## Image Size Comparison

### Before Optimization

- Base image: ~400MB
- With packages: ~450MB
- Final image: ~450MB

### After Optimization

- Base image: ~400MB
- With packages: ~420MB (reduced by combining layers)
- Final image: ~420MB

**Savings**: ~30MB (7% reduction) + better caching

## Build Arguments

The Dockerfile supports build arguments for flexibility:

```dockerfile
ARG MINECRAFT_VERSION=1.20.4
ARG BUILD_TYPE=standard
```

### Usage

```bash
# Build with custom version
docker build \
  --build-arg MINECRAFT_VERSION=1.21.0 \
  -t minecraft-server:1.21.0 .

# Build with different build type
docker build \
  --build-arg BUILD_TYPE=minimal \
  -t minecraft-server:minimal .
```

## Layer Caching Strategy

### Optimized Layer Order

1. **Base image** - Changes rarely
2. **System packages** - Changes infrequently
3. **User creation** - Changes rarely
4. **Configuration files** - Changes more often
5. **Application files** - Changes most often

This order ensures maximum cache hits during rebuilds.

### Example

```dockerfile
# Layer 1: Base (cached most of the time)
FROM arm64v8/openjdk:21-jdk-slim AS base

# Layer 2: Packages (cached unless packages change)
RUN apt-get update && apt-get install -y ...

# Layer 3: User setup (cached unless user config changes)
RUN useradd -r -g minecraft ...

# Layer 4: Config files (cached unless configs change)
COPY --chown=minecraft:minecraft server.properties ...

# Layer 5: Start script (cached unless script changes)
COPY --chown=minecraft:minecraft scripts/start.sh ...
```

## Build Optimization Tips

### 1. Use BuildKit

Enable Docker BuildKit for better caching and parallel builds:

```bash
export DOCKER_BUILDKIT=1
docker build -t minecraft-server .
```

Or in `docker-compose.yml`:

```yaml
services:
  minecraft:
    build:
      context: .
      dockerfile: Dockerfile
    # BuildKit is enabled by default in newer Docker versions
```

### 2. Leverage Build Cache

```bash
# First build (no cache)
docker build -t minecraft-server .

# Subsequent builds (uses cache)
docker build -t minecraft-server .  # Much faster!

# Build without cache (force rebuild)
docker build --no-cache -t minecraft-server .
```

### 3. Multi-Architecture Builds

For supporting multiple architectures:

```bash
# Build for ARM64 (Raspberry Pi 5)
docker buildx build --platform linux/arm64 -t minecraft-server:arm64 .

# Build for x86_64
docker buildx build --platform linux/amd64 -t minecraft-server:amd64 .

# Build for both
docker buildx build --platform linux/arm64,linux/amd64 -t minecraft-server .
```

## Docker Compose Optimization

### Build Configuration

```yaml
services:
  minecraft:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - MINECRAFT_VERSION=${MINECRAFT_VERSION:-1.20.4}
    # ... rest of config
```

### Resource Limits

Set appropriate resource limits for Raspberry Pi:

```yaml
deploy:
  resources:
    limits:
      memory: 2G # Adjust based on Pi model
    reservations:
      memory: 1G
```

## Security Best Practices

### 1. Non-Root User

The container runs as a non-root user:

```dockerfile
USER minecraft
```

### 2. Minimal Base Image

Uses `-slim` variant to reduce attack surface:

```dockerfile
FROM arm64v8/openjdk:21-jdk-slim
```

### 3. No Unnecessary Packages

Only installs required packages:

```dockerfile
RUN apt-get install -y --no-install-recommends \
    wget curl ca-certificates
```

### 4. Clean Package Cache

Removes apt cache after installation:

```dockerfile
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

## Performance Optimization

### 1. Layer Ordering

Place frequently changing files last:

```dockerfile
# Static files first (better caching)
COPY server.properties /minecraft/server/

# Dynamic files last
COPY scripts/start.sh /minecraft/start.sh
```

### 2. Combine Commands

Reduce number of layers:

```dockerfile
# Bad: Multiple layers
RUN apt-get update
RUN apt-get install -y wget
RUN apt-get clean

# Good: Single layer
RUN apt-get update && \
    apt-get install -y wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### 3. Use .dockerignore

Exclude unnecessary files from build context:

```dockerignore
.git
.gitignore
*.md
docs/
tests/
node_modules/
backups/
data/
```

## Monitoring Image Size

### Check Image Size

```bash
# List images and sizes
docker images minecraft-server

# Detailed image inspection
docker inspect minecraft-server | grep -i size
```

### Analyze Layers

```bash
# Use dive tool to analyze layers
dive minecraft-server

# Or use docker history
docker history minecraft-server
```

## Troubleshooting

### Build Fails on Raspberry Pi

**Issue**: Build takes too long or fails

**Solution**:

- Use BuildKit: `export DOCKER_BUILDKIT=1`
- Build on more powerful machine and push to registry
- Use pre-built images from registry

### Image Too Large

**Issue**: Image size is larger than expected

**Solution**:

- Check for unnecessary packages
- Use multi-stage builds
- Remove build dependencies in final stage
- Use `.dockerignore` to exclude files

### Slow Builds

**Issue**: Builds are slow even with cache

**Solution**:

- Optimize layer order
- Combine RUN commands
- Use BuildKit
- Consider building on faster machine

## Advanced Optimizations

### 1. Distroless Images

For maximum security (advanced):

```dockerfile
FROM gcr.io/distroless/java21-debian12
# Note: Requires different approach for scripts
```

### 2. Alpine Linux

For smaller images (may have compatibility issues):

```dockerfile
FROM alpine:latest
# Requires different package manager and may have glibc issues
```

### 3. Custom Base Image

Create your own optimized base:

```dockerfile
FROM arm64v8/openjdk:21-jdk-slim AS base
# Add your customizations
```

## Best Practices Summary

1. ✅ Use multi-stage builds
2. ✅ Combine RUN commands
3. ✅ Remove package caches
4. ✅ Use non-root user
5. ✅ Order layers by change frequency
6. ✅ Use .dockerignore
7. ✅ Enable BuildKit
8. ✅ Set resource limits
9. ✅ Use health checks
10. ✅ Document build args

## Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [BuildKit](https://docs.docker.com/build/buildkit/)
- [Dockerfile Best Practices](https://docs.docker.com/reference/dockerfile/)

## See Also

- [Installation Guide](INSTALL.md) - Docker setup instructions
- [Development Guide](DEVELOPMENT.md) - Development workflow
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
