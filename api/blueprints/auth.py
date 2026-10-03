"""Authentication: register/login/logout, 2FA, session/CSRF, and OAuth
(Google + Apple).

Every shared helper, flag and dict below is reached through its module object
rather than imported by name: `server` (USERS, ...), `auth_guard`
(require_auth, CSRF) and `auth_crypto` (password/JWT/TOTP): the test suite
extensively does `patch("api.server.some_name", ...)` or
`monkeypatch.setattr(api_module, "some_name", ...)`, which rebinds that name
in the module's own namespace. A name copied into this module at import time
would keep pointing at the pre-patch original.
"""

import secrets
import urllib.parse
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, request, session

from api import auth_crypto, auth_guard, server

bp = Blueprint("auth", __name__)


@bp.route("/api/auth/register", methods=["POST"])
@server.auth_rate_limit("10/hour")
def register():
    """Register a new user"""
    if server.USERS and not server.REGISTRATION_ENABLED:
        return (
            jsonify({"error": "Registration is closed. Ask an administrator to create your account."}),
            403,
        )

    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if not auth_crypto.BCRYPT_AVAILABLE:
        return jsonify({"error": "Password hashing not available"}), 500

    # Validate username
    if len(username) < 3 or len(username) > 32:
        return jsonify({"error": "Username must be 3-32 characters"}), 400

    # Validate password
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    hashed_password = auth_crypto.hash_password(password)

    # Held across the whole decide-role-and-insert sequence: two registrations
    # arriving together could otherwise both find USERS empty and both be
    # granted the bootstrap admin role, which is the defect this guards.
    with server._users_lock:
        # Re-checked under the lock, in the same order as the fast path above:
        # the check there is only there to avoid hashing a password for a
        # request that is going to be refused anyway.
        if server.USERS and not server.REGISTRATION_ENABLED:
            return (
                jsonify({"error": "Registration is closed. Ask an administrator to create your account."}),
                403,
            )

        if username in server.USERS:
            return jsonify({"error": "Username already exists"}), 400

        # The first account bootstraps the server and has to be an admin; every
        # later one starts with no privileges and is promoted by an admin
        # through /api/users/<username>/role.
        role = "admin" if not server.USERS else "user"

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

    # Create session or token
    session["username"] = username
    csrf_token = auth_guard.issue_csrf_token()

    token = auth_crypto.generate_token(username) if auth_crypto.JWT_AVAILABLE else None

    server.log_audit_event(username, "user_registered", {"role": server.USERS[username]["role"]})

    return jsonify(
        {
            "success": True,
            "message": "User registered successfully",
            "user": {"username": username, "role": server.USERS[username]["role"]},
            "token": token,
            "csrf_token": csrf_token,
        }
    )


@bp.route("/api/auth/login", methods=["POST"])
@server.auth_rate_limit("5/minute;20/hour")
def login():
    """Login user"""
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    totp_token = data.get("totp_token")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if not auth_crypto.BCRYPT_AVAILABLE:
        return jsonify({"error": "Password hashing not available"}), 500

    # Check if user exists
    if username not in server.USERS:
        # Deliberately the same audit action/detail shape as a wrong password
        # below -- which of the two it was isn't exposed to the client, and
        # keeping the audit log symmetric avoids that leaking some other way
        # (e.g. by timing, if a reader correlates action names to log lines).
        server.log_audit_event(username, "login_failure", {"reason": "unknown_username_or_password"})
        return jsonify({"error": "Invalid username or password"}), 401

    user = server.USERS[username]

    # Check if user is enabled
    if not user.get("enabled", True):
        server.log_audit_event(username, "login_failure", {"reason": "account_disabled"})
        return jsonify({"error": "Account disabled"}), 401

    # Verify password
    if not auth_crypto.verify_password(password, user["password_hash"]):
        server.log_audit_event(username, "login_failure", {"reason": "unknown_username_or_password"})
        return jsonify({"error": "Invalid username or password"}), 401

    # Check if 2FA is enabled
    if user.get("totp_enabled", False):
        if not totp_token:
            return jsonify({"error": "2FA token required", "requires_2fa": True}), 401

        totp_secret = user.get("totp_secret")
        if not totp_secret:
            return jsonify({"error": "2FA not properly configured"}), 500

        if not auth_crypto.PYOTP_AVAILABLE:
            return jsonify({"error": "2FA not available"}), 500

        if not auth_crypto.verify_totp(totp_secret, totp_token):
            server.log_audit_event(username, "login_failure", {"reason": "invalid_2fa_token"})
            return jsonify({"error": "Invalid 2FA token"}), 401

    # Create session or token
    session["username"] = username
    csrf_token = auth_guard.issue_csrf_token()

    token = auth_crypto.generate_token(username) if auth_crypto.JWT_AVAILABLE else None

    server.log_audit_event(username, "login_success", {"method": "password"})

    return jsonify(
        {
            "success": True,
            "message": "Login successful",
            "user": {"username": username, "role": user.get("role", "user")},
            "token": token,
            "csrf_token": csrf_token,
        }
    )


@bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """Logout user"""
    if "username" in session:
        server.log_audit_event(session["username"], "logout")
    session.pop("username", None)
    session.pop("csrf_token", None)
    return jsonify({"success": True, "message": "Logged out successfully"})


@bp.route("/api/auth/2fa/setup", methods=["POST"])
@server.auth_rate_limit("10/hour")
@auth_guard.require_auth
def setup_2fa():
    """Setup 2FA for current user"""
    if not (auth_crypto.PYOTP_AVAILABLE and auth_crypto.QRCODE_AVAILABLE):
        return jsonify({"error": "2FA not available"}), 500

    username = request.user
    if username not in server.USERS:
        return jsonify({"error": "User not found"}), 404

    user = server.USERS[username]

    # Setup replaces the secret and leaves 2FA off until the new one is
    # verified, so on an account with 2FA on it used to switch 2FA off with
    # nothing but a session. Turning it off goes through /2fa/disable, which
    # asks for the password.
    if user.get("totp_enabled", False):
        return jsonify({"error": "2FA is already enabled. Disable it first to set it up again."}), 409

    # 2FA is a second step of password login. An account that signs in only
    # through Google or Apple never reaches that step, so a code would protect
    # nothing; that sign-in's own second factor lives with the provider.
    if not user.get("password_hash"):
        return (
            jsonify(
                {"error": "This account signs in with Google or Apple. Turn on 2-step verification with that provider."}
            ),
            400,
        )

    # Generate new secret
    secret = auth_crypto.generate_totp_secret()
    user["totp_secret"] = secret
    user["totp_enabled"] = False  # Not enabled until verified

    # Generate QR code
    uri = auth_crypto.generate_totp_uri(username, secret)
    qr_code = auth_crypto.generate_qr_code(uri)

    if not server.save_users():
        return jsonify({"error": "Failed to save user"}), 500

    return jsonify(
        {
            "success": True,
            "secret": secret,
            "qr_code": qr_code,
            "uri": uri,
            "message": "Scan QR code with authenticator app, then verify to enable 2FA",
        }
    )


@bp.route("/api/auth/2fa/verify", methods=["POST"])
@server.auth_rate_limit("10/minute")
@auth_guard.require_auth
def verify_2fa_setup():
    """Verify 2FA setup with token"""
    if not auth_crypto.PYOTP_AVAILABLE:
        return jsonify({"error": "2FA not available"}), 500

    data = request.get_json() or {}
    token = data.get("token")

    if not token:
        return jsonify({"error": "Token required"}), 400

    username = request.user
    if username not in server.USERS:
        return jsonify({"error": "User not found"}), 404

    user = server.USERS[username]
    secret = user.get("totp_secret")

    if not secret:
        return jsonify({"error": "2FA not set up. Please set up 2FA first."}), 400

    if auth_crypto.verify_totp(secret, token):
        user["totp_enabled"] = True
        if not server.save_users():
            return jsonify({"error": "Failed to save user"}), 500
        server.log_audit_event(username, "2fa_enabled")
        return jsonify(
            {
                "success": True,
                "message": "2FA enabled successfully",
            }
        )
    else:
        server.log_audit_event(username, "2fa_verify_failed")
        return jsonify({"error": "Invalid token"}), 401


