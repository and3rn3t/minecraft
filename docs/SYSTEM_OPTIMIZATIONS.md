# System and Filesystem Optimizations

This guide covers comprehensive system and filesystem optimizations for the Minecraft server on Raspberry Pi 5.

## Table of Contents

1. [Filesystem Optimizations](#filesystem-optimizations)
2. [System-Level Optimizations](#system-level-optimizations)
3. [Code Optimizations](#code-optimizations)
4. [Docker Optimizations](#docker-optimizations)
5. [Log Management](#log-management)
6. [Disk Space Management](#disk-space-management)
7. [Memory Optimizations](#memory-optimizations)
8. [Network Optimizations](#network-optimizations)
9. [Automated Cleanup](#automated-cleanup)

## Filesystem Optimizations

### Mount Options

Optimize filesystem mount options for better performance and SD card longevity:

```bash
# Edit /etc/fstab
sudo nano /etc/fstab

# Add noatime, nodiratime to reduce writes
# Change from:
/dev/mmcblk0p2  /  ext4  defaults,noatime  0  1

# To:
/dev/mmcblk0p2  /  ext4  defaults,noatime,nodiratime,commit=60  0  1
```

**Benefits:**

- `noatime`: Don't update access times (reduces writes)
- `nodiratime`: Don't update directory access times
- `commit=60`: Commit changes every 60 seconds (reduces writes, slight risk)

### Use tmpfs for Temporary Files

Move temporary files to RAM:

```bash
# Add to /etc/fstab
sudo nano /etc/fstab

# Add these lines:
tmpfs /tmp tmpfs defaults,noatime,size=512M 0 0
tmpfs /var/tmp tmpfs defaults,noatime,size=256M 0 0
tmpfs /home/pi/minecraft-server/tmp tmpfs defaults,noatime,size=256M 0 0
```

**Benefits:**

- Faster I/O (RAM is much faster than SD card)
- Reduces SD card wear
- Automatic cleanup on reboot

### Enable TRIM for SD Card

```bash
# Enable TRIM timer (weekly)
sudo systemctl enable fstrim.timer
sudo systemctl start fstrim.timer

# Manual TRIM
sudo fstrim -v /
```

### I/O Scheduler Optimization

Set optimal I/O scheduler for SD card:

```bash
# Check current scheduler
cat /sys/block/mmcblk0/queue/scheduler

# Set to mq-deadline (better for SD cards)
echo mq-deadline | sudo tee /sys/block/mmcblk0/queue/scheduler

# Make permanent
echo 'ACTION=="add|change", KERNEL=="mmcblk[0-9]*", ATTR{queue/scheduler}="mq-deadline"' | \
    sudo tee /etc/udev/rules.d/60-ioscheduler.rules
```

## System-Level Optimizations

### Kernel Parameters (sysctl)

Optimize kernel parameters:

```bash
# Edit /etc/sysctl.conf
sudo nano /etc/sysctl.conf

# Add these optimizations:
# Memory management
vm.swappiness=1                    # Minimize swap usage
vm.vfs_cache_pressure=50           # Keep more inode/dentry cache
vm.dirty_ratio=15                  # Write dirty pages at 15% memory
vm.dirty_background_ratio=5       # Start writing at 5%
vm.overcommit_memory=1             # Allow memory overcommit

# Network optimizations
net.core.rmem_max=134217728        # 128MB max receive buffer
net.core.wmem_max=134217728        # 128MB max send buffer
net.core.somaxconn=1024            # Max pending connections
net.ipv4.tcp_rmem=4096 87380 67108864
net.ipv4.tcp_wmem=4096 65536 67108864
net.ipv4.tcp_congestion_control=bbr  # BBR congestion control
net.ipv4.tcp_slow_start_after_idle=0
net.ipv4.tcp_tw_reuse=1
net.ipv4.ip_local_port_range=10000 65535

# File system
fs.file-max=2097152                # Increase max open files
fs.inotify.max_user_watches=524288

# Apply immediately
sudo sysctl -p
```

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

### Swap Optimization

Reduce or disable swap for better performance:

```bash
# For 4GB Pi: Reduce swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change: CONF_SWAPSIZE=100 to CONF_SWAPSIZE=512
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# For 8GB Pi: Disable swap entirely
sudo swapoff -a
sudo systemctl disable dphys-swapfile.service
```

## Code Optimizations

### API Response Caching

Add caching to reduce database/disk reads:

```python
# In api/server.py, add caching decorator
from functools import lru_cache
import time

# Cache status endpoint for 5 seconds
@lru_cache(maxsize=128)
def get_cached_status():
    # Expensive operation
    return get_server_status()

# Clear cache periodically
def clear_cache():
    get_cached_status.cache_clear()
```

### Lazy Loading

Load heavy modules only when needed:

```python
# Instead of importing at top
def get_heavy_module():
    if not hasattr(get_heavy_module, '_module'):
        import heavy_module
        get_heavy_module._module = heavy_module
    return get_heavy_module._module
```

### Connection Pooling

Reuse database/API connections:

```python
# Use connection pooling for external APIs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=Retry(total=3, backoff_factor=0.3)
)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

## Docker Optimizations

### Build Cache Optimization

```dockerfile
# Order Dockerfile by change frequency
# 1. Base image (rarely changes)
FROM arm64v8/openjdk:21-jre-slim

# 2. System packages (rarely changes)
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# 3. Configuration (changes occasionally)
COPY server.properties /minecraft/server/

# 4. Application code (changes frequently)
COPY start.sh /minecraft/
```

### Layer Optimization

```dockerfile
# Combine RUN commands to reduce layers
RUN apt-get update && \
    apt-get install -y wget curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### Resource Limits

```yaml
# docker-compose.yml
services:
  minecraft:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '3.0'
        reservations:
          memory: 1G
          cpus: '2.0'
    # Use tmpfs for temporary files
    tmpfs:
      - /tmp:size=512M,noatime
      - /minecraft/server/logs:size=256M,noatime
```

## Log Management

### Log Rotation

Configure automatic log rotation:

```bash
# Create logrotate config
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
    sharedscripts
    postrotate
        docker exec minecraft-server kill -USR1 1 2>/dev/null || true
    endscript
}

/home/pi/minecraft-server/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pi pi
}
```

### Docker Log Rotation

```yaml
# docker-compose.yml
services:
  minecraft:
    logging:
      driver: 'json-file'
      options:
        max-size: '10m'
        max-file: '3'
        compress: 'true'
```

### Systemd Journal Limits

```bash
# Edit journal config
sudo nano /etc/systemd/journald.conf

# Set:
SystemMaxUse=50M
SystemKeepFree=100M
MaxRetentionSec=1week
MaxFileSec=1day

# Restart journal
sudo systemctl restart systemd-journald
```

## Disk Space Management

### Automated Cleanup Script

```bash
#!/bin/bash
# scripts/cleanup-system.sh

# Clean Docker
docker system prune -af --volumes --filter "until=168h"  # 7 days

# Clean old backups (keep last 10)
find ~/minecraft-server/backups -name "*.tar.gz" -type f -mtime +30 -delete

# Clean old logs
find ~/minecraft-server/data/logs -name "*.log.gz" -type f -mtime +14 -delete
find ~/minecraft-server/logs -name "*.log" -type f -mtime +30 -delete

# Clean package cache
sudo apt-get clean
sudo apt-get autoremove -y

# Clean temporary files
rm -rf /tmp/*
rm -rf ~/.cache/*

# Report disk usage
df -h
du -sh ~/minecraft-server/*
```

### Disk Space Monitoring

```bash
# Add to crontab for daily check
# crontab -e
0 2 * * * /home/pi/minecraft-server/scripts/check-disk-space.sh
```

## Memory Optimizations

### Python Memory Management

```python
# In api/server.py
import gc

# Force garbage collection periodically
def periodic_gc():
    gc.collect()

# Use generators for large datasets
def get_large_dataset():
    for item in large_list:
        yield process(item)
```

### Node.js Memory Limits

```bash
# For web build process
export NODE_OPTIONS="--max-old-space-size=512"
npm run build
```

## Network Optimizations

### TCP Tuning

Already covered in sysctl.conf above.

### Connection Limits

```bash
# Increase file descriptor limits
sudo nano /etc/security/limits.conf

# Add:
* soft nofile 65535
* hard nofile 65535
pi soft nofile 65535
pi hard nofile 65535
```

## Automated Cleanup

### Systemd Timer for Cleanup

Create `/etc/systemd/system/minecraft-cleanup.service`:

```ini
[Unit]
Description=Minecraft Server Cleanup
After=network-online.target

[Service]
Type=oneshot
User=pi
Group=pi
WorkingDirectory=/home/pi/minecraft-server
ExecStart=/home/pi/minecraft-server/scripts/cleanup-system.sh
```

Create `/etc/systemd/system/minecraft-cleanup.timer`:

```ini
[Unit]
Description=Daily Minecraft Cleanup
Requires=minecraft-cleanup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable minecraft-cleanup.timer
sudo systemctl start minecraft-cleanup.timer
```

## Implementation Script

See `scripts/optimize-system.sh` for automated implementation.

## Quick Reference

### Essential Optimizations

1. **Filesystem**: Add `noatime,nodiratime` to fstab
2. **tmpfs**: Use RAM for temporary files
3. **TRIM**: Enable fstrim.timer
4. **sysctl**: Optimize kernel parameters
5. **CPU Governor**: Set to performance
6. **Swap**: Reduce or disable
7. **Log Rotation**: Configure logrotate
8. **Docker**: Set resource limits and log rotation
9. **Cleanup**: Automated daily cleanup

### Performance Targets

- **Disk I/O**: <50% utilization
- **Memory**: <90% usage
- **CPU**: <80% average
- **Disk Space**: >20% free
- **Log Files**: <1GB total

## Monitoring

Use the monitoring script to track optimizations:

```bash
./scripts/monitor-rpi5.sh
```

## Additional Resources

- [Raspberry Pi 5 Performance Tuning](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [Linux Performance Tuning](https://www.kernel.org/doc/Documentation/sysctl/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
