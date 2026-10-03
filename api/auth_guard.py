"""Authentication and authorisation for requests: who is calling, and may they.

``require_auth`` and ``require_permission`` are the decorators every protected
route uses. The accounts and API keys they check (``USERS``, ``API_KEYS``) live
on ``api.server``, where the tests patch them, and are read through it at call
time so a patched value is the one used here.
"""

import secrets
from functools import wraps

from flask import jsonify, request, session

from api import rbac


def get_username_from_request():
    """Get username from request (API key, session, or token)"""
    # Check API key. Header only -- see the matching comment in require_auth.
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key in server.API_KEYS:
        return f"api_key:{server.API_KEYS[api_key].get('name', 'unknown')}"

    # Check session
    if "username" in session:
        return session.get("username")

    # Check JWT token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        username = auth_crypto.verify_token(token)
        if username:
            return username

    return "unknown"


def get_user_permissions(username):
    """Get list of permissions for a user based on their role"""
    if username == "__api_key__":
        return rbac.get_api_key_permissions(getattr(request, "api_key_info", {}))
    if username not in server.USERS:
        return []
    user_role = server.USERS[username].get("role", "user")
    return rbac.ROLE_PERMISSIONS.get(user_role, rbac.ROLE_PERMISSIONS["user"])


def has_permission(username, permission):
    """Check if user has a specific permission"""
    # API keys are scoped by their own role, not by the caller's. This used to
    # return True unconditionally, which made every key a full admin
    # credential regardless of what it was created for.
    if username == "__api_key__":
        key_info = getattr(request, "api_key_info", {})
        # An admin-scoped key matches an admin user, which is what the check
        # just below does. Without this, an admin key is refused any permission
        # missing from rbac.PERMISSIONS while an admin user sails through — the
        # asymmetry that locked admin keys out of the server.manage endpoints.
        # A key carrying an explicit allowlist is held to that list instead.
        if key_info.get("permissions") is None and key_info.get("role") == "admin":
            return True
        return permission in rbac.get_api_key_permissions(key_info)
    if username not in server.USERS:
        return False
    user_role = server.USERS[username].get("role", "user")
    # Admins have all permissions
    if user_role == "admin":
        return True
    user_permissions = rbac.ROLE_PERMISSIONS.get(user_role, rbac.ROLE_PERMISSIONS["user"])
    return permission in user_permissions


def require_permission(permission):
    """Decorator to require a specific permission"""

    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            username = getattr(request, "user", None)
            if not username:
                return jsonify({"error": "Authentication required"}), 401

            if not has_permission(username, permission):
                return (
                    jsonify(
                        {
                            "error": "Permission denied",
                            "required_permission": permission,
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def issue_csrf_token():
    """Generate a fresh CSRF token, store it in the session, and return it.

    Call this everywhere a session cookie gets created (login, register,
    OAuth callbacks) so the response can hand the token to the client for it
    to echo back via X-CSRF-Token on later mutating requests.
    """
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return token


def _csrf_check_failed():
    """True if the current request is session-cookie-authenticated, mutating,
    and missing/wrong the CSRF token -- see require_auth's session branch.

    Only the session-cookie path needs this: a browser attaches cookies to a
    cross-site request automatically (that's the CSRF vector), but never
    attaches a custom header or an Authorization/X-API-Key value on its own,
    so the Bearer-JWT and API-key paths aren't exploitable the same way and
    don't need a token.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return False
    expected = session.get("csrf_token")
    provided = request.headers.get("X-CSRF-Token")
    return not expected or not provided or not secrets.compare_digest(expected, provided)


def _account_active(username):
    """True while the account behind a session or token may still be used."""
    user = server.USERS.get(username)
    return user is not None and user.get("enabled", True)


def require_auth(f):
    """Decorator to require user authentication (session, token, or API key)"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For OAuth routes, check provider validity first (if provider in args)
        # This allows provider validation errors to return 400 instead of 401
        if len(kwargs) > 0 and "provider" in kwargs:
            provider = kwargs["provider"]
            if provider not in ["google", "apple"]:
                return jsonify({"error": "Invalid OAuth provider"}), 400

        # Check API key first (for backward compatibility). Header only --
        # a key in the URL (?api_key=...) leaks into nginx access logs,
        # browser history, and any Referer header a follow-on request sends.
        api_key = request.headers.get("X-API-Key")
        if api_key:
            if api_key in server.API_KEYS and server.API_KEYS[api_key].get("enabled", True):
                key_info = server.API_KEYS[api_key]
                request.api_key_info = key_info
                request.user = "__api_key__"
                request.user_info = {
                    "username": "__api_key__",
                    "role": key_info.get("role", rbac.DEFAULT_API_KEY_ROLE),
                    "key_name": key_info.get("name", "unknown"),
                }
                return f(*args, **kwargs)
            else:
                # Deliberately the same answer for an unknown key and a
                # disabled one: telling them apart would confirm to someone
                # guessing keys that a disabled key exists.
                return jsonify({"error": "Invalid API key"}), 401

        # Check JWT token before the session cookie. The web panel is
        # same-origin behind nginx, so the browser attaches the session
        # cookie to every request automatically -- including ones where the
        # panel is deliberately authenticating with its Bearer token
        # instead. If the session branch were checked first, every such
        # request would be forced through the CSRF check below even though
        # a valid, non-forgeable Bearer credential was already presented,
        # which breaks every mutating panel action once a cookie exists
        # from the same login. A Bearer token can't be attached by a
        # cross-site page the way a cookie can, so trusting it here doesn't
        # weaken the CSRF protection the cookie path still needs.
        #
        # Both user branches re-check that the account still exists and is
        # enabled. Only password login used to: disabling or deleting a user
        # left their session cookie and bearer token working until expiry.
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            username = auth_crypto.verify_token(token)
            if username and _account_active(username):
                request.user = username
                request.user_info = server.USERS.get(username, {})
                return f(*args, **kwargs)

        # Check session
        if "username" in session:
            if not _account_active(session["username"]):
                session.pop("username", None)
                session.pop("csrf_token", None)
                return jsonify({"error": "Authentication required"}), 401
            if _csrf_check_failed():
                return jsonify({"error": "Missing or invalid CSRF token"}), 403
            request.user = session.get("username")
            request.user_info = server.USERS.get(session.get("username"), {})
            return f(*args, **kwargs)

        return jsonify({"error": "Authentication required"}), 401

    return decorated_function


# Imported last, on purpose. api.server imports this module, this module reads
# state from api.server, and the blueprints use the decorators above while
# api.server is still importing them. Both of these (auth_crypto also imports
# server) are only used inside the functions above, at call time, so loading
# them after every name here is defined keeps this module complete whichever
# module is imported first. At the top they fail with "partially initialized
# module" when this one is imported first.
from api import auth_crypto, server  # noqa: E402
