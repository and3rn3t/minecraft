"""The file browser: list/read/write/delete/upload/download within the
allow-listed roots.

ALLOWED_FILE_PATHS stays defined on `server` (with PROJECT_ROOT) rather than
moving here: it is monkeypatched directly (`setattr(api_module,
"ALLOWED_FILE_PATHS", ...)`) in tests/api/test_file_browser.py and
test_file_access.py, which requires the attribute to already exist on
api.server. The checks themselves live in api.paths
(_within_allowed_roots, is_path_allowed, resolve_allowed_path) and read it
from there at call time.

CodeQL does not carry the sanitizer's effect across the module boundary: the
routes here, calling api.paths.resolve_allowed_path(...), are not credited
with the check (see the py/path-injection entries in .codeql-triage.yaml).
The routes are still attacked directly by tests/api/test_path_traversal.py,
which is what actually guards this.
"""

import os
import shutil
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from api import auth_guard, paths, server

bp = Blueprint("files", __name__)


@bp.route("/api/files/list", methods=["GET"])
@auth_guard.require_permission("files.view")
def list_files():
    """List files and directories in a given path"""
    path_param = request.args.get("path", "")
    if not path_param:
        # List allowed root directories
        roots = []
        for allowed_path in server.ALLOWED_FILE_PATHS:
            if allowed_path.exists():
                roots.append(
                    {
                        "name": allowed_path.name,
                        "path": str(allowed_path.relative_to(server.PROJECT_ROOT)),
                        "type": "directory",
                        "size": 0,
                    }
                )
        return jsonify({"success": True, "files": roots, "path": ""}), 200

    # Resolve path (canonicalises .., resolves symlinks — required before any FS operation)
    file_path, refusal = paths.resolve_allowed_path(path_param)
    if refusal:
        return refusal

    if not file_path.exists():
        return jsonify({"error": "Path not found"}), 404

    if not file_path.is_dir():
        return jsonify({"error": "Path is not a directory"}), 400

    # List directory contents
    files = []
    try:
        for item in file_path.iterdir():
            try:
                stat = item.stat()
                files.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(server.PROJECT_ROOT)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            except (OSError, PermissionError):
                continue

        # Sort: directories first, then files, both alphabetically
        files.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))

        return (
            jsonify(
                {
                    "success": True,
                    "files": files,
                    "path": str(file_path.relative_to(server.PROJECT_ROOT)),
                }
            ),
            200,
        )
    except PermissionError:
        return jsonify({"error": "Permission denied"}), 403


@bp.route("/api/files/read", methods=["GET"])
@auth_guard.require_permission("files.view")
def read_file():
    """Read file content"""
    path_param = request.args.get("path", "")
    if not path_param:
        return jsonify({"error": "Path required"}), 400

    file_path, refusal = paths.resolve_allowed_path(path_param)
    if refusal:
        return refusal

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    if not file_path.is_file():
        return jsonify({"error": "Path is not a file"}), 400

    # Check file size (limit to 1MB for safety)
    if file_path.stat().st_size > 1024 * 1024:
        return jsonify({"error": "File too large (max 1MB)"}), 400

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return (
            jsonify(
                {
                    "success": True,
                    "content": content,
                    "path": str(file_path.relative_to(server.PROJECT_ROOT)),
                    "size": file_path.stat().st_size,
                }
            ),
            200,
        )
    except UnicodeDecodeError:
        return jsonify({"error": "File is not a text file"}), 400


@bp.route("/api/files/write", methods=["POST"])
@auth_guard.require_permission("config.edit")
def write_file():
    """Write file content"""
    data = request.get_json() or {}
    path_param = data.get("path", "")
    content = data.get("content", "")

    if not path_param:
        return jsonify({"error": "Path required"}), 400

    file_path, refusal = paths.resolve_allowed_path(path_param)
    if refusal:
        return refusal

    # Create backup if file exists
    backup_path = None
    if file_path.exists():
        backup_dir = server.PROJECT_ROOT / "backups" / "file-edits"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{file_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
        try:
            shutil.copy2(file_path, backup_path)
        except Exception:
            pass  # Backup copy is optional; failure is non-fatal

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "File saved successfully",
                    "path": str(file_path.relative_to(server.PROJECT_ROOT)),
                    "backup": (
                        str(backup_path.relative_to(server.PROJECT_ROOT))
                        if backup_path and backup_path.exists()
                        else None
                    ),
                }
            ),
            200,
        )
    except Exception as e:
        # Restore from backup on failure
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, file_path)
            except Exception:
                pass  # Restore attempt is best-effort
        server.app.logger.error(f"Failed to write file: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/files/delete", methods=["DELETE"])
@auth_guard.require_permission("config.edit")
def delete_file():
    """Delete a file or directory"""
    path_param = request.args.get("path", "")
    if not path_param:
        return jsonify({"error": "Path required"}), 400

    file_path, refusal = paths.resolve_allowed_path(path_param)
    if refusal:
        return refusal

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    # The allowed roots themselves are never deleted. Compared as resolved
    # paths: matching by name left backups/ deletable (it was not in the
    # list) and refused any folder merely named "config", such as a
    # plugin's own config folder under data/.
    roots = {os.path.realpath(str(root)) for root in server.ALLOWED_FILE_PATHS}
    if str(file_path) in roots:
        return jsonify({"error": "Cannot delete critical directory"}), 403

    if file_path.is_dir():
        shutil.rmtree(file_path)
    else:
        file_path.unlink()
    return jsonify({"success": True, "message": "File deleted successfully"}), 200


@bp.route("/api/files/upload", methods=["POST"])
@auth_guard.require_permission("config.edit")
def upload_file():
    """Upload a file"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    path_param = request.form.get("path", "")

    if not path_param:
        return jsonify({"error": "Path required"}), 400

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Check file size (limit to 10MB)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset
    if file_size > 10 * 1024 * 1024:
        return jsonify({"error": "File too large (max 10MB)"}), 400

    safe_name = secure_filename(file.filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400
    file_path, refusal = paths.resolve_allowed_path(str(server.Path(path_param) / safe_name))
    if refusal:
        return refusal

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file
    file.save(str(file_path))

    return (
        jsonify(
            {
                "success": True,
                "message": "File uploaded successfully",
                "path": str(file_path.relative_to(server.PROJECT_ROOT)),
            }
        ),
        200,
    )


@bp.route("/api/files/download", methods=["GET"])
@auth_guard.require_permission("files.view")
def download_file():
    """Download a file"""
    path_param = request.args.get("path", "")
    if not path_param:
        return jsonify({"error": "Path required"}), 400

    file_path, refusal = paths.resolve_allowed_path(path_param)
    if refusal:
        return refusal

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    if not file_path.is_file():
        return jsonify({"error": "Path is not a file"}), 400

    return send_file(str(file_path), as_attachment=True)
