# Raspberry Pi Image Preparation - Quick Checklist

Print this checklist or keep it open while preparing your Raspberry Pi image.

## Pre-Flash Preparation

### Hardware

- [ ] Raspberry Pi 5 (4GB or 8GB)
- [ ] MicroSD card (32GB+ recommended, Class 10, A2 rating)
- [ ] Power supply (Official 27W USB-C)
- [ ] Cooling solution (case with fan or heatsink)
- [ ] Ethernet cable OR WiFi adapter
- [ ] Computer with SD card reader

### Software

- [ ] Raspberry Pi Imager downloaded and installed
- [ ] SD card reader working

### Information Needed

- [ ] Hostname chosen: `_________________`
- [ ] Username: `_________________` (default: `pi`)
- [ ] Password: `_________________` (save securely!)
- [ ] Timezone: `_________________`
- [ ] Keyboard layout: `_________________`
- [ ] WiFi SSID (if using WiFi): `_________________`
- [ ] WiFi password (if using WiFi): `_________________`
- [ ] WiFi country code (if using WiFi): `_________________`

## Raspberry Pi Imager Configuration

### Basic Settings

- [ ] Device: **Raspberry Pi 5** selected
- [ ] OS: **Raspberry Pi OS (64-bit)** selected
- [ ] Storage: Correct SD card selected

### Advanced Options (Gear Icon ⚙️)

#### General Settings

- [ ] Hostname set: `_________________`
- [ ] Username set: `_________________`
- [ ] Password set: `_________________`
- [ ] WiFi configured (if using): SSID, password, country code
- [ ] Timezone set: `_________________`
- [ ] Keyboard layout set: `_________________`

#### Services

- [ ] SSH enabled: ✅
- [ ] Password authentication selected

#### Options

- [ ] Eject media when finished: ✅ (recommended)

### Configuration Save

- [ ] Configuration saved to: `_________________` (optional but recommended)

## Image Writing

- [ ] All settings reviewed and correct
- [ ] Write button clicked
- [ ] Erase confirmation accepted
- [ ] Writing completed (5-10 minutes)
- [ ] Verification completed (2-5 minutes)
- [ ] "Write Successful" message shown
- [ ] SD card safely ejected

## Post-Flash Verification

### Hardware Check

- [ ] SD card inserted into Raspberry Pi 5
- [ ] Power supply connected
- [ ] Ethernet cable connected (if using)
- [ ] Cooling solution in place

### Boot Verification

- [ ] Power LED lights up
- [ ] Activity LED blinks during boot
- [ ] Network LED shows activity (if Ethernet)
- [ ] Boot completed (2-3 minutes)

### Network Verification

- [ ] Raspberry Pi found on network
  - Hostname: `minecraft-server.local` OR
  - IP address: `_________________`
- [ ] SSH connection successful

  ```bash
  ssh pi@minecraft-server.local
  # OR
  ssh pi@_________________
  ```

- [ ] Internet connectivity verified

  ```bash
  ping -c 4 google.com
  ```

## Post-Boot Setup

### System Updates

- [ ] System updated

  ```bash
  sudo apt update && sudo apt upgrade -y
  ```

### Security (Essential)

- [ ] Password changed (if not done in Imager)
- [ ] Firewall configured

  ```bash
  sudo apt install ufw -y
  sudo ufw allow ssh
  sudo ufw allow 25565/tcp
  sudo ufw enable
  ```

- [ ] Automatic security updates enabled (optional)

  ```bash
  sudo apt install unattended-upgrades -y
  ```

### System Optimizations (Optional)

- [ ] GPU memory split configured (if needed)
- [ ] Swap optimized (for 4GB Pi)
- [ ] Unnecessary services disabled
- [ ] CPU governor set to performance

## Ready for Minecraft Server Setup

- [ ] All checks completed
- [ ] System ready
- [ ] Proceed to: [Installation Guide](INSTALL.md)

---

**Quick Commands Reference:**

```bash
# Find IP address
hostname -I

# Test connectivity
ping -c 4 google.com

# Check system info
cat /proc/device-tree/model
free -h

# Check temperature
vcgencmd measure_temp
```

---

**Troubleshooting Quick Links:**

- Can't boot? → Check power supply and SD card
- Can't SSH? → Verify SSH enabled, check network
- WiFi not working? → Verify SSID, password, country code
- Hostname not resolving? → Use IP address instead

**Next Steps:**

1. Follow [Installation Guide](INSTALL.md)
2. Run setup script: `./setup-rpi.sh`
3. Start server: `./manage.sh start`

---

**Save this checklist!** You may need it for future reference.
