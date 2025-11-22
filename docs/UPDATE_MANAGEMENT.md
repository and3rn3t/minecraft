# Update Management Guide

This guide covers the automatic version checking and update management features.

## Version Checking

### Check for Updates

Check if a newer Minecraft version is available:

```bash
./scripts/manage.sh check-version
```

Or use the script directly:

```bash
./scripts/check-version.sh
```

The script will:

- Query Mojang's version manifest API
- Compare your current version with the latest release
- Display update availability

### Automatic Version Checking

Configure automatic version checking in `config/update-check.conf`:

```bash
# Enable version checking
CHECK_ENABLED=true

# Check frequency: daily, weekly, or manual
CHECK_FREQUENCY=daily

# Notify when updates are available
NOTIFY_ON_UPDATE=true
```

Set up a cron job for automatic checking:

```bash
# Daily check at 2 AM
0 2 * * * /path/to/minecraft-server/scripts/check-version.sh
```

## Server Updates

### One-Command Update

Update to the latest version:

```bash
./scripts/manage.sh update
```

Update to a specific version:

```bash
./scripts/manage.sh update 1.21.0
```

The update process:

1. Checks for available updates
2. Runs compatibility checks
3. Creates a backup automatically
4. Stops the server
5. Downloads the new server jar
6. Updates docker-compose.yml
7. Rebuilds the container
8. Starts the server

### Compatibility Checking

Before updating, check compatibility:

```bash
./scripts/manage.sh check-compatibility 1.21.0
```

Or use the script directly:

```bash
./scripts/check-compatibility.sh 1.21.0
```

The compatibility checker verifies:

- **Version compatibility**: Major vs minor version changes
- **World compatibility**: World format and structure
- **Plugin compatibility**: Installed plugins
- **Mod compatibility**: Installed mods
- **Configuration validity**: server.properties and other configs

### Update Process Details

#### Automatic Backup

Before updating, the system automatically:

- Saves the world (`save-all` command)
- Creates a full backup
- Verifies backup integrity

#### Rollback

If an update fails, you can rollback:

```bash
# Stop the server
./scripts/manage.sh stop

# Restore from backup
tar -xzf backups/minecraft_backup_YYYYMMDD_HHMMSS.tar.gz -C ./data/

# Restore docker-compose.yml
cp docker-compose.yml.bak docker-compose.yml

# Start the server
./scripts/manage.sh start
```

## Server Type Support

### Supported Server Types

- **Vanilla**: Official Minecraft server
- **Paper**: High-performance server with plugin support
- **Spigot**: Plugin-compatible server (requires BuildTools)
- **Fabric**: Mod-compatible server

### Switching Server Types

List available server types:

```bash
./scripts/switch-server-type.sh list
```

Check current server type:

```bash
./scripts/switch-server-type.sh current
```

Switch to a different server type:

```bash
# Switch to Paper
./scripts/switch-server-type.sh paper

# Switch to Fabric
./scripts/switch-server-type.sh fabric

# Switch back to Vanilla
./scripts/switch-server-type.sh vanilla
```

The switcher will:

- Stop the server if running
- Update docker-compose.yml
- Download the appropriate server jar if needed
- Update configuration files

### Downloading Server Jars

Download server jars manually:

```bash
# Download Vanilla server
./scripts/download-server.sh --type vanilla --version 1.21.0

# Download Paper server
./scripts/download-server.sh --type paper --version 1.21.0

# Download Fabric server
./scripts/download-server.sh --type fabric --version 1.21.0
```

## Configuration

### Update Check Configuration

Edit `config/update-check.conf`:

```bash
# Enable/disable version checking
CHECK_ENABLED=true

# Check frequency
CHECK_FREQUENCY=daily  # daily, weekly, or manual

# Notification settings
NOTIFY_ON_UPDATE=true

# Auto-update (WARNING: Use with caution)
AUTO_UPDATE=false
```

### Server Type Configuration

Set server type in `docker-compose.yml` or `.env`:

```yaml
environment:
  - SERVER_TYPE=paper  # vanilla, paper, spigot, or fabric
```

Or in `.env`:

```bash
SERVER_TYPE=paper
```

## Troubleshooting

### Update Fails

1. **Check compatibility**:

   ```bash
   ./scripts/manage.sh check-compatibility <version>
   ```

2. **Check logs**:

   ```bash
   ./scripts/manage.sh logs
   ```

3. **Restore from backup**:

   ```bash
   # Find latest backup
   ls -lt backups/ | head -2

   # Restore
   ./scripts/manage.sh stop
   tar -xzf backups/minecraft_backup_YYYYMMDD_HHMMSS.tar.gz -C ./data/
   ./scripts/manage.sh start
   ```

### Version Check Fails

1. **Check internet connection**:

   ```bash
   curl -s https://launchermeta.mojang.com/mc/game/version_manifest.json | head
   ```

2. **Check API availability**:
   - Visit: <https://launchermeta.mojang.com/mc/game/version_manifest.json>
   - Should return JSON data

3. **Manual version check**:

   ```bash
   # Get latest version manually
   curl -s https://launchermeta.mojang.com/mc/game/version_manifest.json | \
     grep -oP '"latest"\s*:\s*\{[^}]*"release"\s*:\s*"\K[^"]+'
   ```

### Download Fails

1. **Check disk space**:

   ```bash
   df -h
   ```

2. **Check permissions**:

   ```bash
   ls -la data/
   ```

3. **Manual download**:
   - Vanilla: <https://www.minecraft.net/en-us/download/server>
   - Paper: <https://papermc.io/downloads/paper>
   - Fabric: <https://fabricmc.net/use/server/>

### Compatibility Warnings

If compatibility check shows warnings:

1. **Review warnings** carefully
2. **Backup your world** before updating
3. **Test in a separate environment** if possible
4. **Check plugin/mod compatibility** with the new version
5. **Update plugins/mods** before updating the server

## Best Practices

1. **Always backup before updating**:

   ```bash
   ./scripts/manage.sh backup
   ```

2. **Check compatibility first**:

   ```bash
   ./scripts/manage.sh check-compatibility <version>
   ```

3. **Test updates on a copy** if possible

4. **Keep backups for at least 30 days** after major updates

5. **Update plugins/mods** before updating the server

6. **Monitor server logs** after updating:

   ```bash
   ./scripts/manage.sh logs
   ```

7. **Check server health** after updating:

   ```bash
   ./scripts/health-check.sh
   ```

## Examples

### Daily Update Check

Add to crontab:

```bash
# Check for updates daily at 2 AM
0 2 * * * cd /path/to/minecraft-server && ./scripts/check-version.sh >> logs/update-check.log 2>&1
```

### Weekly Update with Backup

```bash
# Create backup
./scripts/manage.sh backup

# Check compatibility
./scripts/manage.sh check-compatibility

# Update if compatible
./scripts/manage.sh update
```

### Switch to Paper for Better Performance

```bash
# Switch server type
./scripts/switch-server-type.sh paper

# Start server
./scripts/manage.sh start

# Monitor performance
./scripts/monitor.sh
```
