#!/bin/bash
# System and Filesystem Optimization Script
# Applies comprehensive optimizations for Raspberry Pi 5

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== System and Filesystem Optimization ===${NC}\n"

# Check if running as root for some operations
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Some operations require root. You may be prompted for sudo.${NC}\n"
fi

# 1. Filesystem Optimizations
echo -e "${BLUE}[1/9] Optimizing filesystem mount options...${NC}"

# Backup fstab
sudo cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d)

# Check if already optimized
if grep -q "noatime,nodiratime" /etc/fstab; then
    echo -e "${YELLOW}⚠ Filesystem already optimized${NC}"
else
    # Add noatime and nodiratime to root filesystem
    sudo sed -i 's|/dev/mmcblk0p2.*ext4.*defaults|/dev/mmcblk0p2  /  ext4  defaults,noatime,nodiratime,commit=60|' /etc/fstab
    echo -e "${GREEN}✓ Filesystem mount options optimized${NC}"
    echo -e "${YELLOW}⚠ Reboot required for mount options to take effect${NC}"
fi

# 2. Enable TRIM
echo -e "\n${BLUE}[2/9] Enabling TRIM for SD card...${NC}"
if systemctl is-enabled fstrim.timer >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ TRIM already enabled${NC}"
else
    sudo systemctl enable fstrim.timer
    sudo systemctl start fstrim.timer
    echo -e "${GREEN}✓ TRIM enabled${NC}"
fi

# 3. I/O Scheduler
echo -e "\n${BLUE}[3/9] Optimizing I/O scheduler...${NC}"
if [ -f /etc/udev/rules.d/60-ioscheduler.rules ]; then
    echo -e "${YELLOW}⚠ I/O scheduler already configured${NC}"
else
    echo 'ACTION=="add|change", KERNEL=="mmcblk[0-9]*", ATTR{queue/scheduler}="mq-deadline"' | \
        sudo tee /etc/udev/rules.d/60-ioscheduler.rules > /dev/null
    echo mq-deadline | sudo tee /sys/block/mmcblk0/queue/scheduler > /dev/null
    echo -e "${GREEN}✓ I/O scheduler set to mq-deadline${NC}"
fi

# 4. Kernel Parameters (sysctl)
echo -e "\n${BLUE}[4/9] Optimizing kernel parameters...${NC}"

SYSCTL_CONFIG="/etc/sysctl.conf"
SYSCTL_BACKUP="${SYSCTL_CONFIG}.backup.$(date +%Y%m%d)"

# Backup sysctl.conf
sudo cp "$SYSCTL_CONFIG" "$SYSCTL_BACKUP"

# Add optimizations if not present
if ! grep -q "# Minecraft Server Optimizations" "$SYSCTL_CONFIG"; then
    sudo tee -a "$SYSCTL_CONFIG" > /dev/null <<EOF

# Minecraft Server Optimizations
# Memory management
vm.swappiness=1
vm.vfs_cache_pressure=50
vm.dirty_ratio=15
vm.dirty_background_ratio=5
vm.overcommit_memory=1

# Network optimizations
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.core.somaxconn=1024
net.ipv4.tcp_rmem=4096 87380 67108864
net.ipv4.tcp_wmem=4096 65536 67108864
net.ipv4.tcp_congestion_control=bbr
net.ipv4.tcp_slow_start_after_idle=0
net.ipv4.tcp_tw_reuse=1
net.ipv4.ip_local_port_range=10000 65535

# File system
fs.file-max=2097152
fs.inotify.max_user_watches=524288
EOF
    echo -e "${GREEN}✓ Kernel parameters added${NC}"
    sudo sysctl -p > /dev/null
    echo -e "${GREEN}✓ Kernel parameters applied${NC}"
else
    echo -e "${YELLOW}⚠ Kernel parameters already configured${NC}"
fi

# 5. CPU Governor
echo -e "\n${BLUE}[5/9] Setting CPU governor to performance...${NC}"
if command -v cpufreq-set >/dev/null 2>&1 || [ -f /etc/default/cpufrequtils ]; then
    if grep -q 'GOVERNOR="performance"' /etc/default/cpufrequtils 2>/dev/null; then
        echo -e "${YELLOW}⚠ CPU governor already set to performance${NC}"
    else
        if ! command -v cpufrequtils >/dev/null 2>&1; then
            sudo apt-get install -y cpufrequtils
        fi
        echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils > /dev/null
        sudo systemctl enable cpufrequtils 2>/dev/null || true
        sudo systemctl start cpufrequtils 2>/dev/null || true
        echo -e "${GREEN}✓ CPU governor set to performance${NC}"
    fi
