# Raspberry Pi 5 Compatibility Guide

This guide outlines the steps needed to ensure the project runs correctly on Raspberry Pi 5 (ARM64 architecture).

## Table of Contents

1. [Architecture Compatibility](#architecture-compatibility)
2. [Docker Configuration](#docker-configuration)
3. [Dependencies Verification](#dependencies-verification)
4. [Build Process](#build-process)
5. [Testing on Raspberry Pi](#testing-on-raspberry-pi)
6. [Performance Considerations](#performance-considerations)
7. [Troubleshooting](#troubleshooting)

## Architecture Compatibility

### Current Status

✅ **Dockerfile**: Uses `arm64v8/openjdk:21-jdk-slim` - ARM64 compatible  
✅ **Shell Scripts**: Architecture-agnostic (bash)  
✅ **Python API**: Pure Python - architecture-agnostic  
✅ **React Web**: JavaScript - architecture-agnostic  
⚠️ **Docker Compose**: May need platform specification  
⚠️ **Python Dependencies**: Need verification for ARM64  
⚠️ **Node.js Dependencies**: Need verification for ARM64

### Architecture Detection

The project should detect and handle ARM64 architecture:

```bash
# Check architecture
uname -m
# Should output: aarch64 (ARM64)

# Check in scripts
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
    echo "Running on ARM64"
fi
```

## Docker Configuration

### Dockerfile Verification

The Dockerfile already uses ARM64 base image:

```dockerfile
FROM arm64v8/openjdk:21-jdk-slim
```

**Action Required**: ✅ Already configured correctly

### Docker Compose Platform Specification

**Current Issue**: `docker-compose.yml` doesn't specify platform, which may cause issues when building on x86_64 and running on ARM64.

**Solution**: Add platform specification to `docker-compose.yml`:

```yaml
services:
  minecraft:
    platform: linux/arm64
    build:
      context: .
      dockerfile: Dockerfile
      # ... rest of config
```

**Action Required**: ⚠️ Add platform specification

### Building Docker Images

When building on Raspberry Pi 5:

```bash
# Build directly on Pi (recommended)
docker-compose build

# Or specify platform explicitly
docker buildx build --platform linux/arm64 -t minecraft-server .
```

**Action Required**: ✅ Works, but document build process

## Dependencies Verification

### Python Dependencies

All Python dependencies in `api/requirements.txt` are pure Python and should work on ARM64:

- Flask==3.0.0 ✅
- flask-cors==4.0.0 ✅
- flask-socketio==5.3.5 ✅
- eventlet==0.33.3 ✅
- bcrypt==4.1.2 ✅ (has C extensions, but supports ARM64)
- pyjwt==2.8.0 ✅
- authlib==1.3.0 ✅
- requests==2.31.0 ✅

**Action Required**: ✅ Verify installation on Pi

**Verification Steps**:

```bash
# On Raspberry Pi
cd ~/minecraft-server/api
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Should complete without errors
```

### Node.js Dependencies

All Node.js dependencies in `web/package.json` are JavaScript and should work on ARM64:

- React, Vite, Tailwind CSS - all architecture-agnostic ✅

**Action Required**: ✅ Verify build on Pi

**Verification Steps**:

```bash
# On Raspberry Pi
cd ~/minecraft-server/web
npm install
npm run build
# Should complete without errors
```

**Note**: Node.js must be installed on Raspberry Pi OS. The setup script should install it.

## Build Process

### On Raspberry Pi 5 (Recommended)

Building directly on the Pi ensures ARM64 compatibility:

```bash
# 1. Clone repository
cd ~
git clone https://github.com/and3rn3t/minecraft.git minecraft-server
cd minecraft-server

# 2. Run setup script
chmod +x scripts/setup-rpi.sh
./scripts/setup-rpi.sh

# 3. Build Docker image
docker-compose build

# 4. Start server
./scripts/manage.sh start
```

### Cross-Platform Building (Advanced)

If building on x86_64 for ARM64 (not recommended for production):

```bash
# Enable buildx
docker buildx create --name multiarch --use

# Build for ARM64
docker buildx build --platform linux/arm64 -t minecraft-server:arm64 .

# Or with docker-compose
docker-compose build --build-arg BUILDPLATFORM=linux/arm64
```

**Action Required**: ⚠️ Document cross-platform building (optional)

## Testing on Raspberry Pi

### Pre-Deployment Checklist

Before deploying to Raspberry Pi 5:

- [ ] **Hardware Ready**:

  - [ ] Raspberry Pi 5 (4GB or 8GB RAM)
  - [ ] MicroSD card (32GB+)
  - [ ] Power supply (27W USB-C)
  - [ ] Cooling solution (case with fan)
  - [ ] Network connection (Ethernet recommended)

- [ ] **Software Ready**:

  - [ ] Raspberry Pi OS (64-bit) flashed
  - [ ] SSH enabled
  - [ ] System updated: `sudo apt update && sudo apt upgrade -y`

- [ ] **Docker Ready**:
  - [ ] Docker installed: `docker --version`
  - [ ] Docker Compose installed: `docker-compose --version`
  - [ ] User in docker group: `groups | grep docker`

### Deployment Testing

1. **Clone and Setup**:

   ```bash
   cd ~
   git clone https://github.com/and3rn3t/minecraft.git minecraft-server
   cd minecraft-server
   chmod +x scripts/setup-rpi.sh
   ./scripts/setup-rpi.sh
   ```

2. **Verify Architecture**:

   ```bash
   uname -m  # Should show: aarch64
   docker info | grep Architecture  # Should show: aarch64
   ```

3. **Build Docker Image**:

   ```bash
   docker-compose build
   # Should complete without errors
   ```

4. **Start Server**:

   ```bash
   ./scripts/manage.sh start
   ./scripts/manage.sh status
   # Should show container as "Up"
   ```

5. **Test API** (if API server is running):

   ```bash
   curl http://localhost:5000/api/health
   # Should return JSON response
   ```

6. **Test Web Interface** (if web server is running):
   ```bash
   curl http://localhost:3000
   # Should return HTML
   ```

### Integration Testing

Run the test suite on Raspberry Pi:

```bash
# Python API tests
cd ~/minecraft-server
python3 -m pytest tests/api/ -v

# Shell script syntax checks
bash -n scripts/*.sh

# Docker Compose validation
docker-compose config
```

## Performance Considerations

### Memory Optimization

Raspberry Pi 5 has limited RAM (4GB or 8GB):

**Recommended Settings**:

- **4GB Pi**:

  - Minecraft: `MEMORY_MIN=1G`, `MEMORY_MAX=2G`
  - System: Leave 1-2GB for OS and Docker

- **8GB Pi**:
  - Minecraft: `MEMORY_MIN=2G`, `MEMORY_MAX=4G`
  - System: Leave 2-3GB for OS and Docker

**Action Required**: ✅ Already documented in README

### CPU Optimization

Raspberry Pi 5 has 4 cores. Optimize JVM flags in `scripts/start.sh`:

```bash
# Use appropriate GC for ARM64
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
```

**Action Required**: ✅ Already optimized in start.sh

### Storage Optimization

- Use high-quality microSD card (Class 10, A2 rating)
- Consider external SSD for better I/O
- Enable TRIM: `sudo systemctl enable fstrim.timer`

**Action Required**: ✅ Documented in image preparation guide

## Troubleshooting

### Common Issues

#### 1. Docker Build Fails

**Symptoms**: `docker-compose build` fails with architecture errors

**Solutions**:

```bash
# Check Docker platform
docker info | grep Architecture

# Force ARM64 build
docker buildx build --platform linux/arm64 -t minecraft-server .

# Or update docker-compose.yml to specify platform
```

#### 2. Python Dependencies Fail to Install

**Symptoms**: `pip install -r requirements.txt` fails

**Solutions**:

```bash
# Update pip
pip install --upgrade pip setuptools wheel

# Install build dependencies
sudo apt install python3-dev build-essential

# Try installing again
pip install -r requirements.txt
```

#### 3. Node.js Build Fails

**Symptoms**: `npm install` or `npm run build` fails

**Solutions**:

```bash
# Install Node.js (if not installed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Clear cache and retry
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### 4. Container Won't Start

**Symptoms**: Container exits immediately

**Solutions**:

```bash
# Check logs
docker-compose logs

# Check architecture compatibility
docker inspect minecraft-server | grep Architecture

# Verify image was built for ARM64
docker images minecraft-server
```

#### 5. Performance Issues

**Symptoms**: Server is slow or laggy

**Solutions**:

- Reduce memory allocation
- Lower view distance in `server.properties`
- Check CPU temperature: `vcgencmd measure_temp`
- Ensure adequate cooling
- Check for memory leaks: `docker stats`

## Action Items Summary

### Critical (Must Do)

1. ✅ **Dockerfile**: Already uses ARM64 base image
2. ⚠️ **Docker Compose**: Add `platform: linux/arm64` to docker-compose.yml
3. ⚠️ **Setup Script**: Verify Node.js installation for web interface
4. ⚠️ **Documentation**: Add ARM64 build instructions

### Important (Should Do)

5. ⚠️ **Python Dependencies**: Test installation on Pi
6. ⚠️ **Node.js Dependencies**: Test build on Pi
7. ⚠️ **Integration Tests**: Run full test suite on Pi
8. ⚠️ **Performance Testing**: Benchmark on actual hardware

### Optional (Nice to Have)

9. ⚠️ **Cross-Platform Build**: Document building for ARM64 from x86_64
10. ⚠️ **CI/CD**: Add ARM64 testing to CI pipeline
11. ⚠️ **Multi-Arch Images**: Publish multi-architecture Docker images

## Verification Checklist

Before considering the project "Raspberry Pi 5 ready":

- [ ] Dockerfile uses ARM64 base image ✅
- [ ] Docker Compose specifies platform
- [ ] All Python dependencies install on ARM64
- [ ] Node.js dependencies build on ARM64
- [ ] Docker image builds successfully on Pi
- [ ] Server starts and runs on Pi
- [ ] API server works on Pi
- [ ] Web interface works on Pi
- [ ] All scripts execute correctly
- [ ] Integration tests pass on Pi
- [ ] Performance is acceptable
- [ ] Documentation updated with Pi-specific instructions

## Next Steps

1. **Update docker-compose.yml** with platform specification
2. **Update setup-rpi.sh** to install Node.js if needed
3. **Test on actual Raspberry Pi 5** hardware
4. **Update documentation** with Pi-specific build instructions
5. **Add CI/CD** testing for ARM64 (if using GitHub Actions)

## Additional Resources

- [Raspberry Pi 5 Documentation](https://www.raspberrypi.com/documentation/)
- [Docker Multi-Architecture Builds](https://docs.docker.com/build/building/multi-platform/)
- [ARM64 Architecture Guide](https://en.wikipedia.org/wiki/AArch64)
- [Installation Guide](INSTALL.md)

---

**Last Updated**: 2025-01-27  
**Status**: In Progress - Needs verification on actual hardware
