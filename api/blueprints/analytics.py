"""Analytics: collection trigger, the general report, and the
trends/anomalies/predictions/player-behavior/custom-report endpoints that all
lazily import analytics_processor.AnalyticsProcessor (optional, so each
degrades to a placeholder response on ImportError rather than a 500).
"""

import json
import subprocess
import sys
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from api import auth_guard, server

bp = Blueprint("analytics", __name__)


@bp.route("/api/analytics/collect", methods=["POST"])
@auth_guard.require_permission("analytics.view")
def collect_analytics():
    """Trigger analytics data collection"""
    stdout, stderr, code = server.run_script("analytics-collector.sh")
    if code == 0:
        return jsonify({"success": True, "message": "Analytics data collected"}), 200
    return server.script_error(stderr, "Failed to collect analytics")


@bp.route("/api/analytics/report", methods=["GET"])
@auth_guard.require_permission("analytics.view")
def get_analytics_report():
    """Get analytics report"""
    try:
        hours = int(request.args.get("hours", 24))
    except (TypeError, ValueError):
        hours = 24

    result = subprocess.run(
        [
            sys.executable,
            str(server.SCRIPTS_DIR / "analytics-processor.py"),
            str(hours),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(server.PROJECT_ROOT),
        check=False,
    )

    if result.returncode != 0:
        return jsonify({"error": "Failed to generate report", "details": result.stderr}), 500

    # Load latest report
    report_file = server.PROJECT_ROOT / "analytics" / "processed" / "latest_report.json"
    if report_file.exists():
        with open(report_file, "r") as f:
            report = json.load(f)
        return jsonify({"report": report}), 200
    else:
        return jsonify({"error": "Report not available"}), 404


@bp.route("/api/analytics/trends", methods=["GET"])
@auth_guard.require_permission("analytics.view")
def get_analytics_trends():
    """Get performance trends"""
    try:
        hours = int(request.args.get("hours", 24))
        metric_type = request.args.get("type", "performance")  # performance, players, network

        server._ensure_analytics_processor_module()
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()

        if metric_type == "performance":
            trends = processor.analyze_performance_trends(hours)
        elif metric_type == "players":
            trends = processor.analyze_player_behavior(hours)
        else:
            trends = {}

        return jsonify({"trends": trends, "period_hours": hours}), 200

    except ImportError:
        # Fallback: return basic trends from metrics
        return jsonify({"trends": {}, "period_hours": hours, "note": "Full analytics not available"}), 200
    except Exception as e:  # noqa: BLE001 - route boundary: logged, generic 500 to the client
        server.app.logger.error(f"Failed to get trends: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/analytics/anomalies", methods=["GET"])
@auth_guard.require_permission("analytics.view")
def get_analytics_anomalies():
    """Get detected anomalies"""
    try:
        hours = int(request.args.get("hours", 24))
        metric = request.args.get("metric", "tps")  # tps, cpu, memory

        server._ensure_analytics_processor_module()
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()
        perf_data = processor.load_analytics_data("performance", hours)

        if not perf_data:
            return jsonify({"anomalies": [], "message": "No data available"}), 200

        anomalies = processor.detect_anomalies(perf_data, metric)
        return jsonify({"anomalies": anomalies, "metric": metric, "period_hours": hours}), 200

    except ImportError:
        return jsonify({"anomalies": [], "note": "Full analytics not available"}), 200
    except Exception as e:  # noqa: BLE001 - route boundary: logged, generic 500 to the client
        server.app.logger.error(f"Failed to get anomalies: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/analytics/predictions", methods=["GET"])
@auth_guard.require_permission("analytics.view")
def get_analytics_predictions():
    """Get resource usage predictions"""
    try:
        hours_ahead = int(request.args.get("hours_ahead", 1))
        metric = request.args.get("metric", "memory")  # memory, tps, cpu

        server._ensure_analytics_processor_module()
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()
        perf_data = processor.load_analytics_data("performance", hours=24)

        if not perf_data:
            return jsonify({"prediction": {}, "message": "No data available"}), 200

        prediction = processor.predict_future(perf_data, metric, hours_ahead)
        return jsonify({"prediction": prediction, "metric": metric, "hours_ahead": hours_ahead}), 200

    except ImportError:
        return jsonify({"prediction": {}, "note": "Full analytics not available"}), 200
    except Exception as e:  # noqa: BLE001 - route boundary: logged, generic 500 to the client
        server.app.logger.error(f"Failed to get predictions: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/analytics/player-behavior", methods=["GET"])
@auth_guard.require_permission("analytics.view")
def get_player_behavior():
    """Get player behavior analytics"""
    try:
        hours = int(request.args.get("hours", 24))

        server._ensure_analytics_processor_module()
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()
        behavior = processor.analyze_player_behavior(hours)

        return jsonify({"behavior": behavior, "period_hours": hours}), 200

    except ImportError:
        return jsonify({"behavior": {}, "note": "Full analytics not available"}), 200
    except Exception as e:  # noqa: BLE001 - route boundary: logged, generic 500 to the client
        server.app.logger.error(f"Failed to get player behavior: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/analytics/custom-report", methods=["POST"])
@auth_guard.require_permission("analytics.generate")
def generate_custom_report():
    """Generate custom analytics report"""
    try:
        data = request.get_json() or {}
        hours = int(data.get("hours", 24))
        metrics = data.get("metrics", ["performance", "players"])

        server._ensure_analytics_processor_module()
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_hours": hours,
            "requested_metrics": metrics,
        }

        if "performance" in metrics:
            report["performance"] = processor.analyze_performance_trends(hours)

        if "players" in metrics:
            report["player_behavior"] = processor.analyze_player_behavior(hours)

        # Save custom report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"custom_report_{timestamp}.json"
        processor.save_report(report, filename)

        return jsonify({"report": report, "saved_as": filename}), 200

    except ImportError:
        return jsonify({"error": "Analytics processor not available"}), 500
    except Exception as e:  # noqa: BLE001 - route boundary: logged, generic 500 to the client
        server.app.logger.error(f"Failed to generate report: {e}")
        return jsonify({"error": "Internal server error"}), 500
