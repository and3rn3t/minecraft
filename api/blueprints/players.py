"""Online players, whitelist, bans, ops, server.properties, and per-player
statistics.
"""

import json
import re

from flask import Blueprint, jsonify, request

from api import server

bp = Blueprint("players", __name__)


@bp.route("/api/players", methods=["GET"])
@server.require_permission("players.view")
def get_players():
    """Get list of online players"""
    stdout, _, _ = server.run_rcon_command("list")

    # Parse player list from RCON response
    players = []
    if stdout:
        match = re.search(r"online:\s*(.+)", stdout)
        if match:
            player_list = match.group(1).strip()
            players = [p.strip() for p in player_list.split(",") if p.strip()]

    return jsonify({"players": players, "count": len(players)})


@bp.route("/api/players/whitelist", methods=["GET"])
@server.require_permission("players.manage")
def get_whitelist():
    """Get whitelisted players"""
    whitelist_file = server.PROJECT_ROOT / "data" / "whitelist.json"
    if not whitelist_file.exists():
        return jsonify({"success": True, "players": []}), 200

    with open(whitelist_file, "r") as f:
        whitelist = json.load(f)

    return jsonify({"success": True, "players": whitelist}), 200


@bp.route("/api/players/whitelist", methods=["POST"])
@server.require_permission("players.manage")
def add_whitelist():
    """Add player to whitelist"""
    data = request.get_json() or {}
    player = data.get("player")
    if not player:
        return jsonify({"error": "Player name required"}), 400

    stdout, stderr, code = server.run_script("whitelist-manager.sh", "add", player)
    if code == 0:
        return jsonify({"success": True, "message": f"Player '{player}' added to whitelist"}), 200
    return server.script_error(stderr, "Failed to add player to whitelist")


@bp.route("/api/players/whitelist/<player>", methods=["DELETE"])
@server.require_permission("players.manage")
def remove_whitelist(player):
    """Remove player from whitelist"""
    stdout, stderr, code = server.run_script("whitelist-manager.sh", "remove", player)
    if code == 0:
        return jsonify({"success": True, "message": f"Player '{player}' removed from whitelist"}), 200
    return server.script_error(stderr, "Failed to remove player from whitelist")


@bp.route("/api/players/banned", methods=["GET"])
@server.require_permission("players.manage")
def get_banned():
    """Get banned players"""
    banned_file = server.PROJECT_ROOT / "data" / "banned-players.json"
    if not banned_file.exists():
        return jsonify({"success": True, "players": []}), 200

    with open(banned_file, "r") as f:
        banned = json.load(f)

    return jsonify({"success": True, "players": banned}), 200


@bp.route("/api/players/ban", methods=["POST"])
@server.require_permission("players.manage")
def ban_player():
    """Ban a player"""
    data = request.get_json() or {}
    player = data.get("player")
    reason = data.get("reason", "Banned by operator")
    if not player:
        return jsonify({"error": "Player name required"}), 400

    username = server.get_username_from_request()
    server.log_audit_event(username, "player.ban", {"player": player, "reason": reason})

    stdout, stderr, code = server.run_script("ban-manager.sh", "ban", player, reason)
    if code == 0:
        return jsonify({"success": True, "message": f"Player '{player}' banned"}), 200
    return server.script_error(stderr, "Failed to ban player")


@bp.route("/api/players/ban/<player>", methods=["DELETE"])
@server.require_permission("players.manage")
def unban_player(player):
    """Unban a player"""
    stdout, stderr, code = server.run_script("ban-manager.sh", "unban", player)
    if code == 0:
        return jsonify({"success": True, "message": f"Player '{player}' unbanned"}), 200
    return server.script_error(stderr, "Failed to unban player")


@bp.route("/api/players/ops", methods=["GET"])
@server.require_permission("players.manage")
def get_ops():
    """Get operators"""
    ops_file = server.PROJECT_ROOT / "data" / "ops.json"
    if not ops_file.exists():
        return jsonify({"success": True, "operators": []}), 200

    with open(ops_file, "r") as f:
        ops = json.load(f)

    return jsonify({"success": True, "operators": ops}), 200


@bp.route("/api/players/op", methods=["POST"])
@server.require_permission("players.manage")
def grant_op():
    """Grant operator status"""
    data = request.get_json() or {}
    player = data.get("player")
    level = data.get("level", 4)
    if not player:
        return jsonify({"error": "Player name required"}), 400

    stdout, stderr, code = server.run_script("op-manager.sh", "grant", player, str(level))
    if code == 0:
        return jsonify({"success": True, "message": f"Operator status granted to '{player}'"}), 200
    return server.script_error(stderr, "Failed to grant operator status")


@bp.route("/api/players/op/<player>", methods=["DELETE"])
@server.require_permission("players.manage")
def revoke_op(player):
    """Revoke operator status"""
    stdout, stderr, code = server.run_script("op-manager.sh", "revoke", player)
    if code == 0:
        return jsonify({"success": True, "message": f"Operator status revoked from '{player}'"}), 200
    return server.script_error(stderr, "Failed to revoke operator status")


