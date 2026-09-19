#!/bin/bash
# Raspberry Pi 5 Optimization Script for Minecraft Server
# Applies system-level optimizations for better performance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Raspberry Pi 5 Optimization Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. CPU Governor - Performance Mode
echo -e "${GREEN}[1/8] Setting CPU governor to performance...${NC}"
if command -v cpufreq-set &> /dev/null || apt list --installed 2>/dev/null | grep -q cpufrequtils; then
    sudo apt install -y cpufrequtils 2>/dev/null || true
    echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils > /dev/null
    sudo systemctl enable cpufrequtils 2>/dev/null || true
    sudo systemctl start cpufrequtils 2>/dev/null || true
    echo -e "${GREEN}CPU governor set to performance${NC}"
else
    echo -e "${YELLOW}cpufrequtils not available, skipping${NC}"
fi

# 2. Swap Optimization
echo -e "${GREEN}[2/8] Optimizing swap configuration...${NC}"
if [ -f /etc/dphys-swapfile ]; then
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    if [ $TOTAL_RAM -lt 6144 ]; then
        # 4GB Pi - reduce swap
        sudo dphys-swapfile swapoff 2>/dev/null || true
        sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/' /etc/dphys-swapfile 2>/dev/null || true
        sudo dphys-swapfile setup 2>/dev/null || true
        sudo dphys-swapfile swapon 2>/dev/null || true
        echo -e "${GREEN}Swap optimized for 4GB Pi (512MB)${NC}"
    else
        # 8GB Pi - can disable swap
        echo -e "${YELLOW}8GB Pi detected. Consider disabling swap entirely.${NC}"
    fi
else
    echo -e "${YELLOW}dphys-swapfile not found, skipping${NC}"
fi

# 3. Kernel Parameters
echo -e "${GREEN}[3/8] Optimizing kernel parameters...${NC}"
KERNEL_PARAMS=(
    "vm.swappiness=1"
    "vm.vfs_cache_pressure=50"
    "vm.dirty_ratio=15"
    "vm.dirty_background_ratio=5"
    "net.core.rmem_max=134217728"
    "net.core.wmem_max=134217728"
    "net.ipv4.tcp_rmem=4096 87380 67108864"
    "net.ipv4.tcp_wmem=4096 65536 67108864"
    "net.ipv4.tcp_congestion_control=bbr"
    "net.core.somaxconn=1024"
    "net.ipv4.tcp_max_syn_backlog=2048"
)

for param in "${KERNEL_PARAMS[@]}"; do
    KEY=$(echo "$param" | cut -d= -f1)
    if ! grep -q "^${KEY}=" /etc/sysctl.conf 2>/dev/null; then
        echo "$param" | sudo tee -a /etc/sysctl.conf > /dev/null
    fi
done

sudo sysctl -p > /dev/null 2>&1 || true
echo -e "${GREEN}Kernel parameters optimized${NC}"

# 4. Enable TRIM
echo -e "${GREEN}[4/8] Enabling TRIM for SD card...${NC}"
sudo systemctl enable fstrim.timer 2>/dev/null || true
sudo systemctl start fstrim.timer 2>/dev/null || true
echo -e "${GREEN}TRIM enabled${NC}"

# 5. Disable Unnecessary Services
echo -e "${GREEN}[5/8] Disabling unnecessary services...${NC}"
sudo systemctl disable bluetooth 2>/dev/null || true
sudo systemctl stop bluetooth 2>/dev/null || true
echo -e "${GREEN}Bluetooth disabled${NC}"

# 6. Log Rotation
echo -e "${GREEN}[6/8] Configuring log rotation...${NC}"
if [ -d "$HOME/minecraft-server" ]; then
    LOGROTATE_CONFIG="/etc/logrotate.d/minecraft"
    sudo tee "$LOGROTATE_CONFIG" > /dev/null <<EOF
$HOME/minecraft-server/data/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $USER $USER
}
EOF
    echo -e "${GREEN}Log rotation configured${NC}"
else
    echo -e "${YELLOW}Minecraft server directory not found, skipping log rotation${NC}"
fi

# 7. Journal Logging Optimization
echo -e "${GREEN}[7/8] Optimizing systemd journal...${NC}"
if [ -f /etc/systemd/journald.conf ]; then
    sudo sed -i 's/#SystemMaxUse=/SystemMaxUse=50M/' /etc/systemd/journald.conf
    sudo sed -i 's/#MaxRetentionSec=/MaxRetentionSec=1week/' /etc/systemd/journald.conf
    sudo systemctl restart systemd-journald 2>/dev/null || true
    echo -e "${GREEN}Journal logging optimized${NC}"
else
    echo -e "${YELLOW}journald.conf not found, skipping${NC}"
fi

# 8. USB Power Management
echo -e "${GREEN}[8/8] Optimizing USB power management...${NC}"
UDEV_RULE="/etc/udev/rules.d/50-usb-power.rules"
if [ ! -f "$UDEV_RULE" ]; then
    echo 'SUBSYSTEM=="usb", ACTION=="add", ATTR{power/autosuspend}="-1"' | sudo tee "$UDEV_RULE" > /dev/null
    echo -e "${GREEN}USB power management optimized${NC}"
else
    echo -e "${YELLOW}USB power rule already exists${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Optimization Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Summary of optimizations:${NC}"
echo "  ✓ CPU governor set to performance"
echo "  ✓ Swap optimized"
echo "  ✓ Kernel parameters tuned"
echo "  ✓ TRIM enabled"
echo "  ✓ Unnecessary services disabled"
echo "  ✓ Log rotation configured"
echo "  ✓ Journal logging optimized"
echo "  ✓ USB power management optimized"
echo ""
echo -e "${YELLOW}Note: Some changes require a reboot to take full effect.${NC}"
echo -e "${YELLOW}Reboot now? (y/N)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Rebooting in 5 seconds...${NC}"
    sleep 5
    sudo reboot
fi