@bp.route("/api/auth/2fa/disable", methods=["POST"])
@server.auth_rate_limit("10/minute")
@auth_guard.require_auth
def disable_2fa():
    """Disable 2FA for current user"""
    username = request.user
    if username not in server.USERS:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    user = server.USERS[username]

    # Confirmed with the password; an account with none (created by Google or
    # Apple sign-in) confirms with a current 2FA code instead. It used to
    # index user["password_hash"] and fail with a 500, leaving 2FA stuck on.
    if user.get("password_hash"):
        password = data.get("password")
        if not password:
            return jsonify({"error": "Password required to disable 2FA"}), 400
        if not auth_crypto.verify_password(password, user["password_hash"]):
            server.log_audit_event(username, "2fa_disable_failed", {"reason": "invalid_password"})
            return jsonify({"error": "Invalid password"}), 401
    else:
        token = data.get("token")
        if not token:
            return jsonify({"error": "A current 2FA code is required to disable 2FA"}), 400
        secret = user.get("totp_secret")
        if not secret or not auth_crypto.PYOTP_AVAILABLE or not auth_crypto.verify_totp(secret, str(token)):
            server.log_audit_event(username, "2fa_disable_failed", {"reason": "invalid_2fa_token"})
            return jsonify({"error": "Invalid 2FA code"}), 401

    # Disable 2FA
    user["totp_enabled"] = False
    user.pop("totp_secret", None)

    if not server.save_users():
        return jsonify({"error": "Failed to save user"}), 500

    server.log_audit_event(username, "2fa_disabled")

    return jsonify(
        {
            "success": True,
            "message": "2FA disabled successfully",
        }
    )


@bp.route("/api/auth/2fa/status", methods=["GET"])
@auth_guard.require_auth
def get_2fa_status():
    """Get 2FA status for current user"""
    username = request.user
    if username not in server.USERS:
        return jsonify({"error": "User not found"}), 404

    user = server.USERS[username]
    return jsonify(
        {
            "success": True,
            "enabled": user.get("totp_enabled", False),
            "configured": "totp_secret" in user,
            # Tells the UI which confirmation /2fa/disable wants
            "has_password": bool(user.get("password_hash")),
        }
    )


@bp.route("/api/auth/me", methods=["GET"])
@auth_guard.require_auth
def get_current_user():
    """Get current user info"""
    username = request.user
    user_info = server.USERS.get(username, {})
    return jsonify(
        {
            "username": username,
            "role": user_info.get("role", "user"),
            "email": user_info.get("email", ""),
            "created": user_info.get("created", ""),
            "oauth_providers": user_info.get("oauth_providers", []),
        }
    )


@bp.route("/api/auth/csrf-token", methods=["GET"])
@auth_guard.require_auth
def get_csrf_token():
    """Return the CSRF token for the current session, minting one if needed.

    Only meaningful for session-cookie auth (see auth_guard.require_auth /
    _csrf_check_failed); Bearer-JWT and API-key clients don't send this
    header and don't need to, since only the cookie path is CSRF-checked.
    """
    token = session.get("csrf_token") or auth_guard.issue_csrf_token()
    return jsonify({"csrf_token": token})


# OAuth Endpoints
def _issue_oauth_state():
    """Generate a fresh OAuth state nonce and stash it in the session.

    get_oauth_url() embeds this in the provider's authorization URL; the
    provider echoes it back on the redirect to our callback, and
    _verify_oauth_state() checks it there. Without this, nothing stops an
    attacker from starting their own OAuth flow, capturing the resulting
    code/id_token, and feeding it to a victim's browser -- the victim's
    session would then link (or log in as) an identity the attacker
    controls. session-based (not a signed cookie of its own) since the
    whole flow already runs in the same browser session that requested the
    URL in the first place.
    """
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    return state


