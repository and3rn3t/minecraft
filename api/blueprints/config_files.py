"""Config file browser: list/get/save/validate for the small allow-listed set
of files the admin panel can edit (server.properties, docker-compose.yml,
...).

CONFIG_ALLOWED_PATHS stays on `server`. describe_yaml_error and
redact_config_secrets live in api.config_redaction, shared with
get_ddns_config (api.blueprints.ddns).
"""

from flask import Blueprint, jsonify, request

from api import auth_guard, config_redaction, server

bp = Blueprint("config_files", __name__)


@bp.route("/api/config/files", methods=["GET"])
@auth_guard.require_permission("config.view")
def list_config_files():
    """List available configuration files"""
    files = []
    for name, path in server.CONFIG_ALLOWED_PATHS.items():
        exists = path.exists() if path else False
        size = path.stat().st_size if exists and path.is_file() else 0
        files.append(
            {
                "name": name,
                "path": str(path.relative_to(server.PROJECT_ROOT)) if path else "",
                "exists": exists,
                "size": size,
            }
        )
    return jsonify({"files": files})


@bp.route("/api/config/files/<path:filename>", methods=["GET"])
@auth_guard.require_permission("config.view")
def get_config_file(filename):
    """Get configuration file content"""
    if filename not in server.CONFIG_ALLOWED_PATHS:
        return jsonify({"error": "File not allowed"}), 403

    file_path = server.CONFIG_ALLOWED_PATHS[filename]

    # Also check if server.properties exists at root as fallback
    if filename == "server.properties":
        if not file_path.exists():
            # Try root directory
            root_path = server.PROJECT_ROOT / "server.properties"
            if root_path.exists():
                file_path = root_path
            else:
                # Use data directory (will be created if needed)
                data_dir = server.PROJECT_ROOT / "data"
                if not data_dir.exists():
                    data_dir.mkdir(parents=True, exist_ok=True)
                file_path = data_dir / "server.properties"

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Only config.edit (admin) sees credentials: they are the ones who can
    # save, so a masked value can never be written back over a real one.
    redacted = False
    if not auth_guard.has_permission(request.user, "config.edit"):
        content, redacted = config_redaction.redact_config_secrets(content)
    return jsonify(
        {
            "name": filename,
            "path": str(file_path.relative_to(server.PROJECT_ROOT)),
            "content": content,
            "size": file_path.stat().st_size,
            "redacted": redacted,
        }
    )


@bp.route("/api/config/files/<path:filename>", methods=["POST"])
@auth_guard.require_permission("config.edit")
def save_config_file(filename):
    """Save configuration file with automatic backup"""
    if filename not in server.CONFIG_ALLOWED_PATHS:
        return jsonify({"error": "File not allowed"}), 403

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Content required"}), 400

    file_path = server.CONFIG_ALLOWED_PATHS[filename]

    # Also check if server.properties exists at root as fallback
    if filename == "server.properties":
        if not file_path.exists():
            # Try root directory
            root_path = server.PROJECT_ROOT / "server.properties"
            if root_path.exists():
                file_path = root_path
            else:
                # Create in data directory if it doesn't exist
                data_dir = server.PROJECT_ROOT / "data"
                if not data_dir.exists():
                    data_dir.mkdir(parents=True, exist_ok=True)
                file_path = data_dir / "server.properties"

    # Create backup before saving
    backup_dir = server.PROJECT_ROOT / "backups" / "config"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if file_path.exists():
        backup_path = backup_dir / f"{filename}.{server.datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
        try:
            import shutil

            shutil.copy2(file_path, backup_path)
        except Exception as e:
            server.app.logger.error(f"Failed to create backup: {e}")
            return jsonify({"error": "Internal server error"}), 500

    # Validate content (basic validation)
    content = data["content"]

    # Validate based on file type
    if filename.endswith(".properties"):
        # Basic properties file validation
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith("#") and "=" not in line:
                return (
                    jsonify(
                        {
                            "error": f"Invalid properties format at line {i}",
                            "line": i,
                        }
                    ),
                    400,
                )
    elif filename.endswith(".yml") or filename.endswith(".yaml"):
        # Basic YAML validation
        try:
            import yaml

            yaml.safe_load(content)
        except ImportError:
            pass  # YAML library not available, skip validation
        except yaml.YAMLError as e:
            # The caller needs to know where their YAML is wrong, so the line
            # and column are reported — but built from the parser's own fields
            # rather than str(e), which formats the surrounding context and is
            # a route for anything else in the exception to reach the response.
            return jsonify({"error": config_redaction.describe_yaml_error(e)}), 400

    # Save file
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return jsonify(
            {
                "success": True,
                "message": "File saved successfully",
                "backup": str(backup_path.relative_to(server.PROJECT_ROOT)) if backup_path else None,
            }
        )
    except Exception as e:
        # Restore from backup on failure
        if backup_path and backup_path.exists():
            try:
                import shutil

                shutil.copy2(backup_path, file_path)
            except Exception:
                pass  # Restore attempt is best-effort
        server.app.logger.error(f"Failed to save file: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/config/files/<path:filename>/validate", methods=["POST"])
@auth_guard.require_permission("config.edit")
def validate_config_file(filename):
    """Validate configuration file content"""
    if filename not in server.CONFIG_ALLOWED_PATHS:
        return jsonify({"error": "File not allowed"}), 403

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Content required"}), 400

    content = data["content"]
    errors = []
    warnings = []

    # Validate based on file type
    if filename.endswith(".properties"):
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith("#"):
                if "=" not in line_stripped:
                    errors.append(
                        {
                            "line": i,
                            "message": "Missing '=' separator",
                        }
                    )
    elif filename.endswith(".yml") or filename.endswith(".yaml"):
        try:
            import yaml

            yaml.safe_load(content)
        except ImportError:
            warnings.append({"message": "YAML validation unavailable"})
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            errors.append(
                {
                    "line": (mark.line + 1) if mark is not None else 0,
                    "message": config_redaction.describe_yaml_error(e),
                }
            )

    return jsonify(
        {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    )
