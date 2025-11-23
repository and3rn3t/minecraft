# Analytics & Monitoring Guide

The Minecraft Server Management system includes comprehensive analytics and monitoring capabilities to help you understand server performance, player behavior, and resource usage patterns.

## Overview

The analytics system provides:

- **Performance Trends**: Track TPS, CPU, and memory usage over time
- **Player Behavior Analytics**: Understand player activity patterns and peak hours
- **Anomaly Detection**: Automatically detect unusual performance issues
- **Resource Predictions**: Forecast future resource usage
- **Custom Reports**: Generate detailed analytics reports

## Features

### 1. Performance Monitoring

Track server performance metrics:

- **TPS (Ticks Per Second)**: Server performance indicator
- **CPU Usage**: Processor utilization
- **Memory Usage**: RAM consumption
- **Network I/O**: Network traffic statistics

### 2. Player Behavior Analytics

Analyze player activity:

- **Unique Players**: Count of distinct players
- **Peak Hours**: Identify busiest times
- **Hourly Distribution**: Activity patterns throughout the day
- **Session Duration**: Average play time (when available)

### 3. Anomaly Detection

Automatically detect performance anomalies:

- **Statistical Analysis**: Uses Z-score method to identify outliers
- **Severity Levels**: High and medium severity classifications
- **Alert System**: Warnings for detected anomalies

### 4. Resource Predictions

Forecast future resource usage:

- **Linear Prediction**: Simple trend-based forecasting
- **Confidence Scores**: Reliability indicators for predictions
- **Trend Analysis**: Identify increasing/decreasing patterns

### 5. Custom Reports

Generate detailed analytics reports:

- **Time Periods**: 1 hour, 6 hours, 24 hours, 1 week
- **Metric Selection**: Choose specific metrics to include
- **Export**: Save reports for later analysis

## Usage

### Collecting Analytics Data

#### Manual Collection

```bash
# Collect analytics data manually
./scripts/analytics-collector.sh
```

#### Automated Collection

Set up a cron job for regular data collection:

```bash
# Collect every 5 minutes
*/5 * * * * /path/to/minecraft-server/scripts/analytics-collector.sh

# Collect every hour
0 * * * * /path/to/minecraft-server/scripts/analytics-collector.sh
```

#### Via API

```bash
# Trigger data collection via API
curl -X POST http://localhost:8080/api/analytics/collect \
  -H "X-API-Key: your-api-key"
```

### Generating Reports

#### Command Line

```bash
# Generate analytics report
python3 scripts/analytics-processor.py
```

The report will be saved to `analytics/processed/latest_report.json`.

#### Via API

```bash
# Get analytics report (last 24 hours)
curl http://localhost:8080/api/analytics/report?hours=24 \
  -H "X-API-Key: your-api-key"

# Get report for different time periods
curl http://localhost:8080/api/analytics/report?hours=168 \
  -H "X-API-Key: your-api-key"
```

### Web Interface

Access the analytics dashboard through the web interface:

1. Navigate to **Analytics** in the sidebar
2. Select time period (1 hour, 6 hours, 24 hours, 1 week)
3. View different tabs:
   - **Overview**: Summary and quick stats
   - **Performance**: Detailed performance metrics
   - **Players**: Player behavior analytics
   - **Anomalies**: Detected performance issues
   - **Predictions**: Resource usage forecasts

### API Endpoints

#### Collect Analytics Data

```http
POST /api/analytics/collect
```

Triggers immediate data collection.

#### Get Analytics Report

```http
GET /api/analytics/report?hours=24
```

Returns comprehensive analytics report for specified time period.

**Parameters:**

- `hours` (optional): Time period in hours (1, 6, 24, 168). Default: 24

#### Get Performance Trends

```http
GET /api/analytics/trends?hours=24&type=performance
```

Returns performance trends analysis.

**Parameters:**

- `hours` (optional): Time period in hours. Default: 24
- `type` (optional): Type of trends (`performance`, `players`, `network`). Default: `performance`

#### Get Anomalies

```http
GET /api/analytics/anomalies?hours=24&metric=tps
```

Returns detected anomalies.

**Parameters:**

- `hours` (optional): Time period in hours. Default: 24
- `metric` (optional): Metric to analyze (`tps`, `cpu`, `memory`). Default: `tps`

#### Get Predictions

```http
GET /api/analytics/predictions?hours_ahead=1&metric=memory
```

Returns resource usage predictions.

**Parameters:**

- `hours_ahead` (optional): Hours into the future to predict. Default: 1
- `metric` (optional): Metric to predict (`memory`, `tps`, `cpu`). Default: `memory`

#### Get Player Behavior

```http
GET /api/analytics/player-behavior?hours=24
```

Returns player behavior analytics.

**Parameters:**

- `hours` (optional): Time period in hours. Default: 24

#### Generate Custom Report

```http
POST /api/analytics/custom-report
Content-Type: application/json

{
  "hours": 24,
  "metrics": ["performance", "players"]
}
```

Generates a custom analytics report.

**Request Body:**

- `hours` (required): Time period in hours
- `metrics` (required): Array of metrics to include (`performance`, `players`)

## Data Storage

Analytics data is stored in JSONL (JSON Lines) format:

- `analytics/players.jsonl` - Player data
- `analytics/player_events.jsonl` - Join/leave events
- `analytics/performance.jsonl` - Performance metrics
- `analytics/network.jsonl` - Network statistics
- `analytics/world_stats.jsonl` - World statistics
- `analytics/system.jsonl` - System metrics (Raspberry Pi)

