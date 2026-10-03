"""Bedtime mode and Oracle routes.

Both are small, self-contained game features with an on/off switch and their
own settings; grouped together as the first blueprint extracted out of
server.py because neither has dependents elsewhere.

Every shared helper, flag and feature module below is reached through the
`server` module object (`server.run_script(...)`, not a bare `run_script`
imported by name) rather than imported directly by name: the test suite
extensively does `patch("api.server.some_name", ...)`, which rebinds that
name in api.server's own namespace. A name copied into this module at import
time would keep pointing at the pre-patch original, so tests patching it
would silently patch a reference nothing here still uses.
"""

from flask import Blueprint, jsonify, request

from api import auth_guard, server
from api.security import sanitize_string

bp = Blueprint("oracle", __name__)


@bp.route("/api/bedtime", methods=["GET"])
@auth_guard.require_permission("server.view")
def get_bedtime_status():
    """Current bedtime status: when it is, how long is left, whether it holds."""
    if not server.BEDTIME_AVAILABLE:
        return jsonify({"error": "Bedtime mode is unavailable"}), 503

    return jsonify(server.bedtime_mode.get_bedtime().status())


def _bedtime_control(operation):
    """Shared plumbing for the three bedtime controls.

    Each returns (ok, message); a refusal is a 409 because the request was
    well-formed and the server simply will not do it right now.
    """
    if not server.BEDTIME_AVAILABLE:
        return jsonify({"error": "Bedtime mode is unavailable"}), 503

    ok, message = operation(server.bedtime_mode.get_bedtime())

    server.log_audit_event(
        auth_guard.get_username_from_request(), "bedtime.control", {"result": sanitize_string(message[:100])}
    )
    if not ok:
        return jsonify({"success": False, "error": message}), 409
    return jsonify({"success": True, "message": message, "status": server.bedtime_mode.get_bedtime().status()})


@bp.route("/api/bedtime/extend", methods=["POST"])
@auth_guard.require_permission("server.control")
def extend_bedtime():
    """Grant "five more minutes", within the configured limit."""
    return _bedtime_control(lambda bed: bed.extend())


@bp.route("/api/bedtime/skip", methods=["POST"])
@auth_guard.require_permission("server.control")
def skip_bedtime():
    """Cancel bedtime for tonight only."""
    return _bedtime_control(lambda bed: bed.skip_tonight())


@bp.route("/api/bedtime/now", methods=["POST"])
@auth_guard.require_permission("server.control")
def start_bedtime_now():
    """Bring bedtime forward to right now."""
    return _bedtime_control(lambda bed: bed.start_now())


@bp.route("/api/oracle", methods=["GET"])
@auth_guard.require_permission("oracle.view")
def get_oracle_status():
    """Whether the Oracle is on, its settings, and whether it has an API key."""
    if not server.ORACLE_AVAILABLE:
        return jsonify({"error": "The Oracle is unavailable"}), 503

    return jsonify(server.oracle.get_oracle().status())


@bp.route("/api/oracle/exchanges", methods=["GET"])
@auth_guard.require_permission("oracle.view")
def get_oracle_exchanges():
    """Recent chat messages the Oracle has triaged, newest first."""
    if not server.ORACLE_AVAILABLE:
        return jsonify({"error": "The Oracle is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    return jsonify(server.oracle.get_oracle().read_exchanges(limit=limit))


@bp.route("/api/oracle/quests", methods=["GET"])
@auth_guard.require_permission("oracle.view")
def get_oracle_quests():
    """Recently generated quests, newest first."""
    if not server.ORACLE_AVAILABLE:
        return jsonify({"error": "The Oracle is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    return jsonify(server.oracle.get_oracle().read_quests(limit=limit))


def _oracle_set_enabled(enabled):
    if not server.ORACLE_AVAILABLE:
        return jsonify({"error": "The Oracle is unavailable"}), 503

    orc = server.oracle.get_oracle()
    orc.set_enabled(enabled)

    server.log_audit_event(
        auth_guard.get_username_from_request(), "oracle.enabled" if enabled else "oracle.disabled", {}
    )
    return jsonify({"success": True, "status": orc.status()})


@bp.route("/api/oracle/enable", methods=["PUT"])
@auth_guard.require_permission("oracle.manage")
def enable_oracle():
    """Turn the Oracle on."""
    return _oracle_set_enabled(True)


@bp.route("/api/oracle/disable", methods=["PUT"])
@auth_guard.require_permission("oracle.manage")
def disable_oracle():
    """Turn the Oracle off -- the kill switch."""
    return _oracle_set_enabled(False)


@bp.route("/api/oracle/settings", methods=["PUT"])
@auth_guard.require_permission("oracle.manage")
def update_oracle_settings():
    """Edit the allowlist and/or the per-player rate limit."""
    if not server.ORACLE_AVAILABLE:
        return jsonify({"error": "The Oracle is unavailable"}), 503

    data = request.get_json(silent=True) or {}
    allowlist = None
    rate_limit_per_minute = None

    if "allowlist" in data:
        raw = data["allowlist"]
        if not isinstance(raw, list) or not all(isinstance(name, str) for name in raw):
            return jsonify({"error": "allowlist must be a list of usernames"}), 400
        invalid = [name for name in raw if not server.oracle.MINECRAFT_USERNAME_RE.match(name)]
        if invalid:
            return jsonify({"error": f"Invalid usernames: {', '.join(invalid)}"}), 400
        allowlist = raw

    if "rate_limit_per_minute" in data:
        try:
            rate_limit_per_minute = int(data["rate_limit_per_minute"])
        except (TypeError, ValueError):
            return jsonify({"error": "rate_limit_per_minute must be an integer"}), 400
        if not 1 <= rate_limit_per_minute <= 60:
            return jsonify({"error": "rate_limit_per_minute must be between 1 and 60"}), 400

    orc = server.oracle.get_oracle()
    orc.update_settings(allowlist=allowlist, rate_limit_per_minute=rate_limit_per_minute)

    server.log_audit_event(
        auth_guard.get_username_from_request(),
        "oracle.settings",
        {"allowlist": allowlist, "rate_limit_per_minute": rate_limit_per_minute},
    )
    return jsonify({"success": True, "status": orc.status()})
