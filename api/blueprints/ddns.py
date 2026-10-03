"""Dynamic DNS: status/update trigger and the ddns.conf viewer/editor.

DDNS_CONFIG_FILE and DDNS_SCRIPT stay on `server`, not module constants here,
in case anything else ever needs the same path (matches the CONFIG_ALLOWED_PATHS
pattern in api.blueprints.config_files).
"""

import os
import shutil
import subprocess
from datetime import datetime

from flask import Blueprint, jsonify, request

from api import config_redaction, server

bp = Blueprint("ddns", __name__)


@bp.route("/api/ddns/status", methods=["GET"])
@server.require_permission("settings.view")
def get_ddns_status():
    """Get DDNS configuration status and current IP"""
    # Run status command
    result = subprocess.run(
        [str(server.DDNS_SCRIPT), "status"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(server.PROJECT_ROOT),
    )

    if result.returncode == 0:
        # Parse status output
        status_output = result.stdout
        return jsonify({"success": True, "status": status_output}), 200
    else:
        return jsonify({"success": False, "error": result.stderr or "Failed to get status"}), 500


@bp.route("/api/ddns/update", methods=["POST"])
@server.require_permission("settings.edit")
def update_ddns():
    """Manually trigger DDNS update"""
    try:
        result = subprocess.run(
            [str(server.DDNS_SCRIPT), "update"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(server.PROJECT_ROOT),
        )

        if result.returncode == 0:
            return jsonify({"success": True, "message": "DDNS updated successfully", "output": result.stdout}), 200
        else:
            return jsonify({"success": False, "error": result.stderr or "DDNS update failed"}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "DDNS update timed out"}), 504
    except Exception as e:
        server.app.logger.error(f"Failed to update DDNS: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/ddns/config", methods=["GET"])
@server.require_permission("config.view")
def get_ddns_config():
    """Get DDNS configuration file content"""
    config_file = server.DDNS_CONFIG_FILE
    if not config_file.exists():
        # Return example config
        example_file = server.PROJECT_ROOT / "config" / "ddns.conf.example"
        if example_file.exists():
            content = example_file.read_text()
            return jsonify({"content": content, "is_example": True}), 200
        return jsonify({"error": "DDNS configuration not found"}), 404

    content = config_file.read_text()
    # ddns.conf holds the Cloudflare token and the No-IP and DuckDNS
    # credentials; mask them exactly as the config-file viewer does.
    redacted = False
    if not server.has_permission(request.user, "config.edit"):
        content, redacted = config_redaction.redact_config_secrets(content)
    return jsonify({"content": content, "is_example": False, "redacted": redacted}), 200


@bp.route("/api/ddns/config", methods=["POST"])
@server.require_permission("config.edit")
def save_ddns_config():
    """Save DDNS configuration file"""
    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Content required"}), 400

    content = data["content"]
    config_file = server.DDNS_CONFIG_FILE

    # Create backup if file exists
    backup_path = None
    if config_file.exists():
        backup_path = config_file.with_suffix(f".conf.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(config_file, backup_path)

    # Write new content
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(content)

    # Set restrictive permissions (600)
    os.chmod(config_file, 0o600)

    return jsonify(
        {
            "success": True,
            "message": "DDNS configuration saved successfully",
            "backup": str(backup_path.relative_to(server.PROJECT_ROOT)) if backup_path and backup_path.exists() else None,
        }
    )
