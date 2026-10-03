# System and Filesystem Optimizations

Host-level tuning for the Raspberry Pi 5 that runs the server: filesystem options,
the kernel, swap and logs. Pi-specific tuning (JVM flags, Docker limits, power,
network) is in [RASPBERRY_PI_OPTIMIZATIONS.md](RASPBERRY_PI_OPTIMIZATIONS.md), and
image size and build caching in [DOCKER_OPTIMIZATION.md](DOCKER_OPTIMIZATION.md).

Most of this is applied for you by `scripts/optimize-system.sh`; see
[What the Script Applies](#what-the-script-applies) for what it does and what stays manual.

## Table of Contents

1. [Filesystem Optimizations](#filesystem-optimizations)
2. [System-Level Optimizations](#system-level-optimizations)
3. [Log Management](#log-management)
4. [Freeing Disk Space](#freeing-disk-space)
5. [What the Script Applies](#what-the-script-applies)

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

`docker-compose.yml` already limits the container log to three files of 10 MB. This
is the setting, if you need to change it:

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

## Freeing Disk Space

Backups are pruned by retention policy, not by this guide: see
[BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md) and `scripts/cleanup-backups.sh`.
Game and application logs rotate as above, and the log tools are in
[LOG_MANAGEMENT.md](LOG_MANAGEMENT.md).

`scripts/cleanup-system.sh` is a manual clean-up for Docker leftovers, old logs and
package and tool caches, and it reports disk usage before it finishes. Run it by hand
when the disk is filling up. Read it first: it is a plain shell script, and nothing
schedules it.

## What the Script Applies

`scripts/optimize-system.sh` makes nine changes, and skips any that are already in place:

1. `noatime,nodiratime,commit=60` on the root filesystem (`/etc/fstab`)
2. Enables the `fstrim.timer`
3. An I/O scheduler rule (`/etc/udev/rules.d/60-ioscheduler.rules`)
4. Kernel parameters (sysctl)
5. The `performance` CPU governor
6. Swap: shrunk on a 4GB Pi, and on an 8GB Pi it asks whether to disable it
7. Log rotation
8. systemd journal size limits
9. File descriptor limits of 65535 in `/etc/security/limits.conf`

Not applied by the script, so do it by hand if you want it: tmpfs for temporary files.
The container's own log is already limited by `docker-compose.yml`.

To watch the effect, use `./scripts/monitor-rpi5.sh`.

## Additional Resources

- [Raspberry Pi 5 Performance Tuning](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [Linux Performance Tuning](https://www.kernel.org/doc/Documentation/sysctl/)
