# Multi-Architecture Support Guide

This guide covers building and running the Minecraft Server on multiple CPU architectures, including ARM64, ARM32, and x86_64.

## Overview

The project supports multiple architectures:

- **ARM64 (linux/arm64)** - Raspberry Pi 5, Apple Silicon, AWS Graviton
- **ARM32 (linux/arm/v7)** - Raspberry Pi 4 and earlier
- **AMD64/x86_64 (linux/amd64)** - Intel/AMD processors

## Quick Start

### Build for All Architectures

```bash
# Build and push to registry (requires Docker Hub or other registry)
./scripts/build-multiarch.sh all
```

### Build for Specific Architecture

```bash
# Build for ARM64 (Raspberry Pi 5)
./scripts/build-multiarch.sh arch arm64

# Build for ARM32 (Raspberry Pi 4)
./scripts/build-multiarch.sh arch arm32

# Build for x86_64
./scripts/build-multiarch.sh arch amd64
```

## Prerequisites

### Docker Buildx

Multi-architecture builds require Docker Buildx:

```bash
# Check if buildx is available
docker buildx version

# If not available, install Docker Desktop or update Docker
# Docker Desktop includes buildx by default
```

### Setup Buildx Builder

```bash
# Setup multi-architecture builder
./scripts/build-multiarch.sh setup
```

This creates a buildx builder instance with QEMU emulation support.

## Architecture Details

### ARM64 (linux/arm64)

**Use Cases**:

- Raspberry Pi 5
- Apple Silicon (M1/M2/M3 Macs)
- AWS Graviton instances
- Modern ARM servers

**Base Image**: `arm64v8/openjdk:21-jdk-slim`

**Performance**: Best performance on ARM64 hardware

### ARM32 (linux/arm/v7)

**Use Cases**:

- Raspberry Pi 4 and earlier
- Older ARM devices
- Embedded systems

**Base Image**: `arm32v7/openjdk:21-jdk-slim`

**Performance**: Lower performance than ARM64, but compatible with older hardware

**Note**: ARM32 support may have limitations due to 32-bit architecture constraints.

### AMD64/x86_64 (linux/amd64)

**Use Cases**:

- Intel/AMD desktop and server processors
- Most cloud providers (AWS, GCP, Azure)
- Development machines

**Base Image**: `openjdk:21-jdk-slim`

**Performance**: Excellent performance on x86_64 hardware

## Building Images

### Single Architecture Build

Build for your current architecture:

```bash
# Standard Docker build (uses current architecture)
docker build -t minecraft-server:latest .
```

### Multi-Architecture Build

Build for multiple architectures:

```bash
# Build for all supported architectures
./scripts/build-multiarch.sh all

# Or manually with docker buildx
docker buildx build \
  --platform linux/arm64,linux/arm/v7,linux/amd64 \
  --tag minecraft-server:latest \
  --push .
```

### Architecture-Specific Build

Build for a specific architecture:

```bash
# ARM64
./scripts/build-multiarch.sh arch arm64

# ARM32
./scripts/build-multiarch.sh arch arm32

# AMD64
./scripts/build-multiarch.sh arch amd64
```

## Dockerfile Architecture Support

The Dockerfile uses Docker's automatic architecture detection:

```dockerfile
# Docker buildx automatically selects the correct base image
# based on the --platform flag
FROM openjdk:21-jdk-slim AS base
```

When building with `--platform`, Docker automatically:

- For `linux/arm64`: Uses ARM64-compatible base image
- For `linux/arm/v7`: Uses ARM32-compatible base image
- For `linux/amd64`: Uses x86_64 base image

The `openjdk:21-jdk-slim` image is multi-architecture and Docker will pull the correct variant.

## Running on Different Architectures

### Raspberry Pi 5 (ARM64)

```bash
# Standard setup (already ARM64)
./setup-rpi.sh
./manage.sh start
```

### Raspberry Pi 4 (ARM32)

```bash
# Use ARM32 image
docker pull minecraft-server:latest-arm32
docker tag minecraft-server:latest-arm32 minecraft-server:latest

# Or build locally
./scripts/build-multiarch.sh arch arm32
./manage.sh start
```

