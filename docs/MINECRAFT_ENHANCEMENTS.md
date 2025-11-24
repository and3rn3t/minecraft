# Minecraft-Specific Enhancements

This document outlines potential Minecraft-specific configurations and enhancements for the project.

## Current State

The project currently supports:

- ✅ Basic server.properties management (via API)
- ✅ RCON integration
- ✅ World management
- ✅ Plugin management
- ✅ Mod loader detection
- ✅ Basic player management (mentioned but not fully implemented)

## Implemented Enhancements ✅

### 1. Enhanced Server Properties Manager ✅

**Status: Complete**

Created dedicated script and API endpoints for managing `server.properties`:

- **CLI Tool**: `scripts/server-properties-manager.sh`

  - Get/set individual properties
  - Validate property values
  - Apply presets (performance, gameplay, etc.)
  - Backup before changes

- **API Endpoints**:

  - `GET /api/server/properties` - Get all properties
  - `GET /api/server/properties/<key>` - Get specific property
  - `PUT /api/server/properties/<key>` - Update property
  - `POST /api/server/properties/preset` - Apply preset

- **Features**:
  - Property validation (e.g., view-distance: 3-32)
  - Preset profiles (Performance, Balanced, High Quality)
  - Change preview before applying
  - Automatic backup on changes

### 2. Player Management Scripts

**Priority: P1 (High)**

Complete player management functionality:

- **Whitelist Manager**: `scripts/whitelist-manager.sh`

  - Add/remove players
  - List whitelisted players
  - Enable/disable whitelist
  - Import/export whitelist

- **Ban Manager**: `scripts/ban-manager.sh`

  - Ban/unban players
  - List banned players
  - Temporary bans with expiration
  - Ban reason management

- **OP Manager**: `scripts/op-manager.sh`

  - Grant/revoke operator status
  - List operators
  - Set operator level (1-4)

- **API Endpoints**:
  - `GET /api/players/whitelist` - List whitelist
  - `POST /api/players/whitelist` - Add to whitelist
  - `DELETE /api/players/whitelist/<player>` - Remove from whitelist
  - `GET /api/players/banned` - List banned players
  - `POST /api/players/ban` - Ban player
  - `DELETE /api/players/ban/<player>` - Unban player
  - `GET /api/players/ops` - List operators
  - `POST /api/players/op` - Grant OP
  - `DELETE /api/players/op/<player>` - Revoke OP

### 3. Datapack Manager

**Priority: P2 (Medium)**

Manage Minecraft datapacks:

- **Script**: `scripts/datapack-manager.sh`

  - Install datapacks from URL/file
  - List installed datapacks
  - Enable/disable datapacks
  - Remove datapacks
  - Verify datapack structure

- **API Endpoints**:
  - `GET /api/datapacks` - List datapacks
  - `POST /api/datapacks/install` - Install datapack
  - `PUT /api/datapacks/<name>/enable` - Enable datapack
  - `PUT /api/datapacks/<name>/disable` - Disable datapack
  - `DELETE /api/datapacks/<name>` - Remove datapack

### 4. Resource Pack Manager

**Priority: P2 (Medium)**

Manage server resource packs:

- **Script**: `scripts/resource-pack-manager.sh`

  - Set server resource pack URL
  - Upload resource pack
  - Enable/disable resource pack
  - Configure resource pack hash

- **API Endpoints**:
  - `GET /api/resourcepack` - Get resource pack info
  - `POST /api/resourcepack` - Set resource pack
  - `DELETE /api/resourcepack` - Remove resource pack

### 5. Gamerule Manager

**Priority: P2 (Medium)**

Easy gamerule management:

- **Script**: `scripts/gamerule-manager.sh`

  - Get/set gamerules
  - List all gamerules
  - Apply gamerule presets
  - Validate gamerule values

- **API Endpoints**:
  - `GET /api/gamerules` - List all gamerules
  - `GET /api/gamerules/<rule>` - Get gamerule value
  - `PUT /api/gamerules/<rule>` - Set gamerule

### 6. ~~JVM Arguments Optimizer~~ ✅ **COMPLETE**

**Status: Complete** - See section 3 above

- **Script**: `scripts/jvm-optimizer.sh`

  - Generate optimized JVM args based on:
    - Available memory
    - CPU cores
    - Server type (Vanilla/Paper/Spigot/Fabric)
    - Minecraft version
  - Preset profiles (Performance, Balanced, Stability)
  - Validate JVM arguments

- **Features**:
  - Aikar's Flags integration
  - G1GC optimization
  - Memory allocation optimization
  - Raspberry Pi 5 specific optimizations

### 7. World Border Manager

**Priority: P3 (Low)**

Manage world borders:

- **Script**: `scripts/world-border-manager.sh`

  - Set world border center
  - Set world border size
  - Set border damage/knockback
  - Animate border changes

- **API Endpoints**:
  - `GET /api/worldborder` - Get border settings
  - `POST /api/worldborder` - Set border settings

### 8. Spawn Protection Manager

**Priority: P3 (Low)**

Configure spawn protection:

- **Script**: `scripts/spawn-protection-manager.sh`

  - Set spawn protection radius
  - Configure spawn protection behavior
  - Manage spawn area

