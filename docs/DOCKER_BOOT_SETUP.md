# Docker Boot Setup for Raspberry Pi 5

This guide explains how to configure your Raspberry Pi 5 to boot up and automatically pull and run a Docker image as its primary workload.

## Overview

Instead of using a full desktop OS, this setup uses:

- **Minimal OS**: Raspberry Pi OS Lite (headless, minimal footprint)
- **Docker**: Container runtime for running your application
- **Systemd**: Service manager to auto-start Docker containers on boot
- **Auto-pull**: Automatically pulls the latest Docker image on boot

## Prerequisites

- Raspberry Pi 5
- MicroSD card (32GB+ recommended)
- Internet connection
- Computer to flash the SD card

## Method 1: Minimal OS with Docker Auto-Start (Recommended)

This is the most practical approach for Raspberry Pi 5.

### Step 1: Flash Raspberry Pi OS Lite

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert your microSD card
3. Open Raspberry Pi Imager
4. Choose OS: **Raspberry Pi OS Lite (64-bit)**
5. Click the gear icon (⚙️) for advanced options:
   - **Enable SSH**: Check this box
   - **Set username**: `pi` (or your preferred username)
   - **Set password**: Choose a secure password
   - **Configure WiFi**: Optional, but recommended
   - **Set hostname**: e.g., `docker-server`
6. Click **Write** and wait for completion

### Step 2: First Boot and Docker Installation

1. Insert the SD card into your Raspberry Pi 5
2. Power on and wait 2-3 minutes for first boot
3. SSH into your Pi:

```bash
ssh pi@docker-server.local
# Or use IP: ssh pi@192.168.1.XXX
```

4. Update the system:

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

5. Install Docker:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh
```

6. Install Docker Compose (optional, but recommended):

**Note**: Modern Docker installations include Docker Compose as a plugin. Check if it's already available:

```bash
docker compose version
```

If that works, you're all set! The plugin is already installed.

If you get an error, you can install the standalone version (though the plugin is preferred):

```bash
# Only if docker compose plugin is not available
sudo apt-get install -y docker-compose
```

**Important**: If you get a conflict error about `docker-compose-plugin`, the plugin is already installed. Use `docker compose` (with space) instead of `docker-compose` (with hyphen).

7. **Important**: Log out and back in for Docker permissions:

```bash
exit
# SSH back in
ssh pi@docker-server.local
```

### Step 3: Configure Auto-Pull and Start on Boot

Create a systemd service that will:

1. Pull the Docker image on boot
2. Start the container automatically
3. Restart the container if it crashes

#### Option A: Using Docker Compose (Recommended)

If you have a `docker-compose.yml` file:

```bash
# Create service directory
sudo mkdir -p /etc/systemd/system

# Create systemd service
sudo nano /etc/systemd/system/docker-app.service
```

Add this content:

```ini
[Unit]
Description=Docker Application Service
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/docker-app
ExecStartPre=/usr/bin/docker compose pull
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose up -d --force-recreate
Restart=on-failure
RestartSec=10
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable docker-app.service
sudo systemctl start docker-app.service
```

#### Option B: Using Docker Run Command

For a single container without docker compose:

```bash
sudo nano /etc/systemd/system/docker-app.service
```

Add this content (replace with your image name):

```ini
[Unit]
Description=Docker Application Container
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=-/usr/bin/docker stop docker-app
ExecStartPre=-/usr/bin/docker rm docker-app
ExecStartPre=/usr/bin/docker pull your-registry/your-image:latest
ExecStart=/usr/bin/docker run --name docker-app \
    --restart unless-stopped \
    -p 25565:25565 \
    -v /home/pi/app-data:/data \
    your-registry/your-image:latest
ExecStop=/usr/bin/docker stop docker-app
ExecStopPost=/usr/bin/docker rm docker-app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable docker-app.service
sudo systemctl start docker-app.service
```

### Step 4: Verify Auto-Start

1. Reboot your Pi:

```bash
sudo reboot
```

2. After reboot, SSH back in and check:

```bash
# Check if Docker container is running
docker ps

# Check service status
sudo systemctl status docker-app.service

# View logs
docker logs docker-app
# Or for docker compose
docker compose logs -f
```

## Method 2: Using Pre-built Docker Image Registry

If you want to pull from a Docker registry (Docker Hub, GitHub Container Registry, etc.):

### Step 1: Configure Docker Login (if using private registry)

```bash
# Login to Docker Hub
docker login

# Or for GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### Step 2: Update Systemd Service

Modify the service file to include authentication:

```ini
[Service]
Environment="DOCKER_USERNAME=your-username"
Environment="DOCKER_PASSWORD=your-password"
ExecStartPre=/bin/sh -c 'echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin'
ExecStartPre=/usr/bin/docker pull your-registry/your-image:latest
```

**Security Note**: For production, use Docker credential helpers or secrets management instead of plain passwords.

## Method 3: Pull from Git Repository on Boot

If your Docker image is built from a Git repository:

```bash
sudo nano /etc/systemd/system/docker-app.service
```

```ini
[Unit]
Description=Docker Application from Git
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/docker-app
ExecStartPre=/usr/bin/git pull origin main
ExecStartPre=/usr/bin/docker compose build
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10
User=pi

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Docker Compose Installation Conflict

**Error**: `dpkg: error processing archive ... trying to overwrite '/usr/libexec/docker/cli-plugins/docker-compose', which is also in package docker-compose-plugin`

**Solution**: The `docker-compose-plugin` is already installed. You don't need the standalone `docker-compose` package. Use the plugin version instead:

```bash
# Verify the plugin is installed
docker compose version

