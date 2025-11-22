# RCON Guide

This guide covers Remote Console (RCON) setup and usage for remote server management.

## Overview

RCON (Remote Console) allows you to:

- Send commands to the server remotely
- Manage the server without direct console access
- Automate server operations
- Integrate with external tools and scripts

## Quick Start

### Enable RCON

```bash
# Enable with auto-generated password
./scripts/rcon-setup.sh enable

# Enable with custom password
./scripts/rcon-setup.sh enable mypassword

# Enable with custom password and port
./scripts/rcon-setup.sh enable mypassword 25576
```

### Test RCON Connection

```bash
./scripts/rcon-client.sh test
```

### Send Commands

```bash
# Single command
./scripts/manage.sh rcon command "list"

# Or use script directly
./scripts/rcon-client.sh command "say Hello World"
```

## Setup

### Initial Setup

1. **Enable RCON**:

   ```bash
   ./scripts/rcon-setup.sh enable
   ```

   This will:
   - Generate a secure random password
   - Enable RCON in server.properties
   - Set RCON port (default: 25575)
   - Save configuration for the client

2. **Restart Server**:

   ```bash
   ./scripts/manage.sh restart
   ```

3. **Test Connection**:

   ```bash
   ./scripts/rcon-client.sh test
   ```

### Configuration

RCON settings are stored in:

- `server.properties` - Server-side configuration
- `config/rcon.conf` - Client-side configuration (password storage)

**Security Note**: The `config/rcon.conf` file contains the RCON password and has restricted permissions (600).

### Change Password

```bash
# Generate new password
./scripts/rcon-setup.sh change-password

# Set custom password
./scripts/rcon-setup.sh change-password mynewpassword
```

**Note**: Restart server after changing password.

### Disable RCON

```bash
./scripts/rcon-setup.sh disable
```

## Usage

### Single Commands

Send a single command to the server:

```bash
./scripts/manage.sh rcon command "list"
./scripts/manage.sh rcon command "say Server maintenance in 5 minutes"
./scripts/manage.sh rcon command "whitelist add PlayerName"
./scripts/manage.sh rcon command "op PlayerName"
```

### Interactive Session

Start an interactive RCON session:

```bash
./scripts/manage.sh rcon interactive
```

This opens a command prompt where you can send multiple commands:

```
RCON> list
There are 2 of a max of 10 players online: Player1, Player2

RCON> say Hello everyone!
[Server] Hello everyone!

RCON> whitelist list
There are 3 whitelisted players: Player1, Player2, Player3

RCON> exit
```

### Common Commands

**Player Management**:

```bash
./scripts/manage.sh rcon command "list"
./scripts/manage.sh rcon command "whitelist add PlayerName"
./scripts/manage.sh rcon command "whitelist remove PlayerName"
./scripts/manage.sh rcon command "ban PlayerName"
./scripts/manage.sh rcon command "pardon PlayerName"
./scripts/manage.sh rcon command "kick PlayerName"
./scripts/manage.sh rcon command "op PlayerName"
./scripts/manage.sh rcon command "deop PlayerName"
```

**Server Management**:

```bash
./scripts/manage.sh rcon command "save-all"
./scripts/manage.sh rcon command "stop"
./scripts/manage.sh rcon command "reload"  # Paper/Spigot only
./scripts/manage.sh rcon command "say Message"
```

**World Management**:

```bash
./scripts/manage.sh rcon command "time set day"
./scripts/manage.sh rcon command "weather clear"
./scripts/manage.sh rcon command "difficulty normal"
```

## Security

### Best Practices

1. **Use Strong Passwords**: Let the script generate a secure password
2. **Restrict Access**: Only expose RCON port on localhost or VPN
3. **Change Password Regularly**: Update RCON password periodically
4. **Secure Configuration**: The `config/rcon.conf` file has restricted permissions
5. **Firewall Rules**: Don't expose RCON port to the internet

### Port Configuration

By default, RCON uses port 25575. To change it:

1. Edit `server.properties`:

   ```properties
   rcon.port=25576
   ```

2. Update client config:

   ```bash
   ./scripts/rcon-setup.sh enable <password> 25576
   ```

3. Restart server

### Docker Port Mapping

If using Docker, map RCON port in `docker-compose.yml`:

```yaml
ports:
  - "25565:25565"  # Minecraft port
  - "127.0.0.1:25575:25575"  # RCON (localhost only)
```

