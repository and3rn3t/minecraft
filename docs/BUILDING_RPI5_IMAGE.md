# Building Docker Image for Raspberry Pi 5

This guide provides step-by-step instructions for building a Docker image optimized for Raspberry Pi 5 (ARM64 architecture).

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Building Methods](#building-methods)
4. [Method 1: Build Directly on Raspberry Pi 5](#method-1-build-directly-on-raspberry-pi-5)
5. [Method 2: Cross-Platform Build from x86_64](#method-2-cross-platform-build-from-x86_64)
6. [Method 3: Build and Push to Registry](#method-3-build-and-push-to-registry)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

## Quick Start

If you're on a Raspberry Pi 5, the simplest method:

```bash
# Navigate to project directory
cd ~/minecraft-server

# Build the image
docker build -t minecraft-server:latest .

# Or use docker-compose (recommended)
docker-compose build
```

## Prerequisites

### On Raspberry Pi 5

- **Docker** installed (via `setup-rpi.sh`)
- **Docker Compose** installed
- **Git** to clone the repository
- **Internet connection** for downloading base images

Verify Docker installation:

```bash
docker --version
docker-compose --version
```

### On Development Machine (x86_64)

If building from a development machine:

- **Docker** with **Docker Buildx** enabled
- **Internet connection** for downloading base images

Verify Buildx availability:

```bash
docker buildx version
```

If not available, install Docker Desktop or update Docker to a version that includes buildx.

## Building Methods

You have three main options for building the image:

1. **Build directly on Raspberry Pi 5** (simplest, native build)
2. **Cross-platform build from x86_64** (faster, requires buildx)
3. **Build and push to registry** (best for distribution)

Choose based on your needs:

- **Local development**: Method 1 or 2
- **Distribution**: Method 3
- **Speed**: Method 2 (from powerful machine)
- **Simplicity**: Method 1 (on Raspberry Pi 5)

## Method 1: Build Directly on Raspberry Pi 5

This is the simplest method when you have access to the Raspberry Pi 5.

### Step 1: Clone Repository

```bash
cd ~
git clone https://github.com/and3rn3t/minecraft.git minecraft-server
cd minecraft-server
```

### Step 2: Build with Docker Compose (Recommended)

```bash
# Build the image
docker-compose build

# Or build with specific version
MINECRAFT_VERSION=1.21.0 docker-compose build
```

### Step 3: Build with Docker (Alternative)

```bash
# Basic build
docker build -t minecraft-server:latest .

# Build with custom version
docker build \
  --build-arg MINECRAFT_VERSION=1.21.0 \
  -t minecraft-server:1.21.0 .

# Build with BuildKit for better caching
DOCKER_BUILDKIT=1 docker build -t minecraft-server:latest .
```

### Step 4: Verify Build

```bash
# Check image was created
docker images minecraft-server

# Check image architecture
docker inspect minecraft-server:latest | grep Architecture
# Should show: "Architecture": "arm64"
```

### Advantages

- ✅ No cross-compilation needed
- ✅ Native ARM64 build
- ✅ Simple setup
- ✅ Best compatibility

### Disadvantages

- ❌ Slower on Raspberry Pi 5
- ❌ Requires access to Raspberry Pi 5

### Estimated Build Time

- **First build**: 10-20 minutes (depending on internet speed)
- **Subsequent builds**: 2-5 minutes (with cache)

## Method 2: Cross-Platform Build from x86_64

Build ARM64 image from a more powerful x86_64 machine (faster builds).

### Step 1: Setup Buildx Builder

```bash
# Setup multi-architecture builder
./scripts/build-multiarch.sh setup

# Or manually
docker buildx create --name multiarch-builder --use --bootstrap
```

### Step 2: Build for ARM64

```bash
# Build for ARM64 only (loads into local Docker)
./scripts/build-multiarch.sh arch arm64

# Or manually
docker buildx build \
  --platform linux/arm64 \
  --build-arg MINECRAFT_VERSION=1.20.4 \
  --tag minecraft-server:latest \
  --load \
  .
```

### Step 3: Save and Transfer Image

```bash
# Save image to tar file
docker save minecraft-server:latest | gzip > minecraft-server-arm64.tar.gz

# Transfer to Raspberry Pi 5
scp minecraft-server-arm64.tar.gz pi@minecraft-server.local:~/minecraft-server/

# On Raspberry Pi 5, load the image
docker load < minecraft-server-arm64.tar.gz
```

### Advantages

- ✅ Faster builds (on powerful machine)
- ✅ Can build without Raspberry Pi 5
- ✅ Good for CI/CD

### Disadvantages

- ❌ Requires buildx setup
- ❌ Need to transfer image to Raspberry Pi 5
- ❌ Cross-compilation (may have issues)

### Estimated Build Time

- **First build**: 5-10 minutes (on powerful machine)
- **Image transfer**: 1-5 minutes (depending on network)

## Method 3: Build and Push to Registry

Best for distribution and CI/CD. Build multi-architecture images and push to Docker Hub or other registry.

### Step 1: Setup Buildx Builder

```bash
# Setup multi-architecture builder
./scripts/build-multiarch.sh setup
```

### Step 2: Login to Registry

```bash
# Login to Docker Hub
docker login

# Or for other registries
docker login registry.example.com
```

### Step 3: Build and Push

```bash
# Build for all architectures and push
./scripts/build-multiarch.sh all

# Or manually
docker buildx build \
  --platform linux/arm64,linux/arm/v7,linux/amd64 \
  --build-arg MINECRAFT_VERSION=1.20.4 \
  --tag yourusername/minecraft-server:latest \
  --tag yourusername/minecraft-server:1.20.4 \
  --push \
  .
```

### Step 4: Pull on Raspberry Pi 5

```bash
# Pull the ARM64 image (automatic)
docker pull yourusername/minecraft-server:latest

# Verify architecture
docker inspect yourusername/minecraft-server:latest | grep Architecture
```

### Advantages

- ✅ Can build once, deploy everywhere
- ✅ Supports multiple architectures
- ✅ Good for CI/CD pipelines
- ✅ No manual image transfer

### Disadvantages

- ❌ Requires registry account
- ❌ More complex setup

### Using with Docker Compose

Update `docker-compose.yml`:

```yaml
services:
  minecraft:
    image: yourusername/minecraft-server:latest
    # Remove build section if using pre-built image
    # build: ...
```

## Verification

### Check Image Architecture

```bash
# Check architecture
docker inspect minecraft-server:latest | grep Architecture

# Should show for Raspberry Pi 5:
# "Architecture": "arm64"
```

### Test Image

```bash
# Run a test container
docker run --rm minecraft-server:latest java -version

# Should show ARM64 Java version
```

### Check Image Size

```bash
# List images with sizes
docker images minecraft-server

# Typical ARM64 image size: ~400-450MB
```

## Troubleshooting

### Build Fails: "exec format error"

**Issue**: Wrong architecture or missing buildx.

**Solution**:

```bash
# Ensure you're building for ARM64
docker buildx build --platform linux/arm64 ...

# Or build directly on Raspberry Pi 5
```

### Build Takes Too Long

**Issue**: Slow build process.

**Solution**:

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1
docker build ...

# Or build on more powerful machine and transfer
```

### Cannot Load Image: "exec format error"

**Issue**: Image architecture doesn't match Raspberry Pi 5.

**Solution**:

```bash
# Verify image architecture
docker inspect minecraft-server:latest | grep Architecture

# Rebuild for ARM64
docker buildx build --platform linux/arm64 --load ...
```

### Out of Memory During Build

**Issue**: Raspberry Pi 5 runs out of memory.

**Solution**:

```bash
# Reduce parallel builds
DOCKER_BUILDKIT=1 DOCKER_BUILDKIT_BUILDKIT_INLINE_CACHE=1 docker build ...

# Or build on more powerful machine
# Or add swap space to Raspberry Pi 5
```

### Base Image Pull Fails

**Issue**: Cannot download base image.

**Solution**:

```bash
# Check internet connection
ping -c 3 8.8.8.8

# Try pulling base image manually
docker pull arm64v8/openjdk:21-jdk-slim

# Check Docker daemon is running
sudo systemctl status docker
```

## Best Practices

### 1. Use Docker Compose for Local Development

```bash
# Build and run with one command
docker-compose up --build
```

### 2. Enable BuildKit

```bash
# Add to ~/.docker/config.json or use environment variable
export DOCKER_BUILDKIT=1
```

### 3. Use Multi-Stage Builds

The Dockerfile already uses multi-stage builds for optimization.

### 4. Tag Images Properly

```bash
# Tag with version
docker tag minecraft-server:latest minecraft-server:1.20.4

# Tag for registry
docker tag minecraft-server:latest yourusername/minecraft-server:latest
```

### 5. Clean Up Old Images

```bash
# Remove unused images
docker image prune -a

# Remove specific image
docker rmi minecraft-server:old-tag
```

## Next Steps

After building the image:

1. **Start the server**: See [README.md](../README.md) for startup instructions
2. **Configure server**: See [CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md)
3. **Set up backups**: See [BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md)
4. **Optimize performance**: See [RASPBERRY_PI_OPTIMIZATIONS.md](RASPBERRY_PI_OPTIMIZATIONS.md)

## See Also

- [Multi-Architecture Guide](MULTI_ARCHITECTURE.md) - Detailed multi-arch build guide
- [Docker Optimization Guide](DOCKER_OPTIMIZATION.md) - Image optimization techniques
- [Installation Guide](INSTALL.md) - Complete setup instructions
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