@bp.route("/api/server/properties", methods=["GET"])
@server.require_permission("server.manage")
def get_server_properties():
    """Get all server properties"""
    props_file = server.PROJECT_ROOT / "data" / "server.properties"
    if not props_file.exists():
        return jsonify({"error": "server.properties not found"}), 404

    properties = {}
    with open(props_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                properties[key.strip()] = value.strip()

    return jsonify({"success": True, "properties": properties}), 200


@bp.route("/api/server/properties/<key>", methods=["GET"])
@server.require_permission("server.manage")
def get_server_property(key):
    """Get specific server property"""
    stdout, stderr, code = server.run_script("server-properties-manager.sh", "get", key)
    if code == 0:
        return jsonify({"success": True, "key": key, "value": stdout.strip()}), 200
    return server.script_error(stderr, f"Property '{key}' not found", status=404)


@bp.route("/api/server/properties/<key>", methods=["PUT"])
@server.require_permission("server.manage")
def set_server_property(key):
    """Set server property"""
    data = request.get_json() or {}
    value = data.get("value")
    if value is None:
        return jsonify({"error": "Value is required"}), 400

    stdout, stderr, code = server.run_script("server-properties-manager.sh", "set", key, str(value))
    if code == 0:
        return jsonify({"success": True, "message": f"Property '{key}' set to '{value}'"}), 200
    return server.script_error(stderr, "Failed to set property")


# The presets themselves live in scripts/server-properties-manager.sh; this
# list only decides what the API passes through to it. The script also answers
# to the aliases "performance" and "high", which its own help does not mention;
# the API exposes the three documented names only.
SERVER_PROPERTY_PRESETS = ("low-end", "balanced", "high-performance")


@bp.route("/api/server/properties/preset", methods=["POST"])
@server.require_permission("server.manage")
def apply_server_preset():
    """Apply a performance preset to server.properties"""
    data = request.get_json() or {}
    requested = data.get("preset")
    if not requested:
        return jsonify({"error": "Preset name required"}), 400

    # Resolve the request to the matching constant and carry that onward,
    # so nothing downstream — the script argument, the log line, the audit
    # entry — handles the caller's string.
    preset = next((p for p in SERVER_PROPERTY_PRESETS if p == requested), None)
    if preset is None:
        return (
            jsonify({"error": f"Invalid preset. Valid: {', '.join(SERVER_PROPERTY_PRESETS)}"}),
            400,
        )

    stdout, stderr, code = server.run_script("server-properties-manager.sh", "preset", preset)
    if code != 0:
        # stderr carries filesystem paths, so it goes to the log rather
        # than to the caller, and it is subprocess output going into a log
        # line, so it is stripped of newlines first — otherwise it could
        # forge entries of its own.
        server.app.logger.error("Preset '%s' failed: %s", preset, server.sanitize_string(stderr, max_length=200))
        return jsonify({"error": "Failed to apply preset"}), 500

    server.log_audit_event(server.get_username_from_request(), "server.properties.preset", {"preset": preset})
    return jsonify({"success": True, "message": f"Preset '{preset}' applied"}), 200


# Player Statistics Endpoints
#
# These read <world>/stats/<uuid>.json and <world>/advancements/<uuid>.json,
# which the game writes and keeps current. There is no collection step: the
# number in the file is the answer, so a read is idempotent. The log-scraping
# tracker these replaced added its findings to the previous totals on every
# run, so the same unchanged log reported 1, then 2, then 3.
def _require_player_stats():
    """None when the module is importable, otherwise the error to return."""
    if server.PLAYER_STATS_AVAILABLE:
        return None
    return jsonify({"error": "Player statistics are unavailable"}), 503


@bp.route("/api/players/stats", methods=["GET"])
@server.require_permission("players.view")
def get_all_player_stats():
    """Statistics for every player the world has a file for"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    players = [p.as_dict() for p in server.player_stats.read_all()]
    return jsonify({"success": True, "players": players, "count": len(players)}), 200


@bp.route("/api/players/stats/leaderboard", methods=["GET"])
@server.require_permission("players.view")
def get_player_stats_leaderboard():
    """Rank players by one counter"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    metric = request.args.get("metric", "play_time_minutes")
    try:
        # Clamped 1-50, as /api/deaths/leaderboard is: an unbounded limit lets
        # a caller ask for every player on the server, and every stats file
        # behind them, in one request.
        limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    try:
        return jsonify({"success": True, **server.player_stats.leaderboard(metric, limit)}), 200
    except ValueError:
        # An unknown metric is the caller's mistake, so name the ones that
        # exist. The message is built here from our own list rather than
        # passing the exception's text out, which would be a route for
        # internals to reach the caller.
        valid = ", ".join(sorted(server.player_stats.LEADERBOARD_METRICS))
        return jsonify({"error": f"Unknown metric. Valid: {valid}"}), 400
    except Exception as e:
        server.app.logger.error(f"Failed to build the leaderboard: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/players/stats/metrics", methods=["GET"])
@server.require_permission("players.view")
def get_player_stats_metrics():
    """The counters a leaderboard can be built on"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    return jsonify({"success": True, "metrics": server.player_stats.LEADERBOARD_METRICS}), 200


# Werkzeug matches static rules ahead of converters regardless of registration
# order, so /leaderboard and /metrics above are not captured by <player>. A
# test pins that, since it is the kind of thing that breaks silently.
@bp.route("/api/players/stats/<player>", methods=["GET"])
@server.require_permission("players.view")
def get_player_stats(player):
    """One player's statistics, by name"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    found = server.player_stats.find_by_name(player)

    if found is None:
        return jsonify({"error": "Player not found"}), 404

    include_raw = request.args.get("raw", "").lower() in ("1", "true", "yes")
    return jsonify({"success": True, "player": found.name, "stats": found.as_dict(include_raw)}), 200
