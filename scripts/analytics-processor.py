#!/usr/bin/env python3
"""
Analytics Processing Engine
Processes collected analytics data to generate insights, trends, predictions, and anomaly detection
"""

import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add project root to path
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

ANALYTICS_DIR = PROJECT_DIR / "analytics"
OUTPUT_DIR = PROJECT_DIR / "analytics" / "processed"


class AnalyticsProcessor:
    """Process analytics data and generate insights"""

    def __init__(self):
        self.analytics_dir = ANALYTICS_DIR
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_analytics_data(self, data_type: str, hours: int = 24) -> List[Dict]:
        """Load analytics data from JSONL files"""
        file_path = self.analytics_dir / f"{data_type}.jsonl"
        if not file_path.exists():
            return []

        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        data = []

        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("timestamp", 0) >= cutoff_time:
                            data.append(record)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        return sorted(data, key=lambda x: x.get("timestamp", 0))

    def calculate_trends(self, data: List[Dict], value_key: str) -> Dict:
        """Calculate trends (slope, direction) from time series data"""
        if len(data) < 2:
            # For single data point, return basic info
            if len(data) == 1:
                value = float(data[0].get("data", {}).get(value_key, 0))
                return {
                    "direction": "stable",
                    "slope": 0,
                    "change_percent": 0,
                    "current": value,
                    "average": value,
                    "min": value,
                    "max": value,
                }
            return {"direction": "stable", "slope": 0, "change_percent": 0}

        values = [float(record.get("data", {}).get(value_key, 0)) for record in data]
        if not values or all(v == 0 for v in values):
            return {"direction": "stable", "slope": 0, "change_percent": 0}

        # Simple linear regression for trend
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Calculate percentage change
        if values[0] != 0:
            change_percent = ((values[-1] - values[0]) / values[0]) * 100
        else:
            change_percent = 0

        direction = "increasing" if slope > 0.01 else ("decreasing" if slope < -0.01 else "stable")

        return {
            "direction": direction,
            "slope": slope,
            "change_percent": round(change_percent, 2),
            "current": values[-1],
            "average": round(statistics.mean(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
        }

    def detect_anomalies(self, data: List[Dict], value_key: str, threshold: float = 2.0) -> List[Dict]:
        """Detect anomalies using statistical methods (Z-score)"""
        if len(data) < 3:
            return []

        values = [float(record.get("data", {}).get(value_key, 0)) for record in data]
        if not values:
            return []

        mean = statistics.mean(values)
        if len(values) > 1:
            stdev = statistics.stdev(values)
        else:
            stdev = 0

        if stdev == 0:
            return []

        anomalies = []
        for i, (record, value) in enumerate(zip(data, values)):
            z_score = abs((value - mean) / stdev) if stdev > 0 else 0
            if z_score > threshold:
                anomalies.append(
                    {
                        "timestamp": record.get("timestamp"),
                        "datetime": record.get("datetime"),
                        "value": value,
                        "z_score": round(z_score, 2),
                        "severity": "high" if z_score > 3.0 else "medium",
                    }
                )

        return anomalies

    def predict_future(self, data: List[Dict], value_key: str, hours_ahead: int = 1) -> Dict:
        """Simple linear prediction for future values"""
        if len(data) < 2:
            return {"predicted": 0, "confidence": 0}

        values = [float(record.get("data", {}).get(value_key, 0)) for record in data]
        if not values:
            return {"predicted": 0, "confidence": 0}

        # Simple moving average with trend
        recent_values = values[-min(10, len(values)) :]
        avg = statistics.mean(recent_values)

        # Calculate trend per data point (for linear extrapolation)
        if len(values) >= 2:
            # Calculate trend as change per data point
            trend_per_point = (values[-1] - values[0]) / (len(values) - 1) if len(values) > 1 else 0
            # For prediction, use the last value and extrapolate
            predicted = values[-1] + (trend_per_point * hours_ahead)
        else:
            trend_per_point = 0
            predicted = avg

        # Confidence based on data quality
        confidence = min(100, max(0, (len(data) / 100) * 100))

        return {
            "predicted": round(predicted, 2),
            "confidence": round(confidence, 1),
            "trend": round(trend_per_point, 2),
        }

    def analyze_player_behavior(self, hours: int = 24) -> Dict:
        """Analyze player behavior patterns"""
        player_data = self.load_analytics_data("players", hours)
        event_data = self.load_analytics_data("player_events", hours)

        # Count unique players
        unique_players = set()
        for record in player_data:
            players = record.get("data", [])
            if isinstance(players, list):
                unique_players.update(players)

        # Analyze peak hours
        hourly_activity = defaultdict(int)
        for record in player_data:
            try:
                dt = datetime.fromtimestamp(record.get("timestamp", 0))
                hour = dt.hour
                players = record.get("data", [])
                player_count = len(players) if isinstance(players, list) else 0
                hourly_activity[hour] += player_count
            except (ValueError, TypeError):
                continue

        peak_hour = max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else 0

        # Calculate average session duration (simplified)
        # In production, would track individual player sessions
        avg_session_duration = 0  # Placeholder

        return {
            "unique_players": len(unique_players),
            "peak_hour": peak_hour,
            "hourly_distribution": dict(hourly_activity),
            "average_session_duration_minutes": avg_session_duration,
            "total_events": len(event_data),
        }

    def analyze_performance_trends(self, hours: int = 24) -> Dict:
        """Analyze server performance trends"""
        perf_data = self.load_analytics_data("performance", hours)

        if not perf_data:
            return {}

        tps_values = [float(r.get("data", {}).get("tps", 0)) for r in perf_data]
        cpu_values = [float(r.get("data", {}).get("cpu", 0)) for r in perf_data]
        memory_values = [float(r.get("data", {}).get("memory", 0)) for r in perf_data]

        tps_trend = self.calculate_trends(perf_data, "tps")
        cpu_trend = self.calculate_trends(perf_data, "cpu")
        memory_trend = self.calculate_trends(perf_data, "memory")

        # Detect anomalies
        tps_anomalies = self.detect_anomalies(perf_data, "tps", threshold=1.4)
        cpu_anomalies = self.detect_anomalies(perf_data, "cpu", threshold=1.5)
        memory_anomalies = self.detect_anomalies(perf_data, "memory", threshold=1.5)

        # Predictions
        tps_prediction = self.predict_future(perf_data, "tps", hours_ahead=1)
        memory_prediction = self.predict_future(perf_data, "memory", hours_ahead=1)

        return {
            "tps": {
                "trend": tps_trend,
                "anomalies": tps_anomalies,
                "prediction": tps_prediction,
                "current": tps_values[-1] if tps_values else 0,
                "average": round(statistics.mean(tps_values), 2) if tps_values else 0,
            },
            "cpu": {
                "trend": cpu_trend,
                "anomalies": cpu_anomalies,
                "current": cpu_values[-1] if cpu_values else 0,
                "average": round(statistics.mean(cpu_values), 2) if cpu_values else 0,
            },
            "memory": {
                "trend": memory_trend,
                "anomalies": memory_anomalies,
                "prediction": memory_prediction,
                "current": memory_values[-1] if memory_values else 0,
                "average": round(statistics.mean(memory_values), 2) if memory_values else 0,
            },
        }

    def generate_report(self, hours: int = 24) -> Dict:
        """Generate comprehensive analytics report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "period_hours": hours,
            "player_behavior": self.analyze_player_behavior(hours),
            "performance": self.analyze_performance_trends(hours),
            "summary": {},
        }

        # Generate summary
        perf = report.get("performance", {})
        tps_info = perf.get("tps", {})
        memory_info = perf.get("memory", {})

        summary = {
            "status": "healthy",
            "warnings": [],
            "recommendations": [],
        }

        # Check TPS
        if tps_info.get("current", 20) < 18:
            summary["warnings"].append("Low TPS detected - server may be lagging")
            summary["status"] = "warning"

        # Check memory
        if memory_info.get("current", 0) > 3000:  # > 3GB
            summary["warnings"].append("High memory usage detected")
            if summary["status"] == "healthy":
                summary["status"] = "warning"

        # Check anomalies
        tps_anomalies = tps_info.get("anomalies", [])
        if len(tps_anomalies) > 3:
            summary["warnings"].append(f"{len(tps_anomalies)} TPS anomalies detected")
            summary["status"] = "critical"

        # Recommendations
        if tps_info.get("trend", {}).get("direction") == "decreasing":
            summary["recommendations"].append("Consider reducing view distance or max players")

        if memory_info.get("trend", {}).get("direction") == "increasing":
            summary["recommendations"].append("Monitor memory usage - may need optimization")

        report["summary"] = summary

        return report

    def save_report(self, report: Dict, filename: str = "latest_report.json"):
        """Save report to file"""
        file_path = self.output_dir / filename
        with open(file_path, "w") as f:
            json.dump(report, f, indent=2)
        return str(file_path)


def main():
    """Main function"""
    processor = AnalyticsProcessor()

    # Generate reports for different time periods
    periods = [1, 6, 24, 168]  # 1 hour, 6 hours, 24 hours, 1 week
    reports = {}

    for hours in periods:
        report = processor.generate_report(hours)
        reports[f"{hours}h"] = report

    # Save latest report
    latest_report = processor.generate_report(24)
    processor.save_report(latest_report, "latest_report.json")

    # Save all reports
    processor.save_report(reports, "all_reports.json")

    print(json.dumps(latest_report, indent=2))


if __name__ == "__main__":
    main()