- **API Endpoints**:
  - `GET /api/spawn-protection` - Get spawn protection settings
  - `PUT /api/spawn-protection` - Update spawn protection

### 9. Entity Management

**Priority: P2 (Medium)**

Optimize entity handling:

- **Script**: `scripts/entity-manager.sh`

  - Set mob caps
  - Configure entity tracking range
  - Manage entity density
  - Optimize entity performance

- **API Endpoints**:
  - `GET /api/entities/stats` - Get entity statistics
  - `POST /api/entities/optimize` - Apply entity optimizations

### 10. ~~Performance Presets~~ ✅ **COMPLETE**

**Status: Complete** - See section 4 above

- **Script**: `scripts/performance-presets.sh`

  - Apply preset: Low-End, Balanced, High-Performance
  - Custom preset creation
  - Preset comparison

- **Presets**:
  - **Low-End (4GB Pi)**: View distance 6, simulation 4, max players 5
  - **Balanced (8GB Pi)**: View distance 10, simulation 8, max players 10
  - **High-Performance**: View distance 12, simulation 10, max players 20

### 11. Server Icon Manager

**Priority: P3 (Low)**

Manage server icon:

- **Script**: `scripts/server-icon-manager.sh`

  - Set server icon from file
  - Generate server icon from image
  - Validate icon format (64x64 PNG)
  - Remove server icon

- **API Endpoints**:
  - `GET /api/server/icon` - Get server icon
  - `POST /api/server/icon` - Upload server icon
  - `DELETE /api/server/icon` - Remove server icon

### 12. Function/Command Block Manager

**Priority: P3 (Low)**

Manage datapack functions and command blocks:

- **Script**: `scripts/function-manager.sh`

  - List datapack functions
  - Create/edit functions
  - Enable/disable functions
  - Test functions

- **API Endpoints**:
  - `GET /api/functions` - List functions
  - `POST /api/functions` - Create function
  - `PUT /api/functions/<name>` - Update function
  - `DELETE /api/functions/<name>` - Delete function

## Implementation Priority

### Phase 1 (High Priority - P1)

1. Enhanced Server Properties Manager
2. Player Management Scripts (Whitelist, Ban, OP)
3. JVM Arguments Optimizer
4. Performance Presets

### Phase 2 (Medium Priority - P2)

5. Datapack Manager
6. Resource Pack Manager
7. Gamerule Manager
8. Entity Management

### Phase 3 (Low Priority - P3)

9. World Border Manager
10. Spawn Protection Manager
11. Server Icon Manager
12. Function/Command Block Manager

## Benefits

### For Users

- **Easier Configuration**: GUI/CLI tools for common tasks
- **Better Performance**: Optimized settings for Raspberry Pi
- **Time Saving**: Automated management tasks
- **Error Prevention**: Validation and presets

### For Developers

- **Consistent API**: Standardized endpoints
- **Reusable Code**: Shared utilities
- **Better Testing**: Testable components
- **Documentation**: Clear usage examples

## Integration Points

### With Existing Features

- **API Integration**: All features accessible via REST API
- **Web UI**: Frontend components for management
- **RCON**: Use RCON for server commands
- **Backup**: Auto-backup before configuration changes
- **Monitoring**: Track performance impact of changes

### With External Tools

- **Minecraft Server Jars**: Support all server types
- **Datapack Repositories**: CurseForge, Planet Minecraft
- **Resource Pack Sources**: Direct URLs, file uploads

## Example Usage

### Server Properties Manager

```bash
# Get property
./scripts/server-properties-manager.sh get view-distance

# Set property
./scripts/server-properties-manager.sh set view-distance 10

# Apply preset
./scripts/server-properties-manager.sh preset performance
```

### Player Management

```bash
# Whitelist player
./scripts/whitelist-manager.sh add PlayerName

# Ban player
./scripts/ban-manager.sh ban PlayerName "Griefing"

# Grant OP
./scripts/op-manager.sh grant PlayerName 4
```

### JVM Optimizer

```bash
# Generate optimized JVM args
./scripts/jvm-optimizer.sh generate --memory 2G --cores 4 --type paper

# Apply preset
./scripts/jvm-optimizer.sh preset performance
```

## Additional Gameplay Enhancements

For more advanced Minecraft gameplay features, see:

- **[Minecraft Gameplay Enhancements](MINECRAFT_GAMEPLAY_ENHANCEMENTS.md)** - Advanced features including:
  - Enhanced command automation and scheduling
  - Player experience enhancements (stats, teleport, notes)
  - Server events and automation
  - Scoreboard and team management
  - Advanced world features
  - Achievement and advancement systems
  - Communication and messaging systems
  - Economy and rewards (plugin-dependent)
  - Performance optimization tools
  - Data management (recipes, loot tables)

## See Also

- [Server Properties Guide](https://minecraft.fandom.com/wiki/Server.properties)
- [Gamerules Reference](https://minecraft.fandom.com/wiki/Game_rule)
- [Datapacks Guide](https://minecraft.fandom.com/wiki/Data_pack)
- [Performance Tuning](RASPBERRY_PI_OPTIMIZATIONS.md)
- [Gameplay Enhancements](MINECRAFT_GAMEPLAY_ENHANCEMENTS.md)
