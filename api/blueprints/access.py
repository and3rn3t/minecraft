"""API key, user, permission and role management -- everything that reads or
writes API_KEYS/USERS.

All access to those two dicts goes through `server.API_KEYS`/`server.USERS`
attribute lookups rather than a name imported once at module load: tests
routinely do `monkeypatch.setattr(api_module, "API_KEYS", {...})` or
`patch("api.server.API_KEYS", ...)` to swap the whole dict out, which only
rebinds api.server's own attribute. A name copied into this module earlier
would keep pointing at the pre-patch dict.
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from api import server

bp = Blueprint("access", __name__)


@bp.route("/api/keys", methods=["GET"])
@server.require_permission("api_keys.view")
def list_api_keys():
    """List all API keys (without showing full key values)"""
    keys_list = []
    for key, info in server.API_KEYS.items():
        keys_list.append(
            {
                "id": key[:8] + "..." + key[-4:],  # Show preview only
                "name": info.get("name", "Unknown"),
                "description": info.get("description", ""),
                "enabled": info.get("enabled", True),
                "created": info.get("created", ""),
                "role": info.get("role", server.DEFAULT_API_KEY_ROLE),
                "permissions": server.get_api_key_permissions(info),
            }
        )
    return jsonify({"success": True, "keys": keys_list}), 200


@bp.route("/api/keys", methods=["POST"])
@server.require_permission("api_keys.manage")
def create_api_key():
    """Create a new API key"""
    data = request.get_json() or {}
    name = data.get("name")
    description = data.get("description", "")
    role = data.get("role", server.DEFAULT_API_KEY_ROLE)
    permissions = data.get("permissions")

    if not name:
        return jsonify({"error": "Key name is required"}), 400

    scope_error = server.validate_api_key_scope(role, permissions)
    if scope_error:
        return jsonify({"error": scope_error}), 400

    # Generate new API key
    api_key = server.generate_api_key()

    # Create key entry
    entry = {
        "name": name,
        "description": description,
        "enabled": True,
        "created": datetime.now(timezone.utc).isoformat(),
        "role": role,
    }
    if permissions is not None:
        entry["permissions"] = permissions
    server.API_KEYS[api_key] = entry

    if not server.save_api_keys():
        del server.API_KEYS[api_key]
        return jsonify({"error": "Failed to save API key"}), 500

    server.log_audit_event(
        server.get_username_from_request(),
        "api_keys.create",
        {"name": name, "role": role, "permissions": permissions},
    )

    return (
        jsonify(
            {
                "success": True,
                "key": api_key,  # Return full key only on creation
                "id": api_key[:8] + "..." + api_key[-4:],
                "name": name,
                "description": description,
                "role": role,
                "permissions": server.get_api_key_permissions(entry),
                "message": "API key created. Save this key securely - it will not be shown again.",
            }
        ),
        201,
    )


def _find_api_key(key_id):
    """Resolve the id shown by GET /api/keys back to the full key.

    The listing and the web UI use a preview -- the first 8 characters, an
    ellipsis, then the last 4 -- so that form has to resolve or every action
    taken from the API Keys page fails. Matching only a raw prefix or suffix
    meant it never did.

    An id that matches more than one key resolves to nothing rather than to
    whichever happened to come first in the dict.
    """
    if key_id in server.API_KEYS:
        return key_id

    if "..." in key_id:
        prefix, _, suffix = key_id.partition("...")
        matches = [k for k in server.API_KEYS if k.startswith(prefix) and k.endswith(suffix)]
    else:
        matches = [k for k in server.API_KEYS if k.startswith(key_id) or k.endswith(key_id)]

    return matches[0] if len(matches) == 1 else None


@bp.route("/api/keys/<key_id>", methods=["PUT"])
@server.require_permission("api_keys.manage")
def update_api_key_scope(key_id):
    """Narrow or widen what an API key may do."""
    try:
        key = _find_api_key(key_id)
        if not key:
            return jsonify({"error": "API key not found"}), 404

        data = request.get_json() or {}
        if "role" not in data and "permissions" not in data:
            return jsonify({"error": "role or permissions required"}), 400

        entry = server.API_KEYS[key]
        role = data.get("role", entry.get("role", server.DEFAULT_API_KEY_ROLE))
        permissions = data["permissions"] if "permissions" in data else entry.get("permissions")

        scope_error = server.validate_api_key_scope(role, permissions)
        if scope_error:
            return jsonify({"error": scope_error}), 400

        # Keep the old scope so a failed write can be undone. Otherwise the
        # request reports failure while this process keeps serving the new
        # scope, until a restart reloads the old one from disk.
        previous = dict(entry)

        entry["role"] = role
        if permissions is None:
            entry.pop("permissions", None)
        else:
            entry["permissions"] = permissions

        if not server.save_api_keys():
            server.API_KEYS[key] = previous
            return jsonify({"error": "Failed to save changes"}), 500

        server.log_audit_event(
            server.get_username_from_request(),
            "api_keys.scope",
            {"name": entry.get("name", "Unknown"), "role": role, "permissions": permissions},
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "API key scope updated",
                    "role": role,
                    "permissions": server.get_api_key_permissions(entry),
                }
            ),
            200,
        )
    except Exception as e:
        # The message is logged rather than returned: an exception raised while
        # re-scoping a credential can carry internals the caller should not see.
        server.app.logger.error(f"Failed to update API key scope: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/api/keys/<key_id>", methods=["DELETE"])
@server.require_permission("api_keys.manage")
def delete_api_key(key_id):
    """Delete an API key"""
    key_to_delete = _find_api_key(key_id)

    if not key_to_delete:
        return jsonify({"error": "API key not found"}), 404

    # Delete the key
    key_name = server.API_KEYS[key_to_delete].get("name", "Unknown")
    del server.API_KEYS[key_to_delete]

    if not server.save_api_keys():
        return jsonify({"error": "Failed to save changes"}), 500

    return jsonify({"success": True, "message": f"API key '{key_name}' deleted"}), 200


@bp.route("/api/keys/<key_id>/enable", methods=["PUT"])
@server.require_permission("api_keys.manage")
def enable_api_key(key_id):
    """Enable an API key"""
    key_to_enable = _find_api_key(key_id)

    if not key_to_enable:
        return jsonify({"error": "API key not found"}), 404

    was_enabled = server.API_KEYS[key_to_enable].get("enabled", True)
    server.API_KEYS[key_to_enable]["enabled"] = True

    if not server.save_api_keys():
        server.API_KEYS[key_to_enable]["enabled"] = was_enabled
        return jsonify({"error": "Failed to save changes"}), 500

    return jsonify({"success": True, "message": "API key enabled"}), 200


@bp.route("/api/keys/<key_id>/disable", methods=["PUT"])
@server.require_permission("api_keys.manage")
def disable_api_key(key_id):
    """Disable an API key"""
    key_to_disable = _find_api_key(key_id)

    if not key_to_disable:
        return jsonify({"error": "API key not found"}), 404

    was_enabled = server.API_KEYS[key_to_disable].get("enabled", True)
    server.API_KEYS[key_to_disable]["enabled"] = False

    if not server.save_api_keys():
        server.API_KEYS[key_to_disable]["enabled"] = was_enabled
        return jsonify({"error": "Failed to save changes"}), 500

    return jsonify({"success": True, "message": "API key disabled"}), 200


@bp.route("/api/users", methods=["GET"])
@server.require_permission("users.view")
def list_users():
    """List all users (without sensitive information)"""
    users_list = []
    for username, user_info in server.USERS.items():
        users_list.append(
            {
                "username": username,
                "role": user_info.get("role", "user"),
                "email": user_info.get("email", ""),
                "enabled": user_info.get("enabled", True),
                "created": user_info.get("created", ""),
            }
        )
    return jsonify({"success": True, "users": users_list}), 200


@bp.route("/api/users", methods=["POST"])
@server.require_permission("users.manage")
def create_user():
    """Create a user. This is how accounts are added once registration closes."""
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if not server.BCRYPT_AVAILABLE:
        return jsonify({"error": "Password hashing not available"}), 500

    if len(username) < 3 or len(username) > 32:
        return jsonify({"error": "Username must be 3-32 characters"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    if role not in server.ROLE_PERMISSIONS:
        return (
            jsonify({"error": f"Invalid role. Valid roles: {', '.join(server.ROLE_PERMISSIONS.keys())}"}),
            400,
        )

    hashed_password = server.hash_password(password)

    with server._users_lock:
        if username in server.USERS:
            return jsonify({"error": "Username already exists"}), 400

        server.USERS[username] = {
            "username": username,
            "password_hash": hashed_password,
            "email": email,
            "role": role,
            "enabled": True,
            "created": datetime.now(timezone.utc).isoformat(),
        }

        if not server.save_users():
            del server.USERS[username]
            return jsonify({"error": "Failed to save user"}), 500

    server.log_audit_event(server.get_username_from_request(), "users.create", {"username": username, "role": role})

    return (
        jsonify(
            {
                "success": True,
                "message": "User created",
                "user": {"username": username, "role": role},
            }
        ),
        201,
    )


def _is_last_enabled_admin(username):
    """True when removing this account's admin access would leave none.

    Only an enabled admin counts, on both sides: counting the target along
    with everyone else refused to delete, demote or disable a *disabled*
    admin whenever exactly one other admin was active.
    """
    user = server.USERS.get(username, {})
    if user.get("role") != "admin" or not user.get("enabled", True):
        return False
    return not any(
        u.get("role") == "admin" and u.get("enabled", True) for name, u in server.USERS.items() if name != username
    )


@bp.route("/api/users/<username>/role", methods=["PUT"])
@server.require_permission("users.manage")
def update_user_role(username):
    """Update a user's role"""
    data = request.get_json() or {}
    new_role = data.get("role")

    if not new_role:
        return jsonify({"error": "Role is required"}), 400

    # Validate role
    if new_role not in server.ROLE_PERMISSIONS:
        return (
            jsonify({"error": f"Invalid role. Valid roles: {', '.join(server.ROLE_PERMISSIONS.keys())}"}),
            400,
        )

    with server._users_lock:
        if username not in server.USERS:
            return jsonify({"error": "User not found"}), 404

        # Prevent removing the last admin
        if new_role != "admin" and _is_last_enabled_admin(username):
            return (
                jsonify({"error": "Cannot remove the last admin. At least one admin user must exist."}),
                400,
            )

        old_role = server.USERS[username].get("role")
        server.USERS[username]["role"] = new_role

        if not server.save_users():
            server.USERS[username]["role"] = old_role
            return jsonify({"error": "Failed to save changes"}), 500

    return (
        jsonify(
            {
                "success": True,
                "message": f"User role updated to {new_role}",
                "user": {"username": username, "role": new_role},
            }
        ),
        200,
    )