# If that works, you're all set! Use 'docker compose' (with space) instead of 'docker-compose' (with hyphen)
```

**Fix the broken package state**:

```bash
# Remove the broken package state
sudo apt-get remove --purge docker-compose
sudo apt-get autoremove
sudo apt-get autoclean

# Verify docker compose plugin works
docker compose version
```

**Important**: Always use `docker compose` (with space) when the plugin is installed, not `docker-compose` (with hyphen).

### Service Fails to Start (Error Code)

**Error**: `Job for docker-app.service failed because the control process exited with error code`

**Quick Diagnosis**:

```bash
# See the actual error
sudo journalctl -xeu docker-app.service --no-pager | tail -30

# Check service status
sudo systemctl status docker-app.service
```

**Common Fix: Docker Compose Command with Space**

If you're using `docker compose` (plugin), systemd needs it wrapped in a shell. The service file should use:

```ini
ExecStartPre=/bin/sh -c 'cd /home/pi/docker-app && /usr/bin/docker compose pull'
ExecStart=/bin/sh -c 'cd /home/pi/docker-app && /usr/bin/docker compose up -d'
ExecStop=/bin/sh -c 'cd /home/pi/docker-app && /usr/bin/docker compose down'
```

**Fix the service file**:

```bash
# Edit the service file
sudo nano /etc/systemd/system/docker-app.service

# Update the ExecStart lines to use /bin/sh -c wrapper
# Then reload and restart:
sudo systemctl daemon-reload
sudo systemctl restart docker-app.service
```

**Other Common Issues**:

- **Working directory doesn't exist**: `mkdir -p /home/pi/docker-app`
- **docker-compose.yml missing**: Create it or update WorkingDirectory
- **Permission denied**: `sudo chown -R pi:pi /home/pi/docker-app`
- **Docker not running**: `sudo systemctl start docker`

### Container Doesn't Start on Boot

1. Check service status:

```bash
sudo systemctl status docker-app.service
```

2. Check Docker service:

```bash
sudo systemctl status docker
```

3. View service logs:

```bash
sudo journalctl -u docker-app.service -f
```

4. Check Docker logs:

```bash
docker logs docker-app
```

### Image Pull Fails

1. Check internet connectivity:

```bash
ping -c 3 8.8.8.8
```

2. Test Docker pull manually:

```bash
docker pull your-registry/your-image:latest
```

3. Check Docker daemon:

```bash
sudo systemctl status docker
docker info
```

### Permission Issues

1. Ensure user is in docker group:

```bash
groups
# Should show 'docker' in the list
```

2. If not, add user:

```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Container Starts but Immediately Stops

1. Check container logs:

```bash
docker logs docker-app
```

2. Check container status:

```bash
docker ps -a
```

3. Test run manually:

```bash
docker run --rm your-registry/your-image:latest
```

## Advanced Configuration

### Pull Specific Image Tag

To always pull the latest tag:

```ini
ExecStartPre=/usr/bin/docker pull your-registry/your-image:latest
```

To pull a specific version:

```ini
ExecStartPre=/usr/bin/docker pull your-registry/your-image:v1.2.3
```

### Pull Only If Not Present

To avoid unnecessary pulls:

```ini
ExecStartPre=/bin/sh -c '/usr/bin/docker image inspect your-registry/your-image:latest >/dev/null 2>&1 || /usr/bin/docker pull your-registry/your-image:latest'
```

### Network Configuration

If your container needs specific network settings:

```ini
ExecStart=/usr/bin/docker run --name docker-app \
    --network host \
    --restart unless-stopped \
    your-registry/your-image:latest
```

### Resource Limits

Set memory and CPU limits:

```ini
ExecStart=/usr/bin/docker run --name docker-app \
    --memory="2g" \
    --cpus="2" \
    --restart unless-stopped \
    your-registry/your-image:latest
```

## Security Considerations

1. **Use Read-Only Root Filesystem** (if possible):

```bash
docker run --read-only --tmpfs /tmp your-image
```

2. **Use Non-Root User in Container**:

```bash
docker run --user 1000:1000 your-image
```

3. **Limit Container Capabilities**:

```bash
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE your-image
```

4. **Use Secrets Management**:

Instead of hardcoding passwords, use Docker secrets or environment files:

```bash
docker run --env-file /path/to/.env your-image
```

## Performance Optimization

1. **Use Docker BuildKit** for faster builds:

```bash
export DOCKER_BUILDKIT=1
docker build .
```

2. **Enable Docker Buildx** for multi-arch builds:

```bash
docker buildx create --use
```

3. **Optimize Image Layers**:

- Use multi-stage builds
- Minimize image size
- Use .dockerignore

## Alternative: Container-Optimized OS

For a more container-focused approach, consider:

- **BalenaOS**: Container-optimized OS for IoT devices
- **HypriotOS**: Docker-optimized Raspberry Pi OS
- **Alpine Linux**: Minimal Linux distribution

However, these require more setup and may not be as well-supported as Raspberry Pi OS Lite.

## Example: Minecraft Server Auto-Start

For this Minecraft server project specifically:

```bash
# Clone repository
cd ~
git clone https://github.com/and3rn3t/minecraft.git minecraft-server
cd minecraft-server

# Create systemd service
sudo nano /etc/systemd/system/minecraft.service
```

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
ExecStartPre=/usr/bin/docker compose pull
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable minecraft.service
sudo systemctl start minecraft.service
```

## Summary

This setup provides:

✅ **Minimal OS footprint** - Only what's needed  
✅ **Automatic image pulling** - Always up-to-date  
✅ **Auto-start on boot** - No manual intervention  
✅ **Automatic recovery** - Restarts on failure  
✅ **Easy updates** - Pull latest image and restart

Your Raspberry Pi 5 will now boot directly into your Docker containerized application!
