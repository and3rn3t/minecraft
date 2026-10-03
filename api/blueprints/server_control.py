"""Server lifecycle: status, start/stop/restart, and one-off RCON commands."""

import subprocess
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from api import auth_guard, server

bp = Blueprint("server_control", __name__)


@bp.route("/api/status", methods=["GET"])
@auth_guard.require_permission("server.view")
def get_status():
    """Get server status"""
    # Check if server is running. The filter is anchored (^...$) so a
    # container merely named similarly (e.g. "minecraft-server-test") can't
    # match -- the same exact-name check scripts/lib/common.sh's
    # container_running() makes for every other caller.
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=^minecraft-server$", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        is_running = "Up" in result.stdout if result.returncode == 0 else False
        status_text = result.stdout if result.returncode == 0 else "Unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        is_running = False
        status_text = "Unable to check status"

    return jsonify({"running": is_running, "status": status_text, "timestamp": datetime.now(timezone.utc).isoformat()})


@bp.route("/api/server/start", methods=["POST"])
@auth_guard.require_permission("server.control")
def start_server():
    """Start the server"""
    username = auth_guard.get_username_from_request()
    server.log_audit_event(username, "server.start", {"action": "start_server"})

    stdout, stderr, code = server.run_script("manage.sh", "start", timeout=server.LONG_SCRIPT_TIMEOUT)

    if code == 0:
        return jsonify({"success": True, "message": "Server starting", "output": stdout}), 200
    return server.script_error(stderr, "Failed to start server", include_success_flag=True)


@bp.route("/api/server/stop", methods=["POST"])
@auth_guard.require_permission("server.control")
def stop_server():
    """Stop the server"""
    stdout, stderr, code = server.run_script("manage.sh", "stop", timeout=server.LONG_SCRIPT_TIMEOUT)

    if code == 0:
        return jsonify({"success": True, "message": "Server stopping", "output": stdout}), 200
    return server.script_error(stderr, "Failed to stop server", include_success_flag=True)


@bp.route("/api/server/restart", methods=["POST"])
@auth_guard.require_permission("server.control")
def restart_server():
    """Restart the server"""
    stdout, stderr, code = server.run_script("manage.sh", "restart", timeout=server.LONG_SCRIPT_TIMEOUT)

    if code == 0:
        return jsonify({"success": True, "message": "Server restarting", "output": stdout}), 200
    return server.script_error(stderr, "Failed to restart server", include_success_flag=True)


@bp.route("/api/server/command", methods=["POST"])
@auth_guard.require_permission("server.command")
@server.auth_rate_limit("30/minute")
def send_command():
    """Send a command to the server via RCON"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    command = data.get("command")
    if not command:
        return jsonify({"error": "Command required"}), 400
    if not isinstance(command, str):
        # The sanitizer calls string methods, so a JSON number or object would
        # raise inside it and surface as a 500 rather than a bad request.
        return jsonify({"error": "Command must be a string"}), 400

    # Validate and sanitize command to prevent command injection
    is_valid, sanitized_command, error_msg = server.sanitize_minecraft_command(command)
    if not is_valid:
        server.log_audit_event(
            auth_guard.get_username_from_request(),
            "server.command.rejected",
            {"original_command": server.sanitize_string(command[:100]), "reason": error_msg},
        )
        return jsonify({"error": "Invalid command format"}), 400
    command = sanitized_command

    username = auth_guard.get_username_from_request()
    server.log_audit_event(username, "server.command", {"command": server.sanitize_string(command[:100])})

    stdout, stderr, code = server.run_rcon_command(command)

    if code == 0:
        # Sanitize response before returning
        safe_stdout = server.sanitize_string(stdout, max_length=5000) if stdout else stdout
        return jsonify({"success": True, "response": safe_stdout, "command": server.sanitize_string(command[:100])}), 200
    else:
        # Don't expose detailed error messages - generic error only
        error_msg = "Command execution failed"
        if stderr:
            # Only log detailed error, don't expose to client
            safe_stderr = server.sanitize_string(stderr[:500])
            server.log_audit_event(username, "server.command.failed", {"error": safe_stderr[:100]})
        return jsonify({"success": False, "error": error_msg}), 500
