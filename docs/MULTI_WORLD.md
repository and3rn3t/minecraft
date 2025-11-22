# Multi-World Management Guide

This guide covers managing multiple worlds on your Minecraft server, including creation, switching, configuration, and backups.

## Overview

The multi-world system allows you to:

- Create and manage multiple worlds
- Switch between worlds easily
- Configure each world independently
- Create world templates for quick setup
- Schedule per-world backups
- Monitor world sizes

## Quick Start

### List Worlds

```bash
./manage.sh worlds list
```

### Create a New World

```bash
# Create a normal world
./manage.sh worlds create myworld

# Create a flat world
./manage.sh worlds create flatworld flat

# Create a world with a specific seed
./manage.sh worlds create seededworld normal 12345
```

### Switch Worlds

```bash
./manage.sh worlds switch myworld
```

## World Management

### Creating Worlds

Create a new world with specific settings:

```bash
./manage.sh worlds create <name> [type] [seed]
```

**World Types**:

- `normal` - Standard Minecraft world (default)
- `flat` - Superflat world
- `amplified` - Amplified terrain (resource intensive)
- `large_biomes` - Large biomes variant

**Examples**:

```bash
# Standard world
./manage.sh worlds create survival

# Flat world for building
./manage.sh worlds create creative flat

# World with seed
./manage.sh worlds create adventure normal -1234567890
```

### Listing Worlds

View all available worlds:

```bash
./manage.sh worlds list
```

Shows:

- World name
- Size
- Type (Overworld, Nether, End)
- Active status

### World Information

Get detailed information about a world:

```bash
./manage.sh worlds info <world-name>
```

Or for the current world:

```bash
./manage.sh worlds info
```

### Switching Worlds

Switch to a different world:

```bash
./manage.sh worlds switch <world-name>
```

This will:

- Stop the server if running
- Update server.properties
- Apply world-specific configuration
- Ready the server to start with the new world

**Note**: The server must be restarted to load the new world.

### Deleting Worlds

Delete a world (with automatic backup):

```bash
./manage.sh worlds delete <world-name>
```

**Warning**: This permanently deletes the world. A backup is created before deletion.

**Note**: You cannot delete the currently active world. Switch to another world first.

## Per-World Configuration

### World Configuration Files

Each world has a configuration file in `config/worlds/<world-name>.conf`:

```bash
# World configuration for survival
WORLD_NAME=survival
WORLD_TYPE=normal
WORLD_SEED=
CREATED=2025-01-15 10:30:00
```

### Applying World Configuration

Apply world-specific settings:

```bash
./manage.sh worlds config <world-name>
```

This applies:

- World type (normal/flat/amplified)
- World seed
- Other world-specific settings

### World-Specific server.properties

When switching worlds, the system automatically:

- Updates `level-name` in server.properties
- Applies world type settings
- Applies seed if specified

## World Templates

### Creating Templates

Create a template from an existing world:

```bash
./manage.sh worlds create-template <template-name> [source-world]
```

**Example**:

```bash
# Create template from current world
./manage.sh worlds create-template mytemplate

# Create template from specific world
./manage.sh worlds create-template survival-template survival
```

Templates are stored in `config/world-templates/` and can be reused to create new worlds quickly.

### Creating Worlds from Templates

Create a new world from a template:

```bash
./manage.sh worlds from-template <world-name> <template-name>
```

**Example**:

```bash
./manage.sh worlds from-template newworld survival-template
```

This creates a new world with the same structure as the template (excluding player data).

## World Backups

### Manual World Backup

Backup a specific world:

```bash
./manage.sh worlds backup <world-name>
```

Or backup the current world:

```bash
./manage.sh worlds backup
```

Backups are stored in `backups/worlds/` with timestamps.

### Per-World Backup Scheduling

Configure automatic backups for each world in `config/world-backup-schedule.conf`:

```bash
# Default settings (apply to all worlds)
DEFAULT_BACKUP_ENABLED=true
DEFAULT_BACKUP_FREQUENCY=daily
DEFAULT_BACKUP_TIME="02:00"
DEFAULT_BACKUP_RETENTION_DAYS=7

# Per-world settings
WORLD_survival_ENABLED=true
WORLD_survival_FREQUENCY=daily
WORLD_survival_TIME="03:00"
WORLD_survival_RETENTION_DAYS=14

# Disable backups for test world
WORLD_test_ENABLED=false
```

### Running Scheduled Backups

Run scheduled backups manually:

```bash
./scripts/world-backup-scheduler.sh run
```

Backup all enabled worlds:

```bash
./scripts/world-backup-scheduler.sh backup-all
```

Clean up old backups:

```bash
./scripts/world-backup-scheduler.sh cleanup
```

### Automated Backup Scheduling

Add to crontab for automatic backups:

```bash
# Daily backups at 2 AM
0 2 * * * cd /path/to/minecraft-server && ./scripts/world-backup-scheduler.sh run

# Weekly cleanup on Sunday at 3 AM
0 3 * * 0 cd /path/to/minecraft-server && ./scripts/world-backup-scheduler.sh cleanup
```

## World Size Monitoring

Monitor world sizes:

```bash
./manage.sh worlds sizes
```

Shows:

- Size of each world
- Total size of all worlds
- World count

Useful for:

- Disk space management
- Identifying large worlds
- Planning backups

## World Types

### Normal World

Standard Minecraft world with varied terrain:

```bash
./manage.sh worlds create myworld normal
```

### Flat World

Superflat world for building:

```bash
./manage.sh worlds create flatworld flat
```

Configure in `server.properties`:

```properties
level-type=minecraft:flat
generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}
```

### Amplified World

Amplified terrain (requires more resources):

```bash
./manage.sh worlds create amplifiedworld amplified
```

**Note**: Amplified worlds are resource-intensive and may not perform well on Raspberry Pi 5.

### Large Biomes

Large biomes variant:

```bash
./manage.sh worlds create largeworld large_biomes
```

## Best Practices

1. **Naming Conventions**: Use descriptive names (e.g., `survival`, `creative`, `pvp`)
2. **Regular Backups**: Schedule backups for important worlds
3. **Monitor Sizes**: Check world sizes regularly to manage disk space
4. **Templates**: Create templates for commonly used world configurations
5. **Test Worlds**: Use separate worlds for testing plugins/modifications

## Troubleshooting

### World Won't Switch

**Problem**: World switch doesn't work

**Solutions**:

1. Ensure server is stopped: `./manage.sh stop`
2. Check world exists: `./manage.sh worlds list`
3. Verify server.properties is writable
4. Check world directory has `level.dat`

### World Not Generating

**Problem**: New world doesn't generate when server starts

**Solutions**:

1. Check server.properties has correct `level-name`
2. Verify world directory exists
3. Check server logs for errors
4. Ensure sufficient disk space

### Backup Fails

**Problem**: World backup fails

**Solutions**:

1. Check disk space: `df -h`
2. Verify world directory exists
3. Check file permissions
4. Try manual backup: `./manage.sh worlds backup <name>`

### World Too Large

**Problem**: World is taking too much disk space

**Solutions**:

1. Monitor sizes: `./manage.sh worlds sizes`
2. Delete unused worlds
3. Use MCA Selector or similar tools to delete unused chunks
4. Consider using flat worlds for building

## Advanced Usage

### Multiple Servers with Different Worlds

Run multiple servers with different worlds:

1. Create separate docker-compose files for each world
2. Use different ports for each server
3. Configure different world directories

### World Migration

Move worlds between servers:

1. Backup world: `./manage.sh worlds backup <name>`
2. Copy backup file to new server
3. Extract backup: `tar -xzf world_<name>_*.tar.gz -C data/`
4. Switch to world: `./manage.sh worlds switch <name>`

### World Cloning

Clone an existing world:

1. Create template: `./manage.sh worlds create-template template <source>`
2. Create from template: `./manage.sh worlds from-template <new-name> template`

---

For more information, see:

- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
- [BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md) - Backup guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting guide
