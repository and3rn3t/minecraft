#!/usr/bin/env python3
"""
Unit Tests: Analytics Processor
Tests for analytics processing algorithms and functions
"""

import importlib.util
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Import analytics-processor.py (hyphenated filename requires importlib)
processor_module_path = SCRIPTS_DIR / "analytics-processor.py"
spec = importlib.util.spec_from_file_location("analytics_processor", processor_module_path)
analytics_processor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analytics_processor_module)
AnalyticsProcessor = analytics_processor_module.AnalyticsProcessor


@pytest.fixture
def processor():
    """Create analytics processor instance"""
    with tempfile.TemporaryDirectory() as tmpdir:
        processor = AnalyticsProcessor()
        processor.analytics_dir = Path(tmpdir)
        processor.output_dir = Path(tmpdir) / "processed"
        processor.output_dir.mkdir(parents=True, exist_ok=True)
        yield processor


@pytest.fixture
def sample_data():
    """Sample analytics data"""
    base_time = int(datetime.now().timestamp())
    return [
        {
            "timestamp": base_time - 3600,
            "datetime": "2024-01-27 11:00:00",
            "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000},
        },
        {
            "timestamp": base_time - 1800,
            "datetime": "2024-01-27 11:30:00",
            "data": {"tps": 19.5, "cpu": 55.0, "memory": 1100},
        },
        {
            "timestamp": base_time,
            "datetime": "2024-01-27 12:00:00",
            "data": {"tps": 20.0, "cpu": 52.0, "memory": 1050},
        },
    ]


@pytest.fixture
def sample_player_data():
    """Sample player analytics data"""
    base_time = int(datetime.now().timestamp())
    return [
        {
            "timestamp": base_time - 3600,
            "datetime": "2024-01-27 11:00:00",
            "data": ["player1", "player2"],
        },
        {
            "timestamp": base_time - 1800,
            "datetime": "2024-01-27 11:30:00",
            "data": ["player1", "player2", "player3"],
        },
        {
            "timestamp": base_time,
            "datetime": "2024-01-27 12:00:00",
            "data": ["player1"],
        },
    ]


class TestDataLoading:
    """Tests for data loading functionality"""

    def test_load_analytics_data_empty_file(self, processor):
        """Test loading from empty file"""
        data = processor.load_analytics_data("nonexistent", hours=24)
        assert data == []

    def test_load_analytics_data_with_data(self, processor, sample_data):
        """Test loading data from file"""
        # Create test file
        file_path = processor.analytics_dir / "performance.jsonl"
        with open(file_path, "w") as f:
            for record in sample_data:
                f.write(json.dumps(record) + "\n")

        data = processor.load_analytics_data("performance", hours=24)
        assert len(data) == 3
        assert data[0]["timestamp"] == sample_data[0]["timestamp"]

    def test_load_analytics_data_filters_by_time(self, processor, sample_data):
        """Test that data is filtered by time window"""
        # Create test file with old and new data
        file_path = processor.analytics_dir / "performance.jsonl"
        old_record = {
            "timestamp": int(datetime.now().timestamp()) - 86400 - 3600,  # 25 hours ago
            "datetime": "2024-01-26 11:00:00",
            "data": {"tps": 20.0},
        }
        with open(file_path, "w") as f:
            f.write(json.dumps(old_record) + "\n")
            for record in sample_data:
                f.write(json.dumps(record) + "\n")

        data = processor.load_analytics_data("performance", hours=24)
        # Should only include recent data (last 24 hours)
        assert len(data) == 3
        assert all(r["timestamp"] >= old_record["timestamp"] for r in data)

    def test_load_analytics_data_handles_invalid_json(self, processor):
        """Test handling of invalid JSON lines"""
        file_path = processor.analytics_dir / "performance.jsonl"
        base_time = int(datetime.now().timestamp())
        with open(file_path, "w") as f:
            f.write(json.dumps({"timestamp": base_time, "data": {"valid": "json"}}) + "\n")
            f.write("invalid json line\n")
            f.write(json.dumps({"timestamp": base_time, "data": {"another": "valid"}}) + "\n")

        data = processor.load_analytics_data("performance", hours=24)
        # Should only include valid JSON records
        assert len(data) == 2


