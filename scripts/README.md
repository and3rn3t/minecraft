# Scripts Directory

This directory contains utility scripts for server management and automation.

## Available Scripts

### backup-scheduler.sh

Automated backup scheduling using cron or systemd timers.

### cleanup-backups.sh

Clean up old backups based on retention policies.

### update-checker.sh

Check for Minecraft server version updates.

### health-check.sh

Server health monitoring and alerting.

### ddns-updater.sh

Dynamic DNS update script for various providers.

## Usage

All scripts should be made executable:

```bash
chmod +x scripts/*.sh
```

## Adding New Scripts

1. Create script in this directory
2. Add shebang: `#!/bin/bash`
3. Make executable: `chmod +x script.sh`
4. Add to `.gitignore` if needed
5. Document in this README

## Best Practices

- Use `set -e` for error handling
- Add color output for better UX
- Include usage/help function
- Add error handling and validation
- Test on Raspberry Pi 5 before committing
