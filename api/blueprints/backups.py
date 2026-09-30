"""Backup create/list/restore/delete."""

import re
from datetime import datetime

from flask import Blueprint, jsonify

from api import server

bp = Blueprint("backups", __name__)


@bp.route("/api/backup", methods=["POST"])
@server.require_permission("backup.create")
def create_backup():
    """Create a server backup"""
    username = server.get_username_from_request()
    server.log_audit_event(username, "backup.create", {"action": "create_backup"})

    stdout, stderr, code = server.run_script("manage.sh", "backup", timeout=server.LONG_SCRIPT_TIMEOUT)

    if code == 0:
        return jsonify({"success": True, "message": "Backup created", "output": stdout}), 200
    return server.script_error(stderr, "Backup failed", include_success_flag=True)


@bp.route("/api/backups", methods=["GET"])
@server.require_permission("backup.view")
def list_backups():
    """List available backups"""
    backups_dir = server.PROJECT_ROOT / "backups"
    backups = []

    if backups_dir.exists():
        for backup_file in backups_dir.glob("minecraft_backup_*.tar.gz"):
            stat = backup_file.stat()
            backups.append(
                {
                    "name": backup_file.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(backup_file.relative_to(server.PROJECT_ROOT)),
                }
            )

    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x["created"], reverse=True)

    return jsonify({"backups": backups, "count": len(backups)})


@bp.route("/api/backups/<path:filename>/restore", methods=["POST"])
@server.require_permission("backup.restore")
def restore_backup(filename):
    """Restore a backup"""
    username = server.get_username_from_request()
    server.log_audit_event(username, "backup.restore", {"filename": filename})

    # Check for path traversal attacks first
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid backup filename"}), 400

    backups_dir = server.PROJECT_ROOT / "backups"
    backup_path = backups_dir / filename

    # Check if file exists first (404 takes precedence over format validation)
    if not backup_path.exists():
        return jsonify({"error": "Backup not found"}), 404

    # Validate backup file format
    if not filename.startswith("minecraft_backup_") or not filename.endswith(".tar.gz"):
        return jsonify({"error": "Invalid backup file format"}), 400

    # Delegate to manage.sh restore: it takes the same update lock
    # deploy-agent.sh/auto-update.sh hold, stops the server, moves the
    # existing ./data aside (never deletes it), extracts, restarts, and
    # fails loudly if the world doesn't come back up cleanly -- a second,
    # less careful implementation living here too previously extracted
    # in place and tarred the old data, a materially different (and worse)
    # safety model for the same operation. The confirmation prompt it reads
    # from stdin is auto-accepted, since the permission check above already
    # gates who can call this.
    stdout, stderr, code = server.run_script(
        "manage.sh", "restore", filename, input_text="y\n", timeout=server.LONG_SCRIPT_TIMEOUT
    )
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", stdout or "")

    # manage.sh exits 0 on a declined confirmation too ("Cancelled"); that
    # should never happen given the "y\n" above, but treat it as a failure
    # rather than reporting a restore that didn't actually happen.
    if code == 0 and "Cancelled" not in clean_output:
        pre_restore_backup = None
        match = re.search(r"Moving current data aside: ([^\x1b\s]+)", clean_output)
        if match:
            pre_restore_backup = match.group(1)
        return jsonify(
            {
                "success": True,
                "message": "Backup restored successfully",
                "pre_restore_backup": pre_restore_backup,
            }
        )
    else:
        clean_lines = [line for line in clean_output.strip().splitlines() if line]
        error = clean_lines[-1] if clean_lines else (stderr or "Failed to restore backup")
        return jsonify({"error": error}), 500


@bp.route("/api/backups/<path:filename>", methods=["DELETE"])
@server.require_permission("backup.delete")
def delete_backup(filename):
    """Delete a backup"""
    # Check for path traversal attacks first
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid backup filename"}), 400

    backups_dir = server.PROJECT_ROOT / "backups"
    backup_path = backups_dir / filename

    # Check if file exists first (404 takes precedence over format validation)
    if not backup_path.exists():
        return jsonify({"error": "Backup not found"}), 404

    # Validate backup file format
    if not filename.startswith("minecraft_backup_") or not filename.endswith(".tar.gz"):
        return jsonify({"error": "Invalid backup file format"}), 400

    backup_path.unlink()
    return jsonify({"success": True, "message": "Backup deleted successfully"})
