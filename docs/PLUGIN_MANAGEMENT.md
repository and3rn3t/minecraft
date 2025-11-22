# Plugin Management Guide

This guide covers plugin installation, updates, enable/disable, and configuration management for your Minecraft server.

## Prerequisites

Plugins require a server type that supports them:

- **Paper** (recommended) - Best performance and plugin support
- **Spigot** - Good plugin support
- **Vanilla** - Does NOT support plugins

Switch to Paper or Spigot before installing plugins:

```bash
# Switch to Paper
./scripts/switch-server-type.sh paper

# Restart server
./scripts/manage.sh restart
```

## Plugin Installation

### Install from File

Install a plugin from a .jar file:

```bash
./scripts/plugin-manager.sh install /path/to/plugin.jar
```

Or use the manage.sh wrapper:

```bash
./scripts/manage.sh plugins install /path/to/plugin.jar
```

The installer will:

- **Check compatibility** with your server type and version
- **Check dependencies** and warn about missing required plugins
- Extract plugin information (name, version, API version)
- Copy plugin to the plugins directory
- Backup existing plugin if it exists
- Backup plugin configuration if it exists

**Compatibility Checks**:
- Verifies server type supports plugins (Paper/Spigot required)
- Checks API version compatibility with server version
- Warns if plugin may not work correctly

**Dependency Resolution**:
- Automatically detects required dependencies from plugin.yml
- Warns about missing dependencies
- Allows installation to continue (dependencies may be optional)

### Plugin Locations

Plugins are stored in:

- `./plugins/` - Main plugin directory
- `./data/plugins/` - Alternative location (for some server types)

Plugin configurations are stored in:

- `./data/plugins/<plugin-name>/` - Plugin configuration files

## Plugin Management

### List Installed Plugins

```bash
./scripts/plugin-manager.sh list
```

Shows:

- Plugin name and version
- Plugin file name
- Total plugin count
- Disabled plugins count

### Enable Plugin

Enable a previously disabled plugin:

```bash
./scripts/plugin-manager.sh enable <plugin-name>
```

Disabled plugins are moved to `plugins/disabled/` directory.

### Disable Plugin

Disable a plugin without removing it:

```bash
./scripts/plugin-manager.sh disable <plugin-name>
```

The plugin is moved to `plugins/disabled/` and won't load on server start.

### Remove Plugin

Completely remove a plugin:

```bash
./scripts/plugin-manager.sh remove <plugin-name>
```

This will:

- Remove the plugin .jar file
- Remove plugin configuration directory
- Create a backup before removal

**Warning**: This action cannot be undone (except from backup).

### Update Plugin

Update a plugin to a newer version:

```bash
./scripts/plugin-manager.sh update <plugin-name> /path/to/new-plugin.jar
```

The updater will:

- Check compatibility of new version
- Backup old plugin and configuration
- Replace plugin .jar file
- Preserve existing configuration

**Note**: Review configuration changes after updating - some plugins change config format between versions.

### Check for Plugin Updates

Check which plugins have updates available:

```bash
./scripts/plugin-manager.sh check-updates
```

This will:
- List all installed plugins with their current versions
- Show update status (requires API integration for automatic checking)

**Note**: Currently shows installed versions. Full automatic update checking requires integration with SpigotMC/PaperMC APIs.

### Hot-Reload Plugins

Reload plugins without restarting the server (Paper/Spigot only):

```bash
./scripts/plugin-manager.sh reload
```

Or via manage.sh:

```bash
./scripts/manage.sh plugins reload
```