### x86_64 Systems

```bash
# Pull or build AMD64 image
docker pull minecraft-server:latest-amd64
docker tag minecraft-server:latest-amd64 minecraft-server:latest

# Or build locally
./scripts/build-multiarch.sh arch amd64
./manage.sh start
```

## Docker Compose Configuration

### Architecture-Specific Compose Files

Create `docker-compose.arm64.yml`:

```yaml
services:
  minecraft:
    image: minecraft-server:latest-arm64
    # ... rest of config
```

Create `docker-compose.amd64.yml`:

```yaml
services:
  minecraft:
    image: minecraft-server:latest-amd64
    # ... rest of config
```

### Using with Docker Compose

```bash
# ARM64
docker-compose -f docker-compose.yml -f docker-compose.arm64.yml up -d

# AMD64
docker-compose -f docker-compose.yml -f docker-compose.amd64.yml up -d
```

## Registry Setup

### Pushing Multi-Architecture Images

To push multi-architecture images to a registry:

```bash
# Login to registry
docker login

# Build and push
./scripts/build-multiarch.sh all
```

### Pulling Architecture-Specific Images

Docker automatically pulls the correct image for your platform:

```bash
# Docker automatically selects correct architecture
docker pull minecraft-server:latest
```

## Performance Considerations

### ARM64 vs ARM32

- **ARM64**: Better performance, 64-bit addressing, recommended for Raspberry Pi 5
- **ARM32**: Compatibility with older hardware, 32-bit limitations

### x86_64 vs ARM

- **x86_64**: Generally faster, more mature ecosystem
- **ARM**: Lower power consumption, cost-effective

### Emulation Performance

Running ARM images on x86_64 (or vice versa) uses QEMU emulation:

- **Performance**: Significantly slower (10-50x)
- **Use Case**: Development and testing only
- **Production**: Always use native architecture

## Troubleshooting

### Build Fails on Cross-Architecture

**Issue**: Build fails when building for different architecture

**Solution**:

- Ensure buildx is set up: `./scripts/build-multiarch.sh setup`
- Check QEMU is installed (usually automatic with buildx)
- Try building for native architecture first

### Wrong Architecture Image

**Issue**: Pulled image doesn't match system architecture

**Solution**:

- Check architecture: `docker image inspect minecraft-server:latest | grep Architecture`
- Pull specific architecture: `docker pull --platform linux/arm64 minecraft-server:latest`
- Rebuild for correct architecture

### Performance Issues

**Issue**: Server runs slowly on target architecture

**Solution**:

- Verify correct architecture is running
- Check if emulation is being used (shouldn't be in production)
- Review memory and CPU allocation
- Consider architecture-specific optimizations

## CI/CD Integration

### GitHub Actions Multi-Architecture Build

```yaml
name: Multi-Architecture Build

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          platforms: linux/arm64,linux/arm/v7,linux/amd64
          push: true
          tags: minecraft-server:latest
```

## Best Practices

### 1. Build for Target Architecture

Always build for the architecture you'll run on:

```bash
# On Raspberry Pi 5
./scripts/build-multiarch.sh arch arm64

# On x86_64 development machine
./scripts/build-multiarch.sh arch amd64
```

### 2. Use Multi-Architecture Images in Registry

For distribution, build and push multi-architecture images:

```bash
./scripts/build-multiarch.sh all
```

### 3. Test on Target Architecture

Always test on the target architecture before production deployment.

### 4. Document Architecture Requirements

Document which architectures are supported and tested.

## Resources

- [Docker Buildx Documentation](https://docs.docker.com/build/buildx/)
- [Multi-Architecture Images](https://docs.docker.com/build/building/multi-platform/)
- [QEMU Emulation](https://www.qemu.org/)

## See Also

- [Docker Optimization Guide](DOCKER_OPTIMIZATION.md) - Image optimization
- [Installation Guide](INSTALL.md) - Setup instructions
- [Performance Benchmarking](PERFORMANCE_BENCHMARKING.md) - Performance testing
