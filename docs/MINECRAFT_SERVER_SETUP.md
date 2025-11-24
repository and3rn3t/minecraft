# Setting Up Minecraft Server with Auto-Start

This guide will help you configure your Minecraft server to start automatically on boot using the Docker boot setup.

## Prerequisites

- Raspberry Pi 5 with Docker installed and working
- Docker boot service configured (see [DOCKER_BOOT_SETUP.md](DOCKER_BOOT_SETUP.md))
- Internet connection

## Step 1: Clone or Copy the Minecraft Server Project

If you haven't already, get the Minecraft server files on your Pi:

```bash
# Option A: Clone from Git (if you have a repository)
cd ~
git clone https://github.com/and3rn3t/minecraft.git minecraft-server
cd minecraft-server

# Option B: Copy files from your computer using SCP
# From your computer:
# scp -r /path/to/minecraft pi@docker-server.local:~/minecraft-server
```

## Step 2: Create Required Directories

The Minecraft server needs these directories:

```bash
cd ~/minecraft-server

# Create required directories
mkdir -p data backups plugins config

# Set proper permissions
chmod -R 755 data backups plugins config
```

## Step 3: Configure the Server (Optional)

Before starting, you may want to customize settings:

```bash
# Edit memory settings for your Pi (4GB or 8GB)
nano docker-compose.yml

# For 4GB Pi, use:
#   MEMORY_MIN=1G
#   MEMORY_MAX=2G

# For 8GB Pi, use:
#   MEMORY_MIN=2G
#   MEMORY_MAX=4G
```

## Step 4: Stop the Test Service

If you still have the test nginx service running:

```bash
# Stop and disable the test service
sudo systemctl stop docker-app.service
sudo systemctl disable docker-app.service
```

## Step 5: Set Up Minecraft Server Service

Use the automated setup script:

```bash
cd ~/minecraft-server

# Make the script executable
chmod +x scripts/setup-docker-boot.sh

# Run the Minecraft setup
./scripts/setup-docker-boot.sh minecraft
```

Or manually create the service:

```bash
# Create the service file
sudo nano /etc/systemd/system/minecraft.service
```

Add this content (adjust paths if needed):

```ini
[Unit]
Description=Minecraft Server
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/minecraft-server
ExecStartPre=/bin/sh -c 'cd /home/pi/minecraft-server && /usr/bin/docker compose pull || true'
ExecStart=/bin/sh -c 'cd /home/pi/minecraft-server && /usr/bin/docker compose up -d --build'
ExecStop=/bin/sh -c 'cd /home/pi/minecraft-server && /usr/bin/docker compose down'
ExecReload=/bin/sh -c 'cd /home/pi/minecraft-server && /usr/bin/docker compose up -d --force-recreate'
Restart=on-failure
RestartSec=10
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
```

**Note**: The `|| true` after `docker compose pull` allows the service to continue even if the image hasn't been pushed to a registry (it will build locally instead).

## Step 6: Enable and Start the Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable minecraft.service

# Start the service now
sudo systemctl start minecraft.service

# Check status
sudo systemctl status minecraft.service
```

## Step 7: Monitor the First Start

The first start will take 5-10 minutes as it:

1. Builds the Docker image
2. Downloads the Minecraft server JAR
3. Generates the world
4. Prepares the spawn area

Watch the logs:

```bash
# View service logs
sudo journalctl -u minecraft.service -f

# Or view Docker container logs
cd ~/minecraft-server
docker compose logs -f

# Or use the management script
./manage.sh logs
```

Wait for "Done!" in the logs, which means the server is ready.

## Step 8: Verify Server is Running

```bash
# Check container status
docker ps

# Should show minecraft-server container running

# Check server logs for "Done!"
docker compose logs | grep -i "done"

# Test connection (from another machine)
# Use your Pi's IP: 192.168.1.XXX:25565
```

## Step 9: Accept EULA (If Required)

If you see EULA errors in the logs:

```bash
cd ~/minecraft-server

# The EULA should be auto-accepted via environment variable
# But if needed, you can check:
cat data/eula.txt

# Or manually accept:
echo "eula=true" > data/eula.txt
```

## Step 10: Configure Server Properties (Optional)

Customize your server:

```bash
cd ~/minecraft-server

# Edit server properties
nano data/server.properties

# Common settings:
# max-players=10
# difficulty=normal
# gamemode=survival
# view-distance=10
# motd=My Minecraft Server

# Restart to apply changes
sudo systemctl restart minecraft.service
```

## Management Commands

### Using systemd:

```bash
# Start server
sudo systemctl start minecraft.service

# Stop server
sudo systemctl stop minecraft.service

# Restart server
sudo systemctl restart minecraft.service

# Check status
sudo systemctl status minecraft.service

# View logs
sudo journalctl -u minecraft.service -f
```

### Using Docker Compose:

```bash
cd ~/minecraft-server

# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# Restart
docker compose restart
```

### Using Management Script:

```bash
cd ~/minecraft-server

# Make executable (if not already)
chmod +x manage.sh

# Start
./manage.sh start

# Stop
./manage.sh stop

# Status
./manage.sh status

# Logs
./manage.sh logs

# Console (attach to server)
./manage.sh console
```

## Troubleshooting

### Service Won't Start

```bash
# Check detailed error
sudo journalctl -xeu minecraft.service --no-pager | tail -30

# Common issues:
# - WorkingDirectory doesn't exist: mkdir -p /home/pi/minecraft-server
# - docker-compose.yml missing: Check you're in the right directory
# - Permission denied: sudo chown -R pi:pi /home/pi/minecraft-server
```

### Container Build Fails

```bash
# Check build logs
docker compose build --no-cache

# Check Dockerfile exists
ls -la Dockerfile

# Check disk space
df -h
```

### Server Won't Start

```bash
# Check container logs
docker compose logs

# Check if port 25565 is already in use
sudo netstat -tulpn | grep 25565

# Check memory
free -h

# Reduce memory in docker-compose.yml if needed
```

### Can't Connect to Server

```bash
# Check if server is running
docker ps

# Check if port is open
sudo ufw status
sudo ufw allow 25565/tcp

# Check server IP
hostname -I

# Test locally
telnet localhost 25565
```

## Next Steps

- Set up port forwarding on your router (port 25565)
- Configure backups (see [BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md))
- Install plugins (see [PLUGIN_MANAGEMENT.md](PLUGIN_MANAGEMENT.md))
- Set up the web interface (see [WEB_INTERFACE.md](WEB_INTERFACE.md))
- Configure RCON (see [RCON.md](RCON.md))

## Summary

Your Minecraft server is now configured to:

- ✅ Start automatically on boot
- ✅ Pull/build latest image on boot
- ✅ Restart automatically if it crashes
- ✅ Run in the background via systemd

The server will be accessible at `YOUR_PI_IP:25565` once it's fully started.