**Requirements**:
- Server must be running
- Server type must be Paper or Spigot (Vanilla doesn't support hot-reload)
- Some plugins may not support hot-reload and may require a full restart

**Note**: Hot-reload is experimental. Some plugins may not reload correctly. If issues occur, restart the server.

## Plugin Configuration Management

### List Plugin Configurations

```bash
./scripts/plugin-config-manager.sh list
```

Shows all plugins with configuration files.

### Validate Configuration

Validate a plugin's configuration file:

```bash
./scripts/plugin-config-manager.sh validate <plugin-name>
```

Or validate a specific file:

```bash
./scripts/plugin-config-manager.sh validate <plugin-name> /path/to/config.yml
```

Checks for:

- YAML syntax errors
- File readability
- Basic structure

### Backup Plugin Configuration

Backup a plugin's configuration:

```bash
./scripts/plugin-config-manager.sh backup <plugin-name>
```

Backups are stored in `backups/plugins/configs/` with timestamps.

### Restore Plugin Configuration

Restore from a backup:

```bash
./scripts/plugin-config-manager.sh restore <plugin-name> /path/to/backup.tar.gz
```

### Configuration Templates

Create a configuration template from existing config:

```bash
./scripts/plugin-config-manager.sh create-template <plugin-name>
```

Templates are stored in `config/plugin-templates/` and can be reused.

Apply a template to create a new configuration:

```bash
./scripts/plugin-config-manager.sh apply-template <plugin-name>
```

## Recommended Plugins

### Performance & Optimization

- **Chunky** - Pre-generate chunks for better performance
- **ClearLag** - Remove lag-causing entities
- **Spark** - Performance profiling

### Essentials

- **EssentialsX** - Essential commands and features
- **WorldEdit** - World editing tools
- **WorldGuard** - World protection

### Management

- **LuckPerms** - Permission management
- **Vault** - Economy API
- **PlaceholderAPI** - Placeholder system

## Plugin Compatibility

### Checking Compatibility

Before installing plugins, check compatibility:

1. **Server Version**: Ensure plugin supports your Minecraft version
2. **Server Type**: Verify plugin works with Paper/Spigot
3. **Dependencies**: Check if plugin requires other plugins
4. **API Version**: Some plugins require specific API versions

### Common Issues

#### Plugin Not Loading

1. Check server logs:

   ```bash
   ./scripts/manage.sh logs | grep -i error
   ```

2. Verify plugin is in correct directory:

   ```bash
   ls -la plugins/
   ```

3. Check plugin compatibility with server version

4. Ensure server type supports plugins (Paper/Spigot)

#### Plugin Conflicts

If plugins conflict:

1. Disable one plugin:

   ```bash
   ./scripts/plugin-manager.sh disable <plugin-name>
   ```

2. Restart server and test

3. Check plugin documentation for known conflicts

#### Configuration Errors

1. Validate configuration:

   ```bash
   ./scripts/plugin-config-manager.sh validate <plugin-name>
   ```

2. Restore from backup if needed:

   ```bash
   ./scripts/plugin-config-manager.sh restore <plugin-name> <backup-file>
   ```

3. Recreate from template:

   ```bash
   ./scripts/plugin-config-manager.sh apply-template <plugin-name>
   ```

## Best Practices

### Before Installing

1. **Backup server**:

   ```bash
   ./scripts/manage.sh backup
   ```

2. **Check compatibility** with server version

3. **Read plugin documentation**

4. **Test in a separate environment** if possible

### After Installing

1. **Restart server** to load plugin:

   ```bash
   ./scripts/manage.sh restart
   ```

2. **Check server logs** for errors:

   ```bash
   ./scripts/manage.sh logs
   ```

3. **Test plugin functionality**

4. **Configure plugin** as needed

### Regular Maintenance

1. **Update plugins regularly**:

   ```bash
   ./scripts/plugin-manager.sh update <plugin-name> <new-file>
   ```

2. **Backup configurations** before updates:

   ```bash
   ./scripts/plugin-config-manager.sh backup <plugin-name>
   ```

3. **Remove unused plugins** to reduce load:

   ```bash
   ./scripts/plugin-manager.sh remove <plugin-name>
   ```

4. **Monitor plugin performance** using monitoring tools

## Plugin Directories Structure

```
minecraft-server/
├── plugins/              # Active plugins
│   ├── plugin1.jar
│   ├── plugin2.jar
│   └── disabled/        # Disabled plugins
│       └── old-plugin.jar
├── data/
│   └── plugins/         # Plugin configurations
│       ├── plugin1/
│       │   └── config.yml
│       └── plugin2/
│           └── config.yml
└── backups/
    └── plugins/         # Plugin backups
        ├── configs/     # Configuration backups
        └── *.jar.backup.*
```

## Troubleshooting

### Plugin Not Appearing in List

1. Check plugin file is a valid .jar:

   ```bash
   file plugins/plugin.jar
   ```

2. Verify plugin is in correct directory:

   ```bash
   ls -la plugins/*.jar
   ```

3. Check plugin file permissions:

   ```bash
   ls -la plugins/
   ```

### Server Won't Start After Plugin Install

1. Check server logs:

   ```bash
   ./scripts/manage.sh logs
   ```

2. Disable recently installed plugins:

   ```bash
   ./scripts/plugin-manager.sh disable <plugin-name>
   ```

3. Restart server:

   ```bash
   ./scripts/manage.sh restart
   ```

4. Re-enable plugins one by one to identify the problem

### Configuration Not Loading

1. Validate configuration:

   ```bash
   ./scripts/plugin-config-manager.sh validate <plugin-name>
   ```

2. Check file permissions:

   ```bash
   ls -la data/plugins/<plugin-name>/
   ```

3. Restore from backup:

   ```bash
   ./scripts/plugin-config-manager.sh restore <plugin-name> <backup>
   ```

## Examples

### Complete Plugin Installation Workflow

```bash
# 1. Switch to Paper (if not already)
./scripts/switch-server-type.sh paper

# 2. Backup server
./scripts/manage.sh backup

# 3. Install plugin
./scripts/plugin-manager.sh install /path/to/plugin.jar

# 4. Restart server
./scripts/manage.sh restart

# 5. Check logs
./scripts/manage.sh logs

# 6. Configure plugin (edit config files)
nano data/plugins/<plugin-name>/config.yml

# 7. Restart to apply config
./scripts/manage.sh restart
```

### Updating Multiple Plugins

```bash
# Backup all plugin configs
for plugin in $(./scripts/plugin-manager.sh list | grep -oP '^\s+✓\s+\K[^\s]+'); do
    ./scripts/plugin-config-manager.sh backup "$plugin"
done

# Update each plugin
./scripts/plugin-manager.sh update plugin1 /path/to/plugin1-new.jar
./scripts/plugin-manager.sh update plugin2 /path/to/plugin2-new.jar

# Restart server
./scripts/manage.sh restart
```

### Disabling Plugins Temporarily

```bash
# Disable plugin for testing
./scripts/plugin-manager.sh disable problematic-plugin

# Restart server
./scripts/manage.sh restart

# Test server without plugin

# Re-enable if needed
./scripts/plugin-manager.sh enable problematic-plugin
./scripts/manage.sh restart
```
