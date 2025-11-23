# Performance Benchmarking Guide

This guide covers the performance benchmarking suite for the Minecraft Server project, designed to measure and track server performance over time.

## Overview

The benchmarking suite provides:

- **Performance baselines** - Establish expected performance metrics
- **Regression detection** - Identify performance degradation
- **Optimization validation** - Verify performance improvements
- **Resource monitoring** - Track CPU, memory, and TPS over time

## Quick Start

### Create a Baseline

```bash
# Run full benchmark suite and create baseline
./scripts/benchmark.sh baseline
```

### Compare Against Baseline

```bash
# Compare current performance against baseline
./scripts/benchmark.sh compare
```

### Run Individual Benchmarks

```bash
# Benchmark startup time
./scripts/benchmark.sh startup

# Benchmark TPS (Ticks Per Second)
./scripts/benchmark.sh tps

# Benchmark memory usage
./scripts/benchmark.sh memory

# Benchmark CPU usage
./scripts/benchmark.sh cpu
```

## Benchmark Metrics

### Startup Time

Measures the time from server start command to server ready state.

**Target**: < 60 seconds for Raspberry Pi 5

**Measurement**:

- Time from `docker-compose up` to server logs showing "Done"
- Includes container startup, JVM initialization, and world loading

### TPS (Ticks Per Second)

Measures server tick performance. Minecraft servers should maintain 20 TPS.

**Target**:

- Average: 20.0 TPS
- Minimum: 18.0 TPS (acceptable)
- Below 18.0: Performance issue

**Measurement**:

- Samples TPS every 5 seconds (configurable)
- Calculates average, minimum, and maximum
- Duration: 5 minutes (configurable)

### Memory Usage

Tracks memory consumption over time.

**Target**:

- Should stay within allocated memory limits
- No memory leaks (gradual increase over time)

**Measurement**:

- Samples memory usage every 5 seconds
- Tracks average, peak, and minimum usage
- Reports in MB

### CPU Usage

Monitors CPU utilization.

**Target**:

- Average: < 80% on Raspberry Pi 5
- Peak: < 95%
- Sustained > 90%: Performance issue

**Measurement**:

- Samples CPU usage every 5 seconds
- Tracks average, peak, and minimum usage
- Reports as percentage

## Configuration

### Environment Variables

```bash
# Warmup time before benchmarking (default: 60 seconds)
export WARMUP_TIME=60

# Benchmark duration (default: 300 seconds / 5 minutes)
export BENCHMARK_DURATION=300

# Sampling interval (default: 5 seconds)
export SAMPLING_INTERVAL=5
```

### Example

```bash
# Quick benchmark (1 minute warmup, 2 minute test)
WARMUP_TIME=60 BENCHMARK_DURATION=120 ./scripts/benchmark.sh tps

# Extended benchmark (2 minute warmup, 10 minute test)
WARMUP_TIME=120 BENCHMARK_DURATION=600 ./scripts/benchmark.sh all
```

## Baseline Management

### Creating a Baseline

A baseline establishes expected performance metrics for your specific hardware and configuration.

```bash
./scripts/benchmark.sh baseline
```

This creates `benchmarks/baselines/baseline.json` with:

- Timestamp
- Server version information
- Performance metrics
- Performance thresholds

### Baseline File Structure

```json
{
  "timestamp": "2025-01-27T12:00:00",
  "version": "openjdk version \"21.0.1\"",
  "minecraft_version": "1.20.4",
  "server_type": "vanilla",
  "memory_min": "1G",
  "memory_max": "2G",
  "metrics": {
    "startup_time": 45.2,
    "tps_avg": 20.0,
    "memory_avg": 1024.5,
    "cpu_avg": 65.3
  },
  "thresholds": {
    "startup_time_max": 54.24,
    "tps_min": 18.0,
    "memory_max": 1331.85,
    "cpu_max": 97.95
  }
}
```

### Comparing Against Baseline

```bash
./scripts/benchmark.sh compare
```

This runs benchmarks and compares results against the baseline, showing:

- ✓ OK - Performance within acceptable range
- ⚠️ REGRESSION - Performance degraded
- ⚠️ BELOW THRESHOLD - Performance below minimum acceptable