def _verify_oauth_state(provided_state):
    """True if provided_state matches the one this session's
    get_oauth_url() call issued. Consumes it either way (one-shot), so a
    replayed or guessed value can't be reused across multiple callbacks."""
    expected = session.pop("oauth_state", None)
    return bool(expected) and bool(provided_state) and secrets.compare_digest(expected, provided_state)


def _oauth_sign_in(provider, oauth_id, email, fallback_name):
    """Find or create the account for a verified OAuth identity.

    Returns ``(username, None)``, or ``(None, response)`` with the refusal.

    A new identity is an account creation, so it obeys server.REGISTRATION_ENABLED
    exactly as /api/auth/register does. It used not to: anyone with a Google
    or Apple account could give themselves a "user" account on a panel whose
    registration was closed. The decision and the insert share server._users_lock
    for the same reason register() holds it, so two first sign-ins can't both
    become the bootstrap admin.

    A disabled account is refused here as it is at password login.
    """
    with server._users_lock:
        username = next(
            (name for name, user in server.USERS.items() if oauth_id in user.get("oauth_providers", [])),
            None,
        )

        if username is None:
            if server.USERS and not server.REGISTRATION_ENABLED:
                server.log_audit_event("unknown", "oauth_login_failure", {"provider": provider, "reason": "registration_closed"})
                return None, (
                    jsonify({"error": "Registration is closed. Ask an administrator to create your account."}),
                    403,
                )

            username_base = email.split("@")[0] if email else fallback_name
            username = username_base
            counter = 1
            while username in server.USERS:
                username = f"{username_base}_{counter}"
                counter += 1

            server.USERS[username] = {
                "username": username,
                "email": email,
                "oauth_providers": [oauth_id],
                "role": "admin" if not server.USERS else "user",
                "enabled": True,
                "created": datetime.now(timezone.utc).isoformat(),
            }
            # As in register(): an account that could not be saved would sign
            # in now and vanish on the next restart.
            if not server.save_users():
                del server.USERS[username]
                return None, (jsonify({"error": "Failed to save user"}), 500)
        elif not server.USERS[username].get("enabled", True):
            server.log_audit_event(username, "oauth_login_failure", {"provider": provider, "reason": "account_disabled"})
            return None, (jsonify({"error": "Account disabled"}), 401)

    return username, None