Processed reports are stored in:

- `analytics/processed/latest_report.json` - Latest generated report
- `analytics/processed/all_reports.json` - All time period reports
- `analytics/processed/custom_report_*.json` - Custom reports

## Understanding Reports

### Report Structure

```json
{
  "generated_at": "2025-01-27T12:00:00",
  "period_hours": 24,
  "player_behavior": {
    "unique_players": 5,
    "peak_hour": 20,
    "hourly_distribution": {...},
    "average_session_duration_minutes": 0
  },
  "performance": {
    "tps": {
      "trend": {
        "direction": "stable",
        "slope": 0.1,
        "change_percent": 2.5,
        "current": 20.0,
        "average": 19.8
      },
      "anomalies": [...],
      "prediction": {
        "predicted": 20.1,
        "confidence": 85.0
      }
    },
    "cpu": {...},
    "memory": {...}
  },
  "summary": {
    "status": "healthy",
    "warnings": [],
    "recommendations": []
  }
}
```

### Status Indicators

- **healthy**: No issues detected
- **warning**: Minor issues or recommendations
- **critical**: Significant problems detected

### Trend Directions

- **increasing**: Metric is trending upward
- **decreasing**: Metric is trending downward
- **stable**: Metric is relatively constant

### Anomaly Severity

- **high**: Significant deviation from normal (Z-score > 3.0)
- **medium**: Moderate deviation (Z-score > 2.0)

## Best Practices

### 1. Regular Data Collection

Set up automated collection to ensure continuous data:

```bash
# Add to crontab
*/5 * * * * /path/to/minecraft-server/scripts/analytics-collector.sh
```

### 2. Monitor Anomalies

Regularly check the anomalies tab for performance issues:

- High TPS anomalies may indicate lag spikes
- Memory anomalies may indicate memory leaks
- CPU anomalies may indicate resource contention

### 3. Review Predictions

Use predictions to plan resource allocation:

- Monitor memory predictions to prevent OOM errors
- Use TPS predictions to optimize server settings
- Plan for peak hours based on player behavior

### 4. Generate Regular Reports

Create weekly reports to track long-term trends:

```bash
# Generate weekly report
python3 scripts/analytics-processor.py
```

### 5. Act on Recommendations

The analytics system provides recommendations:

- Reduce view distance if TPS is decreasing
- Monitor memory if usage is increasing
- Optimize settings based on player patterns

## Troubleshooting

### No Data Available

**Issue**: Reports show "No data available"

**Solutions**:

1. Run the analytics collector: `./scripts/analytics-collector.sh`
2. Check that the server is running
3. Verify analytics directory exists: `mkdir -p analytics`

### Import Errors

**Issue**: `ImportError` when running analytics processor

**Solutions**:

1. Ensure Python 3 is installed: `python3 --version`
2. Check script permissions: `chmod +x scripts/analytics-processor.py`
3. Verify script path is correct

### Missing Metrics

**Issue**: Some metrics are missing from reports

**Solutions**:

1. Ensure RCON is configured for player data
2. Check Docker container is running
3. Verify log files are accessible

### Low Confidence Predictions

**Issue**: Predictions have low confidence scores

**Solutions**:

1. Collect more data over time
2. Ensure regular data collection (every 5 minutes)
3. Wait for sufficient historical data (24+ hours)

## Integration

### Prometheus

Analytics data can be exported to Prometheus:

```bash
# Export metrics
./scripts/prometheus-exporter.sh
```

### Grafana

Use Grafana to visualize analytics data:

1. Set up Prometheus data source
2. Import Minecraft server dashboard
3. Configure alerts based on anomalies

### Webhooks

Set up webhooks for anomaly alerts (future feature):

```json
{
  "url": "https://your-webhook-url.com/alerts",
  "events": ["anomaly_detected", "high_memory", "low_tps"]
}
```

## Performance Considerations

### Data Retention

Analytics data grows over time. Consider:

- Rotating old data files
- Compressing historical data
- Setting retention policies

### Collection Frequency

Balance between data granularity and system load:

- **Every 5 minutes**: Good balance for most servers
- **Every minute**: More detailed but higher overhead
- **Every hour**: Less detailed but lower overhead

### Storage Requirements

Approximate storage per day:

- Basic metrics: ~1-2 MB
- Full analytics: ~5-10 MB
- With system metrics: ~10-20 MB

## Examples

### Example: Monitoring TPS

```bash
# Collect data
./scripts/analytics-collector.sh

# Check TPS trends
curl http://localhost:8080/api/analytics/trends?type=performance \
  -H "X-API-Key: your-api-key" | jq '.trends.tps'
```

### Example: Finding Peak Hours

```bash
# Get player behavior
curl http://localhost:8080/api/analytics/player-behavior?hours=168 \
  -H "X-API-Key: your-api-key" | jq '.behavior.peak_hour'
```

### Example: Detecting Anomalies

```bash
# Check for TPS anomalies
curl http://localhost:8080/api/analytics/anomalies?metric=tps \
  -H "X-API-Key: your-api-key" | jq '.anomalies'
```

## See Also

- [Backup & Monitoring Guide](BACKUP_AND_MONITORING.md)
- [API Documentation](API.md)
- [Web Interface Guide](WEB_INTERFACE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
