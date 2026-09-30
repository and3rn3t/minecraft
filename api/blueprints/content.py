"""Worlds, plugins and datapacks: read-mostly content management routes that
all shell out to a scripts/*-manager.sh --list-json and pass the result
through.
"""

import json
import os
import re
import tempfile

from flask import Blueprint, jsonify, request

from api import server

bp = Blueprint("content", __name__)


@bp.route("/api/worlds", methods=["GET"])
@server.require_permission("worlds.view")
def list_worlds():
    """List all worlds"""
    stdout, _, _ = server.run_script("world-manager.sh", "list-json")

    try:
        worlds = json.loads(stdout) if stdout else []
    except (ValueError, TypeError):
        worlds = []

    return jsonify({"worlds": worlds, "count": len(worlds)})


@bp.route("/api/plugins", methods=["GET"])
@server.require_permission("plugins.view")
def list_plugins():
    """List installed plugins"""
    stdout, _, _ = server.run_script("plugin-manager.sh", "list-json")

    try:
        plugins = json.loads(stdout) if stdout else []
    except (ValueError, TypeError):
        plugins = []

    return jsonify({"plugins": plugins, "count": len(plugins)})


# Mirrors datapack-manager.sh's _validate_name(). Checking it here too means
# a bad name gets a clean 400 from the API instead of a generic 500 surfaced
# from the script's own exit code.
DATAPACK_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


@bp.route("/api/datapacks", methods=["GET"])
@server.require_permission("datapacks.view")
def list_datapacks():
    """List datapacks tracked under config/datapacks/, with enabled state for the current world"""
    stdout, _, _ = server.run_script("datapack-manager.sh", "list-json")

    try:
        datapacks = json.loads(stdout) if stdout else []
    except (ValueError, TypeError):
        datapacks = []

    return jsonify({"datapacks": datapacks, "count": len(datapacks)})


@bp.route("/api/datapacks/install", methods=["POST"])
@server.require_permission("datapacks.manage")
def install_datapack():
    """Install a datapack from a URL or an uploaded zip, then deploy and reload it"""
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "Datapack name required"}), 400
    if not DATAPACK_NAME_RE.match(name):
        return jsonify({"error": "Datapack name must contain only letters, numbers, and underscores"}), 400

    url = request.form.get("url", "").strip()
    upload = request.files.get("file")

    if not url and not upload:
        return jsonify({"error": "Provide either 'url' or a 'file' upload"}), 400
    if url and upload:
        return jsonify({"error": "Provide either 'url' or a 'file' upload, not both"}), 400

    tmp_path = None
    try:
        if upload is not None:
            if upload.filename == "":
                return jsonify({"error": "No file selected"}), 400
            fd, tmp_path = tempfile.mkstemp(suffix=".zip")
            os.close(fd)
            upload.save(tmp_path)
            stdout, stderr, code = server.run_script(
                "datapack-manager.sh",
                "install",
                name,
                "--file",
                tmp_path,
                "--yes",
                timeout=server.LONG_SCRIPT_TIMEOUT,
            )
        else:
            stdout, stderr, code = server.run_script(
                "datapack-manager.sh", "install", name, "--url", url, "--yes", timeout=server.LONG_SCRIPT_TIMEOUT
            )
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                # Best-effort cleanup of the uploaded temp file; the install
                # itself already succeeded or failed above, so a leftover
                # temp file here must not turn into a 500 of its own.
                pass

    if code != 0:
        return server.script_error(stderr or stdout, "Install failed")

    return jsonify({"success": True, "message": f"Datapack {name} installed and enabled", "output": stdout}), 200


@bp.route("/api/datapacks/<name>/enable", methods=["PUT"])
@server.require_permission("datapacks.manage")
def enable_datapack(name):
    """Deploy a tracked datapack into the current world and reload"""
    if not DATAPACK_NAME_RE.match(name):
        return jsonify({"error": "Datapack name must contain only letters, numbers, and underscores"}), 400
    stdout, stderr, code = server.run_script("datapack-manager.sh", "enable", name)
    if code != 0:
        return server.script_error(stderr or stdout, "Enable failed")
    return jsonify({"success": True, "message": f"Datapack {name} enabled"}), 200


@bp.route("/api/datapacks/<name>/disable", methods=["PUT"])
@server.require_permission("datapacks.manage")
def disable_datapack(name):
    """Remove a datapack from the current world and reload, keeping its tracked source"""
    if not DATAPACK_NAME_RE.match(name):
        return jsonify({"error": "Datapack name must contain only letters, numbers, and underscores"}), 400
    stdout, stderr, code = server.run_script("datapack-manager.sh", "disable", name)
    if code != 0:
        return server.script_error(stderr or stdout, "Disable failed")
    return jsonify({"success": True, "message": f"Datapack {name} disabled"}), 200


@bp.route("/api/datapacks/<name>", methods=["DELETE"])
@server.require_permission("datapacks.manage")
def delete_datapack(name):
    """Back up and delete a datapack's tracked source (config/datapacks/<name>)"""
    if not DATAPACK_NAME_RE.match(name):
        return jsonify({"error": "Datapack name must contain only letters, numbers, and underscores"}), 400
    stdout, stderr, code = server.run_script("datapack-manager.sh", "delete", name, "--yes")
    if code != 0:
        return server.script_error(stderr or stdout, "Delete failed")
    return jsonify({"success": True, "message": f"Datapack {name} deleted"}), 200