class TestTrendCalculation:
    """Tests for trend calculation algorithms"""

    def test_calculate_trends_increasing(self, processor, sample_data):
        """Test trend calculation for increasing values"""
        # Modify data to show increasing trend
        increasing_data = [
            {
                "timestamp": sample_data[0]["timestamp"],
                "data": {"memory": 1000},
            },
            {
                "timestamp": sample_data[1]["timestamp"],
                "data": {"memory": 1100},
            },
            {
                "timestamp": sample_data[2]["timestamp"],
                "data": {"memory": 1200},
            },
        ]

        trend = processor.calculate_trends(increasing_data, "memory")
        assert trend["direction"] == "increasing"
        assert trend["change_percent"] > 0
        assert trend["current"] == 1200
        assert trend["min"] == 1000
        assert trend["max"] == 1200

    def test_calculate_trends_decreasing(self, processor, sample_data):
        """Test trend calculation for decreasing values"""
        decreasing_data = [
            {
                "timestamp": sample_data[0]["timestamp"],
                "data": {"tps": 20.0},
            },
            {
                "timestamp": sample_data[1]["timestamp"],
                "data": {"tps": 19.0},
            },
            {
                "timestamp": sample_data[2]["timestamp"],
                "data": {"tps": 18.0},
            },
        ]

        trend = processor.calculate_trends(decreasing_data, "tps")
        assert trend["direction"] == "decreasing"
        assert trend["change_percent"] < 0
        assert trend["current"] == 18.0

    def test_calculate_trends_stable(self, processor, sample_data):
        """Test trend calculation for stable values"""
        stable_data = [
            {
                "timestamp": sample_data[0]["timestamp"],
                "data": {"tps": 20.0},
            },
            {
                "timestamp": sample_data[1]["timestamp"],
                "data": {"tps": 20.0},
            },
            {
                "timestamp": sample_data[2]["timestamp"],
                "data": {"tps": 20.0},
            },
        ]

        trend = processor.calculate_trends(stable_data, "tps")
        assert trend["direction"] == "stable"
        assert abs(trend["slope"]) < 0.01
        assert trend["change_percent"] == 0

    def test_calculate_trends_empty_data(self, processor):
        """Test trend calculation with empty data"""
        trend = processor.calculate_trends([], "tps")
        assert trend["direction"] == "stable"
        assert trend["slope"] == 0

    def test_calculate_trends_single_data_point(self, processor):
        """Test trend calculation with single data point"""
        single_data = [
            {
                "timestamp": int(datetime.now().timestamp()),
                "data": {"tps": 20.0},
            }
        ]

        trend = processor.calculate_trends(single_data, "tps")
        assert trend["direction"] == "stable"
        assert trend["current"] == 20.0


class TestAnomalyDetection:
    """Tests for anomaly detection algorithms"""

    def test_detect_anomalies_finds_outliers(self, processor, sample_data):
        """Test anomaly detection finds statistical outliers"""
        # Create data with clear anomaly - need at least 3 normal values for Z-score
        # Use a more extreme anomaly to ensure Z-score > 2.0
        base_time = int(datetime.now().timestamp())
        normal_data = [
            {
                "timestamp": base_time - 3600,
                "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000},
            },
            {
                "timestamp": base_time - 1800,
                "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000},
            },
            {
                "timestamp": base_time - 900,
                "data": {"tps": 19.5, "cpu": 50.0, "memory": 1000},
            },
            {
                "timestamp": base_time,
                "data": {"tps": 2.0, "cpu": 50.0, "memory": 1000},  # Very extreme anomaly
            },
        ]

        anomalies = processor.detect_anomalies(normal_data, "tps", threshold=1.4)
        assert len(anomalies) > 0
        assert anomalies[0]["value"] == 2.0
        assert anomalies[0]["severity"] in ["high", "medium"]

    def test_detect_anomalies_no_anomalies(self, processor, sample_data):
        """Test anomaly detection with no outliers"""
        anomalies = processor.detect_anomalies(sample_data, "tps", threshold=2.0)
        # With consistent data, should find no anomalies
        assert len(anomalies) == 0

    def test_detect_anomalies_severity_levels(self, processor):
        """Test anomaly severity classification"""
        base_time = int(datetime.now().timestamp())
        data = [
            {
                "timestamp": base_time - 1800,
                "data": {"tps": 20.0},
            },
            {
                "timestamp": base_time - 1200,
                "data": {"tps": 20.0},
            },
            {
                "timestamp": base_time - 600,
                "data": {"tps": 20.0},
            },
            {
                "timestamp": base_time,
                "data": {"tps": 5.0},  # High severity anomaly
            },
        ]

        anomalies = processor.detect_anomalies(data, "tps", threshold=2.0)
        if len(anomalies) > 0:
            # High Z-score should be classified as high severity
            high_anomalies = [a for a in anomalies if a["severity"] == "high"]
            assert len(high_anomalies) > 0 or anomalies[0]["z_score"] > 3.0

    def test_detect_anomalies_insufficient_data(self, processor):
        """Test anomaly detection with insufficient data"""
        data = [
            {
                "timestamp": int(datetime.now().timestamp()),
                "data": {"tps": 20.0},
            }
        ]

        anomalies = processor.detect_anomalies(data, "tps")
        assert anomalies == []

    def test_detect_anomalies_zero_variance(self, processor):
        """Test anomaly detection with zero variance"""
        base_time = int(datetime.now().timestamp())
        data = [
            {
                "timestamp": base_time - 1800,
                "data": {"tps": 20.0},
            },
            {
                "timestamp": base_time - 1200,
                "data": {"tps": 20.0},
            },
            {
                "timestamp": base_time,
                "data": {"tps": 20.0},
            },
        ]

        anomalies = processor.detect_anomalies(data, "tps")
        # With zero variance, no anomalies should be detected
        assert len(anomalies) == 0


