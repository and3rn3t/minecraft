# Log Management Guide

This guide covers the log aggregation, analysis, and management features for the Minecraft Server.

## Overview

The log management system provides:

- **Log Rotation**: Automatic rotation and archiving of log files
- **Log Indexing**: Fast searchable index of log entries
- **Error Detection**: Automatic detection of error patterns
- **Log Search**: Advanced search capabilities across all logs
- **Retention Policies**: Automatic cleanup of old logs

## Quick Start

### Basic Usage

**View recent logs**:

```bash
./manage.sh logs
```

**Search logs**:

```bash
./manage.sh logs-search "player joined"
```

**Manage logs**:

```bash
./manage.sh logs-manage all
```

## Log Management Commands

### Indexing Logs

Index logs for faster searching:

```bash
./manage.sh logs-manage index
```

This will:

- Parse all server log files
- Extract timestamps, log levels, and messages
- Create searchable index files
- Store indexes in `logs/index/`

**When to index**:

- After log rotation
- Before searching large log sets
- Periodically (can be automated via cron)

### Error Detection

Automatically detect errors and warnings:

```bash
./manage.sh logs-manage errors
```

This will:

- Scan all logs for error patterns
- Create error report in `logs/errors_YYYYMMDD.txt`
- Show summary of unique errors
- Alert on common issues (OutOfMemoryError, crashes, etc.)

**Error patterns detected**:

- ERROR, FATAL log levels
- Java exceptions (NullPointerException, OutOfMemoryError, etc.)
- Server warnings (lag, timeout, connection issues)
- Crash indicators

### Log Rotation

Rotate and archive log files:

```bash
./manage.sh logs-manage rotate
```

This will:

- Check log file sizes
- Compress and archive large logs
- Clean up logs older than retention period
- Maintain log directory structure

**Automatic rotation**:

- Configured in `config/log-management.conf`
- Can be scheduled via cron or systemd timer

### Log Statistics

View log statistics:

```bash
./manage.sh logs-manage stats
```

Shows:

- Number of log files
- Total log size
- Number of archived logs
- Number of index files
- Error count for today

## Log Search

### Basic Search

Search for any term in logs:

```bash
./manage.sh logs-search "error"
./manage.sh logs-search "player joined"
./manage.sh logs-search "crash"
```

### Advanced Search Options

**Case-sensitive search**:

```bash
./manage.sh logs-search -c "Error"
```

**Limit results**:

```bash
./manage.sh logs-search -n 20 "error"
# Show maximum 20 results
```

**Search by log level**:

```bash
./manage.sh logs-search -l ERROR
./manage.sh logs-search -l WARN
./manage.sh logs-search -l INFO
```

**Search by date**:

```bash
./manage.sh logs-search -d 2025-01-15 "crash"
# Search on specific date
```

**Search date range**:

```bash
./manage.sh logs-search -r 2025-01-01 2025-01-31 "player"
# Search entire month
```

### Search Examples

**Find all player connections**:

```bash
./manage.sh logs-search "joined the game"
```

**Find all errors in last week**:

```bash
./manage.sh logs-search -r $(date -d "7 days ago" +%Y-%m-%d) $(date +%Y-%m-%d) -l ERROR
```

**Find specific player activity**:

```bash
./manage.sh logs-search "PlayerName"
```

**Find server crashes**:

```bash
./manage.sh logs-search "crash\|exception\|fatal"
```

## Configuration

Edit `config/log-management.conf` to customize:

### Log Rotation

```bash
# Enable/disable log rotation
LOG_ROTATION_ENABLED=true

# Days to keep logs
LOG_RETENTION_DAYS=30

# Maximum log size before rotation (MB)
MAX_LOG_SIZE_MB=100
```

### Indexing

```bash
# Enable/disable indexing
INDEX_ENABLED=true

# Index update schedule (cron format)
INDEX_UPDATE_SCHEDULE="0 */6 * * *"  # Every 6 hours
```

### Error Detection

```bash
# Enable/disable error detection
ERROR_DETECTION_ENABLED=true

# Error detection frequency (cron format)
ERROR_DETECTION_SCHEDULE="0 * * * *"  # Every hour
```

## Automation

### Cron Setup

Add to crontab for automated log management:

