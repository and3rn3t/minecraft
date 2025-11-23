# Raspberry Pi 5 Optimizations & Enhancements

This guide covers optimizations and enhancements specifically for Raspberry Pi 5 to maximize performance and efficiency.

## Table of Contents

1. [Docker Optimizations](#docker-optimizations)
2. [JVM Optimizations](#jvm-optimizations)
3. [System-Level Optimizations](#system-level-optimizations)
4. [Storage Optimizations](#storage-optimizations)
5. [Network Optimizations](#network-optimizations)
6. [Build Optimizations](#build-optimizations)
7. [Resource Management](#resource-management)
8. [Performance Monitoring](#performance-monitoring)
9. [Power Management](#power-management)

## Docker Optimizations

### Multi-Stage Build

Optimize Docker image size and build time:

```dockerfile
# Stage 1: Build dependencies
FROM arm64v8/openjdk:21-jdk-slim AS builder
RUN apt-get update && \
    apt-get install -y wget curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Stage 2: Runtime image
FROM arm64v8/openjdk:21-jre-slim
# Copy only runtime dependencies
COPY --from=builder /usr/lib/jvm /usr/lib/jvm
# ... rest of configuration
```

**Benefits**:

- Smaller final image (JRE instead of JDK)
- Faster builds with layer caching
- Better security (fewer packages)

### Layer Caching Optimization

Order Dockerfile commands by change frequency:

```dockerfile
# 1. Base image (rarely changes)
FROM arm64v8/openjdk:21-jre-slim

# 2. System packages (rarely changes)
RUN apt-get update && apt-get install -y wget curl && ...

# 3. User setup (rarely changes)
RUN useradd -m -U -d /minecraft -s /bin/bash minecraft

# 4. Configuration files (changes occasionally)
COPY --chown=minecraft:minecraft server.properties /minecraft/server/

# 5. Scripts (changes more frequently)
COPY --chown=minecraft:minecraft start.sh /minecraft/
```

### Build Arguments for Optimization

Add build-time optimizations:

```dockerfile
ARG BUILD_DATE
ARG VCS_REF
ARG MINECRAFT_VERSION=1.20.4

LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${MINECRAFT_VERSION}" \
      org.opencontainers.image.architecture="arm64"
```

### Docker Compose Resource Limits

Optimize resource allocation:

```yaml
services:
  minecraft:
    deploy:
      resources:
        limits:
          memory: ${MEMORY_MAX:-2G}
          cpus: '3.0' # Leave 1 core for system
        reservations:
          memory: ${MEMORY_MIN:-1G}
          cpus: '2.0'
```

## JVM Optimizations

### ARM64-Specific JVM Flags

Enhance JVM flags for ARM64 architecture:

```bash
# Add to start.sh
exec java -Xms${MEMORY_MIN} -Xmx${MEMORY_MAX} \
    # ARM64 optimizations
    -XX:+UseG1GC \
    -XX:+UnlockExperimentalVMOptions \
    -XX:+UseStringDeduplication \
    -XX:+OptimizeStringConcat \
    -XX:+UseCompressedOops \
    -XX:+UseCompressedClassPointers \
    # G1GC tuning for ARM64
    -XX:MaxGCPauseMillis=200 \
    -XX:G1HeapRegionSize=8M \
    -XX:G1NewSizePercent=30 \
    -XX:G1MaxNewSizePercent=40 \
    -XX:G1ReservePercent=20 \
    -XX:InitiatingHeapOccupancyPercent=15 \
    # Memory optimizations
    -XX:+AlwaysPreTouch \
    -XX:+DisableExplicitGC \
    -XX:+ParallelRefProcEnabled \
    -XX:MaxTenuringThreshold=1 \
    -XX:SurvivorRatio=32 \
    # Performance
    -XX:+PerfDisableSharedMem \
    -XX:+UseTransparentHugePages \
    -XX:+UseLargePages \
    # ARM64 specific
    -XX:+UseAES \
    -XX:+UseAESIntrinsics \
    -Djava.security.egd=file:/dev/urandom \
    -Dusing.aikars.flags=https://mcflags.emc.gs \
    -Daikars.new.flags=true \
    -jar ${MINECRAFT_JAR} \
    --nogui
```

### Adaptive Memory Allocation

Dynamically adjust memory based on available RAM:

```bash
# Detect available memory
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
AVAILABLE_RAM=$((TOTAL_RAM - 1024))  # Reserve 1GB for system

# Calculate optimal memory
if [ $AVAILABLE_RAM -lt 3072 ]; then
    MEMORY_MAX="1G"
    MEMORY_MIN="512M"
elif [ $AVAILABLE_RAM -lt 6144 ]; then
    MEMORY_MAX="2G"
    MEMORY_MIN="1G"
else
    MEMORY_MAX="4G"
    MEMORY_MIN="2G"
fi
```

### GC Logging for Optimization

Enable GC logging to tune performance:

```bash
exec java ... \
    -Xlog:gc*:file=/minecraft/server/logs/gc.log:time,uptime:filecount=5,filesize=10M \
    -jar ${MINECRAFT_JAR}
```

## System-Level Optimizations

### CPU Governor

Set CPU to performance mode:

```bash
# Install cpufrequtils
sudo apt install cpufrequtils -y

# Set to performance
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl enable cpufrequtils
sudo systemctl start cpufrequtils

# Verify
cpufreq-info | grep "governor"
```

### Memory and Swap Optimization

Optimize swap for SD card longevity:

```bash
# Reduce swap usage (for 4GB Pi)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change: CONF_SWAPSIZE=100 to CONF_SWAPSIZE=512
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Disable swap entirely if using 8GB Pi with enough RAM
sudo swapoff -a
sudo systemctl disable dphys-swapfile.service
```

### Kernel Parameters

Optimize kernel parameters for Minecraft server:

```bash
# Add to /etc/sysctl.conf
sudo nano /etc/sysctl.conf

# Add these lines:
vm.swappiness=1
vm.vfs_cache_pressure=50
vm.dirty_ratio=15
vm.dirty_background_ratio=5
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 67108864
net.ipv4.tcp_wmem=4096 65536 67108864
net.ipv4.tcp_congestion_control=bbr

# Apply changes
sudo sysctl -p
```

### Process Priority

Set higher priority for Docker/Minecraft:

```bash
# Add to docker-compose.yml
services:
  minecraft:
    deploy:
      resources:
        limits:
          cpus: '3.0'
        reservations:
          cpus: '2.0'
    # Or use nice priority
    command: nice -n -10 /minecraft/start.sh
```

## Storage Optimizations

### SD Card Longevity

Reduce writes to extend SD card life:

```bash
# Enable TRIM
sudo systemctl enable fstrim.timer
sudo systemctl start fstrim.timer

# Mount with noatime
# Edit /etc/fstab
sudo nano /etc/fstab
# Change: /dev/mmcblk0p2  /  ext4  defaults,noatime  0  1

# Reduce logging
sudo nano /etc/systemd/journald.conf
# Set: SystemMaxUse=50M
# Set: MaxRetentionSec=1week
sudo systemctl restart systemd-journald
```

### Use External SSD (Recommended)

For better performance and longevity:

1. **Format SSD**:

   ```bash
   sudo mkfs.ext4 /dev/sda1
   ```

2. **Mount SSD**:

   ```bash
   sudo mkdir /mnt/ssd
   sudo mount /dev/sda1 /mnt/ssd
   ```

3. **Move Docker data**:

   ```bash
   sudo systemctl stop docker
   sudo mv /var/lib/docker /mnt/ssd/
   sudo ln -s /mnt/ssd/docker /var/lib/docker
   sudo systemctl start docker
   ```

4. **Move Minecraft data**:
   ```bash
   sudo mv ~/minecraft-server/data /mnt/ssd/
   ln -s /mnt/ssd/data ~/minecraft-server/data
   ```

### Log Rotation

Optimize log management:

```bash
# Configure logrotate for Minecraft
sudo nano /etc/logrotate.d/minecraft

# Add:
/home/pi/minecraft-server/data/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pi pi
}
```

## Network Optimizations

### TCP Optimizations

Optimize network stack:

```bash
# Add to /etc/sysctl.conf
net.core.somaxconn=1024
net.ipv4.tcp_max_syn_backlog=2048
net.ipv4.tcp_slow_start_after_idle=0
net.ipv4.tcp_tw_reuse=1
net.ipv4.ip_local_port_range=10000 65535
```

### Network Interface Tuning

Optimize network interface:

```bash
# Edit /etc/network/interfaces
sudo nano /etc/network/interfaces

# Add for Ethernet:
iface eth0 inet dhcp
    pre-up /sbin/ethtool -s eth0 speed 1000 duplex full autoneg off
```

## Build Optimizations

### Build Cache

Use Docker build cache effectively:

```bash
# Build with cache
docker-compose build --parallel

# Or use BuildKit
DOCKER_BUILDKIT=1 docker-compose build
```

### Parallel Builds

Build multiple services in parallel:

```yaml
# docker-compose.yml
services:
  minecraft:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        BUILDKIT_INLINE_CACHE: 1
```

## Resource Management

### CPU Affinity

Pin Minecraft to specific cores:

```bash
# Add to docker-compose.yml
services:
  minecraft:
    deploy:
      resources:
        reservations:
          cpus: '0-2'  # Use cores 0, 1, 2
```

### Memory Limits

Set appropriate memory limits:

```yaml
# For 4GB Pi
deploy:
  resources:
    limits:
      memory: 2G
    reservations:
      memory: 1G

# For 8GB Pi
deploy:
  resources:
    limits:
      memory: 4G
    reservations:
      memory: 2G
```

### OOM Killer Protection

Protect Minecraft from OOM killer:

```bash
# Add to docker-compose.yml
services:
  minecraft:
    oom_kill_disable: false
    oom_score_adj: -500  # Lower priority for OOM killer
```

## Performance Monitoring

### Enhanced Monitoring Script

Create comprehensive monitoring:

```bash
#!/bin/bash
# scripts/monitor-rpi5.sh

echo "=== Raspberry Pi 5 Performance Monitor ==="
echo ""

# CPU
echo "CPU:"
echo "  Temperature: $(vcgencmd measure_temp | cut -d= -f2)"
echo "  Frequency: $(vcgencmd measure_clock arm | awk -F= '{print $2/1000000 " MHz"}')"
echo "  Throttled: $(vcgencmd get_throttled)"
echo ""

# Memory
echo "Memory:"
free -h | grep -E "Mem|Swap"
echo ""

# Disk
echo "Disk:"
df -h / | tail -1
echo ""

# Docker
echo "Docker:"
docker stats --no-stream minecraft-server
echo ""

# Network
echo "Network:"
ifconfig | grep -E "inet |RX packets|TX packets"
```

### Prometheus Metrics

Enhanced metrics for Raspberry Pi:

```bash
# Add to prometheus-exporter.sh
# CPU temperature
CPU_TEMP=$(vcgencmd measure_temp | cut -d= -f2 | cut -d\' -f1)
echo "rpi_cpu_temperature $CPU_TEMP"

# CPU frequency
CPU_FREQ=$(vcgencmd measure_clock arm | awk -F= '{print $2/1000000}')
echo "rpi_cpu_frequency $CPU_FREQ"

# Throttling
THROTTLED=$(vcgencmd get_throttled | cut -d= -f2)
echo "rpi_throttled $THROTTLED"

# Voltage
VOLTAGE=$(vcgencmd measure_volts | cut -d= -f2 | cut -dV -f1)
echo "rpi_voltage $VOLTAGE"
```

## Power Management

### Disable Unnecessary Services

Reduce background processes:

```bash
# Disable Bluetooth (if not needed)
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# Disable WiFi power management (if using Ethernet)
sudo iwconfig wlan0 power off

# Disable HDMI (if headless)
sudo /usr/bin/tvservice -o
```

### USB Power Management

Optimize USB power:

```bash
# Disable USB autosuspend
echo 'SUBSYSTEM=="usb", ACTION=="add", ATTR{power/autosuspend}="-1"' | sudo tee /etc/udev/rules.d/50-usb-power.rules
```

## Implementation Script

Create an optimization script:

```bash
#!/bin/bash
# scripts/optimize-rpi5.sh

set -e

echo "Optimizing Raspberry Pi 5 for Minecraft Server..."

# 1. CPU Governor
echo "Setting CPU governor to performance..."
sudo apt install -y cpufrequtils
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl enable cpufrequtils
sudo systemctl start cpufrequtils

# 2. Swap optimization
echo "Optimizing swap..."
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# 3. Kernel parameters
echo "Optimizing kernel parameters..."
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF
vm.swappiness=1
vm.vfs_cache_pressure=50
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_congestion_control=bbr
EOF
sudo sysctl -p

# 4. TRIM
echo "Enabling TRIM..."
sudo systemctl enable fstrim.timer
sudo systemctl start fstrim.timer

# 5. Disable unnecessary services
echo "Disabling unnecessary services..."
sudo systemctl disable bluetooth 2>/dev/null || true

echo "Optimization complete!"
echo "Please reboot for all changes to take effect."
```

## Performance Benchmarks

### Before/After Comparison

Track performance improvements:

```bash
# Before optimization
./scripts/monitor-rpi5.sh > benchmark-before.txt

# Apply optimizations

# After optimization
./scripts/monitor-rpi5.sh > benchmark-after.txt

# Compare
diff benchmark-before.txt benchmark-after.txt
```

## Quick Reference

### Essential Optimizations

1. **CPU Governor**: Set to performance
2. **Swap**: Reduce or disable
3. **Kernel Parameters**: Optimize for networking
4. **TRIM**: Enable for SD card
5. **JVM Flags**: ARM64-specific optimizations
6. **Docker Resources**: Set appropriate limits

### Performance Targets

- **TPS**: 20 TPS (constant)
- **CPU Usage**: <80% average
- **Memory**: <90% of allocated
- **Temperature**: <70°C under load
- **Network Latency**: <50ms local

## Additional Resources

- [Raspberry Pi 5 Performance Tuning](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [JVM Tuning Guide](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/)

---

**Last Updated**: 2025-01-27  
**Status**: Ready for implementation
