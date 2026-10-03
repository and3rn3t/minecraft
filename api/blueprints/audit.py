"""Read-only history endpoints: the admin audit trail, raw server/Docker
logs, the typed game-event bus, and the Hall of Deaths.
"""

import json
import subprocess

from flask import Blueprint, jsonify, request

from api import auth_guard, server
from api.security import sanitize_string

bp = Blueprint("audit", __name__)


@bp.route("/api/audit/logs", methods=["GET"])
@auth_guard.require_permission("audit.view")
def get_audit_logs():
    """Get audit logs"""
    # Clamped: a negative limit sliced from the end ("-1" returned all but
    # the oldest entry) and an unbounded one returned the whole file.
    limit = min(max(request.args.get("limit", 100, type=int), 1), 1000)
    offset = max(request.args.get("offset", 0, type=int), 0)
    action_filter = request.args.get("action")
    username_filter = request.args.get("username")

    logs = []
    if server.AUDIT_LOG_FILE.exists():
        with open(server.AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        log_entry = json.loads(line.strip())
                        # Apply filters
                        if action_filter and log_entry.get("action") != action_filter:
                            continue
                        if username_filter and log_entry.get("username") != username_filter:
                            continue
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue

    # Sort by timestamp (newest first)
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Apply pagination
    total = len(logs)
    logs = logs[offset : offset + limit]

    return (
        jsonify(
            {
                "success": True,
                "logs": logs,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        ),
        200,
    )


@bp.route("/api/logs", methods=["GET"])
@auth_guard.require_permission("logs.view")
def get_logs():
    """Get server logs"""
    lines = request.args.get("lines", 100, type=int)

    _, stderr, _ = server.run_script("manage.sh", "logs")

    # Get last N lines from Docker logs
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), "minecraft-server"], capture_output=True, text=True, timeout=10
        )
        logs = result.stdout if result.returncode == 0 else stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logs = stderr or "Unable to retrieve logs"

    return jsonify({"logs": logs.split("\n"), "lines": len(logs.split("\n"))})


@bp.route("/api/events", methods=["GET"])
@auth_guard.require_permission("logs.view")
def get_game_events():
    """Return recent game events, newest first.

    Query parameters: `limit` (default 100, capped at 500), `type` to filter by
    event type, and `player` to filter by player name.
    """
    if not server.EVENTS_AVAILABLE:
        return jsonify({"error": "Event capture is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    event_type = request.args.get("type")
    if event_type and event_type not in server.game_events.ALL_EVENT_TYPES:
        return jsonify({"error": "Unknown event type", "valid_types": list(server.game_events.ALL_EVENT_TYPES)}), 400

    player = request.args.get("player")
    if player:
        player = sanitize_string(player, max_length=16)

    records = server.game_events.get_bus().read(limit=limit, event_type=event_type, player=player)

    return jsonify({"events": records, "count": len(records)})


@bp.route("/api/events/types", methods=["GET"])
@auth_guard.require_permission("logs.view")
def get_game_event_types():
    """List the event types the bus can produce."""
    if not server.EVENTS_AVAILABLE:
        return jsonify({"error": "Event capture is unavailable"}), 503
    return jsonify({"types": list(server.game_events.ALL_EVENT_TYPES)})


@bp.route("/api/deaths", methods=["GET"])
@auth_guard.require_permission("players.view")
def get_deaths():
    """Return recent deaths with their epitaphs, newest first.

    Query parameters: `limit` (default 50, capped at 200), `player`, and
    `category` to filter by how they died.
    """
    if not server.DEATHS_AVAILABLE:
        return jsonify({"error": "The Hall of Deaths is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    player = request.args.get("player")
    if player:
        player = sanitize_string(player, max_length=16)

    category = request.args.get("category")
    if category:
        category = sanitize_string(category, max_length=32)

    hall = server.hall_of_deaths.get_hall()
    return jsonify(
        {
            "deaths": hall.read(limit=limit, player=player, category=category),
            "stats": hall.stats(),
        }
    )


@bp.route("/api/deaths/leaderboard", methods=["GET"])
@auth_guard.require_permission("players.view")
def get_deaths_leaderboard():
    """Per-player death totals, most deaths first."""
    if not server.DEATHS_AVAILABLE:
        return jsonify({"error": "The Hall of Deaths is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    return jsonify({"leaderboard": server.hall_of_deaths.get_hall().leaderboard(limit=limit)})
