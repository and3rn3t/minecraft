# Quick Reference Guide

## Essential Commands

### Server Management
```bash
./manage.sh start      # Start server
./manage.sh stop       # Stop server
./manage.sh restart    # Restart server
./manage.sh status     # Check status
./manage.sh logs       # View logs
./manage.sh backup     # Create backup
```

### Docker Commands
```bash
docker-compose up -d              # Start in background
docker-compose down               # Stop and remove
docker-compose ps                 # List containers
docker-compose logs -f            # Follow logs
docker-compose restart            # Restart services
docker attach minecraft-server    # Attach to console
```

### System Commands
```bash
htop                    # Monitor system resources
docker stats            # Monitor Docker resources
df -h                   # Check disk space
free -h                 # Check memory usage
ip addr show            # Show IP address
sudo systemctl status docker  # Check Docker service
```

## Server Console Commands

Attach to console: `docker attach minecraft-server`
Detach: Press `Ctrl+P` then `Ctrl+Q`

Common Minecraft server commands:
```
/op <player>            # Give operator status
/deop <player>          # Remove operator status
/whitelist add <player> # Add to whitelist
/whitelist remove <player>
/ban <player>           # Ban player
/pardon <player>        # Unban player
/kick <player>          # Kick player
/list                   # List online players
/save-all               # Save the world
/stop                   # Stop server gracefully
```

## File Locations

```
~/minecraft-server/          # Main directory
├── server.properties        # Server configuration
├── docker-compose.yml       # Docker settings
├── data/                    # Server world & data
│   ├── world/              # Main world
│   ├── world_nether/       # Nether dimension
│   ├── world_the_end/      # End dimension
│   ├── logs/               # Server logs
│   └── whitelist.json      # Whitelist file
├── backups/                 # Backup storage
└── plugins/                 # Plugin directory
```

## Common Configuration Changes

### server.properties
```properties
# Change these commonly adjusted settings:
max-players=10              # Player limit
difficulty=normal           # easy/normal/hard/peaceful
gamemode=survival          # survival/creative/adventure
pvp=true                   # Enable/disable PVP
view-distance=10           # Render distance (6-12)
motd=My Server             # Server name/message
white-list=false           # Enable whitelist
online-mode=true           # Require Minecraft authentication
spawn-protection=16        # Protected spawn radius
```

### docker-compose.yml
```yaml
environment:
  - MINECRAFT_VERSION=1.20.4  # Server version
  - MEMORY_MIN=1G             # Minimum RAM
  - MEMORY_MAX=2G             # Maximum RAM
```

## Performance Tuning

### For 4GB Raspberry Pi 5
```yaml
# In docker-compose.yml
environment:
  - MEMORY_MIN=1G
  - MEMORY_MAX=2G

# In server.properties
view-distance=6
simulation-distance=6
max-players=5
```

### For 8GB Raspberry Pi 5
```yaml
# In docker-compose.yml
environment:
  - MEMORY_MIN=2G
  - MEMORY_MAX=4G

# In server.properties
view-distance=10
simulation-distance=8
max-players=10
```

## Network Settings

### Find Your Local IP
```bash
hostname -I
# Or
ip addr show | grep "inet "
```

### Check Port Status
```bash
sudo apt install nmap
nmap -p 25565 localhost
```

### Server Address Format
- **Local network**: `192.168.1.XXX:25565` or `minecraft-server.local:25565`
- **Internet**: `YOUR.PUBLIC.IP:25565`

## Backup & Restore

### Create Backup
```bash
./manage.sh backup
# Stored in: ./backups/minecraft_backup_TIMESTAMP.tar.gz
```

### Restore Backup
```bash
./manage.sh stop
tar -xzf backups/minecraft_backup_YYYYMMDD_HHMMSS.tar.gz -C ./data/
./manage.sh start
```

### Automated Backups (Cron)
```bash
crontab -e
# Add line for daily backup at 3 AM:
0 3 * * * cd ~/minecraft-server && ./manage.sh backup
```

## Troubleshooting Quick Fixes

### Server Won't Start
```bash
sudo systemctl restart docker
docker-compose down
docker-compose up -d
```

### High Memory Usage
```bash
# Reduce memory in docker-compose.yml
# Reduce view-distance in server.properties
# Restart server
./manage.sh restart
```

### Connection Refused
```bash
# Check if server is running
./manage.sh status

# Check if port is open
sudo ufw allow 25565/tcp

# Verify server is listening
sudo netstat -tlnp | grep 25565
```

### Disk Space Full
```bash
# Check space
df -h

# Clean up old backups
rm -f backups/minecraft_backup_OLD*.tar.gz

# Clean Docker
docker system prune -a
```

## Update Procedures

### Update Server Configuration
```bash
cd ~/minecraft-server
git pull
./manage.sh restart
```

### Update Minecraft Version
```bash
# Edit docker-compose.yml
nano docker-compose.yml
# Change MINECRAFT_VERSION

# Rebuild and restart
docker-compose down
rm -rf data/*.jar  # Remove old jar
docker-compose up -d --build
```

### Update Raspberry Pi OS
```bash
sudo apt update
sudo apt upgrade -y
sudo reboot
```

## Security Checklist

- [ ] Change default password
- [ ] Enable SSH key authentication
- [ ] Configure firewall (UFW)
- [ ] Enable whitelist mode
- [ ] Disable unnecessary services
- [ ] Regular backups
- [ ] Keep system updated

### Basic Firewall Setup
```bash
sudo apt install ufw
sudo ufw allow ssh
sudo ufw allow 25565/tcp
sudo ufw enable
```

## Useful Monitoring

### View Resource Usage Continuously
```bash
# Terminal 1: System resources
htop

# Terminal 2: Server logs
cd ~/minecraft-server && ./manage.sh logs

# Terminal 3: Docker stats
docker stats minecraft-server
```

### Check Server Uptime
```bash
docker ps --filter "name=minecraft-server" --format "{{.Status}}"
```

## Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| Can't connect locally | Check if server is running: `./manage.sh status` |
| Can't connect from internet | Configure port forwarding on router |
| Low FPS/lag | Reduce view-distance and max-players |
| Out of memory | Lower MEMORY_MAX in docker-compose.yml |
| Server crash on startup | Check logs: `./manage.sh logs` |
| Permission denied | Run: `sudo chown -R $USER:$USER ~/minecraft-server` |

## Contact & Support

- **Documentation**: See README.md and INSTALL.md
- **Issues**: Open GitHub issue with logs
- **Logs Location**: `./data/logs/latest.log`

---

**Quick Setup Summary:**
1. Flash Raspberry Pi OS with Imager
2. SSH to Pi: `ssh pi@minecraft-server.local`
3. Clone repo: `git clone https://github.com/and3rn3t/minecraft.git minecraft-server`
4. Run setup: `cd minecraft-server && ./setup-rpi.sh`
5. Log out and back in
6. Start server: `./manage.sh start`
7. Connect: `minecraft-server.local:25565`

**Emergency Stop:** `./manage.sh stop` or `docker-compose down`
