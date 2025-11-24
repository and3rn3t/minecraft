# Server Restart Loop Troubleshooting

If your Minecraft server keeps restarting, follow these steps to diagnose and fix the issue.

## Quick Diagnosis

1. **Check container status**:

   ```bash
   docker ps -a | grep minecraft-server
   ```

2. **View recent logs**:

   ```bash
   docker logs --tail 100 minecraft-server
   ```

3. **Check restart count**:

   ```bash
   docker inspect minecraft-server | grep -A 5 RestartCount
   ```

## Common Causes

### 1. Out of Memory (OOM)

**Symptoms**: Logs show `OutOfMemoryError` or container is killed by Docker

**Solution**:

- Reduce memory allocation in `docker-compose.yml`:

  ```yaml
  environment:
    - MEMORY_MIN=512M
    - MEMORY_MAX=1G
  ```

- Check system memory:

  ```bash
  free -h
  ```

### 2. Server JAR Missing or Corrupted

**Symptoms**: "Could not find or load main class" or "Error: Unable to access jarfile"

**Solution**:

```bash
# Stop server
docker-compose down

# Check if server.jar exists
ls -lh data/server.jar

# If missing, the start script will download it on next start
# Or manually download:
cd data
wget -O server.jar https://piston-data.mojang.com/v1/objects/8dd1a28015f51b1803213892b50b7b4fc76e594d/server.jar
```

### 3. Port Already in Use

**Symptoms**: "Address already in use" in logs

**Solution**:

```bash
# Find what's using port 25565
sudo netstat -tlnp | grep 25565
# or
sudo lsof -i :25565

# Kill the process or change port in docker-compose.yml
```

### 4. Corrupted World Data

**Symptoms**: Server crashes during world loading

**Solution**:

```bash
# Stop server
docker-compose down

# Backup and remove corrupted world
mv data/world data/world.backup.$(date +%Y%m%d)
# Or delete if you don't need it:
# rm -rf data/world

# Restart
docker-compose up -d
```

### 5. Healthcheck Failing

**Symptoms**: Container restarts even though Java is running

**Solution**:

- Increase healthcheck start period in `docker-compose.yml`:

  ```yaml
  healthcheck:
    start_period: 180s # Give server more time to start
    retries: 5
  ```

### 6. Disk Space Full

**Symptoms**: "No space left on device" in logs

**Solution**:

```bash
# Check disk space
df -h

# Clean up old backups/logs
./scripts/log-manager.sh clean
# Or manually:
rm -rf backups/*.tar.gz
rm -rf data/logs/*.log.gz
```

### 7. Insufficient Permissions

**Symptoms**: Permission denied errors in logs

**Solution**:

```bash
# Fix permissions
sudo chown -R $USER:$USER data/ backups/ plugins/
chmod -R 755 data/ backups/ plugins/
```

## Temporary Fix: Disable Auto-Restart

To stop the restart loop temporarily and investigate:

1. **Change restart policy**:

   ```yaml
   # In docker-compose.yml, change:
   restart: on-failure
   # to:
   restart: "no"
   ```

2. **Restart container**:

   ```bash
   docker-compose up -d
   ```

3. **Monitor logs**:

   ```bash
   docker logs -f minecraft-server
   ```

4. **Once fixed, restore restart policy**:

   ```yaml
   restart: on-failure
   ```

## Advanced Debugging

### Enable Verbose Logging

Add to `docker-compose.yml`:

```yaml
environment:
  - JAVA_OPTS=-Xlog:gc*:file=/minecraft/server/logs/gc.log -XX:+PrintGCDetails
```

### Check System Resources

```bash
# CPU and Memory usage
docker stats minecraft-server

# System temperature (Raspberry Pi)
vcgencmd measure_temp
vcgencmd get_throttled

# Disk I/O
iostat -x 1
```

### Check Java Process

```bash
# Inside container
docker exec minecraft-server ps aux | grep java
docker exec minecraft-server pgrep -f java

# Check Java version
docker exec minecraft-server java -version
```

## Prevention

1. **Monitor logs regularly**:

   ```bash
   docker logs --tail 50 -f minecraft-server
   ```

2. **Set appropriate memory limits** for your system

3. **Enable log rotation** to prevent disk fill

4. **Regular backups** before making changes

5. **Test changes** in a separate environment first

## Getting Help

If the issue persists, collect this information:

```bash
# System info
uname -a
free -h
df -h

# Docker info
docker version
docker-compose version

# Server logs (last 200 lines)
docker logs --tail 200 minecraft-server > server-logs.txt

# Container inspect
docker inspect minecraft-server > container-info.json

# Server configuration
cat docker-compose.yml
cat data/server.properties | head -20
```

Share these files when asking for help.