## Regression Testing

### Automated Regression Detection

The benchmark suite automatically detects regressions by comparing current performance against baseline thresholds:

- **Startup Time**: > 20% increase triggers warning
- **TPS**: < 18.0 TPS triggers warning
- **Memory**: > 30% increase triggers warning
- **CPU**: > 50% increase or > 80% average triggers warning

### CI/CD Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/benchmark.yml
name: Performance Benchmark

on:
  schedule:
    - cron: '0 2 * * *' # Daily at 2 AM
  workflow_dispatch:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run benchmarks
        run: |
          ./scripts/benchmark.sh compare
```

## Benchmark Results

### Results Directory

Benchmark results are stored in `benchmarks/results/`:

```
benchmarks/
├── baselines/
│   └── baseline.json
└── results/
    ├── benchmark_20250127_120000.json
    ├── startup_20250127_120000.json
    ├── tps_20250127_120000.json
    ├── memory_20250127_120000.json
    └── cpu_20250127_120000.json
```

### Result File Format

Each benchmark creates a JSON file with metrics:

```json
{
  "tps_avg": 20.0,
  "tps_min": 19.8,
  "tps_max": 20.0,
  "samples": [20.0, 19.9, 20.0, ...]
}
```

## Best Practices

### 1. Create Baseline After Optimization

After making performance optimizations, create a new baseline:

```bash
./scripts/benchmark.sh baseline
```

### 2. Regular Benchmarking

Run benchmarks regularly to detect regressions:

```bash
# Weekly comparison
./scripts/benchmark.sh compare
```

### 3. Consistent Environment

Run benchmarks in consistent conditions:

- Same hardware
- Same server configuration
- Similar load conditions
- No other heavy processes running

### 4. Document Changes

When performance changes, document:

- What changed (code, configuration, hardware)
- When it changed
- Impact on metrics

## Troubleshooting

### Server Not Ready

**Issue**: Benchmark fails waiting for server to be ready

**Solution**:

- Check server logs: `docker logs minecraft-server`
- Increase wait time in script
- Verify server is starting correctly

### TPS Not Detected

**Issue**: TPS shows as 20.0 (default) instead of actual value

**Solution**:

- Server type may not support TPS reporting
- Use Paper/Spigot for TPS reporting
- Check server logs for TPS output format

### High Memory Usage

**Issue**: Memory usage exceeds baseline significantly

**Solution**:

- Check for memory leaks
- Review recent changes
- Consider increasing memory allocation
- Restart server before benchmarking

### Inconsistent Results

**Issue**: Benchmark results vary significantly between runs

**Solution**:

- Ensure consistent environment
- Increase warmup time
- Increase benchmark duration
- Check for background processes

## Performance Targets

### Raspberry Pi 5 (4GB)

- **Startup Time**: < 60 seconds
- **TPS**: 20.0 average, > 18.0 minimum
- **Memory**: < 1.5GB average
- **CPU**: < 80% average

### Raspberry Pi 5 (8GB)

- **Startup Time**: < 60 seconds
- **TPS**: 20.0 average, > 18.0 minimum
- **Memory**: < 2.5GB average
- **CPU**: < 80% average

### x86_64 Systems

- **Startup Time**: < 30 seconds
- **TPS**: 20.0 average, > 19.0 minimum
- **Memory**: Varies by allocation
- **CPU**: < 50% average

## Integration with Monitoring

The benchmark suite complements the monitoring system:

- **Monitoring**: Real-time metrics collection
- **Benchmarking**: Performance validation and regression detection

Use both together:

1. Monitor continuously for real-time insights
2. Benchmark periodically for performance validation

## Resources

- [Minecraft Server Performance](https://minecraft.fandom.com/wiki/Server_performance)
- [Aikar's Flags](https://aikar.co/2018/07/02/tuning-the-jvm-g1gc-garbage-collector-flags-for-minecraft/)
- [Paper Performance Guide](https://docs.papermc.io/paper/how-to/optimize-paper)

## See Also

- [Docker Optimization Guide](DOCKER_OPTIMIZATION.md) - Image optimization
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Performance issues
- [Monitoring Guide](BACKUP_AND_MONITORING.md) - Real-time monitoring