@bp.route("/api/users/<username>", methods=["DELETE"])
@server.require_permission("users.manage")
def delete_user(username):
    """Delete a user"""
    # Prevent users from deleting themselves
    current_user = getattr(request, "user", None)
    with server._users_lock:
        if username not in server.USERS:
            return jsonify({"error": "User not found"}), 404

        # Prevent deleting the last admin
        if _is_last_enabled_admin(username):
            return (
                jsonify({"error": "Cannot delete the last admin. At least one admin user must exist."}),
                400,
            )

        if current_user == username:
            return jsonify({"error": "Cannot delete your own account"}), 400

        removed = server.USERS.pop(username)

        if not server.save_users():
            # Otherwise the account is gone until the next restart reloads it
            server.USERS[username] = removed
            return jsonify({"error": "Failed to save changes"}), 500

    return jsonify({"success": True, "message": f"User '{username}' deleted"}), 200


@bp.route("/api/users/<username>/enable", methods=["PUT"])
@server.require_permission("users.manage")
def enable_user(username):
    """Enable a user account"""
    if username not in server.USERS:
        return jsonify({"error": "User not found"}), 404

    was_enabled = server.USERS[username].get("enabled", True)
    server.USERS[username]["enabled"] = True

    if not server.save_users():
        server.USERS[username]["enabled"] = was_enabled
        return jsonify({"error": "Failed to save changes"}), 500

    return jsonify({"success": True, "message": "User enabled"}), 200


