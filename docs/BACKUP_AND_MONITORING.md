# Backup & Monitoring Guide

This guide covers the automated backup and monitoring features implemented for the Minecraft server.

## Backup Features

### Automated Backup Scheduling

The server supports automated backups through two methods:

#### 1. Cron-based Scheduling

To set up cron-based backups, add an entry to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line for daily backups at 3 AM
0 3 * * * /path/to/minecraft-server/scripts/backup-scheduler.sh
```

#### 2. Systemd Timer (Recommended)

For more reliable scheduling, use systemd timers:

```bash
# Install the timer
./scripts/install-backup-timer.sh

# Check timer status
sudo systemctl status minecraft-backup.timer

# View backup logs
sudo journalctl -u minecraft-backup.service
```

### Backup Configuration

Edit `config/backup-schedule.conf` to configure backup frequency:

```bash
# Daily backup at 3 AM
BACKUP_FREQUENCY=daily
BACKUP_TIME="03:00"

# Weekly backup on Sunday at 2 AM
BACKUP_FREQUENCY=weekly
BACKUP_TIME="02:00"
BACKUP_WEEKLY_DAY=0

# Monthly backup on the 1st at midnight
BACKUP_FREQUENCY=monthly
BACKUP_TIME="00:00"
BACKUP_MONTHLY_DAY=1
```

### Backup Retention Policy

Configure backup retention in `config/backup-retention.conf`:

```bash
# Keep last 10 backups regardless of age
KEEP_LAST_N=10

# Keep daily backups for 7 days
KEEP_DAILY_DAYS=7

# Keep weekly backups for 30 days
KEEP_WEEKLY_DAYS=30

# Keep monthly backups for 365 days
KEEP_MONTHLY_DAYS=365
```

### Manual Backup Management

```bash
# Create a backup manually
./scripts/manage.sh backup

# Clean up old backups
./scripts/cleanup-backups.sh

# List backups
ls -lh backups/
```

### Backup Features

- **Pre-backup world save**: Automatically saves the world before backing up
- **Backup verification**: Verifies backup integrity after creation
- **Compression**: Uses gzip compression to save space
- **Retention policies**: Automatically removes old backups based on rules

## Monitoring Features

### Metrics Collection

The monitoring system collects the following metrics:

- **Server Status**: Running, stopped, or unhealthy
- **CPU Usage**: Percentage of CPU used by the server
- **Memory Usage**: Memory consumption in bytes
- **Player Count**: Current number of players online
- **Server Uptime**: How long the server has been running
- **TPS (Ticks Per Second)**: Server performance metric

### Running Monitoring

```bash
# Collect metrics once
./scripts/monitor.sh

# Set up periodic monitoring (add to crontab)
*/5 * * * * /path/to/minecraft-server/scripts/monitor.sh
```

### Metrics Storage

Metrics are stored in CSV format in the `metrics/` directory:

- `metrics/server_status.csv` - Server status over time
- `metrics/cpu_usage.csv` - CPU usage history
- `metrics/memory_usage.csv` - Memory usage history
- `metrics/player_count.csv` - Player count history
- `metrics/server_uptime.csv` - Uptime tracking
- `metrics/tps.csv` - TPS history
- `metrics/all_metrics.csv` - Combined metrics

### Health Checks

The health check script verifies server health:

```bash
# Run health check
./scripts/health-check.sh

# Use in monitoring systems
if ./scripts/health-check.sh; then
    echo "Server is healthy"
else
    echo "Server has issues"
fi
```

Health checks verify:
- Container is running
- Java process is active
- Server port is listening
- CPU usage is within limits
- Memory usage is within limits

### Prometheus Metrics

Export metrics in Prometheus format:

```bash
# Output metrics once
./scripts/prometheus-exporter.sh

# Serve metrics on HTTP endpoint (requires netcat or HTTP server)
./scripts/prometheus-exporter.sh --serve
```

The exporter provides these metrics:
- `minecraft_server_up` - Server status (1 = up, 0 = down)
- `minecraft_server_cpu_usage_percent` - CPU usage
- `minecraft_server_memory_usage_bytes` - Memory usage
- `minecraft_server_memory_limit_bytes` - Memory limit
- `minecraft_server_player_count` - Player count
- `minecraft_server_uptime_seconds` - Uptime
- `minecraft_server_tps` - Ticks per second

### Grafana Integration

To visualize metrics in Grafana:

1. Set up Prometheus to scrape metrics from the exporter
2. Import a Grafana dashboard for Minecraft servers
3. Configure alerts based on metrics

Example Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'minecraft'
    static_configs:
      - targets: ['localhost:9091']
```

## Logs

Monitoring and backup logs are stored in:
- `logs/backup-scheduler.log` - Backup scheduler logs
- `logs/monitor.log` - Monitoring logs (if configured)

## Troubleshooting

### Backups Not Running

1. Check if the scheduler script is executable:
   ```bash
   ls -l scripts/backup-scheduler.sh
   ```

2. Check cron/systemd logs:
   ```bash
   # For cron
   grep CRON /var/log/syslog

   # For systemd
   sudo journalctl -u minecraft-backup.service
   ```

3. Verify configuration file exists:
   ```bash
   cat config/backup-schedule.conf
   ```

### Metrics Not Collecting

1. Ensure the server is running:
   ```bash
   ./scripts/manage.sh status
   ```

2. Check if metrics directory exists:
   ```bash
   ls -la metrics/
   ```

3. Run monitoring manually to see errors:
   ```bash
   ./scripts/monitor.sh
   ```

### Health Check Failing

1. Check server status:
   ```bash
   docker ps | grep minecraft-server
   ```

2. Check container logs:
   ```bash
   docker logs minecraft-server
   ```

3. Verify Java process:
   ```bash
   docker exec minecraft-server pgrep -f java
   ```

## Best Practices

1. **Backup Frequency**: For active servers, daily backups are recommended
2. **Retention**: Adjust retention based on available disk space
3. **Monitoring**: Run monitoring every 5 minutes for active monitoring
4. **Health Checks**: Set up alerts based on health check results
5. **Metrics**: Keep metrics for at least 30 days for trend analysis

## Configuration Examples

### High-Activity Server

```bash
# config/backup-schedule.conf
BACKUP_FREQUENCY=daily
BACKUP_TIME="02:00"

# config/backup-retention.conf
KEEP_LAST_N=20
KEEP_DAILY_DAYS=14
KEEP_WEEKLY_DAYS=60
KEEP_MONTHLY_DAYS=730
```

### Low-Activity Server

```bash
# config/backup-schedule.conf
BACKUP_FREQUENCY=weekly
BACKUP_TIME="03:00"
BACKUP_WEEKLY_DAY=0

# config/backup-retention.conf
KEEP_LAST_N=5
KEEP_DAILY_DAYS=3
KEEP_WEEKLY_DAYS=14
KEEP_MONTHLY_DAYS=180
```

