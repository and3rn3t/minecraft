# Installation Guide - Minecraft Server for Raspberry Pi 5

This guide provides detailed step-by-step instructions for setting up your Minecraft server on a Raspberry Pi 5.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Software Requirements](#software-requirements)
3. [Preparation](#preparation)
4. [Installation Steps](#installation-steps)
5. [First Server Start](#first-server-start)
6. [Network Configuration](#network-configuration)
7. [Verification](#verification)

## Hardware Requirements

### Minimum Requirements

- **Raspberry Pi 5** (4GB RAM model)
- **MicroSD Card**: 32GB, Class 10, A2 rating recommended
- **Power Supply**: Official Raspberry Pi 5 27W USB-C power supply
- **Network**: Ethernet cable (recommended) or WiFi
- **Cooling**: Case with active cooling (fan) recommended

### Recommended Setup

- **Raspberry Pi 5** (8GB RAM model)
- **MicroSD Card**: 64GB or larger, U3, A2 rating
- **Power Supply**: Official Raspberry Pi 5 27W USB-C power supply
- **Network**: Gigabit Ethernet connection
- **Cooling**: Case with active cooling or heatsink
- **Optional**: External SSD for better I/O performance

## Software Requirements

- **Raspberry Pi OS**: 64-bit (Bookworm or newer)
- **Docker**: Will be installed by setup script
- **Docker Compose**: Will be installed by setup script
- **Git**: Will be installed by setup script

## Preparation

> **📘 For a comprehensive guide to preparing your Raspberry Pi image, including detailed configuration options, troubleshooting, and security hardening, see [RASPBERRY_PI_IMAGE_PREPARATION.md](RASPBERRY_PI_IMAGE_PREPARATION.md).**  
> **📋 For a quick checklist, see [IMAGE_PREP_CHECKLIST.md](IMAGE_PREP_CHECKLIST.md).**

This section provides a quick overview. For detailed instructions, refer to the guides above.

### 1. Download Raspberry Pi Imager

Download from: <https://www.raspberrypi.com/software/>

Available for:

- Windows
- macOS
- Linux

### 2. Prepare Your MicroSD Card

1. Insert microSD card into your computer
2. Launch Raspberry Pi Imager
3. Click "Choose Device" → Select "Raspberry Pi 5"
4. Click "Choose OS" → Select "Raspberry Pi OS (64-bit)"
5. Click "Choose Storage" → Select your microSD card

### 3. Configure Advanced Options

Click the gear icon (⚙️) or press `Ctrl+Shift+X`:

#### General Settings

- **Set hostname**: `minecraft-server` (or your preferred name)
- **Set username and password**:
  - Username: `pi` (or your preferred username)
  - Password: Create a strong password

#### Services

- **Enable SSH**: ✅ Check this box
- Select "Use password authentication"

#### WiFi (Optional)

If not using Ethernet:

- **Configure wireless LAN**:
  - SSID: Your WiFi network name
  - Password: Your WiFi password
  - Wireless LAN country: Your country code

#### Locale Settings

- **Set locale settings**:
  - Time zone: Your timezone
  - Keyboard layout: Your keyboard layout

### 4. Write to MicroSD Card

1. Click "Save" to save advanced settings
2. Click "Write" to begin writing
3. Confirm you want to erase the card
4. Wait for the process to complete (5-10 minutes)
5. Wait for verification to complete
6. Safely eject the card

## Installation Steps

### Step 1: First Boot

1. Insert the microSD card into your Raspberry Pi 5
2. Connect Ethernet cable (recommended)
3. Connect power supply
4. Wait 2-3 minutes for first boot and setup

### Step 2: Connect to Your Raspberry Pi

#### Option A: Using Hostname (Easy)

```bash
ssh pi@minecraft-server.local
```

#### Option B: Using IP Address

If hostname doesn't work, find the IP address:

- Check your router's admin panel
- Use network scanning tools (e.g., Angry IP Scanner)

Then connect:

```bash
ssh pi@192.168.1.XXX
```

When prompted, type "yes" to accept the fingerprint and enter your password.

### Step 3: Initial System Update

```bash
# Update package list
sudo apt update

# Upgrade existing packages (optional but recommended)
sudo apt upgrade -y
```

### Step 4: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/and3rn3t/minecraft.git minecraft-server

# Navigate to server directory
cd minecraft-server

# List files to verify
ls -la
```

### Step 5: Run Setup Script

```bash
# Make setup script executable
chmod +x setup-rpi.sh

# Run setup script
./setup-rpi.sh
```

The setup script will:

1. Update system packages
2. Install Docker
3. Install Docker Compose
4. Install additional utilities (git, wget, curl, screen, htop)
5. Create necessary directories
6. Configure Docker service

**This process takes 10-20 minutes.**

### Step 6: Apply Docker Permissions

**Important**: You must log out and back in for Docker group permissions to take effect.

```bash
# Log out
exit

# Log back in
ssh pi@minecraft-server.local

# Verify Docker works without sudo
docker --version
docker-compose --version
```

### Step 7: Configure Server (Optional)

Before starting, you may want to customize settings:

```bash
cd ~/minecraft-server

# Edit server properties
nano server.properties

# Edit memory settings in docker-compose
nano docker-compose.yml
```

Press `Ctrl+X`, then `Y`, then `Enter` to save changes.

## First Server Start

### Start the Server

```bash
# Navigate to server directory
cd ~/minecraft-server

# Make management script executable
chmod +x manage.sh

# Start the server
./manage.sh start
```

### Monitor Startup

```bash
# View logs (Press Ctrl+C to exit)
./manage.sh logs
```

First startup takes 5-10 minutes as it:

1. Downloads Minecraft server jar
2. Generates world
3. Prepares spawn area

You'll see "Done!" in the logs when ready.

## Network Configuration

### Local Network Access

Players on the same network can connect using:

- Your local IP address: `192.168.1.XXX:25565`
- Or hostname: `minecraft-server.local:25565`

Find your local IP:

```bash
hostname -I
```

### Internet Access (Port Forwarding)

For players outside your network:

#### Step 1: Static IP or DHCP Reservation

Set a static local IP for your Raspberry Pi:

**Option A: DHCP Reservation (Recommended)**

1. Log into your router
2. Find DHCP settings
3. Reserve IP for Raspberry Pi's MAC address

**Option B: Static IP on Pi**

```bash
sudo nmtui
# Select "Edit a connection"
# Configure IPv4 as Manual
# Set IP, Gateway, DNS
```

#### Step 2: Configure Port Forwarding

1. Log into your router's admin panel
   - Usually: `192.168.1.1` or `192.168.0.1`
2. Find "Port Forwarding" or "NAT" settings
3. Add new port forward:
   - **Service Name**: Minecraft
   - **External Port**: 25565
   - **Internal Port**: 25565
   - **Internal IP**: Your Pi's local IP
   - **Protocol**: TCP
   - **Enable**: Yes

#### Step 3: Find Your Public IP

Visit: <https://whatismyipaddress.com/>

Share this IP with friends: `YOUR.PUBLIC.IP:25565`

**Note**: Most home IPs are dynamic and may change. Consider using a dynamic DNS service (like No-IP or DuckDNS) for a permanent address.

## Verification

### Check Server Status

```bash
./manage.sh status
```

Should show container as "Up".

### Test Local Connection

1. Open Minecraft Java Edition
2. Go to Multiplayer
3. Add Server
   - Name: My Server
   - Address: `minecraft-server.local:25565` or your local IP
4. Connect and play!

### Check Resource Usage

```bash
# View system resources
htop

# View Docker stats
docker stats minecraft-server
```

### Create First Backup

```bash
./manage.sh backup
```

## Troubleshooting

### Server Won't Start

```bash
# Check Docker service
sudo systemctl status docker

# If not running, start it
sudo systemctl start docker

# Check detailed error logs
docker-compose logs
```

### Memory Issues

If you have 4GB Pi and server is slow:

Edit `docker-compose.yml`:

```yaml
environment:
  - MEMORY_MIN=512M
  - MEMORY_MAX=1G
```

Then restart:

```bash
./manage.sh restart
```

### Permission Errors

```bash
# Fix ownership of server files
sudo chown -R $USER:$USER ~/minecraft-server

# Ensure Docker permissions
sudo usermod -aG docker $USER
# Log out and back in
```

### Cannot Find Server on Network

```bash
# Check if port is accessible
sudo apt install nmap
nmap -p 25565 localhost

# Should show port 25565/tcp open
```

## Next Steps

1. **Configure Server Settings**: Edit `server.properties` to customize gameplay
2. **Set Up Backups**: Create regular backup schedule
3. **Add Whitelist**: If desired, enable whitelist in `server.properties`
4. **Monitor Performance**: Use `htop` and `docker stats` to monitor
5. **Join and Play**: Connect with your friends and enjoy!

## Additional Resources

- [Main README](README.md) - Full documentation
- [Server Properties Guide](https://minecraft.fandom.com/wiki/Server.properties)
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)

## Getting Help

If you encounter issues:

1. Check the Troubleshooting section above
2. Review logs: `./manage.sh logs`
3. Check system resources: `htop`
4. Open an issue on GitHub with:
   - Description of the problem
   - Steps to reproduce
   - Relevant log output
   - Your Raspberry Pi model and RAM

Happy mining! ⛏️🎮
