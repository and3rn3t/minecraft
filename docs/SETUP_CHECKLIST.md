# Minecraft Server Setup Checklist

Use this checklist to ensure your server is fully configured and ready to use.

## ✅ Completed Setup

- [x] Docker installed and working
- [x] Docker Compose plugin configured
- [x] Minecraft server container running
- [x] Systemd service configured for auto-start
- [x] API server running and accessible
- [x] Web frontend running and accessible
- [x] API key created
- [x] Network access configured

## 🔧 Recommended Configuration

### 1. Server Properties Configuration

Configure your server settings:

```bash
cd ~/minecraft-server

# Edit server properties
nano data/server.properties
```

**Key settings to configure:**

```properties
# Server Name
motd=My Minecraft Server

# Player Limits
max-players=10

# Game Settings
difficulty=normal
gamemode=survival
pvp=true

# Performance (adjust for your Pi)
view-distance=10          # Lower = better performance (6-12)
simulation-distance=8     # Lower = better performance (4-10)

# Security
white-list=false          # Set to true to enable whitelist
online-mode=true          # Require Minecraft authentication
spawn-protection=16       # Protected spawn radius

# World Settings
level-name=world
level-seed=              # Leave empty for random
generate-structures=true
```

**After editing, restart:**

```bash
sudo systemctl restart minecraft.service
```

### 2. Memory Settings (Optimize for Your Pi)

Check your Pi's RAM:

```bash
free -h
```

**For 4GB Pi:**

```bash
cd ~/minecraft-server
nano docker-compose.yml
```

Change to:

```yaml
environment:
  - MEMORY_MIN=1G
  - MEMORY_MAX=2G
```

**For 8GB Pi:**

```yaml
environment:
  - MEMORY_MIN=2G
  - MEMORY_MAX=4G
```

Then restart:

```bash
cd ~/minecraft-server
docker compose down
docker compose up -d
```

### 3. Test Minecraft Server Connection

**From your local network:**

1. Open Minecraft
2. Multiplayer → Add Server
3. Server Address: `192.168.1.22:25565` (your Pi's IP)
4. Click Done and join

**Verify server is accessible:**

```bash
# Check if port is listening
sudo netstat -tulpn | grep 25565

# Check server logs
cd ~/minecraft-server
docker compose logs --tail 50
```

### 4. Port Forwarding (For External Access)

To allow players outside your network:

1. **Log into your router** (usually 192.168.1.1)
2. **Find Port Forwarding settings**
3. **Add rule:**
   - External Port: 25565
   - Internal Port: 25565
   - Internal IP: 192.168.1.22 (your Pi's IP)
   - Protocol: TCP
4. **Save and apply**

**Find your public IP:**

```bash
curl ifconfig.me
```

Share this IP with friends: `YOUR_PUBLIC_IP:25565`

### 5. Configure Automatic Backups

Set up automated backups:

```bash
cd ~/minecraft-server

# Create backup schedule config
nano config/backup-schedule.conf
```

Add:

```
SCHEDULE=daily
TIME=03:00
ENABLED=true
```

**Or use the backup script:**

```bash
# Manual backup
./manage.sh backup

# Install automated backup timer
./scripts/install-backup-timer.sh
```

### 6. Firewall Configuration

Ensure ports are open:

```bash
# Allow Minecraft port
sudo ufw allow 25565/tcp

# Allow API port (already done)
sudo ufw allow 8080/tcp

# Allow web frontend port (already done)
sudo ufw allow 5173/tcp

# Check status
sudo ufw status
```

### 7. Optional: Install Plugins (Paper/Spigot)

If you want plugins, switch to Paper:

```bash
cd ~/minecraft-server

# Switch to Paper server
./scripts/switch-server-type.sh paper

# Restart server
sudo systemctl restart minecraft.service

# Install plugins
./scripts/plugin-manager.sh install /path/to/plugin.jar
```

### 8. Optional: Configure RCON (Remote Console)

Enable RCON for remote server management:

```bash
cd ~/minecraft-server

# Setup RCON
./scripts/rcon-setup.sh

# Test RCON connection
./scripts/rcon-client.sh "list"
```

### 9. Server Optimization

**For better performance on Raspberry Pi 5:**

```bash
cd ~/minecraft-server

# Run optimization script
./scripts/optimize-rpi5.sh

# Or manually optimize
./scripts/performance-presets.sh balanced
```

### 10. Test Everything

**Complete system test:**

```bash
cd ~/minecraft-server

# 1. Check Minecraft server
docker ps | grep minecraft
docker compose logs --tail 20

# 2. Check API server
./scripts/api-server.sh status
curl -H "X-API-Key: YOUR_KEY" http://localhost:8080/api/status

# 3. Check web frontend
curl http://localhost:5173

# 4. Test Minecraft connection
# From another computer, try connecting to 192.168.1.22:25565
```

## 📋 Quick Configuration Summary

**Essential settings to check:**

1. ✅ Server name (motd in server.properties)
2. ✅ Max players (max-players)
3. ✅ Difficulty (difficulty)
4. ✅ Memory limits (docker-compose.yml)
5. ✅ View distance (view-distance in server.properties)
6. ✅ Port forwarding (router settings)
7. ✅ Firewall rules (ufw)

## 🎮 Ready to Play!

Once you've completed the checklist:

1. **Local Network**: Players can connect using `192.168.1.22:25565`
2. **External Network**: Players can connect using `YOUR_PUBLIC_IP:25565` (after port forwarding)
3. **Web Interface**: Access at `http://192.168.1.22:5173`
4. **API**: Available at `http://192.168.1.22:8080/api`

## 🔍 Troubleshooting

**Server won't start:**

```bash
docker compose logs
sudo systemctl status minecraft.service
```

**Can't connect:**

```bash
# Check if server is running
docker ps

# Check if port is open
sudo netstat -tulpn | grep 25565

# Check firewall
sudo ufw status
```

**Performance issues:**

- Lower view-distance in server.properties
- Reduce max-players
- Check memory usage: `free -h`
- Monitor server: `docker stats minecraft-server`

## 📚 Additional Resources

- [Server Properties Guide](https://minecraft.fandom.com/wiki/Server.properties)
- [Performance Optimization](docs/RASPBERRY_PI_OPTIMIZATIONS.md)
- [Backup Management](docs/BACKUP_AND_MONITORING.md)
- [Plugin Management](docs/PLUGIN_MANAGEMENT.md)