@bp.route("/api/auth/oauth/<provider>/url", methods=["GET"])
@server.auth_rate_limit("30/minute")
def get_oauth_url(provider):
    """Get OAuth authorization URL"""
    if provider not in ["google", "apple"]:
        return jsonify({"error": "Invalid OAuth provider"}), 400

    # Require redirect_uri in request (for security, don't fall back to config)
    redirect_uri = request.args.get("redirect_uri")
    if not redirect_uri:
        return jsonify({"error": "Redirect URI required"}), 400

    state = _issue_oauth_state()

    if provider == "google":
        if not server.OAUTH_CONFIG["google"].get("client_id"):
            return jsonify({"error": "Google OAuth not configured"}), 500

        scope = "openid email profile"
        params = {
            "client_id": server.OAUTH_CONFIG["google"]["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return jsonify({"url": auth_url})

    elif provider == "apple":
        if not server.OAUTH_CONFIG["apple"].get("client_id"):
            return jsonify({"error": "Apple OAuth not configured"}), 500

        params = {
            "client_id": server.OAUTH_CONFIG["apple"]["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "name email",
            "response_mode": "form_post",
            "state": state,
        }
        auth_url = f"https://appleid.apple.com/auth/authorize?{urllib.parse.urlencode(params)}"
        return jsonify({"url": auth_url})

    return jsonify({"error": "Invalid OAuth provider"}), 400  # unreachable; makes all code paths explicit


@bp.route("/api/auth/oauth/google/callback", methods=["POST"])
@server.auth_rate_limit("10/minute")
def google_oauth_callback():
    """Handle Google OAuth callback"""
    try:
        import requests
    except ImportError:
        return jsonify({"error": "requests library required for OAuth"}), 500

    data = request.get_json()
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")
    state = data.get("state")

    if not code or not redirect_uri:
        return jsonify({"error": "Code and redirect_uri required"}), 400

    if not _verify_oauth_state(state):
        server.log_audit_event("unknown", "oauth_login_failure", {"provider": "google", "reason": "state_mismatch"})
        return jsonify({"error": "Invalid or expired OAuth state"}), 400

    if not server.OAUTH_CONFIG["google"].get("client_id") or not server.OAUTH_CONFIG["google"].get("client_secret"):
        return jsonify({"error": "Google OAuth not configured"}), 500

    try:
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": server.OAUTH_CONFIG["google"]["client_id"],
            "client_secret": server.OAUTH_CONFIG["google"]["client_secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        token_response = requests.post(token_url, data=token_data, timeout=10)
        if token_response.status_code != 200:
            server.log_audit_event("unknown", "oauth_login_failure", {"provider": "google", "reason": "code_exchange_failed"})
            return jsonify({"error": "Failed to exchange code for token"}), 400

        token_json = token_response.json()
        access_token = token_json.get("access_token")

        if not access_token:
            return jsonify({"error": "No access token received"}), 400

        # Get user info from Google
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = requests.get(userinfo_url, headers=headers, timeout=10)

        if userinfo_response.status_code != 200:
            return jsonify({"error": "Failed to get user info"}), 400

        userinfo = userinfo_response.json()
        google_id = userinfo.get("id")
        email = userinfo.get("email", "")

        if not google_id:
            return jsonify({"error": "Invalid user info from Google"}), 400

        username, refusal = _oauth_sign_in("google", f"google:{google_id}", email, f"google_user_{google_id[:8]}")
        if refusal:
            return refusal

        # Create session or token
        session["username"] = username
        csrf_token = auth_guard.issue_csrf_token()
        token = auth_crypto.generate_token(username) if auth_crypto.JWT_AVAILABLE else None

        server.log_audit_event(username, "oauth_login_success", {"provider": "google"})

        return jsonify(
            {
                "success": True,
                "message": "OAuth login successful",
                "user": {"username": username, "role": server.USERS[username].get("role", "user")},
                "token": token,
                "csrf_token": csrf_token,
            }
        )

    except Exception as e:
        server.app.logger.error(f"OAuth callback error: {e}")
        server.log_audit_event("unknown", "oauth_login_failure", {"provider": "google", "reason": "internal_error"})
        return jsonify({"error": "Internal server error"}), 500


def _link_identity(username, provider, oauth_id):
    """Attach a verified OAuth identity to an account; returns the response.

    Shared by both providers. The link is saved before it is reported, and
    audited: it gives the account a new way to sign in. A save that failed
    used to be ignored, so the link worked until the next restart.
    """
    with server._users_lock:
        owner = next(
            (name for name, user in server.USERS.items() if oauth_id in user.get("oauth_providers", [])),
            None,
        )
        if owner is not None and owner != username:
            server.log_audit_event(username, "oauth_link_failure", {"provider": provider, "reason": "linked_elsewhere"})
            return jsonify({"error": "This account is already linked to another user"}), 400

        user = server.USERS[username]
        had_oauth_providers = "oauth_providers" in user
        providers = user.setdefault("oauth_providers", [])
        if oauth_id not in providers:
            providers.append(oauth_id)
            if not server.save_users():
                providers.remove(oauth_id)
                if not had_oauth_providers and not providers:
                    user.pop("oauth_providers", None)
                return jsonify({"error": "Failed to save user"}), 500
            server.log_audit_event(username, "oauth_linked", {"provider": provider})

        return jsonify(
            {
                "success": True,
                "message": f"{provider.capitalize()} account linked successfully",
                "oauth_providers": list(providers),
            }
        )


@bp.route("/api/auth/oauth/<provider>/link", methods=["POST"])
@server.auth_rate_limit("10/minute")
@auth_guard.require_auth
def link_oauth_account(provider):
    """Link OAuth account to existing user"""
    # Provider validity is checked in the require_auth decorator

    username = request.user

    if username not in server.USERS:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")
    id_token = data.get("id_token")
    state = data.get("state")

    if not _verify_oauth_state(state):
        server.log_audit_event(username, "oauth_link_failure", {"provider": provider, "reason": "state_mismatch"})
        return jsonify({"error": "Invalid or expired OAuth state"}), 400

    if provider == "google":
        if not code or not redirect_uri:
            return jsonify({"error": "Code and redirect_uri required"}), 400

        if not server.OAUTH_CONFIG["google"].get("client_id") or not server.OAUTH_CONFIG["google"].get("client_secret"):
            return jsonify({"error": "Google OAuth not configured"}), 500

        try:
            import requests

            # Exchange code for token
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": server.OAUTH_CONFIG["google"]["client_id"],
                "client_secret": server.OAUTH_CONFIG["google"]["client_secret"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }

            token_response = requests.post(token_url, data=token_data, timeout=10)
            if token_response.status_code != 200:
                return jsonify({"error": "Failed to exchange code for token"}), 400

            token_json = token_response.json()
            access_token = token_json.get("access_token")

            if not access_token:
                return jsonify({"error": "No access token received"}), 400

            # Get user info from Google
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            userinfo_response = requests.get(userinfo_url, headers=headers, timeout=10)

            if userinfo_response.status_code != 200:
                return jsonify({"error": "Failed to get user info"}), 400

            userinfo = userinfo_response.json()
            google_id = userinfo.get("id")

            if not google_id:
                return jsonify({"error": "Invalid user info from Google"}), 400

            return _link_identity(username, "google", f"google:{google_id}")

        except ImportError:
            return jsonify({"error": "requests library required for OAuth"}), 500

    elif provider == "apple":
        if not id_token:
            return jsonify({"error": "ID token required"}), 400

        if not server.OAUTH_CONFIG["apple"].get("client_id"):
            return jsonify({"error": "Apple OAuth not configured"}), 500

        if not auth_crypto.JWT_AVAILABLE:
            return jsonify({"error": "JWT library required for Apple OAuth"}), 500

        decoded = auth_crypto.verify_apple_id_token(id_token)
        if decoded is None:
            return jsonify({"error": "Invalid ID token from Apple"}), 401
        apple_id = decoded.get("sub")

        if not apple_id:
            return jsonify({"error": "Invalid ID token from Apple"}), 400

        return _link_identity(username, "apple", f"apple:{apple_id}")

    else:
        return jsonify({"error": "Invalid provider"}), 400



@bp.route("/api/auth/oauth/<provider>/unlink", methods=["POST"])
@auth_guard.require_auth
def unlink_oauth_account(provider):
    """Unlink OAuth account from user"""
    # Provider validity is checked in the require_auth decorator

    username = request.user

    if username not in server.USERS:
        return jsonify({"error": "User not found"}), 404

    user = server.USERS[username]

    # Check if user has a password (can't unlink last auth method)
    has_password = "password_hash" in user
    oauth_providers = user.get("oauth_providers", [])

    # Count how many OAuth providers user has
    provider_count = sum(1 for p in oauth_providers if p.startswith(f"{provider}:"))

    if not has_password and len(oauth_providers) <= provider_count:
        return jsonify({"error": "Cannot unlink last authentication method"}), 400

    # Remove OAuth provider
    previous_providers = user.get("oauth_providers", [])
    oauth_providers = [p for p in previous_providers if not p.startswith(f"{provider}:")]
    user["oauth_providers"] = oauth_providers
    if not server.save_users():
        user["oauth_providers"] = previous_providers
        return jsonify({"error": "Failed to save user"}), 500

    return jsonify(
        {
            "success": True,
            "message": f"{provider.title()} account unlinked successfully",
            "oauth_providers": oauth_providers,
        }
    )


@bp.route("/oauth/callback", methods=["POST"])
@server.auth_rate_limit("10/minute")
def apple_oauth_form_post_relay():
    """Relay Apple's form_post OAuth response into the SPA's callback route.

    Apple *requires* response_mode=form_post whenever the requested scope
    includes name/email (get_oauth_url's Apple branch always requests
    "name email", to get the user's email address) -- meaning Apple POSTs
    the result to the redirect_uri instead of redirecting with it in the
    URL. The SPA's callback page (web/src/pages/OAuthCallback.jsx) only
    ever reads the URL's query string via useSearchParams(); it has no way
    to see a POST body. Without this, the page would load with nothing in
    it and show "No authorization code received" for every Apple sign-in.

    This receives the POST and re-issues it as a 302 redirect to the same
    path with the same fields in the query string instead, which the
    existing client-side handling already expects -- it's exactly what
    Google's flow already looks like, since Google redirects with query
    params directly and never needed this relay.

    Only reached for POST: config/nginx-minecraft.conf routes POST requests
    for this exact path here specifically; GET (a real visitor navigating
    here, or the redirect target of *this* handler) is served by the SPA.
    """
    data = request.form
    params = {}
    for key in ("code", "state", "id_token", "user", "error", "error_description"):
        value = data.get(key)
        if value:
            params[key] = value
    return redirect(f"/oauth/callback?{urllib.parse.urlencode(params)}")


@bp.route("/api/auth/oauth/apple/callback", methods=["POST"])
@server.auth_rate_limit("10/minute")
def apple_oauth_callback():
    """Handle Apple OAuth callback"""
    data = request.get_json()
    id_token = data.get("id_token")
    state = data.get("state")

    if not id_token:
        return jsonify({"error": "ID token required"}), 400

    if not _verify_oauth_state(state):
        server.log_audit_event("unknown", "oauth_login_failure", {"provider": "apple", "reason": "state_mismatch"})
        return jsonify({"error": "Invalid or expired OAuth state"}), 400

    if not server.OAUTH_CONFIG["apple"].get("client_id"):
        return jsonify({"error": "Apple OAuth not configured"}), 500

    try:
        if not auth_crypto.JWT_AVAILABLE:
            return jsonify({"error": "JWT library required for Apple OAuth"}), 500

        decoded = auth_crypto.verify_apple_id_token(id_token)
        if decoded is None:
            server.log_audit_event("unknown", "oauth_login_failure", {"provider": "apple", "reason": "invalid_id_token"})
            return jsonify({"error": "Invalid ID token from Apple"}), 401
        apple_id = decoded.get("sub")
        email = decoded.get("email", "")

        if not apple_id:
            return jsonify({"error": "Invalid ID token from Apple"}), 400

        username, refusal = _oauth_sign_in("apple", f"apple:{apple_id}", email, f"apple_user_{apple_id[:8]}")
        if refusal:
            return refusal

        session["username"] = username
        csrf_token = auth_guard.issue_csrf_token()
        token = auth_crypto.generate_token(username) if auth_crypto.JWT_AVAILABLE else None

        server.log_audit_event(username, "oauth_login_success", {"provider": "apple"})

        return jsonify(
            {
                "success": True,
                "message": "OAuth login successful",
                "user": {"username": username, "role": server.USERS[username].get("role", "user")},
                "token": token,
                "csrf_token": csrf_token,
            }
        )

    except Exception as e:
        server.app.logger.error(f"Failed to process Apple OAuth: {e}")
        server.log_audit_event("unknown", "oauth_login_failure", {"provider": "apple", "reason": "internal_error"})
        return jsonify({"error": "Internal server error"}), 500