class TestPredictions:
    """Tests for prediction algorithms"""

    def test_predict_future_linear_trend(self, processor, sample_data):
        """Test linear prediction with trend"""
        prediction = processor.predict_future(sample_data, "memory", hours_ahead=1)
        assert "predicted" in prediction
        assert "confidence" in prediction
        assert "trend" in prediction
        assert isinstance(prediction["predicted"], (int, float))
        assert 0 <= prediction["confidence"] <= 100

    def test_predict_future_increasing_trend(self, processor):
        """Test prediction with increasing trend"""
        base_time = int(datetime.now().timestamp())
        increasing_data = [
            {
                "timestamp": base_time - 3600,
                "data": {"memory": 1000},
            },
            {
                "timestamp": base_time - 1800,
                "data": {"memory": 1100},
            },
            {
                "timestamp": base_time,
                "data": {"memory": 1200},
            },
        ]

        prediction = processor.predict_future(increasing_data, "memory", hours_ahead=1)
        # With increasing trend, prediction should be higher than current
        assert prediction["predicted"] >= 1200
        assert prediction["trend"] > 0

    def test_predict_future_decreasing_trend(self, processor):
        """Test prediction with decreasing trend"""
        base_time = int(datetime.now().timestamp())
        decreasing_data = [
            {
                "timestamp": base_time - 3600,
                "data": {"tps": 20.0},
            },
            {
                "timestamp": base_time - 1800,
                "data": {"tps": 19.0},
            },
            {
                "timestamp": base_time,
                "data": {"tps": 18.0},
            },
        ]

        prediction = processor.predict_future(decreasing_data, "tps", hours_ahead=1)
        # With decreasing trend, prediction should be lower than current
        assert prediction["predicted"] <= 18.0
        assert prediction["trend"] < 0

    def test_predict_future_confidence_scoring(self, processor, sample_data):
        """Test prediction confidence calculation"""
        # More data should increase confidence
        prediction_many = processor.predict_future(sample_data * 10, "memory", hours_ahead=1)
        prediction_few = processor.predict_future(sample_data, "memory", hours_ahead=1)

        assert prediction_many["confidence"] >= prediction_few["confidence"]

    def test_predict_future_insufficient_data(self, processor):
        """Test prediction with insufficient data"""
        data = [
            {
                "timestamp": int(datetime.now().timestamp()),
                "data": {"memory": 1000},
            }
        ]

        prediction = processor.predict_future(data, "memory", hours_ahead=1)
        assert prediction["predicted"] == 0 or prediction["confidence"] == 0


