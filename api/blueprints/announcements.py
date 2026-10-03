"""Scheduled/one-off in-game announcements, and the /api/metrics endpoint
(grouped here only because it was directly adjacent in the original file --
it has no relation to announcements otherwise).
"""

import json
import subprocess
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from api import auth_guard, server

bp = Blueprint("announcements", __name__)


@bp.route("/api/announcements", methods=["GET"])
@auth_guard.require_permission("server.manage")
def get_announcements():
    """Get all announcements"""
    stdout, stderr, code = server.run_script("announcement-manager.sh", "list")
    if code == 0:
        data = json.loads(stdout)
        return jsonify({"success": True, "announcements": data.get("announcements", [])}), 200
    return server.script_error(stderr, "Failed to get announcements")


@bp.route("/api/announcements", methods=["POST"])
@auth_guard.require_permission("server.manage")
def create_announcement():
    """Create a new announcement"""
    data = request.get_json() or {}
    message = data.get("message")
    ann_type = data.get("type", "say")
    schedule_type = data.get("schedule_type")
    schedule_time = data.get("schedule_time")
    enabled = data.get("enabled", True)

    if not message:
        return jsonify({"error": "Message required"}), 400

    stdout, stderr, code = server.run_script(
        "announcement-manager.sh",
        "create",
        message,
        ann_type,
        schedule_type or "",
        schedule_time or "",
        str(enabled),
    )
    if code == 0:
        announcement = json.loads(stdout)
        return jsonify({"success": True, "announcement": announcement}), 200
    return server.script_error(stderr, "Failed to create announcement")


@bp.route("/api/announcements/<announcement_id>/send", methods=["POST"])
@auth_guard.require_permission("server.manage")
def send_announcement(announcement_id):
    """Send an announcement immediately"""
    stdout, stderr, code = server.run_script("announcement-manager.sh", "send", announcement_id)
    if code == 0:
        return jsonify({"success": True, "message": "Announcement sent"}), 200
    return server.script_error(stderr, "Failed to send announcement")


@bp.route("/api/announcements/<announcement_id>", methods=["DELETE"])
@auth_guard.require_permission("server.manage")
def delete_announcement(announcement_id):
    """Delete an announcement"""
    stdout, stderr, code = server.run_script("announcement-manager.sh", "delete", announcement_id)
    if code == 0:
        return jsonify({"success": True, "message": "Announcement deleted"}), 200
    return server.script_error(stderr, "Failed to delete announcement")


@bp.route("/api/metrics", methods=["GET"])
@auth_guard.require_permission("metrics.view")
def get_metrics():
    """Get server metrics"""
    # Run monitor script
    _, _, _ = server.run_script("monitor.sh")

    metrics = {}

    # Try to get Docker stats
    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "minecraft-server",
                "--no-stream",
                "--format",
                "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                metrics["cpu_percent"] = parts[0].rstrip("%")
                metrics["memory_usage"] = parts[1]
                metrics["memory_percent"] = parts[2].rstrip("%")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # Metrics are best-effort; missing values are acceptable

    return jsonify({"metrics": metrics, "timestamp": datetime.now(timezone.utc).isoformat()})
