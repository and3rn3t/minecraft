# Configuration Directory

This directory contains additional configuration files for the Minecraft server.

## Structure

```
config/
├── backup-schedule.conf    # Backup scheduling configuration
├── backup-retention.conf   # Backup retention policies
├── monitoring.conf         # Monitoring configuration
└── server-overrides.conf   # Server property overrides
```

## Files

### backup-schedule.conf

Configure automatic backup schedules. Example:

```
SCHEDULE=daily
TIME=03:00
ENABLED=true
```

### backup-retention.conf

Configure backup retention policies. Example:

```
KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=12
MAX_BACKUPS=50
```

### monitoring.conf

Configure monitoring and metrics. Example:

```
ENABLED=true
METRICS_PORT=9090
ALERT_THRESHOLD_TPS=18
ALERT_THRESHOLD_MEMORY=90
```

### server-overrides.conf

Override specific server.properties values. Example:

```
MAX_PLAYERS=15
VIEW_DISTANCE=12
```

## Usage

1. Copy example files from `config/examples/` if they exist
2. Customize configuration files
3. Restart the server to apply changes

## Notes

- Configuration files are mounted read-only in the container
- Changes require server restart
- Backup configuration files before making changes