```bash
# Daily log rotation at 2 AM
0 2 * * * cd /path/to/minecraft-server && ./scripts/manage.sh logs-manage rotate

# Index logs every 6 hours
0 */6 * * * cd /path/to/minecraft-server && ./scripts/manage.sh logs-manage index

# Error detection every hour
0 * * * * cd /path/to/minecraft-server && ./scripts/manage.sh logs-manage errors
```

### Systemd Timer

Create a systemd timer for log management:

```ini
# /etc/systemd/system/minecraft-log-manager.service
[Unit]
Description=Minecraft Server Log Management
After=docker.service

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/minecraft-server
ExecStart=/path/to/minecraft-server/scripts/manage.sh logs-manage all

# /etc/systemd/system/minecraft-log-manager.timer
[Unit]
Description=Run Minecraft Log Management Daily
Requires=minecraft-log-manager.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable minecraft-log-manager.timer
sudo systemctl start minecraft-log-manager.timer
```

## Log File Locations

- **Server logs**: `data/logs/`
  - `latest.log` - Current server log
  - `*.log.gz` - Compressed archived logs

- **Docker logs**: Managed by Docker (see docker-compose.yml)
  - Max size: 10MB per file
  - Max files: 3

- **Archived logs**: `logs/archive/`
  - Compressed log archives

- **Index files**: `logs/index/`
  - Searchable index files (one per day)

- **Error reports**: `logs/`
  - `errors_YYYYMMDD.txt` - Daily error reports

## Best Practices

1. **Regular Rotation**: Set up automatic log rotation to prevent disk space issues
2. **Index Before Search**: Index logs before searching large date ranges
3. **Monitor Errors**: Check error reports regularly to catch issues early
4. **Retention Policy**: Adjust retention based on available disk space
5. **Backup Important Logs**: Archive critical log periods before cleanup

## Troubleshooting

### Logs Not Rotating

**Check configuration**:

```bash
cat config/log-management.conf | grep LOG_ROTATION
```

**Manual rotation**:

```bash
./manage.sh logs-manage rotate
```

### Search Returns No Results

**Re-index logs**:

```bash
./manage.sh logs-manage index
```

**Check log files exist**:

```bash
ls -lh data/logs/
ls -lh logs/archive/
```

### Too Much Disk Space Used

**Check log sizes**:

```bash
./manage.sh logs-manage stats
du -sh logs/
du -sh data/logs/
```

**Reduce retention**:

```bash
# Edit config/log-management.conf
LOG_RETENTION_DAYS=7  # Keep only 7 days
```

**Manual cleanup**:

```bash
# Remove old archives
find logs/archive/ -name "*.log.gz" -mtime +30 -delete

# Remove old indexes
find logs/index/ -name "*.txt" -mtime +30 -delete
```

### Error Detection Too Sensitive

The error detection looks for common patterns. If it's too sensitive:

1. Review error reports: `cat logs/errors_$(date +%Y%m%d).txt`
2. Adjust search queries to filter false positives
3. Error detection is informational - it doesn't affect server operation

## Integration with Monitoring

The log management system integrates with:

- **Monitoring script**: `scripts/monitor.sh` uses log data
- **Prometheus exporter**: Can export log metrics
- **Health checks**: Error detection feeds into health status

## Advanced Usage

### Custom Error Patterns

Edit `scripts/log-manager.sh` to add custom error patterns:

```bash
local error_patterns=(
    "ERROR"
    "FATAL"
    "Your Custom Pattern"
)
```

### Export Logs for Analysis

```bash
# Export all errors
./manage.sh logs-manage errors
cat logs/errors_*.txt > all_errors.txt

# Export specific date range
./manage.sh logs-search -r 2025-01-01 2025-01-31 "error" > january_errors.txt
```

### Log Analysis Scripts

Use the indexed logs for custom analysis:

```bash
# Count errors per day
for file in logs/index/*.txt; do
    echo "$(basename $file): $(grep -c ERROR $file)"
done

# Find most common errors
cat logs/errors_*.txt | sort | uniq -c | sort -rn | head -20
```

---

For more information, see:

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [BACKUP_AND_MONITORING.md](BACKUP_AND_MONITORING.md) - Monitoring guide
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