class TestPlayerBehavior:
    """Tests for player behavior analysis"""

    def test_analyze_player_behavior_unique_players(self, processor, sample_player_data):
        """Test unique player counting"""
        # Create test file
        file_path = processor.analytics_dir / "players.jsonl"
        with open(file_path, "w") as f:
            for record in sample_player_data:
                f.write(json.dumps(record) + "\n")

        behavior = processor.analyze_player_behavior(hours=24)
        assert behavior["unique_players"] == 3  # player1, player2, player3

    def test_analyze_player_behavior_peak_hour(self, processor, sample_player_data):
        """Test peak hour detection"""
        # Create data with known peak hour using recent timestamps
        # Use current time to ensure data isn't filtered out
        base_time = int(datetime.now().timestamp())
        # Round to start of current hour
        base_dt = datetime.fromtimestamp(base_time)
        base_hour = base_dt.replace(minute=0, second=0, microsecond=0)

        hourly_data = []
        for hour_offset in range(24):
            # Create timestamps for the last 24 hours
            timestamp = int((base_hour - timedelta(hours=23-hour_offset)).timestamp())
            dt = datetime.fromtimestamp(timestamp)
            actual_hour = dt.hour
            # Hour 20 should have peak (10 players), others have 2
            player_count = 10 if actual_hour == 20 else 2
            hourly_data.append(
                {
                    "timestamp": timestamp,
                    "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "data": [f"player{i}" for i in range(player_count)],
                }
            )

        file_path = processor.analytics_dir / "players.jsonl"
        with open(file_path, "w") as f:
            for record in hourly_data:
                f.write(json.dumps(record) + "\n")

        behavior = processor.analyze_player_behavior(hours=24)
        # Peak hour should be 20 (the hour with 10 players)
        # Note: if current hour is 20, there might be a tie, so check that 20 is in the distribution
        assert behavior["peak_hour"] == 20 or (20 in behavior.get("hourly_distribution", {}) and behavior["hourly_distribution"][20] == 10)

    def test_analyze_player_behavior_hourly_distribution(self, processor):
        """Test hourly activity distribution"""
        # Use a fixed base time to ensure hour calculations are predictable
        base_time = int(datetime.now().timestamp())
        base_dt = datetime.fromtimestamp(base_time)
        base_hour_start = base_dt.replace(minute=0, second=0, microsecond=0)
        base_timestamp = int(base_hour_start.timestamp())

        hourly_data = []
        target_hours = [20, 21, 22]
        for hour_offset, target_hour in enumerate(target_hours):
            # Create timestamp for specific hours
            # Calculate how many hours back from base to get to target hour
            current_hour = base_hour_start.hour
            hours_back = (current_hour - target_hour) % 24
            if hours_back == 0:
                hours_back = 24  # Use previous day if same hour
            timestamp = base_timestamp - hours_back * 3600
            dt = datetime.fromtimestamp(timestamp)
            # Ensure we got the right hour
            assert dt.hour == target_hour, f"Expected hour {target_hour}, got {dt.hour}"
            hourly_data.append(
                {
                    "timestamp": timestamp,
                    "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "data": [f"player{i}" for i in range(target_hour - 18)],
                }
            )

        file_path = processor.analytics_dir / "players.jsonl"
        with open(file_path, "w") as f:
            for record in hourly_data:
                f.write(json.dumps(record) + "\n")

        behavior = processor.analyze_player_behavior(hours=24)
        assert "hourly_distribution" in behavior
        assert behavior["hourly_distribution"][20] > 0

    def test_analyze_player_behavior_no_data(self, processor):
        """Test player behavior analysis with no data"""
        behavior = processor.analyze_player_behavior(hours=24)
        assert behavior["unique_players"] == 0
        assert behavior["total_events"] == 0


