# Troubleshooting Guide

This guide helps you diagnose and fix common issues with the Minecraft Server on Raspberry Pi 5.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Server Startup Issues](#server-startup-issues)
3. [Connection Issues](#connection-issues)
4. [Performance Issues](#performance-issues)
5. [Docker Issues](#docker-issues)
6. [System Issues](#system-issues)

## Installation Issues

### Setup Script Fails

**Symptoms**: `setup-rpi.sh` exits with errors

**Solutions**:

1. **Check internet connection**:

   ```bash
   ping -c 4 google.com
   ```

2. **Update package lists first**:

   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

3. **Run script with more verbose output**:

   ```bash
   bash -x ./setup-rpi.sh
   ```

4. **Check disk space**:

   ```bash
   df -h
   # Should have at least 5GB free
   ```

### Docker Installation Fails

**Symptoms**: Docker or Docker Compose not found after installation

**Solutions**:

1. **Manually install Docker**:

   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Install Docker Compose separately**:

   ```bash
   sudo apt install docker-compose
   ```

3. **Verify installation**:

   ```bash
   docker --version
   docker-compose --version
   ```

### Permission Denied Errors

**Symptoms**: "Permission denied" when running commands

**Solutions**:

1. **Add user to Docker group**:

   ```bash
   sudo usermod -aG docker $USER
   ```

2. **Log out and back in**:

   ```bash
   exit
   # Then SSH back in
   ```

3. **Fix file permissions**:

   ```bash
   sudo chown -R $USER:$USER ~/minecraft-server
   chmod +x ~/minecraft-server/*.sh
   ```

## Server Startup Issues

### Server Won't Start

**Symptoms**: `./manage.sh start` fails or server exits immediately

**Diagnostic Steps**:

1. **Check Docker service**:

   ```bash
   sudo systemctl status docker
   ```

   If not running: `sudo systemctl start docker`

2. **View detailed logs**:

   ```bash
   docker-compose logs
   ```

3. **Check for port conflicts**:

   ```bash
   sudo netstat -tlnp | grep 25565
   ```

4. **Verify disk space**:

   ```bash
   df -h
   ```

**Common Causes & Solutions**:

#### EULA Not Accepted

**Error**: "You need to agree to the EULA"

**Solution**:

```bash
echo "eula=true" > ~/minecraft-server/eula.txt
./manage.sh restart
```

#### Out of Memory

**Error**: "OutOfMemoryError" in logs

**Solution**: Reduce memory allocation in `docker-compose.yml`:

```yaml
environment:
  - MEMORY_MIN=512M
  - MEMORY_MAX=1G
```

#### Port Already in Use

**Error**: "Address already in use"

**Solution**:

```bash
# Find what's using the port
sudo netstat -tlnp | grep 25565

# Kill the process (replace PID)
sudo kill -9 PID

# Or change port in docker-compose.yml
ports:
  - "25566:25565"
```

### Server Crashes During Startup

**Symptoms**: Server starts but crashes during world generation

**Solutions**:

1. **Increase memory allocation**:

   ```yaml
   MEMORY_MAX=2G  # In docker-compose.yml
   ```

2. **Check system temperature**:

   ```bash
   vcgencmd measure_temp
   # Should be below 80°C
   ```

3. **Ensure adequate cooling**:
   - Add heatsink or fan
   - Improve case ventilation

4. **Delete corrupted world**:

   ```bash
   ./manage.sh stop
   rm -rf data/world*
   ./manage.sh start
   ```

### Server Download Fails

**Symptoms**: "Failed to download Minecraft server jar"

**Solutions**:

1. **Check internet connection**:

   ```bash
   curl -I https://www.minecraft.net
   ```

2. **Manually download jar**:

   ```bash
   cd ~/minecraft-server/data
   # Use the same URL from start.sh (line 30)
   wget -O server.jar https://piston-data.mojang.com/v1/objects/8dd1a28015f51b1803213892b50b7b4fc76e594d/server.jar
   ```

3. **Update download URL** in `start.sh` (line 30) for different Minecraft versions
   - Find version-specific URLs at <https://www.minecraft.net/en-us/download/server>

## Connection Issues

### Cannot Connect Locally

**Symptoms**: Can't connect from local network

**Diagnostic Steps**:

1. **Verify server is running**:

   ```bash
   ./manage.sh status
   # Should show "Up"
   ```

2. **Check server logs**:

   ```bash
   ./manage.sh logs
   # Look for "Done!" message
   ```

3. **Test port accessibility**:

   ```bash
   sudo apt install nmap
   nmap -p 25565 localhost
   # Should show "open"
   ```

4. **Check firewall**:

   ```bash
   sudo ufw status
   # If active, add rule:
   sudo ufw allow 25565/tcp
   ```

5. **Verify IP address**:

   ```bash
   hostname -I
   ```

**Solutions**:

1. **Try different addresses**:
   - `localhost:25565` (from Pi itself)
   - `minecraft-server.local:25565`
   - `192.168.1.XXX:25565` (actual IP)

2. **Check server.properties**:

   ```properties
   server-ip=
   # Should be empty for all interfaces
   server-port=25565
   online-mode=true
   ```

### Cannot Connect from Internet

**Symptoms**: Local works, but external connections fail

**Diagnostic Steps**:

1. **Verify port forwarding**:
   - Log into router
   - Check port 25565 is forwarded to Pi's IP
   - Protocol should be TCP

2. **Check public IP**:

   ```bash
   curl ifconfig.me
   ```

3. **Test from external service**:
   - Use <https://mcsrvstat.us/>
   - Enter your public IP

**Solutions**:

1. **Configure port forwarding**:
   - External Port: 25565
   - Internal Port: 25565
   - Internal IP: Pi's local IP (e.g., 192.168.1.100)
   - Protocol: TCP
   - Save and reboot router

2. **Use static local IP** or DHCP reservation

3. **Check ISP restrictions**:
   - Some ISPs block port 25565
   - Try alternate port (e.g., 25566)

4. **Consider dynamic DNS**:
   - Services like No-IP or DuckDNS
   - Provides consistent hostname

### Connection Times Out

**Symptoms**: "Connection timed out" error

**Solutions**:

1. **Increase timeout in Minecraft client**
2. **Check network latency**:

   ```bash
   ping YOUR_SERVER_IP
   ```

3. **Reduce server load**:
   - Lower view-distance
   - Reduce max-players

## Performance Issues

### Server Lag / Low TPS

**Symptoms**: Server is slow, blocks break slowly, entities lag

**Diagnostic Steps**:

1. **Check TPS** (in-game):

   ```
   /forge tps
   # Should be 20 TPS
   ```

2. **Monitor resources**:

   ```bash
   htop
   docker stats minecraft-server
   ```

3. **Check temperature**:

   ```bash
   vcgencmd measure_temp
   ```

**Solutions**:

1. **Optimize server.properties**:

   ```properties
   view-distance=6
   simulation-distance=6
   max-players=5
   entity-broadcast-range-percentage=50
   ```

2. **Reduce memory if swapping**:

   ```bash
   free -h
   # If swap is used, reduce MEMORY_MAX
   ```

3. **Improve cooling**:
   - Ensure case has ventilation
   - Add active cooling (fan)

4. **Use SSD instead of microSD**:
   - Better I/O performance
   - Reduces stuttering

5. **Limit chunk loading**:

   ```properties
   max-chained-neighbor-updates=100000
   ```

### High Memory Usage

**Symptoms**: System becomes unresponsive, OOM errors

**Solutions**:

1. **Check memory usage**:

   ```bash
   free -h
   docker stats
   ```

2. **Reduce allocation**:

   ```yaml
   # docker-compose.yml
   MEMORY_MAX=1G  # Instead of 2G
   ```

3. **Lower view distance**:

   ```properties
   view-distance=6
   simulation-distance=4
   ```

4. **Restart server periodically**:

   ```bash
   # Add to crontab for daily restart
   0 4 * * * cd ~/minecraft-server && ./manage.sh restart
   ```

### High CPU Usage

**Symptoms**: CPU constantly at 100%, slow response

**Solutions**:

1. **Reduce simulation distance**:

   ```properties
   simulation-distance=4
   ```

2. **Limit entities**:

   ```properties
   entity-broadcast-range-percentage=50
   spawn-animals=false  # If not needed
   spawn-monsters=true  # Keep for gameplay
   ```

3. **Ensure thermal throttling isn't occurring**:

   ```bash
   vcgencmd measure_temp
   vcgencmd get_throttled
   # 0x0 = no throttling
   ```

## Docker Issues

### Container Won't Start

**Symptoms**: Docker errors when starting

**Solutions**:

1. **Remove old containers**:

   ```bash
   docker-compose down
   docker rm minecraft-server
   docker-compose up -d
   ```

2. **Rebuild image**:

   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **Check Docker logs**:

   ```bash
   docker logs minecraft-server
   ```

### Docker Disk Space Full

**Symptoms**: "No space left on device"

**Solutions**:

1. **Check Docker disk usage**:

   ```bash
   docker system df
   ```

2. **Clean up Docker**:

   ```bash
   docker system prune -a
   # Warning: removes unused images
   ```

3. **Remove old images**:

   ```bash
   docker images
   docker rmi IMAGE_ID
   ```

### Cannot Attach to Console

**Symptoms**: `docker attach` doesn't work

**Solutions**:

1. **Ensure TTY is enabled**:

   ```yaml
   # In docker-compose.yml
   tty: true
   stdin_open: true
   ```

2. **Use docker exec instead**:

   ```bash
   docker exec -it minecraft-server /bin/bash
   ```

## System Issues

### SD Card Corruption

**Symptoms**: File system errors, read-only filesystem

**Prevention**:

- Use high-quality microSD card (A2 rated)
- Regular backups
- Proper shutdown procedures

**Solutions**:

1. **Check filesystem**:

   ```bash
   sudo fsck -f /dev/mmcblk0p2
   ```

2. **Restore from backup**:

   ```bash
   ./manage.sh stop
   tar -xzf backups/minecraft_backup_*.tar.gz -C data/
   ./manage.sh start
   ```

3. **Consider using SSD**:
   - More reliable
   - Better performance

### Raspberry Pi Won't Boot

**Symptoms**: No display, no SSH access

**Solutions**:

1. **Check power supply**:
   - Use official 27W USB-C adapter
   - Check for undervoltage icon

2. **Re-flash SD card**:
   - Backup data first
   - Use Raspberry Pi Imager
   - Flash fresh OS

3. **Test SD card**:
   - Try different card
   - Test card on computer

### System Overheating

**Symptoms**: Thermal throttling, crashes, slow performance

**Solutions**:

1. **Check temperature**:

   ```bash
   watch vcgencmd measure_temp
   ```

2. **Improve cooling**:
   - Add heatsink to CPU
   - Add active cooling fan
   - Improve case ventilation
   - Reduce ambient temperature

3. **Reduce load**:
   - Lower max-players
   - Reduce view-distance
   - Lower memory allocation

## Log Management

### Viewing Logs

**Basic log viewing**:

```bash
./manage.sh logs
# Shows last 100 lines of server logs
```

**Search logs**:

```bash
./manage.sh logs-search "error"
# Search for "error" in logs

./manage.sh logs-search -l ERROR
# Show all ERROR level messages

./manage.sh logs-search -d 2025-01-15 "crash"
# Search for "crash" on specific date

./manage.sh logs-search -r 2025-01-01 2025-01-31 "player joined"
# Search date range
```

**Log management**:

```bash
./manage.sh logs-manage all
# Run all log operations (rotate, index, errors, stats)

./manage.sh logs-manage index
# Parse and index logs for faster searching

./manage.sh logs-manage errors
# Detect and report error patterns

./manage.sh logs-manage rotate
# Rotate and archive old logs

./manage.sh logs-manage stats
# Show log statistics
```

### Log Configuration

Edit `config/log-management.conf` to configure:

- Log retention period (default: 30 days)
- Maximum log file size before rotation (default: 100MB)
- Indexing and error detection settings

### Common Log Issues

**Logs growing too large**:

```bash
# Manually rotate logs
./manage.sh logs-manage rotate

# Or reduce retention period in config/log-management.conf
LOG_RETENTION_DAYS=7
```

**Cannot find specific log entries**:

```bash
# Re-index logs
./manage.sh logs-manage index

# Then search
./manage.sh logs-search "your search term"
```

**Too many errors detected**:

```bash
# View error summary
./manage.sh logs-manage errors

# Check specific error patterns
./manage.sh logs-search -l ERROR
```

## Getting Additional Help

### Collecting Debug Information

When asking for help, include:

1. **System information**:

   ```bash
   cat /proc/device-tree/model
   free -h
   df -h
   vcgencmd measure_temp
   ```

2. **Server logs**:

   ```bash
   docker-compose logs > logs.txt
   # Or use log management
   ./manage.sh logs-manage errors > errors.txt
   ./manage.sh logs-search "error" > search_results.txt
   ```

3. **Configuration**:

   ```bash
   cat docker-compose.yml
   cat server.properties | grep -v "^#"
   ```

4. **Docker status**:

   ```bash
   docker ps -a
   docker stats --no-stream
   ```

### Support Resources

- **GitHub Issues**: Report bugs and issues
- **README.md**: General documentation
- **INSTALL.md**: Installation guide
- **QUICK_REFERENCE.md**: Command reference
- **Minecraft Wiki**: <https://minecraft.fandom.com/wiki/Server>
- **Raspberry Pi Forums**: <https://forums.raspberrypi.com/>

### Best Practices

1. **Regular backups**: `./manage.sh backup`
2. **Monitor resources**: `htop` and `docker stats`
3. **Keep system updated**: `sudo apt update && sudo apt upgrade`
4. **Use quality hardware**: Good SD card, proper cooling
5. **Document changes**: Note what works for your setup

---

Still having issues? Open an issue on GitHub with:

- Detailed problem description
- Steps to reproduce
- Log output
- System information
- Configuration files
