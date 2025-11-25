# Complete Raspberry Pi 5 Deployment Guide

This guide covers setting up all components of the Minecraft server management system on Raspberry Pi 5:

- Minecraft Server (Docker container)
- REST API Server (Flask/Python)
- Web Interface (React app served by Nginx)

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS (64-bit)
- Docker and Docker Compose installed
- Python 3.9+ installed
- Node.js 18+ installed (for building web interface)
- Nginx installed

## Installation Steps

### 1. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Nginx
sudo apt install -y nginx

# Log out and back in for Docker group to take effect
```

### 2. Clone and Setup Project

```bash
# Clone repository (or copy files)
cd /home/pi
git clone <your-repo-url> minecraft
cd minecraft

# Create necessary directories
mkdir -p logs data backups plugins config

# Install Python dependencies
cd api
pip3 install --user -r requirements.txt
cd ..

# Build web interface
cd web
npm install
npm run build
cd ..
```

### 3. Configure Services

#### Configure API Server

Edit `config/api.conf` if needed (defaults are usually fine):

```bash
# API should be accessible from localhost
API_HOST=127.0.0.1
API_PORT=8080
CORS_ENABLED=true
```

#### Configure Nginx

1. Copy nginx configuration:

```bash
sudo cp config/nginx-minecraft.conf /etc/nginx/sites-available/minecraft
sudo ln -s /etc/nginx/sites-available/minecraft /etc/nginx/sites-enabled/
```

2. Remove default nginx site (optional):

```bash
sudo rm /etc/nginx/sites-enabled/default
```

3. Test nginx configuration:

```bash
sudo nginx -t
```

4. Reload nginx:

```bash
sudo systemctl reload nginx
```

### 4. Install Systemd Services

```bash
# Copy systemd service files
sudo cp systemd/minecraft.service /etc/systemd/system/
sudo cp systemd/minecraft-api.service /etc/systemd/system/
sudo cp systemd/minecraft-web.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable minecraft.service
sudo systemctl enable minecraft-api.service
sudo systemctl enable minecraft-web.service
```

### 5. Start All Services

```bash
# Start services in order
sudo systemctl start minecraft-api.service
sudo systemctl start minecraft-web.service
sudo systemctl start minecraft.service

# Check status
sudo systemctl status minecraft.service
sudo systemctl status minecraft-api.service
sudo systemctl status minecraft-web.service
```

### 6. Verify All Components

Use the health check script:

```bash
chmod +x scripts/check-services.sh
./scripts/check-services.sh
```

Or check manually:

```bash
# Check Minecraft server
docker ps | grep minecraft-server

# Check API server
curl http://127.0.0.1:8080/api/status

# Check web interface
curl http://127.0.0.1/
```

## Service Management

### Start All Services

```bash
sudo systemctl start minecraft.service
sudo systemctl start minecraft-api.service
sudo systemctl start minecraft-web.service
```

### Stop All Services

```bash
sudo systemctl stop minecraft.service
sudo systemctl stop minecraft-api.service
sudo systemctl stop minecraft-web.service
```

### Restart All Services

```bash
sudo systemctl restart minecraft.service
sudo systemctl restart minecraft-api.service
sudo systemctl restart minecraft-web.service
```

### Check Service Status

```bash
# Individual services
sudo systemctl status minecraft.service
sudo systemctl status minecraft-api.service
sudo systemctl status minecraft-web.service

# All at once
sudo systemctl status minecraft.service minecraft-api.service minecraft-web.service
```

### View Logs

```bash
# Minecraft server logs
docker logs -f minecraft-server

# API server logs
tail -f logs/api-server.log
# Or via systemd
sudo journalctl -u minecraft-api.service -f

# Web server logs (nginx)
sudo tail -f /var/log/nginx/minecraft-web-access.log
sudo tail -f /var/log/nginx/minecraft-web-error.log
```

## Updating Components

### Update Web Interface

```bash
cd /home/pi/minecraft/web
git pull  # or update files
npm install  # if dependencies changed
npm run build
sudo systemctl reload nginx
```

### Update API Server

```bash
cd /home/pi/minecraft/api
git pull  # or update files
pip3 install --user -r requirements.txt
sudo systemctl restart minecraft-api.service
```

### Update Minecraft Server

The Minecraft server updates automatically when you push to the main branch (see [AUTO_DEPLOYMENT_SETUP.md](AUTO_DEPLOYMENT_SETUP.md)), or manually:

```bash
cd /home/pi/minecraft
docker compose pull
docker compose up -d
```

## Troubleshooting

### Service Won't Start

1. Check service status:

   ```bash
   sudo systemctl status <service-name>
   ```

2. Check logs:

   ```bash
   sudo journalctl -u <service-name> -n 50
   ```

3. Check permissions:
   ```bash
   ls -la /home/pi/minecraft
   ```

### API Server Not Responding

1. Check if Python dependencies are installed:

   ```bash
   python3 -c "import flask"
   ```

2. Check if port is in use:

   ```bash
   sudo netstat -tuln | grep 8080
   ```

3. Check API config:
   ```bash
   cat config/api.conf
   ```

### Web Interface Not Loading

1. Check if build exists:

   ```bash
   ls -la web/dist/
   ```

2. Rebuild if needed:

   ```bash
   cd web && npm run build
   ```

3. Check nginx configuration:

   ```bash
   sudo nginx -t
   ```

4. Check nginx error logs:
   ```bash
   sudo tail -f /var/log/nginx/minecraft-web-error.log
   ```

### Minecraft Server Not Starting

1. Check Docker:

   ```bash
   docker ps -a
   docker logs minecraft-server
   ```

2. Check permissions:

   ```bash
   ls -la data/ backups/ plugins/
   ```

3. Fix permissions if needed:
   ```bash
   chmod -R 777 data/ backups/ plugins/
   ```

## Accessing the System

- **Web Interface**: `http://<raspberry-pi-ip>/`
- **API**: `http://<raspberry-pi-ip>/api` (or `http://localhost:8080/api` locally)
- **Minecraft Server**: `<raspberry-pi-ip>:25565`

## Security Considerations

1. **Firewall**: Configure firewall to only allow necessary ports:

   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp     # Web interface
   sudo ufw allow 25565/tcp  # Minecraft server
   sudo ufw enable
   ```

2. **API Access**: The API is configured to listen on `127.0.0.1` by default (localhost only). If you need external access, change `API_HOST` in `config/api.conf` to `0.0.0.0` and configure proper authentication.

3. **HTTPS**: For production, set up SSL/TLS certificates and configure nginx for HTTPS.

## Next Steps

- See [AUTO_DEPLOYMENT_SETUP.md](AUTO_DEPLOYMENT_SETUP.md) for automatic updates
- See [API.md](API.md) for API documentation
- See [WEB_INTERFACE.md](WEB_INTERFACE.md) for web interface documentation