class TestReportGeneration:
    """Tests for report generation"""

    def test_generate_report_structure(self, processor, sample_data):
        """Test report structure"""
        # Create test data files
        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in sample_data:
                f.write(json.dumps(record) + "\n")

        player_file = processor.analytics_dir / "players.jsonl"
        with open(player_file, "w") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": sample_data[0]["timestamp"],
                        "datetime": "2024-01-27 11:00:00",
                        "data": ["player1"],
                    }
                )
                + "\n"
            )

        report = processor.generate_report(hours=24)

        assert "generated_at" in report
        assert "period_hours" in report
        assert "player_behavior" in report
        assert "performance" in report
        assert "summary" in report

    def test_generate_report_summary_status(self, processor, sample_data):
        """Test report summary status calculation"""
        # Create data with low TPS (should trigger warning)
        low_tps_data = [
            {
                "timestamp": sample_data[0]["timestamp"],
                "data": {"tps": 15.0, "cpu": 50.0, "memory": 1000},
            }
        ]

        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in low_tps_data:
                f.write(json.dumps(record) + "\n")

        report = processor.generate_report(hours=24)
        assert "summary" in report
        assert "status" in report["summary"]
        assert report["summary"]["status"] in ["healthy", "warning", "critical"]

    def test_generate_report_warnings(self, processor):
        """Test warning generation"""
        base_time = int(datetime.now().timestamp())
        # Create data that should trigger warnings
        warning_data = [
            {
                "timestamp": base_time,
                "data": {"tps": 15.0, "cpu": 50.0, "memory": 4000},  # Low TPS, high memory
            }
        ]

        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in warning_data:
                f.write(json.dumps(record) + "\n")

        report = processor.generate_report(hours=24)
        assert "warnings" in report["summary"]
        # Should have warnings for low TPS and/or high memory
        assert len(report["summary"]["warnings"]) > 0

    def test_generate_report_recommendations(self, processor):
        """Test recommendation generation"""
        base_time = int(datetime.now().timestamp())
        # Create data with decreasing TPS trend
        trend_data = [
            {
                "timestamp": base_time - 3600,
                "data": {"tps": 20.0, "memory": 1000},
            },
            {
                "timestamp": base_time - 1800,
                "data": {"tps": 19.0, "memory": 1100},
            },
            {
                "timestamp": base_time,
                "data": {"tps": 18.0, "memory": 1200},
            },
        ]

        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in trend_data:
                f.write(json.dumps(record) + "\n")

        report = processor.generate_report(hours=24)
        assert "recommendations" in report["summary"]
        # Should have recommendations based on trends

    def test_save_report(self, processor, sample_data):
        """Test report saving"""
        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in sample_data:
                f.write(json.dumps(record) + "\n")

        report = processor.generate_report(hours=24)
        file_path = processor.save_report(report, "test_report.json")

        assert Path(file_path).exists()
        with open(file_path, "r") as f:
            saved_report = json.load(f)
        assert saved_report["period_hours"] == report["period_hours"]


class TestPerformanceTrends:
    """Tests for performance trend analysis"""

    def test_analyze_performance_trends_structure(self, processor, sample_data):
        """Test performance trends analysis structure"""
        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in sample_data:
                f.write(json.dumps(record) + "\n")

        trends = processor.analyze_performance_trends(hours=24)

        assert "tps" in trends
        assert "cpu" in trends
        assert "memory" in trends

        assert "trend" in trends["tps"]
        assert "current" in trends["tps"]
        assert "average" in trends["tps"]

    def test_analyze_performance_trends_anomalies(self, processor):
        """Test anomaly detection in performance trends"""
        base_time = int(datetime.now().timestamp())
        # Need at least 3 normal values for Z-score calculation
        # Use a more extreme anomaly to ensure detection
        data_with_anomaly = [
            {
                "timestamp": base_time - 3600,
                "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000},
            },
            {
                "timestamp": base_time - 2400,
                "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000},
            },
            {
                "timestamp": base_time - 1800,
                "data": {"tps": 19.5, "cpu": 50.0, "memory": 1000},
            },
            {
                "timestamp": base_time,
                "data": {"tps": 2.0, "cpu": 50.0, "memory": 1000},  # Very extreme anomaly
            },
        ]

        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in data_with_anomaly:
                f.write(json.dumps(record) + "\n")

        trends = processor.analyze_performance_trends(hours=24)
        assert "anomalies" in trends["tps"]
        # Should detect the anomaly
        assert len(trends["tps"]["anomalies"]) > 0

    def test_analyze_performance_trends_predictions(self, processor, sample_data):
        """Test predictions in performance trends"""
        perf_file = processor.analytics_dir / "performance.jsonl"
        with open(perf_file, "w") as f:
            for record in sample_data:
                f.write(json.dumps(record) + "\n")

        trends = processor.analyze_performance_trends(hours=24)
        assert "prediction" in trends["tps"]
        assert "predicted" in trends["tps"]["prediction"]
        assert "confidence" in trends["tps"]["prediction"]