@bp.route("/api/users/<username>/disable", methods=["PUT"])
@server.require_permission("users.manage")
def disable_user(username):
    """Disable a user account"""
    with server._users_lock:
        if username not in server.USERS:
            return jsonify({"error": "User not found"}), 404

        # Prevent disabling the last admin
        if _is_last_enabled_admin(username):
            return (
                jsonify({"error": "Cannot disable the last admin. At least one admin user must exist."}),
                400,
            )

        was_enabled = server.USERS[username].get("enabled", True)
        server.USERS[username]["enabled"] = False

        if not server.save_users():
            server.USERS[username]["enabled"] = was_enabled
            return jsonify({"error": "Failed to save changes"}), 500

    return jsonify({"success": True, "message": "User disabled"}), 200


@bp.route("/api/permissions", methods=["GET"])
@server.require_auth
def get_permissions():
    """Get current user's permissions"""
    username = getattr(request, "user", None)
    if not username:
        return jsonify({"error": "Authentication required"}), 401

    user_permissions = server.get_user_permissions(username)
    user_role = server.USERS.get(username, {}).get("role", "user")

    return (
        jsonify(
            {
                "success": True,
                "permissions": user_permissions,
                "role": user_role,
                "all_permissions": server.PERMISSIONS,
                "role_permissions": server.ROLE_PERMISSIONS,
            }
        ),
        200,
    )


@bp.route("/api/roles", methods=["GET"])
@server.require_permission("users.view")
def list_roles():
    """List all available roles and their permissions"""
    roles_info = {}
    for role, permissions in server.ROLE_PERMISSIONS.items():
        roles_info[role] = {
            "permissions": permissions,
            "permission_count": len(permissions),
        }
    return jsonify({"success": True, "roles": roles_info}), 200
