# Raspberry Pi Image Preparation Guide

This guide covers everything you need to prepare before and after flashing the Raspberry Pi OS image for your Minecraft server.

## Table of Contents

1. [Pre-Flash Checklist](#pre-flash-checklist)
2. [Raspberry Pi Imager Configuration](#raspberry-pi-imager-configuration)
3. [Advanced Settings Details](#advanced-settings-details)
4. [Post-Flash Verification](#post-flash-verification)
5. [Hardware Verification](#hardware-verification)
6. [System Optimizations](#system-optimizations)
7. [Security Hardening](#security-hardening)
8. [Troubleshooting Image Issues](#troubleshooting-image-issues)

## Pre-Flash Checklist

### Hardware Requirements

- [ ] **Raspberry Pi 5** (4GB or 8GB RAM recommended)
- [ ] **MicroSD Card**:
  - Minimum: 32GB, Class 10, A2 rating
  - Recommended: 64GB+, U3, A2 rating
  - Verify card is genuine (use H2testw or F3 on Windows/Linux)
- [ ] **Power Supply**: Official Raspberry Pi 5 27W USB-C power supply
- [ ] **Cooling Solution**: Case with active cooling (fan) or heatsink
- [ ] **Network**: Ethernet cable (recommended) or WiFi adapter
- [ ] **Computer**: For flashing the image (Windows, macOS, or Linux)

### Software Requirements

- [ ] **Raspberry Pi Imager** downloaded and installed
  - Download from: <https://www.raspberrypi.com/software/>
  - Latest version recommended
- [ ] **SD Card Reader**: Built-in or USB adapter
- [ ] **Network Information** (if using WiFi):
  - WiFi SSID (network name)
  - WiFi password
  - Country code (e.g., US, GB, DE)

### Information to Gather

Before starting, have ready:

- [ ] **Hostname**: Choose a name (e.g., `minecraft-server`)
- [ ] **Username**: Default is `pi`, or choose your own
- [ ] **Password**: Create a strong password (save it securely!)
- [ ] **Timezone**: Your local timezone (e.g., `America/New_York`, `Europe/London`)
- [ ] **Keyboard Layout**: Your keyboard layout (e.g., `us`, `gb`, `de`)
- [ ] **WiFi Details** (if not using Ethernet):
  - SSID
  - Password
  - Country code
- [ ] **Static IP** (optional): If you want a static IP address

## Raspberry Pi Imager Configuration

### Step 1: Download and Install Raspberry Pi Imager

1. Visit: <https://www.raspberrypi.com/software/>
2. Download for your operating system:
   - Windows: `.exe` installer
   - macOS: `.dmg` file
   - Linux: `.AppImage` or package manager
3. Install following the on-screen instructions

### Step 2: Insert and Prepare SD Card

1. Insert microSD card into your computer's card reader
2. **Important**: Backup any existing data (card will be erased!)
3. Note the drive letter/path of the SD card

### Step 3: Launch Raspberry Pi Imager

1. Open Raspberry Pi Imager
2. Click "Choose Device" → Select **"Raspberry Pi 5"**
3. Click "Choose OS" → Select **"Raspberry Pi OS (64-bit)"**
   - Choose "Raspberry Pi OS (other)" → "Raspberry Pi OS (64-bit)" if needed
4. Click "Choose Storage" → Select your microSD card

### Step 4: Configure Advanced Options

Click the gear icon (⚙️) or press `Ctrl+Shift+X` (Windows/Linux) or `Cmd+Shift+X` (macOS):

#### General Settings Tab

- **Set hostname**: `minecraft-server` (or your preferred name)
  - Must be lowercase, no spaces, use hyphens
  - Examples: `minecraft-server`, `mc-server`, `pi-minecraft`
- **Set username and password**:
  - Username: `pi` (default) or your choice
    - Must be lowercase, no spaces
  - Password: Create a strong password
    - Minimum 8 characters recommended
    - Mix of letters, numbers, and symbols
    - **Save this password securely!**
- **Configure wireless LAN** (if using WiFi):
  - SSID: Your WiFi network name
  - Password: Your WiFi password
  - Wireless LAN country: Your country code (e.g., `US`, `GB`, `DE`, `FR`)
- **Set locale settings**:
  - Time zone: Select your timezone
    - Examples: `America/New_York`, `Europe/London`, `Asia/Tokyo`
  - Keyboard layout: Select your keyboard
    - Examples: `us`, `gb`, `de`, `fr`

#### Services Tab

- **Enable SSH**: ✅ **Check this box** (required!)
- **Use password authentication**: Select this option
  - (SSH key authentication can be configured later)
- **Allow public-key authentication only**: Leave unchecked for now
  - (Can enable later for better security)

#### Options Tab (Optional)

- **Eject media when finished**: ✅ Recommended
- **Enable telemetry**: Your choice (optional)

### Step 5: Save Configuration (Optional but Recommended)

Before writing, you can save your configuration:

1. Click "Save customisation" button
2. Choose a location to save the `.json` file
3. Name it something like `minecraft-server-config.json`
4. This allows you to reuse settings for future images

**To load saved configuration later:**

1. Click gear icon
2. Click "Load customisation"
3. Select your saved `.json` file

### Step 6: Write Image to SD Card

1. Review all settings one more time
2. Click **"Write"** button
3. Confirm you want to erase the card
4. Wait for the process to complete:
   - Writing: 5-10 minutes (depends on card speed)
   - Verifying: 2-5 minutes
5. **Do not remove the card during this process!**
6. Wait for "Write Successful" message

### Step 7: Safely Eject SD Card

1. Wait for verification to complete
2. If "Eject media when finished" was enabled, card will eject automatically
3. Otherwise, safely eject from your operating system:
   - Windows: Right-click → Eject
   - macOS: Drag to Trash or Cmd+E
   - Linux: `umount /dev/sdX` (replace X with your device)

## Advanced Settings Details

### Hostname Best Practices

- Use lowercase letters, numbers, and hyphens only
- Keep it short (under 20 characters)
- Make it descriptive: `minecraft-server`, `mc-pi5`, `game-server`
- Avoid special characters and spaces

### Password Requirements

- Minimum 8 characters (12+ recommended)
- Mix of uppercase, lowercase, numbers, symbols
- Avoid dictionary words
- Don't reuse passwords from other services
- Consider using a password manager

### WiFi Configuration Tips

- **Country Code**: Required for WiFi compliance
  - US: `US`
  - UK: `GB`
  - Germany: `DE`
  - France: `FR`
  - See full list: <https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>
- **Hidden Networks**: Raspberry Pi Imager doesn't support hidden SSIDs
  - Configure manually after first boot if needed
- **5GHz vs 2.4GHz**: Both supported, but 2.4GHz has better range

### Timezone Selection

Common timezones:

- `America/New_York` - Eastern Time (US)
- `America/Chicago` - Central Time (US)
- `America/Denver` - Mountain Time (US)
- `America/Los_Angeles` - Pacific Time (US)
- `Europe/London` - UK
- `Europe/Paris` - Central Europe
- `Asia/Tokyo` - Japan
- `Australia/Sydney` - Australia

Find your timezone: <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>

## Post-Flash Verification

### Visual Inspection

1. **Check SD Card**:

   - Card should show two partitions (boot and rootfs)
   - On Windows: May only show boot partition (this is normal)
   - On Linux/macOS: Both partitions visible

2. **Verify Files**:
   - Boot partition should contain:
     - `config.txt`
     - `cmdline.txt`
     - `ssh` file (if SSH enabled)
     - `userconf` or `userconf.txt` (if password set)
     - `wpa_supplicant.conf` (if WiFi configured)

### Boot Verification Checklist

After inserting card into Raspberry Pi:

- [ ] **Power LED**: Should light up when power connected
- [ ] **Activity LED**: Should blink during boot
- [ ] **Network LED**: Should show activity if Ethernet connected
- [ ] **First Boot**: Takes 2-3 minutes
- [ ] **SSH Access**: Should be accessible after boot

### Network Verification

1. **Find Raspberry Pi on Network**:

   ```bash
   # Using hostname (if mDNS works)
   ping minecraft-server.local

   # Or scan network (Linux/macOS)
   nmap -sn 192.168.1.0/24

   # Or check router admin panel
   ```

2. **Test SSH Connection**:

   ```bash
   ssh pi@minecraft-server.local
   # Or
   ssh pi@192.168.1.XXX
   ```

3. **Verify Network Configuration**:

   ```bash
   # After SSH connection
   hostname -I  # Should show IP address
   ping -c 4 google.com  # Test internet connectivity
   ```

## Hardware Verification

### Before First Boot

1. **Check Power Supply**:

   - Use official Raspberry Pi 5 27W power supply
   - Verify voltage: 5V, current: 5A minimum
   - Avoid USB ports on computers (insufficient power)

2. **Check Cooling**:

   - Ensure case/fan is properly installed
   - Verify fan connection (if applicable)
   - Check for adequate airflow

3. **Check Connections**:
   - SD card fully inserted
   - Ethernet cable connected (if using)
   - Power supply connected

### After First Boot

1. **Check System Information**:

   ```bash
   # Model and memory
   cat /proc/device-tree/model
   free -h

   # CPU info
   lscpu

   # Temperature (if available)
   vcgencmd measure_temp
   ```

2. **Verify Hardware**:

   ```bash
   # Check SD card
   df -h

   # Check network
   ip addr show

   # Check USB devices
   lsusb
   ```

## System Optimizations

### Immediate Post-Boot Optimizations

After first SSH login, run these optimizations:

1. **Update System**:

   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

2. **Enable GPU Memory Split** (if needed):

   ```bash
   sudo raspi-config
   # Advanced Options → Memory Split → 16 (minimum for headless)
   ```

3. **Disable Unnecessary Services** (headless server):

   ```bash
   # Disable GUI if not needed
   sudo systemctl disable graphical.target
   sudo systemctl set-default multi-user.target
   ```

4. **Optimize Swap** (for 4GB Pi):

   ```bash
   # Reduce swap usage
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Change CONF_SWAPSIZE=100 to CONF_SWAPSIZE=512
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

5. **Set CPU Governor** (for performance):

   ```bash
   # Install cpufrequtils
   sudo apt install cpufrequtils -y

   # Set to performance mode
   echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
   sudo systemctl enable cpufrequtils
   sudo systemctl start cpufrequtils
   ```

### Storage Optimizations

1. **Enable TRIM** (for SD card health):

   ```bash
   sudo systemctl enable fstrim.timer
   sudo systemctl start fstrim.timer
   ```

2. **Reduce Log Retention**:

   ```bash
   sudo nano /etc/logrotate.conf
   # Adjust retention as needed
   ```

## Security Hardening

### Essential Security Steps

1. **Change Default Password** (if not done in Imager):

   ```bash
   passwd
   ```

2. **Update System**:

   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Configure Firewall**:

   ```bash
   sudo apt install ufw -y
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow ssh
   sudo ufw allow 25565/tcp  # Minecraft port
   sudo ufw enable
   ```

4. **Disable Unused Services**:

   ```bash
   # List running services
   sudo systemctl list-units --type=service --state=running

   # Disable Bluetooth (if not needed)
   sudo systemctl disable bluetooth

   # Disable WiFi power management (if using Ethernet)
   # Edit /etc/network/interfaces or use raspi-config
   ```

5. **Set Up SSH Key Authentication** (recommended):

   ```bash
   # On your computer, generate key
   ssh-keygen -t ed25519 -C "minecraft-server"

   # Copy to Raspberry Pi
   ssh-copy-id pi@minecraft-server.local

   # Then disable password authentication (after testing key works)
   sudo nano /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   # Set: PubkeyAuthentication yes
   sudo systemctl restart sshd
   ```

6. **Enable Automatic Security Updates**:

   ```bash
   sudo apt install unattended-upgrades -y
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

## Troubleshooting Image Issues

### Image Won't Boot

**Symptoms**: No activity LED, no network, can't SSH

**Solutions**:

1. **Check Power Supply**:

   - Verify 5V 5A power supply
   - Try different power supply
   - Check power LED is on

2. **Check SD Card**:

   - Verify card is genuine (use H2testw/F3)
   - Try different SD card
   - Re-flash image

3. **Check Connections**:

   - SD card fully inserted
   - All cables secure

4. **Check Image**:
   - Re-download Raspberry Pi OS
   - Verify image checksum
   - Re-flash with verification enabled

### Can't Connect via SSH

**Symptoms**: Network LED active but can't SSH

**Solutions**:

1. **Verify SSH Enabled**:

   - Check for `ssh` file in boot partition
   - Create empty `ssh` file if missing:

     ```bash
     # On computer, mount boot partition
     touch /path/to/boot/ssh
     ```

2. **Check Network**:

   ```bash
   # Ping test
   ping minecraft-server.local
   ping 192.168.1.XXX
   ```

3. **Check Firewall**:

   - Router firewall may block SSH
   - Try from same network first

4. **Check Username/Password**:
   - Verify username (default: `pi`)
   - Try password reset if needed

### WiFi Not Connecting

**Symptoms**: Ethernet works but WiFi doesn't

**Solutions**:

1. **Check Configuration**:

   - Verify SSID and password correct
   - Check country code is correct
   - Re-flash with correct WiFi settings

2. **Manual Configuration**:

   ```bash
   sudo raspi-config
   # System Options → Wireless LAN
   # Enter SSID and password
   ```

3. **Check WiFi Adapter**:

   ```bash
   # List WiFi interfaces
   iwconfig

   # Scan for networks
   sudo iwlist wlan0 scan
   ```

### Hostname Not Resolving

**Symptoms**: Can't connect using `.local` hostname

**Solutions**:

1. **Use IP Address Instead**:

   ```bash
   ssh pi@192.168.1.XXX
   ```

2. **Install mDNS** (if missing):

   ```bash
   sudo apt install avahi-daemon -y
   sudo systemctl enable avahi-daemon
   ```

3. **Check Router mDNS Support**:
   - Some routers don't support `.local` resolution
   - Use IP address or configure router

## Saving and Restoring Configuration

### Save Raspberry Pi Imager Settings

1. In Raspberry Pi Imager, configure all settings
2. Click gear icon
3. Click "Save customisation"
4. Save as `.json` file (e.g., `minecraft-server-config.json`)

### Load Saved Configuration

1. Open Raspberry Pi Imager
2. Configure device and OS
3. Click gear icon
4. Click "Load customisation"
5. Select your saved `.json` file
6. Settings will be restored

### Configuration File Format

The saved `.json` file contains:

- Hostname
- Username
- Password (encrypted/hashed)
- WiFi settings
- Locale settings
- SSH configuration

**Note**: Keep this file secure as it contains sensitive information!

## Next Steps

After image preparation is complete:

1. **Insert SD Card** into Raspberry Pi 5
2. **Power On** and wait for boot
3. **SSH Connect**: `ssh pi@minecraft-server.local`
4. **Run Setup Script**: Follow [Installation Guide](INSTALL.md)
5. **Configure Server**: Customize settings as needed
6. **Start Server**: Use `./manage.sh start`

## Additional Resources

- [Raspberry Pi Imager Documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html#using-raspberry-pi-imager)
- [Raspberry Pi OS Documentation](https://www.raspberrypi.com/documentation/computers/os.html)
- [Installation Guide](INSTALL.md) - Next steps after image preparation
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

## Quick Reference Checklist

**Before Flashing:**

- [ ] Hardware ready (Pi 5, SD card, power supply, cooling)
- [ ] Raspberry Pi Imager installed
- [ ] Network information gathered (WiFi if needed)
- [ ] Hostname, username, password decided
- [ ] Timezone and keyboard layout known

**During Flashing:**

- [ ] Device: Raspberry Pi 5 selected
- [ ] OS: Raspberry Pi OS (64-bit) selected
- [ ] Storage: Correct SD card selected
- [ ] Advanced options configured
- [ ] Configuration saved (optional)
- [ ] Image written and verified

**After Flashing:**

- [ ] SD card safely ejected
- [ ] Card inserted into Raspberry Pi
- [ ] Power connected
- [ ] Boot successful (LEDs active)
- [ ] SSH connection working
- [ ] Network connectivity verified
- [ ] System updated
- [ ] Security hardened
- [ ] Ready for Minecraft server setup

---

**Last Updated**: 2025-01-27  
**Related Documents**: [INSTALL.md](INSTALL.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