else
    echo -e "${YELLOW}⚠ cpufrequtils not available, skipping${NC}"
fi

# 6. Swap Optimization
echo -e "\n${BLUE}[6/9] Optimizing swap...${NC}"
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')

if [ "$TOTAL_RAM" -lt 4096 ]; then
    # 4GB Pi: Reduce swap
    if [ -f /etc/dphys-swapfile ]; then
        if grep -q "CONF_SWAPSIZE=100" /etc/dphys-swapfile; then
            sudo dphys-swapfile swapoff 2>/dev/null || true
            sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
            sudo dphys-swapfile setup
            sudo dphys-swapfile swapon
            echo -e "${GREEN}✓ Swap reduced to 512MB (4GB Pi)${NC}"
        else
            echo -e "${YELLOW}⚠ Swap already configured${NC}"
        fi
    fi
else
    # 8GB Pi: Option to disable swap
    echo -e "${YELLOW}8GB Pi detected. Consider disabling swap for better performance.${NC}"
    read -p "Disable swap? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo swapoff -a
        sudo systemctl disable dphys-swapfile.service 2>/dev/null || true
        echo -e "${GREEN}✓ Swap disabled${NC}"
    fi
fi

# 7. Log Rotation
echo -e "\n${BLUE}[7/9] Configuring log rotation...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f /etc/logrotate.d/minecraft ]; then
    echo -e "${YELLOW}⚠ Log rotation already configured${NC}"
else
    sudo tee /etc/logrotate.d/minecraft > /dev/null <<EOF
${PROJECT_DIR}/data/logs/*.log {
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

${PROJECT_DIR}/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pi pi
}
EOF
    echo -e "${GREEN}✓ Log rotation configured${NC}"
fi

# 8. Systemd Journal Limits
echo -e "\n${BLUE}[8/9] Optimizing systemd journal...${NC}"
if grep -q "SystemMaxUse=50M" /etc/systemd/journald.conf; then
    echo -e "${YELLOW}⚠ Journal already optimized${NC}"
else
    sudo sed -i 's/#SystemMaxUse=/SystemMaxUse=50M/' /etc/systemd/journald.conf
    sudo sed -i 's/#SystemKeepFree=/SystemKeepFree=100M/' /etc/systemd/journald.conf
    sudo sed -i 's/#MaxRetentionSec=/MaxRetentionSec=1week/' /etc/systemd/journald.conf
    sudo systemctl restart systemd-journald
    echo -e "${GREEN}✓ Journal limits configured${NC}"
fi

# 9. File Descriptor Limits
echo -e "\n${BLUE}[9/9] Increasing file descriptor limits...${NC}"
if grep -q "minecraft-server" /etc/security/limits.conf; then
    echo -e "${YELLOW}⚠ File descriptor limits already configured${NC}"
else
    sudo tee -a /etc/security/limits.conf > /dev/null <<EOF

# Minecraft Server Optimizations
* soft nofile 65535
* hard nofile 65535
pi soft nofile 65535
pi hard nofile 65535
EOF
    echo -e "${GREEN}✓ File descriptor limits increased${NC}"
    echo -e "${YELLOW}⚠ Log out and back in for limits to take effect${NC}"
fi

# Summary
echo -e "\n${BLUE}=== Optimization Summary ===${NC}"
echo -e "${GREEN}✓ Filesystem mount options optimized${NC}"
echo -e "${GREEN}✓ TRIM enabled${NC}"
echo -e "${GREEN}✓ I/O scheduler optimized${NC}"
echo -e "${GREEN}✓ Kernel parameters configured${NC}"
echo -e "${GREEN}✓ CPU governor set to performance${NC}"
echo -e "${GREEN}✓ Swap optimized${NC}"
echo -e "${GREEN}✓ Log rotation configured${NC}"
echo -e "${GREEN}✓ Systemd journal optimized${NC}"
echo -e "${GREEN}✓ File descriptor limits increased${NC}"

echo -e "\n${YELLOW}⚠ Some changes require a reboot to take effect:${NC}"
echo -e "  - Filesystem mount options"
echo -e "  - File descriptor limits (log out/in)"
echo -e "\n${BLUE}To reboot: sudo reboot${NC}"

echo -e "\n${GREEN}Optimization complete!${NC}"