**Important**: Only expose RCON on localhost (127.0.0.1) unless you have proper security measures.

## Integration

### Scripts

Use RCON in your scripts:

```bash
#!/bin/bash
# Example: Auto-restart script

# Send warning
./scripts/manage.sh rcon command "say Server restarting in 5 minutes"

sleep 300

# Save world
./scripts/manage.sh rcon command "save-all"

# Stop server
./scripts/manage.sh rcon command "stop"
```

### Cron Jobs

Schedule automated commands:

```bash
# Add to crontab
# Daily backup reminder at 2 AM
0 2 * * * cd /path/to/minecraft-server && ./scripts/manage.sh rcon command "say Daily backup starting"
```

### Monitoring

Use RCON for monitoring:

```bash
# Check player count
./scripts/manage.sh rcon command "list" | grep -oP '\d+ of a max'

# Get server TPS (if using Paper)
./scripts/manage.sh rcon command "tps"
```

## Troubleshooting

### RCON Not Working

**Problem**: RCON commands fail

**Solutions**:

1. **Check RCON is enabled**:

   ```bash
   ./scripts/rcon-setup.sh status
   ```

2. **Verify server is running**:

   ```bash
   ./scripts/manage.sh status
   ```

3. **Check password**:
   - Verify password in `config/rcon.conf`
   - Ensure password matches `server.properties`

4. **Test connection**:

   ```bash
   ./scripts/rcon-client.sh test
   ```

5. **Check port**:
   - Verify RCON port in `server.properties`
   - Check if port is accessible
   - Ensure Docker port mapping is correct

### Authentication Failed

**Problem**: "Authentication failed" error

**Solutions**:

1. **Verify password**:

   ```bash
   ./scripts/rcon-setup.sh status
   ```

2. **Regenerate password**:

   ```bash
   ./scripts/rcon-setup.sh change-password
   ./scripts/manage.sh restart
   ```

3. **Check server.properties**:

   ```bash
   grep rcon server.properties
   ```

### Connection Timeout

**Problem**: Connection times out

**Solutions**:

1. **Check server is running**
2. **Verify port mapping** in docker-compose.yml
3. **Check firewall** rules
4. **Test port accessibility**:

   ```bash
   telnet localhost 25575
   ```

### Command Not Executing

**Problem**: Commands sent but not executing

**Solutions**:

1. **Check server logs** for errors
2. **Verify command syntax** (Minecraft commands)
3. **Check permissions** (some commands require OP)
4. **Test with simple command**:

   ```bash
   ./scripts/manage.sh rcon command "list"
   ```

## Advanced Usage

### Custom RCON Client

If you have `rcon-cli` installed locally:

```bash
# Direct usage
rcon-cli -H localhost -p 25575 -P password "list"
```

### Python Integration

Use the Python RCON library:

```python
from mcrcon import MCRcon

with MCRcon("localhost", "password", port=25575) as mcr:
    resp = mcr.command("list")
    print(resp)
```

### API Integration

RCON can be integrated into web APIs or automation systems:

```bash
# Example: Webhook handler
#!/bin/bash
PLAYER_NAME=$1
./scripts/manage.sh rcon command "whitelist add $PLAYER_NAME"
```

## Status

Check RCON status:

```bash
./scripts/rcon-setup.sh status
```

Shows:

- RCON enabled/disabled
- RCON port
- Password status
- Client configuration status

## Examples

### Automated Backup with RCON

```bash
#!/bin/bash
# backup-with-rcon.sh

# Warn players
./scripts/manage.sh rcon command "say Backup starting in 30 seconds"
sleep 30

# Save world
./scripts/manage.sh rcon command "save-all"
sleep 5

# Create backup
./scripts/manage.sh backup

# Notify completion
./scripts/manage.sh rcon command "say Backup complete"
```

### Player Management Script

```bash
#!/bin/bash
# manage-players.sh

ACTION=$1
PLAYER=$2

case $ACTION in
    add)
        ./scripts/manage.sh rcon command "whitelist add $PLAYER"
        ./scripts/manage.sh rcon command "say Welcome $PLAYER!"
        ;;
    remove)
        ./scripts/manage.sh rcon command "whitelist remove $PLAYER"
        ;;
    op)
        ./scripts/manage.sh rcon command "op $PLAYER"
        ;;
    *)
        echo "Usage: $0 {add|remove|op} <player>"
        ;;
esac
```

---

For more information, see:

- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md) - Configuration examples
