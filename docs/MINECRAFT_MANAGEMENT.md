# Minecraft Server Management Guide

This guide covers the Minecraft-specific management tools and scripts.

## Quick Reference

### Server Properties

```bash
# Get property value
./scripts/server-properties-manager.sh get view-distance

# Set property value
./scripts/server-properties-manager.sh set view-distance 10

# List all properties
./scripts/server-properties-manager.sh list

# Apply performance preset
./scripts/server-properties-manager.sh preset balanced

# Show property information
./scripts/server-properties-manager.sh info max-players

# Backup server.properties
./scripts/server-properties-manager.sh backup
```

### Player Management

#### Whitelist

```bash
# Add player to whitelist
./scripts/whitelist-manager.sh add PlayerName

# Remove player from whitelist
./scripts/whitelist-manager.sh remove PlayerName

# List whitelisted players
./scripts/whitelist-manager.sh list

# Enable whitelist
./scripts/whitelist-manager.sh enable

# Disable whitelist
./scripts/whitelist-manager.sh disable

# Import whitelist from file
./scripts/whitelist-manager.sh import players.txt

# Export whitelist to file
./scripts/whitelist-manager.sh export

# Check if player is whitelisted
./scripts/whitelist-manager.sh check PlayerName
```

#### Bans

```bash
# Ban player
./scripts/ban-manager.sh ban PlayerName "Griefing"

# Unban player
./scripts/ban-manager.sh unban PlayerName

# Ban IP address
./scripts/ban-manager.sh ban-ip 192.168.1.100 "Suspicious activity"

# Unban IP address
./scripts/ban-manager.sh unban-ip 192.168.1.100

# List banned players
./scripts/ban-manager.sh list

# Check if player is banned
./scripts/ban-manager.sh check PlayerName
```

#### Operators

```bash
# Grant operator status (level 4)
./scripts/op-manager.sh grant PlayerName 4

# Revoke operator status
./scripts/op-manager.sh revoke PlayerName

# List operators
./scripts/op-manager.sh list

# Get operator level
./scripts/op-manager.sh level PlayerName

# Set operator level
./scripts/op-manager.sh set-level PlayerName 2

# Check if player is operator
./scripts/op-manager.sh check PlayerName
```

### Performance Optimization

#### JVM Arguments

```bash
# Generate optimized JVM arguments (auto-detect)
./scripts/jvm-optimizer.sh generate

# Generate with specific memory and cores
./scripts/jvm-optimizer.sh generate 2G 4 aikar

# Apply preset
./scripts/jvm-optimizer.sh preset rpi 2G 4

# Save to file
./scripts/jvm-optimizer.sh save 2G 4 aikar .jvm-args

# Validate JVM arguments
./scripts/jvm-optimizer.sh validate "-Xms1G -Xmx2G"
```

#### Performance Presets

```bash
# Apply low-end preset (4GB Pi)
./scripts/performance-presets.sh low-end

# Apply balanced preset (8GB Pi)
./scripts/performance-presets.sh balanced

# Apply high-performance preset
./scripts/performance-presets.sh high-performance

# Compare presets
./scripts/performance-presets.sh compare

# Show current settings
./scripts/performance-presets.sh current
```

## API Usage

### Server Properties

```bash
# Get all properties
curl -H "X-API-Key: your-key" http://localhost:8080/api/server/properties

# Get specific property
curl -H "X-API-Key: your-key" http://localhost:8080/api/server/properties/view-distance

# Set property
curl -X PUT -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"value": "10"}' \
  http://localhost:8080/api/server/properties/view-distance

# Apply preset
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"preset": "balanced"}' \
  http://localhost:8080/api/server/properties/preset
```

### Player Management

```bash
# Get whitelist
curl -H "X-API-Key: your-key" http://localhost:8080/api/players/whitelist

# Add to whitelist
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"player": "PlayerName"}' \
  http://localhost:8080/api/players/whitelist

# Remove from whitelist
curl -X DELETE -H "X-API-Key: your-key" \
  http://localhost:8080/api/players/whitelist/PlayerName

# Get banned players
curl -H "X-API-Key: your-key" http://localhost:8080/api/players/banned

# Ban player
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"player": "PlayerName", "reason": "Griefing"}' \
  http://localhost:8080/api/players/ban

# Get operators
curl -H "X-API-Key: your-key" http://localhost:8080/api/players/ops

# Grant OP
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"player": "PlayerName", "level": 4}' \
  http://localhost:8080/api/players/op
```

## Makefile Targets

```bash
# Server properties
make server-props

# Whitelist management
make whitelist

# Ban management
make ban

# OP management
make op

# JVM optimization
make jvm-optimize

# Performance presets
make perf-preset
```

## Common Workflows

### Initial Server Setup

```bash
# 1. Apply performance preset
./scripts/performance-presets.sh balanced

# 2. Optimize JVM arguments
./scripts/jvm-optimizer.sh save 4G 4 aikar

# 3. Configure server properties
./scripts/server-properties-manager.sh set motd "My Server"
./scripts/server-properties-manager.sh set difficulty normal
./scripts/server-properties-manager.sh set gamemode survival

# 4. Enable whitelist (optional)
./scripts/whitelist-manager.sh enable
./scripts/whitelist-manager.sh add PlayerName

# 5. Grant OP to admin
./scripts/op-manager.sh grant AdminName 4
```

### Daily Management

```bash
# Check server properties
./scripts/server-properties-manager.sh list

# Manage whitelist
./scripts/whitelist-manager.sh list
./scripts/whitelist-manager.sh add NewPlayer

# Check bans
./scripts/ban-manager.sh list

# View operators
./scripts/op-manager.sh list
```

### Performance Tuning

```bash
# Check current settings
./scripts/performance-presets.sh current

# Compare presets
./scripts/performance-presets.sh compare

# Apply optimized preset
./scripts/performance-presets.sh balanced

# Generate optimized JVM args
./scripts/jvm-optimizer.sh generate 4G 4 aikar
```

## Property Validation

The server properties manager validates all property values:

- **Integer properties**: Validated against min/max ranges
- **Enum properties**: Validated against allowed values
- **Automatic backups**: Created before any changes

### Valid Property Ranges

- `view-distance`: 3-32
- `simulation-distance`: 3-32
- `max-players`: 1-2147483647
- `server-port`: 1-65535
- `spawn-protection`: 0-2147483647

### Valid Enum Values

- `difficulty`: peaceful, easy, normal, hard
- `gamemode`: survival, creative, adventure, spectator
- `online-mode`: true, false
- `pvp`: true, false
- `white-list`: true, false

## See Also

- [Server Properties Guide](https://minecraft.fandom.com/wiki/Server.properties)
- [Performance Tuning](RASPBERRY_PI_OPTIMIZATIONS.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Quick Reference](QUICK_REFERENCE.md)

