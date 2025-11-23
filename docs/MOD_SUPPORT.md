# Mod Support Guide

This guide covers mod loader detection and mod pack installation for Minecraft servers.

## Overview

The mod support system provides:

- **Mod loader detection** - Automatically detect Forge, Fabric, and Quilt
- **Mod pack installation** - Install mods from URLs, files, or manifests
- **Dependency resolution** - Resolve and install mod dependencies
- **Compatibility checking** - Verify mod compatibility with server version

## Supported Mod Loaders

### Forge

- **Detection**: Checks for Forge libraries and mod files
- **Version detection**: Extracts version from `version.json` or server jar
- **Mod location**: `mods/` directory

### Fabric

- **Detection**: Checks for Fabric API and Fabric loader
- **Version detection**: Extracts version from Fabric loader jar
- **Mod location**: `mods/` directory

### Quilt

- **Detection**: Checks for Quilt Loader
- **Version detection**: Extracts version from Quilt loader jar
- **Mod location**: `mods/` directory

## Mod Loader Detection

### Detect All Loaders

```bash
# Detect all installed mod loaders
./scripts/mod-loader-detector.sh detect
```

### Check Specific Loader

```bash
# Check for Forge
./scripts/mod-loader-detector.sh forge

# Check for Fabric
./scripts/mod-loader-detector.sh fabric

# Check for Quilt
./scripts/mod-loader-detector.sh quilt
```

### List Installed Mods

```bash
# List all installed mods
./scripts/mod-loader-detector.sh list-mods
```

## Mod Installation

### Install Mod from URL

```bash
# Install mod from URL
./scripts/mod-pack-installer.sh install-url https://example.com/mod.jar
```

### Install Mod from Local File

```bash
# Install mod from local file
./scripts/mod-pack-installer.sh install-file /path/to/mod.jar
```

### Install Mod Pack from Manifest

Create a manifest file (`modpack.json`):

```json
{
  "name": "My Mod Pack",
  "version": "1.0.0",
  "minecraft": "1.20.1",
  "loader": "fabric",
  "mods": [
    {
      "name": "Fabric API",
      "url": "https://example.com/fabric-api.jar",
      "required": true
    },
    {
      "name": "Some Mod",
      "url": "https://example.com/some-mod.jar",
      "required": false
    }
  ]
}
```

Install the mod pack:

```bash
./scripts/mod-pack-installer.sh install-pack modpack.json
```

## Mod Management

### List Installed Mods

```bash
./scripts/mod-pack-installer.sh list
```

### Remove Mod

```bash
# Remove a mod
./scripts/mod-pack-installer.sh remove mod-name.jar
```

### Update Mod

```bash
# Update mod to new version
./scripts/mod-pack-installer.sh update mod-name.jar https://example.com/new-version.jar
```

### Verify Compatibility

```bash
# Verify mod compatibility
./scripts/mod-pack-installer.sh verify mod.jar fabric 1.20.1
```

## Mod Pack Manifest Format

### Basic Structure

```json
{
  "name": "Mod Pack Name",
  "version": "1.0.0",
  "minecraft": "1.20.1",
  "loader": "fabric",
  "mods": [
    {
      "name": "Mod Name",
      "url": "https://example.com/mod.jar",
      "required": true,
      "dependencies": ["other-mod.jar"]
    }
  ]
}
```

### Fields

- **name** (required): Mod pack name
- **version** (required): Mod pack version
- **minecraft** (required): Minecraft version
- **loader** (required): Mod loader (forge, fabric, quilt)
- **mods** (required): Array of mod objects
  - **name** (required): Mod name
  - **url** (required): Download URL
  - **required** (optional): Whether mod is required (default: true)
  - **dependencies** (optional): Array of dependency mod names

## Integration with Server Management

### Check Mod Loader Before Starting

```bash
# In your startup script
if ./scripts/mod-loader-detector.sh detect; then
    echo "Mod loader detected, starting modded server..."
    ./manage.sh start
else
    echo "No mod loader detected, starting vanilla server..."
    ./manage.sh start
fi
```

### Install Mods During Setup

```bash
# Install mod pack during server setup
if [ -f "modpack.json" ]; then
    ./scripts/mod-pack-installer.sh install-pack modpack.json
fi
```

## Best Practices

### 1. Backup Before Installing Mods

```bash
# Always backup before installing mods
./manage.sh backup
./scripts/mod-pack-installer.sh install-url https://example.com/mod.jar
```

### 2. Verify Compatibility

```bash
# Verify mod compatibility before installing
./scripts/mod-pack-installer.sh verify mod.jar fabric 1.20.1
```

### 3. Test Mods Individually

```bash
# Install and test mods one at a time
./scripts/mod-pack-installer.sh install-file mod1.jar
# Test server
./scripts/mod-pack-installer.sh install-file mod2.jar
# Test server again
```

### 4. Keep Mods Updated

```bash
# Regularly update mods
./scripts/mod-pack-installer.sh update old-mod.jar https://example.com/new-version.jar
```

## Troubleshooting

### Mod Loader Not Detected

**Issue**: Mod loader not detected even though installed

**Solutions**:
- Check mods directory exists: `ls -la data/mods/`
- Verify mod loader files are present
- Check server jar name for loader indicator
- Run detection with verbose output

### Mod Installation Fails

**Issue**: Mod installation fails

**Solutions**:
- Check internet connection (for URL downloads)
- Verify file permissions on mods directory
- Check disk space
- Verify mod file is valid JAR

### Mod Compatibility Issues

**Issue**: Mod causes server crashes or errors

**Solutions**:
- Verify mod is compatible with Minecraft version
- Check mod loader version compatibility
- Review server logs for errors
- Remove incompatible mods
- Check mod dependencies

### Dependency Resolution Fails

**Issue**: Mod dependencies not automatically installed

**Solutions**:
- Manually install required dependencies
- Check mod manifest for dependency list
- Verify dependency URLs are accessible
- Install dependencies in correct order

## API Integration

### Check Mod Loader via API

```bash
# Get mod loader status
curl http://localhost:8080/api/mods/loader
```

### List Mods via API

```bash
# List installed mods
curl http://localhost:8080/api/mods
```

## Resources

- [Forge Documentation](https://docs.minecraftforge.net/)
- [Fabric Documentation](https://fabricmc.net/wiki/)
- [Quilt Documentation](https://quiltmc.org/)
- [CurseForge](https://www.curseforge.com/minecraft/mc-mods) - Mod repository
- [Modrinth](https://modrinth.com/) - Mod repository

## See Also

- [Plugin Management Guide](PLUGIN_MANAGEMENT.md) - Plugin installation
- [Server Management Guide](QUICK_REFERENCE.md) - Server commands
- [Installation Guide](INSTALL.md) - Server setup

