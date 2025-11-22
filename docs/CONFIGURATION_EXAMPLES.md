# Configuration Examples

This document provides various configuration examples for different use cases.

## Table of Contents
1. [Basic Configurations](#basic-configurations)
2. [Performance Configurations](#performance-configurations)
3. [Security Configurations](#security-configurations)
4. [Gameplay Configurations](#gameplay-configurations)

## Basic Configurations

### Small Family Server (4GB Pi)
**Best for: 2-4 players**

`docker-compose.yml`:
```yaml
environment:
  - MINECRAFT_VERSION=1.20.4
  - MEMORY_MIN=1G
  - MEMORY_MAX=2G
```

`server.properties`:
```properties
max-players=5
view-distance=8
simulation-distance=6
difficulty=normal
gamemode=survival
pvp=true
spawn-protection=16
```

### Medium Server (8GB Pi)
**Best for: 5-10 players**

`docker-compose.yml`:
```yaml
environment:
  - MINECRAFT_VERSION=1.20.4
  - MEMORY_MIN=2G
  - MEMORY_MAX=4G
```

`server.properties`:
```properties
max-players=10
view-distance=10
simulation-distance=8
difficulty=normal
gamemode=survival
pvp=true
spawn-protection=16
```

## Performance Configurations

### Low-End Mode (Maximum Performance)
**For: Older Pi models or low RAM**

`docker-compose.yml`:
```yaml
environment:
  - MEMORY_MIN=512M
  - MEMORY_MAX=1G
```

`server.properties`:
```properties
max-players=3
view-distance=6
simulation-distance=4
max-tick-time=60000
network-compression-threshold=128
entity-broadcast-range-percentage=50
```

### Balanced Mode (Recommended)
**For: Standard gameplay**

`docker-compose.yml`:
```yaml
environment:
  - MEMORY_MIN=1G
  - MEMORY_MAX=2G
```

`server.properties`:
```properties
max-players=8
view-distance=10
simulation-distance=8
network-compression-threshold=256
entity-broadcast-range-percentage=100
```

### High Performance Mode
**For: 8GB Pi with SSD**

`docker-compose.yml`:
```yaml
environment:
  - MEMORY_MIN=2G
  - MEMORY_MAX=4G
```

`server.properties`:
```properties
max-players=12
view-distance=12
simulation-distance=10
network-compression-threshold=512
entity-broadcast-range-percentage=100
```

## Security Configurations

### Whitelist-Only Server

`server.properties`:
```properties
white-list=true
enforce-whitelist=true
online-mode=true
```

Then add players:
```bash
docker attach minecraft-server
# In server console:
/whitelist add PlayerName1
/whitelist add PlayerName2
/whitelist on
```

### Private Server (LAN Only)

`docker-compose.yml`:
```yaml
ports:
  - "127.0.0.1:25565:25565"  # Only accessible locally
```

### Public Server with RCON

`server.properties`:
```properties
enable-rcon=true
rcon.port=25575
rcon.password=YourSecurePasswordHere
```

`docker-compose.yml`:
```yaml
ports:
  - "25565:25565"
  - "127.0.0.1:25575:25575"  # RCON only accessible locally
```

## Gameplay Configurations

### Creative Building Server

`server.properties`:
```properties
gamemode=creative
difficulty=peaceful
spawn-monsters=false
spawn-animals=true
pvp=false
allow-flight=true
force-gamemode=true
max-build-height=319
```

### Survival Challenge (Hard Mode)

`server.properties`:
```properties
gamemode=survival
difficulty=hard
hardcore=false
pvp=true
spawn-monsters=true
spawn-animals=true
allow-flight=false
player-idle-timeout=30
```

### PvP Arena Server

`server.properties`:
```properties
gamemode=adventure
difficulty=normal
pvp=true
spawn-protection=0
allow-flight=false
force-gamemode=true
spawn-monsters=false
spawn-animals=false
```

### Peaceful Exploration

`server.properties`:
```properties
gamemode=survival
difficulty=peaceful
pvp=false
spawn-monsters=false
spawn-animals=true
allow-flight=false
generate-structures=true
```

### Adventure Map Server

`server.properties`:
```properties
gamemode=adventure
difficulty=normal
pvp=false
allow-flight=false
force-gamemode=true
spawn-protection=0
enable-command-block=true
```

## Special Configurations

### SuperFlat World

`server.properties`:
```properties
level-type=minecraft\:flat
generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}
```

### Amplified World (Resource Intensive)

`server.properties`:
```properties
level-type=minecraft\:amplified
# Note: Requires more RAM and CPU
```

### Custom Seed World

`server.properties`:
```properties
level-seed=1234567890
level-name=CustomWorld
```

### Large Biomes

`server.properties`:
```properties
level-type=minecraft\:large_biomes
```

## Development/Testing Configuration

### Test Server (Fast Iterations)

`server.properties`:
```properties
view-distance=4
simulation-distance=3
max-players=2
spawn-protection=0
enable-command-block=true
function-permission-level=4
op-permission-level=4
```

`docker-compose.yml`:
```yaml
environment:
  - MEMORY_MIN=512M
  - MEMORY_MAX=1G
```

## Network Configurations

### Multiple Servers on Same Pi

First Server (`docker-compose.yml`):
```yaml
services:
  minecraft:
    container_name: minecraft-survival
    ports:
      - "25565:25565"
    environment:
      - MEMORY_MIN=1G
      - MEMORY_MAX=1500M
```

Second Server (`docker-compose-creative.yml`):
```yaml
services:
  minecraft:
    container_name: minecraft-creative
    ports:
      - "25566:25565"
    environment:
      - MEMORY_MIN=512M
      - MEMORY_MAX=1G
```

Start both:
```bash
docker-compose up -d
docker-compose -f docker-compose-creative.yml up -d
```

## Backup Configurations

### Automatic Daily Backups

Create backup script `backup-cron.sh`:
```bash
#!/bin/bash
cd /home/pi/minecraft-server
./manage.sh backup

# Keep only last 7 days of backups
find ./backups -name "minecraft_backup_*.tar.gz" -mtime +7 -delete
```

Add to crontab:
```bash
crontab -e
# Add:
0 3 * * * /home/pi/minecraft-server/backup-cron.sh
```

## Advanced Memory Configuration

### Optimized JVM Flags (Already in start.sh)

The `start.sh` includes Aikar's flags optimized for Minecraft:
- G1GC garbage collector
- Optimized for 1-4GB RAM
- Minimizes lag spikes
- Better memory management

### Custom JVM Flags

To modify, edit `start.sh`:
```bash
exec java -Xms${MEMORY_MIN} -Xmx${MEMORY_MAX} \
    -XX:+UseG1GC \
    # Add custom flags here
    -jar ${MINECRAFT_JAR} \
    --nogui
```

## Environmental Variables

All configurable via `docker-compose.yml`:

```yaml
environment:
  - MINECRAFT_VERSION=1.20.4    # Server version
  - MEMORY_MIN=1G               # Minimum heap size
  - MEMORY_MAX=2G               # Maximum heap size
  - SERVER_PORT=25565           # Server port
  - EULA=TRUE                   # Accept EULA
```

## Configuration Tips

### Finding the Right Balance

1. **Start Conservative**: Begin with lower settings
2. **Monitor**: Use `htop` and `docker stats` to watch resources
3. **Adjust Gradually**: Increase settings slowly
4. **Test**: Play with friends and monitor performance
5. **Document**: Note what works for your setup

### Performance vs. Experience

| Setting | Performance | Experience |
|---------|-------------|------------|
| view-distance=6 | High | Basic |
| view-distance=10 | Medium | Good |
| view-distance=12 | Low | Excellent |

### Memory Guidelines

| Pi RAM | Min | Max | Players | View Dist |
|--------|-----|-----|---------|-----------|
| 4GB | 512M | 1G | 2-3 | 6-8 |
| 4GB | 1G | 2G | 4-5 | 8-10 |
| 8GB | 1G | 2G | 5-8 | 8-10 |
| 8GB | 2G | 4G | 8-10 | 10-12 |

## Testing Configurations

After changing configuration:

1. Stop server: `./manage.sh stop`
2. Edit configuration files
3. Start server: `./manage.sh start`
4. Monitor logs: `./manage.sh logs`
5. Test in-game
6. Check resources: `htop` and `docker stats`

## Configuration Backup

Before making major changes:
```bash
# Backup current configuration
cp server.properties server.properties.backup
cp docker-compose.yml docker-compose.yml.backup

# Restore if needed
cp server.properties.backup server.properties
```

## Additional Resources

- [Official Server.properties Documentation](https://minecraft.fandom.com/wiki/Server.properties)
- [Aikar's Flags Explanation](https://aikar.co/2018/07/02/tuning-the-jvm-g1gc-garbage-collector-flags-for-minecraft/)
- [Minecraft Optimization Guide](https://minecraft.fandom.com/wiki/Tutorials/Server_startup_script)
