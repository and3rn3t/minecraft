#!/usr/bin/env python3
"""
Minecraft Server REST API
Provides HTTP API for remote server management
"""

import fcntl
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import uuid
import warnings
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, session

# Optional CORS support
try:
    from flask_cors import CORS  # type: ignore  # noqa: F401

    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    CORS = None  # Placeholder for type checking

# Optional WebSocket support
try:
    import eventlet  # type: ignore[import-untyped]
    from flask_socketio import (
        SocketIO,  # type: ignore[import-untyped]
    )

    # Only monkey patch if not in testing environment
    # eventlet.monkey_patch() can interfere with pytest parallel execution
    # Check multiple environment variables that indicate testing
    is_testing = (
        os.environ.get("TESTING") == "true"
        or os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("PYTEST_RUNNING") == "1"
        or "pytest" in sys.modules
    )
    if not is_testing:
        eventlet.monkey_patch()
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    SocketIO = None  # Placeholder for type checking
    emit = None
    disconnect = None

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import security utilities
try:
    from api.security import (
        is_rate_limit_exceeded,
        sanitize_minecraft_command,
        sanitize_string,
    )

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

    # Provide fallback functions if security module unavailable
    def sanitize_minecraft_command(cmd):
        return True, (cmd[:256] if cmd else ""), None

    def sanitize_file_path(path, base_dir):
        try:
            return True, Path(path), None
        except Exception:
            return False, None, "Invalid path"

    def sanitize_string(s, max_length=1000, allow_newlines=False):
        return str(s)[:max_length] if s else ""

    def validate_username(u):
        return bool(u and len(u) >= 3), None

    def is_rate_limit_exceeded(*args, **kwargs):
        return False


# In-process RCON client. Keeps one authenticated connection open instead of
# paying for a TCP handshake and login per command.
try:
    from api import rcon

    RCON_AVAILABLE = True
except ImportError:
    RCON_AVAILABLE = False
    rcon = None

# Game event bus. Parses the server log into typed events that features can
# subscribe to, instead of every feature re-parsing raw text for itself.
try:
    from api import events as game_events

    EVENTS_AVAILABLE = True
except ImportError:
    EVENTS_AVAILABLE = False
    game_events = None

# Hall of Deaths. The first feature built on the event bus: it writes an
# epitaph for every death, announces it in game and keeps the record.
try:
    from api import hall_of_deaths

    DEATHS_AVAILABLE = True
except ImportError:
    DEATHS_AVAILABLE = False
    hall_of_deaths = None

# Bedtime mode. Warns, counts down, then closes the server for the night.
try:
    from api import bedtime as bedtime_mode

    BEDTIME_AVAILABLE = True
except ImportError:
    BEDTIME_AVAILABLE = False
    bedtime_mode = None

# Player statistics, read from the counters the game itself writes.
try:
    from api import player_stats

    PLAYER_STATS_AVAILABLE = True
except ImportError:
    PLAYER_STATS_AVAILABLE = False
    player_stats = None


app = Flask(__name__)
# SECRET_KEY is resolved further down, once config/api.conf has been read.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max request size
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

# Rate limiting storage (in-memory, use Redis in production)
RATE_LIMIT_STORAGE = {}

# CORS configuration - restrict to specific origins in production
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# Initialize SocketIO if available
if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, async_mode="eventlet")
else:
    socketio = None

# Enable CORS if available
if CORS_AVAILABLE:
    CORS(app, supports_credentials=True, origins=ALLOWED_ORIGINS)
else:
    # Fallback: Add CORS headers manually if needed
    @app.after_request
    def after_request_cors(response):
        origin = request.headers.get("Origin")
        if origin and (ALLOWED_ORIGINS == ["*"] or origin in ALLOWED_ORIGINS):
            response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-API-Key")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response


# Add security headers to all responses
@app.after_request
def security_headers(response):
    """Add security headers to all responses"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Remove server header
    response.headers.pop("Server", None)
    return response


# Rate limiting decorator
def rate_limit(max_per_minute=60, per_endpoint=False):
    """Simple rate limiting decorator"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not SECURITY_AVAILABLE:
                return f(*args, **kwargs)

            # Get identifier (IP address or user)
            identifier = request.remote_addr or "unknown"
            if hasattr(request, "user") and request.user:
                identifier = f"{identifier}:{request.user}"

            # Add endpoint to identifier if per_endpoint is True
            if per_endpoint:
                identifier = f"{identifier}:{request.endpoint}"

            # Check rate limit (60 requests per minute by default)
            if is_rate_limit_exceeded(identifier, max_per_minute, 60, RATE_LIMIT_STORAGE):
                return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Configuration
API_CONFIG_FILE = PROJECT_ROOT / "config" / "api.conf"
API_KEYS_FILE = PROJECT_ROOT / "config" / "api-keys.json"
USERS_FILE = PROJECT_ROOT / "config" / "users.json"
OAUTH_CONFIG_FILE = PROJECT_ROOT / "config" / "oauth.conf"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Default configuration
API_PORT = 8080
API_HOST = "127.0.0.1"  # Only listen on localhost by default
API_ENABLED = True

# Secret keys that must never be used to sign sessions or JWTs. The first was
# shipped as a default in earlier versions; treat it as if it were published.
_REJECTED_SECRET_KEYS = {
    "",
    "minecraft-server-api-secret-change-in-production",
    "change-me",
    "changeme",
    "secret",
}

# Load configuration
_config_secret_key = None
if API_CONFIG_FILE.exists():
    with open(API_CONFIG_FILE, "r") as f:
        config = {}
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                config[key] = value
        API_PORT = int(config.get("API_PORT", API_PORT))
        API_HOST = config.get("API_HOST", API_HOST)
        API_ENABLED = config.get("API_ENABLED", "true").lower() == "true"
        _config_secret_key = config.get("SECRET_KEY")


def _resolve_secret_key(env_value, config_value):
    """Pick the signing key: environment first, then config file, else ephemeral.

    Sessions and JWTs are signed with this value, so a known constant would let
    anyone mint valid tokens. A placeholder from either source is refused and we
    fall back to a random key, which invalidates tokens on restart but is safe.
    """
    for candidate in (env_value, config_value):
        if candidate and candidate.strip() not in _REJECTED_SECRET_KEYS:
            return candidate.strip()

    if (env_value and env_value.strip() in _REJECTED_SECRET_KEYS) or (
        config_value and config_value.strip() in _REJECTED_SECRET_KEYS
    ):
        warnings.warn(
            "SECRET_KEY is set to a known placeholder value and was ignored. "
            "Generate one with: python3 -c 'import secrets; print(secrets.token_hex(32))'",
            stacklevel=2,
        )
    else:
        warnings.warn(
            "No SECRET_KEY configured; generating an ephemeral one. Sessions and "
            "API tokens will be invalidated on every restart. Set SECRET_KEY in the "
            "environment or in config/api.conf to make them durable.",
            stacklevel=2,
        )
    return secrets.token_hex(32)


SECRET_KEY = _resolve_secret_key(os.environ.get("SECRET_KEY"), _config_secret_key)

# Set Flask secret key for sessions
app.config["SECRET_KEY"] = SECRET_KEY

# Load API keys
API_KEYS = {}
if API_KEYS_FILE.exists():
    try:
        with open(API_KEYS_FILE, "r") as f:
            API_KEYS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        API_KEYS = {}


def _migrate_api_key_roles(keys):
    """Give pre-scoping keys an explicit role.

    Keys created before API keys were scoped carried no role and were treated
    as admins by ``has_permission()``. Silently demoting them would break
    whatever is holding them, so they keep admin rights — but explicitly, where
    they show up in ``GET /api/keys`` and can be narrowed with
    ``PUT /api/keys/<id>``. Written back on the next save.
    """
    unscoped = [info for info in keys.values() if "role" not in info and "permissions" not in info]
    for info in unscoped:
        info["role"] = "admin"
    if unscoped:
        warnings.warn(
            f"{len(unscoped)} API key(s) had no role and were kept as admin. "
            "Narrow them with PUT /api/keys/<id> or in the API Keys page; a key "
            "that only reads logs should not be able to manage users.",
            stacklevel=2,
        )
    return keys


_migrate_api_key_roles(API_KEYS)

# Load users
USERS = {}
if USERS_FILE.exists():
    try:
        with open(USERS_FILE, "r") as f:
            USERS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        USERS = {}

# Guards the check-and-insert in registration and user creation. Flask serves
# requests on threads, so two registrations arriving together could otherwise
# both see an empty USERS and both be granted the bootstrap admin role.
_users_lock = threading.Lock()

# Open registration. The default lets the very first account be created to
# bootstrap the server and closes the endpoint afterwards; admins add everyone
# else through POST /api/users. Set REGISTRATION_ENABLED=true to keep it open.
REGISTRATION_ENABLED = os.environ.get("REGISTRATION_ENABLED", "").strip().lower() in ("1", "true", "yes")

# Audit log file
AUDIT_LOG_FILE = PROJECT_ROOT / "config" / "audit.log"

# Command scheduler file
SCHEDULE_FILE = PROJECT_ROOT / "config" / "command-schedule.json"


def save_users():
    """Save users to file"""
    try:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, "w") as f:
            json.dump(USERS, f, indent=2)
        return True
    except Exception:
        return False


def save_api_keys():
    """Save API keys to file"""
    try:
        API_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(API_KEYS_FILE, "w") as f:
            json.dump(API_KEYS, f, indent=2)
        # Set restrictive permissions (owner read/write only) - Unix only
        try:
            import os

            os.chmod(API_KEYS_FILE, 0o600)
        except (AttributeError, OSError):
            # Windows doesn't support chmod the same way, skip
            pass
        return True
    except Exception:
        return False


def generate_api_key():
    """Generate a secure random API key"""
    # Generate 32-character alphanumeric key
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(32))


def require_api_key(f):
    """Decorator to require API key authentication (grants admin permissions)"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")

        if not api_key:
            return jsonify({"error": "API key required"}), 401

        # Check if API key is valid
        if api_key not in API_KEYS:
            return jsonify({"error": "Invalid API key"}), 401

        # Check if key is enabled
        key_info = API_KEYS.get(api_key, {})
        if not key_info.get("enabled", True):
            return jsonify({"error": "API key disabled"}), 401

        # Store key info in request context. has_permission() reads it to scope
        # the key; without it the key would fall back to no permissions.
        request.api_key_info = key_info
        request.user = "__api_key__"
        request.user_info = {
            "username": "__api_key__",
            "role": key_info.get("role", DEFAULT_API_KEY_ROLE),
            "key_name": key_info.get("name", "unknown"),
        }
        return f(*args, **kwargs)

    return decorated_function


# Most management scripts answer in well under a second. Backups, restores and
# server updates tar or download gigabytes, so they get their own budget.
DEFAULT_SCRIPT_TIMEOUT = 30
LONG_SCRIPT_TIMEOUT = 600


def run_script(script_name, *args, timeout=DEFAULT_SCRIPT_TIMEOUT):
    """Run a management script and return (stdout, stderr, returncode).

    A timed-out script yields returncode 504. Callers that wrap long-running
    operations should pass a larger timeout rather than letting a backup of a
    real-sized world look like a failure.
    """
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        return None, f"Script not found: {script_name}", 404

    try:
        result = subprocess.run(
            [str(script_path)] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return None, f"Script execution timeout after {timeout}s", 504
    except Exception as e:
        return None, str(e), 500


def run_rcon_command(command):
    """Execute a Minecraft command over RCON, returning (stdout, stderr, code).

    Prefers the pooled in-process client in ``api/rcon.py``, which reuses one
    authenticated connection. Falls back to ``scripts/rcon-client.sh`` only when
    the command provably never reached the server, because that script can reach
    ``rcon-cli`` inside the container when the port is not published to the host.

    Minecraft commands are not idempotent. ``502`` and ``503`` mean nothing was
    sent, so running the command by another route is safe. Every other code is
    returned as-is: an auth failure or a rejected command would fail the same
    way again, and ``500`` means the command reached the server but its result
    was lost, so repeating it could apply a ``give`` or a ``kill`` twice.
    """
    if RCON_AVAILABLE:
        stdout, stderr, code = rcon.execute(command)
        if code not in (502, 503):
            return stdout, stderr, code

    return run_script("rcon-client.sh", "command", command)


def _stop_server_for_bedtime():
    """Stop the server the way the rest of the project does."""
    _, stderr, code = run_script("manage.sh", "stop", timeout=600)
    if code != 0:
        raise RuntimeError(stderr or f"manage.sh stop returned {code}")


def _run_game_command(command):
    """Run a command for a feature that needs the server to see it."""
    _, stderr, code = run_rcon_command(command)
    if code != 0:
        raise RuntimeError(stderr or f"RCON returned {code}")


def _announce_in_game(command):
    """Run a command whose only purpose is to show players something.

    Raises on failure so the caller can record that the announcement did not
    reach anyone, which is the normal case when the server is stopped.
    """
    _, stderr, code = run_rcon_command(command)
    if code != 0:
        raise RuntimeError(stderr or f"RCON returned {code}")


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0.0"})


# User Authentication Endpoints
try:
    import bcrypt
    import jwt

    BCRYPT_AVAILABLE = True
    JWT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    JWT_AVAILABLE = False
    bcrypt = None
    jwt = None

# Two-Factor Authentication
try:
    import base64
    import io

    import pyotp
    import qrcode

    TOTP_AVAILABLE = True
except ImportError:
    TOTP_AVAILABLE = False
    pyotp = None
    qrcode = None


def hash_password(password):
    """Hash password using bcrypt"""
    if not BCRYPT_AVAILABLE:
        raise ImportError("bcrypt not available")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, hashed):
    """Verify password against hash"""
    if not BCRYPT_AVAILABLE:
        raise ImportError("bcrypt not available")
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_token(username):
    """Generate JWT token for user"""
    if not JWT_AVAILABLE:
        # Fallback to simple session
        return None
    payload = {
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token):
    """Verify JWT token"""
    if not JWT_AVAILABLE:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def generate_totp_secret():
    """Generate a TOTP secret for 2FA"""
    if not TOTP_AVAILABLE:
        raise ImportError("pyotp not available")
    return pyotp.random_base32()


def generate_totp_uri(username, secret, issuer="Minecraft Server"):
    """Generate TOTP URI for QR code"""
    if not TOTP_AVAILABLE:
        raise ImportError("pyotp not available")
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def generate_qr_code(uri):
    """Generate QR code image from URI"""
    if not TOTP_AVAILABLE:
        raise ImportError("qrcode not available")
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def verify_totp(secret, token):
    """Verify TOTP token"""
    if not TOTP_AVAILABLE:
        raise ImportError("pyotp not available")
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # Allow 1 time step window


# Audit Logging
def log_audit_event(username, action, details=None, ip_address=None):
    """Log an audit event"""
    try:
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        ip = ip_address or request.remote_addr if hasattr(request, "remote_addr") else "unknown"

        log_entry = {
            "timestamp": timestamp,
            "username": username,
            "action": action,
            "details": details or {},
            "ip_address": ip,
        }

        # Append to audit log file (JSONL format)
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        # Don't fail the request if audit logging fails
        print(f"Audit logging error: {e}")


def get_username_from_request():
    """Get username from request (API key, session, or token)"""
    # Check API key
    api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
    if api_key and api_key in API_KEYS:
        return f"api_key:{API_KEYS[api_key].get('name', 'unknown')}"

    # Check session
    if "username" in session:
        return session.get("username")

    # Check JWT token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        username = verify_token(token)
        if username:
            return username

    return "unknown"


# Permission System
# Define permissions as constants
PERMISSIONS = {
    # Server control
    "server.view": "View server status",
    "server.control": "Control server (start/stop/restart)",
    "server.command": "Send commands to server",
    "server.manage": "Manage server configuration (properties, presets, announcements, schedules)",
    # Backup management
    "backup.create": "Create backups",
    "backup.restore": "Restore backups",
    "backup.delete": "Delete backups",
    "backup.view": "View backup list",
    # Configuration
    "config.view": "View configuration files",
    "config.edit": "Edit configuration files",
    # Player management
    "players.view": "View player list",
    "players.manage": "Manage players (ban/whitelist/op)",
    # World management
    "worlds.view": "View world list",
    "worlds.manage": "Manage worlds (create/delete/switch)",
    # Plugin management
    "plugins.view": "View plugin list",
    "plugins.manage": "Manage plugins (install/remove/enable/disable)",
    # User management
    "users.view": "View user list",
    "users.manage": "Manage users (create/edit/delete/roles)",
    # API key management
    "api_keys.view": "View API keys",
    "api_keys.manage": "Manage API keys (create/delete/enable/disable)",
    # Logs
    "logs.view": "View server logs",
    # Metrics
    "metrics.view": "View server metrics",
    "analytics.view": "View analytics and reports",
    "analytics.generate": "Generate analytics reports",
    # Settings
    "settings.view": "View application settings",
    "settings.edit": "Edit application settings",
}

# Role to permissions mapping
ROLE_PERMISSIONS = {
    "admin": list(PERMISSIONS.keys()),  # Admins have all permissions
    "user": [
        "server.view",
        "backup.view",
        "config.view",
        "players.view",
        "worlds.view",
        "plugins.view",
        "logs.view",
        "metrics.view",
        "analytics.view",
        "settings.view",
    ],
    "operator": [
        "server.view",
        "server.control",
        "server.command",
        "analytics.view",
        "analytics.generate",
        "backup.create",
        "backup.view",
        "backup.restore",
        "config.view",
        "players.view",
        "players.manage",
        "worlds.view",
        "plugins.view",
        "logs.view",
        "metrics.view",
        "settings.view",
    ],
}


# New API keys start here rather than at "admin": a key lives in a Shortcut, a
# browser or a script, so it is the credential most likely to leak.
DEFAULT_API_KEY_ROLE = "user"


def get_api_key_permissions(key_info):
    """Get the list of permissions an API key record grants.

    A key carries either an explicit ``permissions`` allowlist or a ``role``
    from the same ladder users use. Unknown permission names are dropped so a
    typo in the config file cannot widen a key's reach.
    """
    explicit = key_info.get("permissions")
    if isinstance(explicit, list):
        return [p for p in explicit if p in PERMISSIONS]
    key_role = key_info.get("role", DEFAULT_API_KEY_ROLE)
    return ROLE_PERMISSIONS.get(key_role, ROLE_PERMISSIONS[DEFAULT_API_KEY_ROLE])


def validate_api_key_scope(role, permissions):
    """Return an error string if a requested key scope is not usable, else None."""
    if role not in ROLE_PERMISSIONS:
        return f"Invalid role. Valid roles: {', '.join(ROLE_PERMISSIONS.keys())}"
    if permissions is None:
        return None
    if not isinstance(permissions, list) or not all(isinstance(p, str) for p in permissions):
        return "permissions must be a list of permission names"
    unknown = [p for p in permissions if p not in PERMISSIONS]
    if unknown:
        return f"Unknown permissions: {', '.join(sorted(unknown))}"
    return None


def get_user_permissions(username):
    """Get list of permissions for a user based on their role"""
    if username == "__api_key__":
        return get_api_key_permissions(getattr(request, "api_key_info", {}))
    if username not in USERS:
        return []
    user_role = USERS[username].get("role", "user")
    return ROLE_PERMISSIONS.get(user_role, ROLE_PERMISSIONS["user"])


def has_permission(username, permission):
    """Check if user has a specific permission"""
    # API keys are scoped by their own role, not by the caller's. This used to
    # return True unconditionally, which made every key a full admin
    # credential regardless of what it was created for.
    if username == "__api_key__":
        key_info = getattr(request, "api_key_info", {})
        # An admin-scoped key matches an admin user, which is what the check
        # just below does. Without this, an admin key is refused any permission
        # missing from PERMISSIONS while an admin user sails through — the
        # asymmetry that locked admin keys out of the server.manage endpoints.
        # A key carrying an explicit allowlist is held to that list instead.
        if key_info.get("permissions") is None and key_info.get("role") == "admin":
            return True
        return permission in get_api_key_permissions(key_info)
    if username not in USERS:
        return False
    user_role = USERS[username].get("role", "user")
    # Admins have all permissions
    if user_role == "admin":
        return True
    user_permissions = ROLE_PERMISSIONS.get(user_role, ROLE_PERMISSIONS["user"])
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

        # Check API key first (for backward compatibility)
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if api_key:
            if api_key in API_KEYS and API_KEYS[api_key].get("enabled", True):
                key_info = API_KEYS[api_key]
                request.api_key_info = key_info
                request.user = "__api_key__"
                request.user_info = {
                    "username": "__api_key__",
                    "role": key_info.get("role", DEFAULT_API_KEY_ROLE),
                    "key_name": key_info.get("name", "unknown"),
                }
                return f(*args, **kwargs)
            else:
                return jsonify({"error": "Invalid API key"}), 401

        # Check session
        if "username" in session:
            request.user = session.get("username")
            request.user_info = USERS.get(session.get("username"), {})
            return f(*args, **kwargs)

        # Check JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            username = verify_token(token)
            if username and username in USERS:
                request.user = username
                request.user_info = USERS.get(username, {})
                return f(*args, **kwargs)

        return jsonify({"error": "Authentication required"}), 401

    return decorated_function


@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new user"""
    if USERS and not REGISTRATION_ENABLED:
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

    if not BCRYPT_AVAILABLE:
        return jsonify({"error": "Password hashing not available"}), 500

    # Validate username
    if len(username) < 3 or len(username) > 32:
        return jsonify({"error": "Username must be 3-32 characters"}), 400

    # Validate password
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    hashed_password = hash_password(password)

    # Held across the whole decide-role-and-insert sequence: two registrations
    # arriving together could otherwise both find USERS empty and both be
    # granted the bootstrap admin role, which is the defect this guards.
    with _users_lock:
        # Re-checked under the lock, in the same order as the fast path above:
        # the check there is only there to avoid hashing a password for a
        # request that is going to be refused anyway.
        if USERS and not REGISTRATION_ENABLED:
            return (
                jsonify({"error": "Registration is closed. Ask an administrator to create your account."}),
                403,
            )

        if username in USERS:
            return jsonify({"error": "Username already exists"}), 400

        # The first account bootstraps the server and has to be an admin; every
        # later one starts with no privileges and is promoted by an admin
        # through /api/users/<username>/role.
        role = "admin" if not USERS else "user"

        USERS[username] = {
            "username": username,
            "password_hash": hashed_password,
            "email": email,
            "role": role,
            "enabled": True,
            "created": datetime.now(timezone.utc).isoformat(),
        }

        if not save_users():
            del USERS[username]
            return jsonify({"error": "Failed to save user"}), 500

    # Create session or token
    session["username"] = username

    token = generate_token(username) if JWT_AVAILABLE else None

    return jsonify(
        {
            "success": True,
            "message": "User registered successfully",
            "user": {"username": username, "role": USERS[username]["role"]},
            "token": token,
        }
    )


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Login user"""
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    totp_token = data.get("totp_token")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if not BCRYPT_AVAILABLE:
        return jsonify({"error": "Password hashing not available"}), 500

    # Check if user exists
    if username not in USERS:
        return jsonify({"error": "Invalid username or password"}), 401

    user = USERS[username]

    # Check if user is enabled
    if not user.get("enabled", True):
        return jsonify({"error": "Account disabled"}), 401

    # Verify password
    if not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid username or password"}), 401

    # Check if 2FA is enabled
    if user.get("totp_enabled", False):
        if not totp_token:
            return jsonify({"error": "2FA token required", "requires_2fa": True}), 401

        totp_secret = user.get("totp_secret")
        if not totp_secret:
            return jsonify({"error": "2FA not properly configured"}), 500

        if not TOTP_AVAILABLE:
            return jsonify({"error": "2FA not available"}), 500

        if not verify_totp(totp_secret, totp_token):
            return jsonify({"error": "Invalid 2FA token"}), 401

    # Create session or token
    session["username"] = username

    token = generate_token(username) if JWT_AVAILABLE else None

    return jsonify(
        {
            "success": True,
            "message": "Login successful",
            "user": {"username": username, "role": user.get("role", "user")},
            "token": token,
        }
    )


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Logout user"""
    session.pop("username", None)
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/api/auth/2fa/setup", methods=["POST"])
@require_auth
def setup_2fa():
    """Setup 2FA for current user"""
    if not TOTP_AVAILABLE:
        return jsonify({"error": "2FA not available"}), 500

    username = request.user
    if username not in USERS:
        return jsonify({"error": "User not found"}), 404

    user = USERS[username]

    # Generate new secret
    secret = generate_totp_secret()
    user["totp_secret"] = secret
    user["totp_enabled"] = False  # Not enabled until verified

    # Generate QR code
    uri = generate_totp_uri(username, secret)
    qr_code = generate_qr_code(uri)

    if not save_users():
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


@app.route("/api/auth/2fa/verify", methods=["POST"])
@require_auth
def verify_2fa_setup():
    """Verify 2FA setup with token"""
    if not TOTP_AVAILABLE:
        return jsonify({"error": "2FA not available"}), 500

    data = request.get_json() or {}
    token = data.get("token")

    if not token:
        return jsonify({"error": "Token required"}), 400

    username = request.user
    if username not in USERS:
        return jsonify({"error": "User not found"}), 404

    user = USERS[username]
    secret = user.get("totp_secret")

    if not secret:
        return jsonify({"error": "2FA not set up. Please set up 2FA first."}), 400

    if verify_totp(secret, token):
        user["totp_enabled"] = True
        if not save_users():
            return jsonify({"error": "Failed to save user"}), 500
        return jsonify(
            {
                "success": True,
                "message": "2FA enabled successfully",
            }
        )
    else:
        return jsonify({"error": "Invalid token"}), 401


@app.route("/api/auth/2fa/disable", methods=["POST"])
@require_auth
def disable_2fa():
    """Disable 2FA for current user"""
    username = request.user
    if username not in USERS:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    password = data.get("password")

    if not password:
        return jsonify({"error": "Password required to disable 2FA"}), 400

    user = USERS[username]

    # Verify password
    if not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid password"}), 401

    # Disable 2FA
    user["totp_enabled"] = False
    user.pop("totp_secret", None)

    if not save_users():
        return jsonify({"error": "Failed to save user"}), 500

    return jsonify(
        {
            "success": True,
            "message": "2FA disabled successfully",
        }
    )


@app.route("/api/auth/2fa/status", methods=["GET"])
@require_auth
def get_2fa_status():
    """Get 2FA status for current user"""
    username = request.user
    if username not in USERS:
        return jsonify({"error": "User not found"}), 404

    user = USERS[username]
    return jsonify(
        {
            "success": True,
            "enabled": user.get("totp_enabled", False),
            "configured": "totp_secret" in user,
        }
    )


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def get_current_user():
    """Get current user info"""
    username = request.user
    user_info = USERS.get(username, {})
    return jsonify(
        {
            "username": username,
            "role": user_info.get("role", "user"),
            "email": user_info.get("email", ""),
            "created": user_info.get("created", ""),
            "oauth_providers": user_info.get("oauth_providers", []),
        }
    )


# OAuth Configuration
OAUTH_CONFIG_FILE = PROJECT_ROOT / "config" / "oauth.conf"
OAUTH_CONFIG = {
    "google": {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "",
    },
    "apple": {
        "client_id": "",
        "team_id": "",
        "key_id": "",
        "private_key": "",
        "redirect_uri": "",
    },
}

# Load OAuth configuration
if OAUTH_CONFIG_FILE.exists():
    with open(OAUTH_CONFIG_FILE, "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                if key.startswith("GOOGLE_"):
                    oauth_key = key.replace("GOOGLE_", "").lower()
                    if oauth_key in OAUTH_CONFIG["google"]:
                        OAUTH_CONFIG["google"][oauth_key] = value
                elif key.startswith("APPLE_"):
                    oauth_key = key.replace("APPLE_", "").lower()
                    if oauth_key in OAUTH_CONFIG["apple"]:
                        OAUTH_CONFIG["apple"][oauth_key] = value


# OAuth Endpoints
@app.route("/api/auth/oauth/<provider>/url", methods=["GET"])
def get_oauth_url(provider):
    """Get OAuth authorization URL"""
    if provider not in ["google", "apple"]:
        return jsonify({"error": "Invalid OAuth provider"}), 400

    # Require redirect_uri in request (for security, don't fall back to config)
    redirect_uri = request.args.get("redirect_uri")
    if not redirect_uri:
        return jsonify({"error": "Redirect URI required"}), 400

    if provider == "google":
        if not OAUTH_CONFIG["google"].get("client_id"):
            return jsonify({"error": "Google OAuth not configured"}), 500

        scope = "openid email profile"
        params = {
            "client_id": OAUTH_CONFIG["google"]["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return jsonify({"url": auth_url})

    elif provider == "apple":
        if not OAUTH_CONFIG["apple"].get("client_id"):
            return jsonify({"error": "Apple OAuth not configured"}), 500

        params = {
            "client_id": OAUTH_CONFIG["apple"]["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "name email",
            "response_mode": "form_post",
        }
        auth_url = f"https://appleid.apple.com/auth/authorize?{urllib.parse.urlencode(params)}"
        return jsonify({"url": auth_url})

    return jsonify({"error": "Invalid OAuth provider"}), 400  # unreachable; makes all code paths explicit


@app.route("/api/auth/oauth/google/callback", methods=["POST"])
def google_oauth_callback():
    """Handle Google OAuth callback"""
    try:
        import requests
    except ImportError:
        return jsonify({"error": "requests library required for OAuth"}), 500

    data = request.get_json()
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")

    if not code or not redirect_uri:
        return jsonify({"error": "Code and redirect_uri required"}), 400

    if not OAUTH_CONFIG["google"].get("client_id") or not OAUTH_CONFIG["google"].get("client_secret"):
        return jsonify({"error": "Google OAuth not configured"}), 500

    try:
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": OAUTH_CONFIG["google"]["client_id"],
            "client_secret": OAUTH_CONFIG["google"]["client_secret"],
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
        email = userinfo.get("email", "")

        if not google_id:
            return jsonify({"error": "Invalid user info from Google"}), 400

        # Find or create user
        username = None
        oauth_id = f"google:{google_id}"

        # Check if user exists with this OAuth ID
        for user_key, user_data in USERS.items():
            if oauth_id in user_data.get("oauth_providers", []):
                username = user_key
                break

        # If not found, create new user
        if not username:
            if email:
                username_base = email.split("@")[0]
            else:
                username_base = f"google_user_{google_id[:8]}"

            username = username_base
            counter = 1
            while username in USERS:
                username = f"{username_base}_{counter}"
                counter += 1

            USERS[username] = {
                "username": username,
                "email": email,
                "oauth_providers": [oauth_id],
                "role": "admin" if len(USERS) == 0 else "user",
                "enabled": True,
                "created": datetime.now(timezone.utc).isoformat(),
            }
            save_users()
        else:
            if oauth_id not in USERS[username].get("oauth_providers", []):
                USERS[username].setdefault("oauth_providers", []).append(oauth_id)
                save_users()

        # Create session or token
        session["username"] = username
        token = generate_token(username) if JWT_AVAILABLE else None

        return jsonify(
            {
                "success": True,
                "message": "OAuth login successful",
                "user": {"username": username, "role": USERS[username].get("role", "user")},
                "token": token,
            }
        )

    except Exception as e:
        return jsonify({"error": f"OAuth callback error: {str(e)}"}), 500


@app.route("/api/auth/oauth/<provider>/link", methods=["POST"])
@require_auth
def link_oauth_account(provider):
    """Link OAuth account to existing user"""
    # Provider validity is checked in require_auth decorator

    username = request.user

    if username not in USERS:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")
    id_token = data.get("id_token")

    try:
        if provider == "google":
            if not code or not redirect_uri:
                return jsonify({"error": "Code and redirect_uri required"}), 400

            if not OAUTH_CONFIG["google"].get("client_id") or not OAUTH_CONFIG["google"].get("client_secret"):
                return jsonify({"error": "Google OAuth not configured"}), 500

            try:
                import requests

                # Exchange code for token
                token_url = "https://oauth2.googleapis.com/token"
                token_data = {
                    "code": code,
                    "client_id": OAUTH_CONFIG["google"]["client_id"],
                    "client_secret": OAUTH_CONFIG["google"]["client_secret"],
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

                oauth_id = f"google:{google_id}"

                # Check if this OAuth account is already linked to another user
                for user_key, user_data_check in USERS.items():
                    if user_key != username and oauth_id in user_data_check.get("oauth_providers", []):
                        return jsonify({"error": "This account is already linked to another user"}), 400

                # Link to current user
                if oauth_id not in USERS[username].get("oauth_providers", []):
                    USERS[username].setdefault("oauth_providers", []).append(oauth_id)
                    save_users()

                return jsonify(
                    {
                        "success": True,
                        "message": "Google account linked successfully",
                        "oauth_providers": USERS[username].get("oauth_providers", []),
                    }
                )

            except ImportError:
                return jsonify({"error": "requests library required for OAuth"}), 500

        elif provider == "apple":
            if not id_token:
                return jsonify({"error": "ID token required"}), 400

            if not OAUTH_CONFIG["apple"].get("client_id"):
                return jsonify({"error": "Apple OAuth not configured"}), 500

            if not JWT_AVAILABLE:
                return jsonify({"error": "JWT library required for Apple OAuth"}), 500

            # Decode JWT token without verification
            decoded = jwt.decode(id_token, options={"verify_signature": False})
            apple_id = decoded.get("sub")

            if not apple_id:
                return jsonify({"error": "Invalid ID token from Apple"}), 400

            oauth_id = f"apple:{apple_id}"

            # Check if this OAuth account is already linked to another user
            for user_key, user_data_check in USERS.items():
                if user_key != username and oauth_id in user_data_check.get("oauth_providers", []):
                    return jsonify({"error": "This account is already linked to another user"}), 400

            # Link to current user
            if oauth_id not in USERS[username].get("oauth_providers", []):
                USERS[username].setdefault("oauth_providers", []).append(oauth_id)
                save_users()

            return jsonify(
                {
                    "success": True,
                    "message": "Apple account linked successfully",
                    "oauth_providers": USERS[username].get("oauth_providers", []),
                }
            )

        else:
            return jsonify({"error": "Invalid provider"}), 400

    except Exception as e:
        return jsonify({"error": f"Failed to link OAuth account: {str(e)}"}), 500


@app.route("/api/auth/oauth/<provider>/unlink", methods=["POST"])
@require_auth
def unlink_oauth_account(provider):
    """Unlink OAuth account from user"""
    # Provider validity is checked in require_auth decorator

    username = request.user

    if username not in USERS:
        return jsonify({"error": "User not found"}), 404

    user = USERS[username]

    # Check if user has a password (can't unlink last auth method)
    has_password = "password_hash" in user
    oauth_providers = user.get("oauth_providers", [])

    # Count how many OAuth providers user has
    provider_count = sum(1 for p in oauth_providers if p.startswith(f"{provider}:"))

    if not has_password and len(oauth_providers) <= provider_count:
        return jsonify({"error": "Cannot unlink last authentication method"}), 400

    # Remove OAuth provider
    oauth_providers = [p for p in oauth_providers if not p.startswith(f"{provider}:")]
    user["oauth_providers"] = oauth_providers
    save_users()

    return jsonify(
        {
            "success": True,
            "message": f"{provider.title()} account unlinked successfully",
            "oauth_providers": oauth_providers,
        }
    )


@app.route("/api/auth/oauth/apple/callback", methods=["POST"])
def apple_oauth_callback():
    """Handle Apple OAuth callback"""
    data = request.get_json()
    id_token = data.get("id_token")

    if not id_token:
        return jsonify({"error": "ID token required"}), 400

    if not OAUTH_CONFIG["apple"].get("client_id"):
        return jsonify({"error": "Apple OAuth not configured"}), 500

    try:
        # Decode JWT token without verification
        if not JWT_AVAILABLE:
            return jsonify({"error": "JWT library required for Apple OAuth"}), 500

        decoded = jwt.decode(id_token, options={"verify_signature": False})
        apple_id = decoded.get("sub")
        email = decoded.get("email", "")

        if not apple_id:
            return jsonify({"error": "Invalid ID token from Apple"}), 400

        # Find or create user
        username = None
        oauth_id = f"apple:{apple_id}"

        for user_key, user_data_store in USERS.items():
            if oauth_id in user_data_store.get("oauth_providers", []):
                username = user_key
                break

        if not username:
            if email:
                username_base = email.split("@")[0]
            else:
                username_base = f"apple_user_{apple_id[:8]}"

            username = username_base
            counter = 1
            while username in USERS:
                username = f"{username_base}_{counter}"
                counter += 1

            USERS[username] = {
                "username": username,
                "email": email,
                "oauth_providers": [oauth_id],
                "role": "admin" if len(USERS) == 0 else "user",
                "enabled": True,
                "created": datetime.now(timezone.utc).isoformat(),
            }
            save_users()
        else:
            if oauth_id not in USERS[username].get("oauth_providers", []):
                USERS[username].setdefault("oauth_providers", []).append(oauth_id)
                save_users()

        session["username"] = username
        token = generate_token(username) if JWT_AVAILABLE else None

        return jsonify(
            {
                "success": True,
                "message": "OAuth login successful",
                "user": {"username": username, "role": USERS[username].get("role", "user")},
                "token": token,
            }
        )

    except Exception as e:
        return jsonify({"error": f"Failed to process Apple OAuth: {str(e)}"}), 500


# API Key Management Endpoints
@app.route("/api/keys", methods=["GET"])
@require_permission("api_keys.view")
def list_api_keys():
    """List all API keys (without showing full key values)"""
    try:
        keys_list = []
        for key, info in API_KEYS.items():
            keys_list.append(
                {
                    "id": key[:8] + "..." + key[-4:],  # Show preview only
                    "name": info.get("name", "Unknown"),
                    "description": info.get("description", ""),
                    "enabled": info.get("enabled", True),
                    "created": info.get("created", ""),
                    "role": info.get("role", DEFAULT_API_KEY_ROLE),
                    "permissions": get_api_key_permissions(info),
                }
            )
        return jsonify({"success": True, "keys": keys_list}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to list API keys: {str(e)}"}), 500


@app.route("/api/keys", methods=["POST"])
@require_permission("api_keys.manage")
def create_api_key():
    """Create a new API key"""
    try:
        data = request.get_json() or {}
        name = data.get("name")
        description = data.get("description", "")
        role = data.get("role", DEFAULT_API_KEY_ROLE)
        permissions = data.get("permissions")

        if not name:
            return jsonify({"error": "Key name is required"}), 400

        scope_error = validate_api_key_scope(role, permissions)
        if scope_error:
            return jsonify({"error": scope_error}), 400

        # Generate new API key
        api_key = generate_api_key()

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
        API_KEYS[api_key] = entry

        if not save_api_keys():
            del API_KEYS[api_key]
            return jsonify({"error": "Failed to save API key"}), 500

        log_audit_event(
            get_username_from_request(),
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
                    "permissions": get_api_key_permissions(entry),
                    "message": "API key created. Save this key securely - it will not be shown again.",
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to create API key: {str(e)}"}), 500


def _find_api_key(key_id):
    """Resolve the id shown by GET /api/keys back to the full key.

    The listing and the web UI use a preview — the first 8 characters, an
    ellipsis, then the last 4 — so that form has to resolve or every action
    taken from the API Keys page fails. Matching only a raw prefix or suffix
    meant it never did.

    An id that matches more than one key resolves to nothing rather than to
    whichever happened to come first in the dict.
    """
    if key_id in API_KEYS:
        return key_id

    if "..." in key_id:
        prefix, _, suffix = key_id.partition("...")
        matches = [k for k in API_KEYS if k.startswith(prefix) and k.endswith(suffix)]
    else:
        matches = [k for k in API_KEYS if k.startswith(key_id) or k.endswith(key_id)]

    return matches[0] if len(matches) == 1 else None


@app.route("/api/keys/<key_id>", methods=["PUT"])
@require_permission("api_keys.manage")
def update_api_key_scope(key_id):
    """Narrow or widen what an API key may do."""
    try:
        key = _find_api_key(key_id)
        if not key:
            return jsonify({"error": "API key not found"}), 404

        data = request.get_json() or {}
        if "role" not in data and "permissions" not in data:
            return jsonify({"error": "role or permissions required"}), 400

        entry = API_KEYS[key]
        role = data.get("role", entry.get("role", DEFAULT_API_KEY_ROLE))
        permissions = data["permissions"] if "permissions" in data else entry.get("permissions")

        scope_error = validate_api_key_scope(role, permissions)
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

        if not save_api_keys():
            API_KEYS[key] = previous
            return jsonify({"error": "Failed to save changes"}), 500

        log_audit_event(
            get_username_from_request(),
            "api_keys.scope",
            {"name": entry.get("name", "Unknown"), "role": role, "permissions": permissions},
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "API key scope updated",
                    "role": role,
                    "permissions": get_api_key_permissions(entry),
                }
            ),
            200,
        )
    except Exception as e:
        # The message is logged rather than returned: an exception raised while
        # re-scoping a credential can carry internals the caller should not see.
        app.logger.error(f"Failed to update API key scope: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/keys/<key_id>", methods=["DELETE"])
@require_permission("api_keys.manage")
def delete_api_key(key_id):
    """Delete an API key"""
    try:
        key_to_delete = _find_api_key(key_id)

        if not key_to_delete:
            return jsonify({"error": "API key not found"}), 404

        # Delete the key
        key_name = API_KEYS[key_to_delete].get("name", "Unknown")
        del API_KEYS[key_to_delete]

        if not save_api_keys():
            return jsonify({"error": "Failed to save changes"}), 500

        return jsonify({"success": True, "message": f"API key '{key_name}' deleted"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete API key: {str(e)}"}), 500


@app.route("/api/keys/<key_id>/enable", methods=["PUT"])
@require_permission("api_keys.manage")
def enable_api_key(key_id):
    """Enable an API key"""
    try:
        key_to_enable = _find_api_key(key_id)

        if not key_to_enable:
            return jsonify({"error": "API key not found"}), 404

        API_KEYS[key_to_enable]["enabled"] = True

        if not save_api_keys():
            return jsonify({"error": "Failed to save changes"}), 500

        return jsonify({"success": True, "message": "API key enabled"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to enable API key: {str(e)}"}), 500


@app.route("/api/keys/<key_id>/disable", methods=["PUT"])
@require_permission("api_keys.manage")
def disable_api_key(key_id):
    """Disable an API key"""
    try:
        key_to_disable = _find_api_key(key_id)

        if not key_to_disable:
            return jsonify({"error": "API key not found"}), 404

        API_KEYS[key_to_disable]["enabled"] = False

        if not save_api_keys():
            return jsonify({"error": "Failed to save changes"}), 500

        return jsonify({"success": True, "message": "API key disabled"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to disable API key: {str(e)}"}), 500


# Role and Permission Management Endpoints
@app.route("/api/users", methods=["GET"])
@require_permission("users.view")
def list_users():
    """List all users (without sensitive information)"""
    try:
        users_list = []
        for username, user_info in USERS.items():
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
    except Exception as e:
        return jsonify({"error": f"Failed to list users: {str(e)}"}), 500


@app.route("/api/users", methods=["POST"])
@require_permission("users.manage")
def create_user():
    """Create a user. This is how accounts are added once registration closes."""
    try:
        data = request.get_json() or {}
        username = data.get("username")
        password = data.get("password")
        email = data.get("email", "")
        role = data.get("role", "user")

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        if not BCRYPT_AVAILABLE:
            return jsonify({"error": "Password hashing not available"}), 500

        if len(username) < 3 or len(username) > 32:
            return jsonify({"error": "Username must be 3-32 characters"}), 400

        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400

        if role not in ROLE_PERMISSIONS:
            return (
                jsonify({"error": f"Invalid role. Valid roles: {', '.join(ROLE_PERMISSIONS.keys())}"}),
                400,
            )

        hashed_password = hash_password(password)

        with _users_lock:
            if username in USERS:
                return jsonify({"error": "Username already exists"}), 400

            USERS[username] = {
                "username": username,
                "password_hash": hashed_password,
                "email": email,
                "role": role,
                "enabled": True,
                "created": datetime.now(timezone.utc).isoformat(),
            }

            if not save_users():
                del USERS[username]
                return jsonify({"error": "Failed to save user"}), 500

        log_audit_event(get_username_from_request(), "users.create", {"username": username, "role": role})

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
    except Exception as e:
        app.logger.error(f"Failed to create user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/users/<username>/role", methods=["PUT"])
@require_permission("users.manage")
def update_user_role(username):
    """Update a user's role"""
    try:
        if username not in USERS:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}
        new_role = data.get("role")

        if not new_role:
            return jsonify({"error": "Role is required"}), 400

        # Validate role
        if new_role not in ROLE_PERMISSIONS:
            return (
                jsonify({"error": f"Invalid role. Valid roles: {', '.join(ROLE_PERMISSIONS.keys())}"}),
                400,
            )

        # Prevent removing the last admin
        if USERS[username].get("role") == "admin" and new_role != "admin":
            admin_count = sum(1 for u in USERS.values() if u.get("role") == "admin" and u.get("enabled", True))
            if admin_count <= 1:
                return (
                    jsonify({"error": "Cannot remove the last admin. At least one admin user must exist."}),
                    400,
                )

        USERS[username]["role"] = new_role

        if not save_users():
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
    except Exception as e:
        return jsonify({"error": f"Failed to update user role: {str(e)}"}), 500


@app.route("/api/users/<username>", methods=["DELETE"])
@require_permission("users.manage")
def delete_user(username):
    """Delete a user"""
    try:
        if username not in USERS:
            return jsonify({"error": "User not found"}), 404

        # Prevent deleting the last admin
        if USERS[username].get("role") == "admin":
            admin_count = sum(1 for u in USERS.values() if u.get("role") == "admin" and u.get("enabled", True))
            if admin_count <= 1:
                return (
                    jsonify({"error": "Cannot delete the last admin. At least one admin user must exist."}),
                    400,
                )

        # Prevent users from deleting themselves
        current_user = getattr(request, "user", None)
        if current_user == username:
            return jsonify({"error": "Cannot delete your own account"}), 400

        del USERS[username]

        if not save_users():
            return jsonify({"error": "Failed to save changes"}), 500

        return jsonify({"success": True, "message": f"User '{username}' deleted"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500


@app.route("/api/users/<username>/enable", methods=["PUT"])
@require_permission("users.manage")
def enable_user(username):
    """Enable a user account"""
    try:
        if username not in USERS:
            return jsonify({"error": "User not found"}), 404

        USERS[username]["enabled"] = True

        if not save_users():
            return jsonify({"error": "Failed to save changes"}), 500

        return jsonify({"success": True, "message": "User enabled"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to enable user: {str(e)}"}), 500


@app.route("/api/users/<username>/disable", methods=["PUT"])
@require_permission("users.manage")
def disable_user(username):
    """Disable a user account"""
    try:
        if username not in USERS:
            return jsonify({"error": "User not found"}), 404

        # Prevent disabling the last admin
        if USERS[username].get("role") == "admin":
            admin_count = sum(1 for u in USERS.values() if u.get("role") == "admin" and u.get("enabled", True))
            if admin_count <= 1:
                return (
                    jsonify({"error": "Cannot disable the last admin. At least one admin user must exist."}),
                    400,
                )

        USERS[username]["enabled"] = False

        if not save_users():
            return jsonify({"error": "Failed to save changes"}), 500

        return jsonify({"success": True, "message": "User disabled"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to disable user: {str(e)}"}), 500


@app.route("/api/permissions", methods=["GET"])
@require_auth
def get_permissions():
    """Get current user's permissions"""
    try:
        username = getattr(request, "user", None)
        if not username:
            return jsonify({"error": "Authentication required"}), 401

        user_permissions = get_user_permissions(username)
        user_role = USERS.get(username, {}).get("role", "user")

        return (
            jsonify(
                {
                    "success": True,
                    "permissions": user_permissions,
                    "role": user_role,
                    "all_permissions": PERMISSIONS,
                    "role_permissions": ROLE_PERMISSIONS,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to get permissions: {str(e)}"}), 500


@app.route("/api/roles", methods=["GET"])
@require_permission("users.view")
def list_roles():
    """List all available roles and their permissions"""
    try:
        roles_info = {}
        for role, permissions in ROLE_PERMISSIONS.items():
            roles_info[role] = {
                "permissions": permissions,
                "permission_count": len(permissions),
            }
        return jsonify({"success": True, "roles": roles_info}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to list roles: {str(e)}"}), 500


@app.route("/api/status", methods=["GET"])
@require_auth
@require_permission("server.view")
def get_status():
    """Get server status"""
    # Check if server is running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=minecraft-server", "--format", "{{.Status}}"],
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


@app.route("/api/server/start", methods=["POST"])
@require_permission("server.control")
def start_server():
    """Start the server"""
    username = get_username_from_request()
    log_audit_event(username, "server.start", {"action": "start_server"})

    stdout, stderr, code = run_script("manage.sh", "start", timeout=LONG_SCRIPT_TIMEOUT)

    if code == 0:
        output = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout
        return jsonify({"success": True, "message": "Server starting", "output": output}), 200
    else:
        error = (
            stderr.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes)
            else (stderr or "Failed to start server")
        )
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/server/stop", methods=["POST"])
@require_permission("server.control")
def stop_server():
    """Stop the server"""
    stdout, stderr, code = run_script("manage.sh", "stop", timeout=LONG_SCRIPT_TIMEOUT)

    if code == 0:
        return jsonify({"success": True, "message": "Server stopping", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Failed to stop server"}), 500


@app.route("/api/server/restart", methods=["POST"])
@require_permission("server.control")
def restart_server():
    """Restart the server"""
    stdout, stderr, code = run_script("manage.sh", "restart", timeout=LONG_SCRIPT_TIMEOUT)

    if code == 0:
        return jsonify({"success": True, "message": "Server restarting", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Failed to restart server"}), 500


@app.route("/api/server/command", methods=["POST"])
@require_permission("server.command")
@rate_limit(max_per_minute=30, per_endpoint=True)
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
    if SECURITY_AVAILABLE:
        is_valid, sanitized_command, error_msg = sanitize_minecraft_command(command)
        if not is_valid:
            log_audit_event(
                get_username_from_request(),
                "server.command.rejected",
                {"original_command": sanitize_string(command[:100]), "reason": error_msg},  # Log first 100 chars only
            )
            return jsonify({"error": "Invalid command format"}), 400
        command = sanitized_command
    else:
        # Basic sanitization if security module not available
        command = sanitize_string(command, max_length=256) if SECURITY_AVAILABLE else command[:256]

    username = get_username_from_request()
    log_audit_event(username, "server.command", {"command": sanitize_string(command[:100])})

    stdout, stderr, code = run_rcon_command(command)

    if code == 0:
        # Sanitize response before returning
        safe_stdout = sanitize_string(stdout, max_length=5000) if SECURITY_AVAILABLE and stdout else stdout
        return jsonify({"success": True, "response": safe_stdout, "command": sanitize_string(command[:100])}), 200
    else:
        # Don't expose detailed error messages - generic error only
        error_msg = "Command execution failed"
        if SECURITY_AVAILABLE and stderr:
            # Only log detailed error, don't expose to client
            safe_stderr = sanitize_string(stderr[:500])
            log_audit_event(username, "server.command.failed", {"error": safe_stderr[:100]})
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/backup", methods=["POST"])
@require_permission("backup.create")
def create_backup():
    """Create a server backup"""
    username = get_username_from_request()
    log_audit_event(username, "backup.create", {"action": "create_backup"})

    stdout, stderr, code = run_script("manage.sh", "backup", timeout=LONG_SCRIPT_TIMEOUT)

    if code == 0:
        output = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout
        return jsonify({"success": True, "message": "Backup created", "output": output}), 200
    else:
        error = stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else (stderr or "Backup failed")
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/backups", methods=["GET"])
@require_permission("backup.view")
def list_backups():
    """List available backups"""
    backups_dir = PROJECT_ROOT / "backups"
    backups = []

    if backups_dir.exists():
        for backup_file in backups_dir.glob("minecraft_backup_*.tar.gz"):
            stat = backup_file.stat()
            backups.append(
                {
                    "name": backup_file.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(backup_file.relative_to(PROJECT_ROOT)),
                }
            )

    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x["created"], reverse=True)

    return jsonify({"backups": backups, "count": len(backups)})


@app.route("/api/scheduler/schedules", methods=["GET"])
@require_permission("server.command")
def list_schedules():
    """List all scheduled commands"""
    try:
        return jsonify({"success": True, "schedules": _load_schedules().get("schedules", [])}), 200
    except Exception as e:
        app.logger.error(f"Failed to list schedules: {e}")
        return jsonify({"error": "Internal server error"}), 500


# The types scripts/command-scheduler.py knows how to fire. Anything else would
# be written to the file and then silently never run.
SCHEDULE_TYPES = ("interval", "daily", "weekly", "cron", "once")


@contextmanager
def _schedule_lock():
    """Hold an exclusive lock for the length of a read-modify-write.

    scripts/command-scheduler.py writes this file too, recording last_run and
    run_count on every pass. Without a lock, a pass that started before an API
    write lands will write the pre-edit list back over it, and a reader can
    catch the file mid-truncate. The daemon takes the same lock on the same
    path, so the two exclude each other.
    """
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = SCHEDULE_FILE.with_name(SCHEDULE_FILE.name + ".lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _load_schedules():
    """Read the schedule file the scheduler daemon runs from."""
    if not SCHEDULE_FILE.exists():
        return {"schedules": []}
    try:
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Matches the daemon, which also treats an unreadable file as empty
        # rather than refusing to run at all.
        app.logger.error("Schedule file is not valid JSON; treating it as empty")
        return {"schedules": []}


def _save_schedules(schedule_data):
    """Write the schedule file back, atomically.

    Truncating in place lets the daemon read half a document; writing a
    sibling and renaming means it sees either the old file or the new one.
    """
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(SCHEDULE_FILE.parent), prefix=".schedule-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(schedule_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, SCHEDULE_FILE)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def _schedule_type_fields(schedule_type, data):
    """Pick out the fields a given schedule type needs.

    Returns (fields, error). The defaults match
    ``scripts/command-scheduler.py``'s own reader, so a record written here
    behaves the same as one the script wrote.
    """
    if schedule_type == "interval":
        return {"interval_minutes": data.get("interval_minutes", 60)}, None
    if schedule_type == "daily":
        return {"run_time": data.get("run_time", "00:00")}, None
    if schedule_type == "weekly":
        return {
            "day_of_week": data.get("day_of_week", 0),
            "run_time": data.get("run_time", "00:00"),
        }, None
    if schedule_type == "cron":
        expression = data.get("cron_expression")
        if not expression:
            return None, "cron_expression is required for cron schedules"
        return {"cron_expression": expression}, None
    if schedule_type == "once":
        run_datetime = data.get("run_datetime")
        if not run_datetime:
            return None, "run_datetime is required for once schedules"
        return {"run_datetime": run_datetime}, None
    return None, f"Invalid type. Valid types: {', '.join(SCHEDULE_TYPES)}"


@app.route("/api/scheduler/schedules", methods=["POST"])
@require_permission("server.command")
def create_schedule():
    """Create a new scheduled command"""
    try:
        data = request.get_json() or {}
        command = data.get("command")
        schedule_type = data.get("type", "interval")
        enabled = data.get("enabled", True)

        if not command:
            return jsonify({"error": "Command required"}), 400

        type_fields, error = _schedule_type_fields(schedule_type, data)
        if error:
            return jsonify({"error": error}), 400

        condition = data.get("condition")
        if condition is not None and not isinstance(condition, dict):
            return jsonify({"error": "condition must be an object"}), 400

        schedule = {
            "id": str(uuid.uuid4()),
            "command": command,
            "type": schedule_type,
            "enabled": enabled,
            "created": datetime.now(timezone.utc).isoformat(),
            "last_run": None,
            # The scheduler increments this; start it where the script does so
            # a record created here is indistinguishable from one it wrote.
            "run_count": 0,
        }
        schedule.update(type_fields)

        if condition:
            schedule["condition"] = condition

        with _schedule_lock():
            schedule_data = _load_schedules()
            schedule_data.setdefault("schedules", []).append(schedule)
            _save_schedules(schedule_data)

        username = get_username_from_request()
        log_audit_event(
            username, "scheduler.create", {"schedule_id": schedule["id"], "command": command}
        )

        return jsonify({"success": True, "schedule": schedule}), 201
    except Exception as e:
        app.logger.error(f"Failed to create schedule: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/scheduler/schedules/<schedule_id>/enable", methods=["PUT"])
@require_permission("server.command")
def enable_schedule(schedule_id):
    """Enable a scheduled command"""
    return _set_schedule_enabled(schedule_id, True)


@app.route("/api/scheduler/schedules/<schedule_id>/disable", methods=["PUT"])
@require_permission("server.command")
def disable_schedule(schedule_id):
    """Disable a scheduled command"""
    return _set_schedule_enabled(schedule_id, False)


def _set_schedule_enabled(schedule_id, enabled):
    """Shared body of the enable and disable endpoints."""
    try:
        with _schedule_lock():
            schedule_data = _load_schedules()
            target = next(
                (s for s in schedule_data.get("schedules", []) if s.get("id") == schedule_id), None
            )
            if target is None:
                return jsonify({"error": "Schedule not found"}), 404

            target["enabled"] = enabled
            _save_schedules(schedule_data)

        log_audit_event(
            get_username_from_request(),
            "scheduler.enable" if enabled else "scheduler.disable",
            {"schedule_id": schedule_id},
        )
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Schedule {'enabled' if enabled else 'disabled'}",
                    "schedule": target,
                }
            ),
            200,
        )
    except Exception as e:
        app.logger.error(f"Failed to change schedule state: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/scheduler/schedules/<schedule_id>", methods=["PUT"])
@require_permission("server.command")
def update_schedule(schedule_id):
    """Update a scheduled command"""
    try:
        data = request.get_json() or {}

        if "condition" in data and data["condition"] is not None and not isinstance(data["condition"], dict):
            return jsonify({"error": "condition must be an object"}), 400

        with _schedule_lock():
            return _update_schedule_locked(schedule_id, data)
    except Exception as e:
        app.logger.error(f"Failed to update schedule: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _update_schedule_locked(schedule_id, data):
    """Body of the update endpoint, run while holding the schedule lock."""
    schedule_data = _load_schedules()

    schedule = next(
        (s for s in schedule_data.get("schedules", []) if s.get("id") == schedule_id), None
    )
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404

    # A type change brings its own required fields with it, so validate the
    # result rather than letting a schedule end up as, say, a cron with no
    # expression — which the scheduler would skip forever without saying so.
    new_type = data.get("type", schedule.get("type"))
    if new_type not in SCHEDULE_TYPES:
        return jsonify({"error": f"Invalid type. Valid types: {', '.join(SCHEDULE_TYPES)}"}), 400

    merged = {**schedule, **{k: v for k, v in data.items() if k != "type"}}
    type_fields, error = _schedule_type_fields(new_type, merged)
    if error:
        return jsonify({"error": error}), 400

    if "command" in data:
        schedule["command"] = data["command"]
    if "enabled" in data:
        schedule["enabled"] = data["enabled"]
    if "condition" in data:
        if data["condition"]:
            schedule["condition"] = data["condition"]
        else:
            schedule.pop("condition", None)

    # Drop the old type's fields so a schedule switched from daily to
    # interval doesn't keep a stale run_time hanging off it.
    for stale in ("interval_minutes", "run_time", "day_of_week", "cron_expression", "run_datetime"):
        schedule.pop(stale, None)
    schedule["type"] = new_type
    schedule.update(type_fields)

    _save_schedules(schedule_data)

    log_audit_event(get_username_from_request(), "scheduler.update", {"schedule_id": schedule_id})

    return jsonify({"success": True, "schedule": schedule}), 200


@app.route("/api/scheduler/schedules/<schedule_id>", methods=["DELETE"])
@require_permission("server.command")
def delete_schedule(schedule_id):
    """Delete a scheduled command"""
    try:
        with _schedule_lock():
            schedule_data = _load_schedules()
            schedules = schedule_data.get("schedules", [])

            remaining = [s for s in schedules if s.get("id") != schedule_id]
            # Reporting success for an id that was never there hides a typo in
            # the caller, and the old handler did exactly that.
            if len(remaining) == len(schedules):
                return jsonify({"error": "Schedule not found"}), 404

            schedule_data["schedules"] = remaining
            _save_schedules(schedule_data)

        username = get_username_from_request()
        log_audit_event(username, "scheduler.delete", {"schedule_id": schedule_id})

        return jsonify({"success": True, "message": "Schedule deleted"}), 200
    except Exception as e:
        app.logger.error(f"Failed to delete schedule: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/audit/logs", methods=["GET"])
@require_permission("logs.view")
def get_audit_logs():
    """Get audit logs"""
    try:
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        action_filter = request.args.get("action")
        username_filter = request.args.get("username")

        logs = []
        if AUDIT_LOG_FILE.exists():
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            log_entry = json.loads(line.strip())
                            # Apply filters
                            if action_filter and log_entry.get("action") != action_filter:
                                continue
                            if username_filter and log_entry.get("username") != username_filter:
                                continue
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            continue

        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Apply pagination
        total = len(logs)
        logs = logs[offset : offset + limit]

        return (
            jsonify(
                {
                    "success": True,
                    "logs": logs,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to get audit logs: {str(e)}"}), 500


@app.route("/api/backups/<path:filename>/restore", methods=["POST"])
@require_permission("backup.restore")
def restore_backup(filename):
    """Restore a backup"""
    username = get_username_from_request()
    log_audit_event(username, "backup.restore", {"filename": filename})

    # Check for path traversal attacks first
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid backup filename"}), 400

    backups_dir = PROJECT_ROOT / "backups"
    backup_path = backups_dir / filename

    # Check if file exists first (404 takes precedence over format validation)
    if not backup_path.exists():
        return jsonify({"error": "Backup not found"}), 404

    # Validate backup file format
    if not filename.startswith("minecraft_backup_") or not filename.endswith(".tar.gz"):
        return jsonify({"error": "Invalid backup file format"}), 400

    data_dir = PROJECT_ROOT / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Stop server before restore
        run_script("manage.sh", "stop", timeout=LONG_SCRIPT_TIMEOUT)

        # Create a backup of current state before restoring
        current_backup = backups_dir / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        if data_dir.exists() and any(data_dir.iterdir()):
            import tarfile

            with tarfile.open(current_backup, "w:gz") as tar:
                tar.add(data_dir, arcname=".")

        # Extract backup — validate members first to prevent path traversal (tarslip)
        import tarfile

        def _safe_members(tf, dest):
            resolved_dest = Path(dest).resolve()
            for member in tf.getmembers():
                member_path = (resolved_dest / member.name).resolve()
                if not member_path.is_relative_to(resolved_dest):
                    raise ValueError(f"Unsafe path in archive member: {member.name}")
                yield member

        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=data_dir, members=_safe_members(tar, data_dir))

        return jsonify(
            {
                "success": True,
                "message": "Backup restored successfully",
                "pre_restore_backup": str(current_backup.relative_to(PROJECT_ROOT)),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to restore backup: {str(e)}"}), 500


@app.route("/api/backups/<path:filename>", methods=["DELETE"])
@require_permission("backup.delete")
def delete_backup(filename):
    """Delete a backup"""
    # Check for path traversal attacks first
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid backup filename"}), 400

    backups_dir = PROJECT_ROOT / "backups"
    backup_path = backups_dir / filename

    # Check if file exists first (404 takes precedence over format validation)
    if not backup_path.exists():
        return jsonify({"error": "Backup not found"}), 404

    # Validate backup file format
    if not filename.startswith("minecraft_backup_") or not filename.endswith(".tar.gz"):
        return jsonify({"error": "Invalid backup file format"}), 400

    try:
        backup_path.unlink()
        return jsonify({"success": True, "message": "Backup deleted successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to delete backup: {str(e)}"}), 500


@app.route("/api/logs", methods=["GET"])
@require_permission("logs.view")
def get_logs():
    """Get server logs"""
    lines = request.args.get("lines", 100, type=int)

    _, stderr, _ = run_script("manage.sh", "logs")

    # Get last N lines from Docker logs
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), "minecraft-server"], capture_output=True, text=True, timeout=10
        )
        logs = result.stdout if result.returncode == 0 else stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logs = stderr or "Unable to retrieve logs"

    return jsonify({"logs": logs.split("\n"), "lines": len(logs.split("\n"))})


@app.route("/api/events", methods=["GET"])
@require_permission("logs.view")
def get_game_events():
    """Return recent game events, newest first.

    Query parameters: `limit` (default 100, capped at 500), `type` to filter by
    event type, and `player` to filter by player name.
    """
    if not EVENTS_AVAILABLE:
        return jsonify({"error": "Event capture is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    event_type = request.args.get("type")
    if event_type and event_type not in game_events.ALL_EVENT_TYPES:
        return jsonify({"error": "Unknown event type", "valid_types": list(game_events.ALL_EVENT_TYPES)}), 400

    player = request.args.get("player")
    if player:
        player = sanitize_string(player, max_length=16)

    try:
        records = game_events.get_bus().read(limit=limit, event_type=event_type, player=player)
    except Exception as e:
        app.logger.error(f"Error reading events: {e}")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"events": records, "count": len(records)})


@app.route("/api/events/types", methods=["GET"])
@require_permission("logs.view")
def get_game_event_types():
    """List the event types the bus can produce."""
    if not EVENTS_AVAILABLE:
        return jsonify({"error": "Event capture is unavailable"}), 503
    return jsonify({"types": list(game_events.ALL_EVENT_TYPES)})


@app.route("/api/deaths", methods=["GET"])
@require_permission("players.view")
def get_deaths():
    """Return recent deaths with their epitaphs, newest first.

    Query parameters: `limit` (default 50, capped at 200), `player`, and
    `category` to filter by how they died.
    """
    if not DEATHS_AVAILABLE:
        return jsonify({"error": "The Hall of Deaths is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    player = request.args.get("player")
    if player:
        player = sanitize_string(player, max_length=16)

    category = request.args.get("category")
    if category:
        category = sanitize_string(category, max_length=32)

    try:
        hall = hall_of_deaths.get_hall()
        return jsonify(
            {
                "deaths": hall.read(limit=limit, player=player, category=category),
                "stats": hall.stats(),
            }
        )
    except Exception as e:
        app.logger.error(f"Error reading deaths: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/deaths/leaderboard", methods=["GET"])
@require_permission("players.view")
def get_deaths_leaderboard():
    """Per-player death totals, most deaths first."""
    if not DEATHS_AVAILABLE:
        return jsonify({"error": "The Hall of Deaths is unavailable"}), 503

    try:
        limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400

    try:
        return jsonify({"leaderboard": hall_of_deaths.get_hall().leaderboard(limit=limit)})
    except Exception as e:
        app.logger.error(f"Error building the death leaderboard: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/bedtime", methods=["GET"])
@require_permission("server.view")
def get_bedtime_status():
    """Current bedtime status: when it is, how long is left, whether it holds."""
    if not BEDTIME_AVAILABLE:
        return jsonify({"error": "Bedtime mode is unavailable"}), 503

    try:
        return jsonify(bedtime_mode.get_bedtime().status())
    except Exception as e:
        app.logger.error(f"Error reading bedtime status: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _bedtime_control(operation):
    """Shared plumbing for the three bedtime controls.

    Each returns (ok, message); a refusal is a 409 because the request was
    well-formed and the server simply will not do it right now.
    """
    if not BEDTIME_AVAILABLE:
        return jsonify({"error": "Bedtime mode is unavailable"}), 503

    try:
        ok, message = operation(bedtime_mode.get_bedtime())
    except Exception as e:
        app.logger.error(f"Bedtime control failed: {e}")
        return jsonify({"error": "Internal server error"}), 500

    log_audit_event(get_username_from_request(), "bedtime.control", {"result": sanitize_string(message[:100])})
    if not ok:
        return jsonify({"success": False, "error": message}), 409
    return jsonify({"success": True, "message": message, "status": bedtime_mode.get_bedtime().status()})


@app.route("/api/bedtime/extend", methods=["POST"])
@require_permission("server.control")
def extend_bedtime():
    """Grant "five more minutes", within the configured limit."""
    return _bedtime_control(lambda bed: bed.extend())


@app.route("/api/bedtime/skip", methods=["POST"])
@require_permission("server.control")
def skip_bedtime():
    """Cancel bedtime for tonight only."""
    return _bedtime_control(lambda bed: bed.skip_tonight())


@app.route("/api/bedtime/now", methods=["POST"])
@require_permission("server.control")
def start_bedtime_now():
    """Bring bedtime forward to right now."""
    return _bedtime_control(lambda bed: bed.start_now())


@app.route("/api/players", methods=["GET"])
@require_permission("players.view")
def get_players():
    """Get list of online players"""
    stdout, _, _ = run_rcon_command("list")

    # Parse player list from RCON response
    players = []
    if stdout:
        # Extract player names from RCON response
        import re

        match = re.search(r"online:\s*(.+)", stdout)
        if match:
            player_list = match.group(1).strip()
            players = [p.strip() for p in player_list.split(",") if p.strip()]

    return jsonify({"players": players, "count": len(players)})


@app.route("/api/players/whitelist", methods=["GET"])
@require_permission("players.manage")
def get_whitelist():
    """Get whitelisted players"""
    try:
        whitelist_file = PROJECT_ROOT / "data" / "whitelist.json"
        if not whitelist_file.exists():
            return jsonify({"success": True, "players": []}), 200

        with open(whitelist_file, "r") as f:
            whitelist = json.load(f)

        return jsonify({"success": True, "players": whitelist}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get whitelist: {str(e)}"}), 500


@app.route("/api/players/whitelist", methods=["POST"])
@require_permission("players.manage")
def add_whitelist():
    """Add player to whitelist"""
    try:
        data = request.get_json() or {}
        player = data.get("player")
        if not player:
            return jsonify({"error": "Player name required"}), 400

        stdout, stderr, code = run_script("whitelist-manager.sh", "add", player)
        if code == 0:
            return jsonify({"success": True, "message": f"Player '{player}' added to whitelist"}), 200
        else:
            return jsonify({"error": stderr or "Failed to add player to whitelist"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to add to whitelist: {str(e)}"}), 500


@app.route("/api/players/whitelist/<player>", methods=["DELETE"])
@require_permission("players.manage")
def remove_whitelist(player):
    """Remove player from whitelist"""
    try:
        stdout, stderr, code = run_script("whitelist-manager.sh", "remove", player)
        if code == 0:
            return jsonify({"success": True, "message": f"Player '{player}' removed from whitelist"}), 200
        else:
            return jsonify({"error": stderr or "Failed to remove player from whitelist"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to remove from whitelist: {str(e)}"}), 500


@app.route("/api/players/banned", methods=["GET"])
@require_permission("players.manage")
def get_banned():
    """Get banned players"""
    try:
        banned_file = PROJECT_ROOT / "data" / "banned-players.json"
        if not banned_file.exists():
            return jsonify({"success": True, "players": []}), 200

        with open(banned_file, "r") as f:
            banned = json.load(f)

        return jsonify({"success": True, "players": banned}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get ban list: {str(e)}"}), 500


@app.route("/api/players/ban", methods=["POST"])
@require_permission("players.manage")
def ban_player():
    """Ban a player"""
    try:
        data = request.get_json() or {}
        player = data.get("player")
        reason = data.get("reason", "Banned by operator")
        if not player:
            return jsonify({"error": "Player name required"}), 400

        username = get_username_from_request()
        log_audit_event(username, "player.ban", {"player": player, "reason": reason})

        stdout, stderr, code = run_script("ban-manager.sh", "ban", player, reason)
        if code == 0:
            return jsonify({"success": True, "message": f"Player '{player}' banned"}), 200
        else:
            return jsonify({"error": stderr or "Failed to ban player"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to ban player: {str(e)}"}), 500


@app.route("/api/players/ban/<player>", methods=["DELETE"])
@require_permission("players.manage")
def unban_player(player):
    """Unban a player"""
    try:
        stdout, stderr, code = run_script("ban-manager.sh", "unban", player)
        if code == 0:
            return jsonify({"success": True, "message": f"Player '{player}' unbanned"}), 200
        else:
            return jsonify({"error": stderr or "Failed to unban player"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to unban player: {str(e)}"}), 500


@app.route("/api/players/ops", methods=["GET"])
@require_permission("players.manage")
def get_ops():
    """Get operators"""
    try:
        ops_file = PROJECT_ROOT / "data" / "ops.json"
        if not ops_file.exists():
            return jsonify({"success": True, "operators": []}), 200

        with open(ops_file, "r") as f:
            ops = json.load(f)

        return jsonify({"success": True, "operators": ops}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get operators: {str(e)}"}), 500


@app.route("/api/players/op", methods=["POST"])
@require_permission("players.manage")
def grant_op():
    """Grant operator status"""
    try:
        data = request.get_json() or {}
        player = data.get("player")
        level = data.get("level", 4)
        if not player:
            return jsonify({"error": "Player name required"}), 400

        stdout, stderr, code = run_script("op-manager.sh", "grant", player, str(level))
        if code == 0:
            return jsonify({"success": True, "message": f"Operator status granted to '{player}'"}), 200
        else:
            return jsonify({"error": stderr or "Failed to grant operator status"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to grant operator: {str(e)}"}), 500


@app.route("/api/players/op/<player>", methods=["DELETE"])
@require_permission("players.manage")
def revoke_op(player):
    """Revoke operator status"""
    try:
        stdout, stderr, code = run_script("op-manager.sh", "revoke", player)
        if code == 0:
            return jsonify({"success": True, "message": f"Operator status revoked from '{player}'"}), 200
        else:
            return jsonify({"error": stderr or "Failed to revoke operator status"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to revoke operator: {str(e)}"}), 500


@app.route("/api/server/properties", methods=["GET"])
@require_permission("server.manage")
def get_server_properties():
    """Get all server properties"""
    try:
        props_file = PROJECT_ROOT / "data" / "server.properties"
        if not props_file.exists():
            return jsonify({"error": "server.properties not found"}), 404

        properties = {}
        with open(props_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    properties[key.strip()] = value.strip()

        return jsonify({"success": True, "properties": properties}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get server properties: {str(e)}"}), 500


@app.route("/api/server/properties/<key>", methods=["GET"])
@require_permission("server.manage")
def get_server_property(key):
    """Get specific server property"""
    try:
        stdout, stderr, code = run_script("server-properties-manager.sh", "get", key)
        if code == 0:
            return jsonify({"success": True, "key": key, "value": stdout.strip()}), 200
        else:
            return jsonify({"error": stderr or f"Property '{key}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get property: {str(e)}"}), 500


@app.route("/api/server/properties/<key>", methods=["PUT"])
@require_permission("server.manage")
def set_server_property(key):
    """Set server property"""
    try:
        data = request.get_json() or {}
        value = data.get("value")
        if value is None:
            return jsonify({"error": "Value is required"}), 400

        stdout, stderr, code = run_script("server-properties-manager.sh", "set", key, str(value))
        if code == 0:
            return jsonify({"success": True, "message": f"Property '{key}' set to '{value}'"}), 200
        else:
            return jsonify({"error": stderr or "Failed to set property"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to set property: {str(e)}"}), 500


# The presets themselves live in scripts/server-properties-manager.sh; this
# list only decides what the API passes through to it. The script also answers
# to the aliases "performance" and "high", which its own help does not mention;
# the API exposes the three documented names only.
SERVER_PROPERTY_PRESETS = ("low-end", "balanced", "high-performance")


@app.route("/api/server/properties/preset", methods=["POST"])
@require_permission("server.manage")
def apply_server_preset():
    """Apply a performance preset to server.properties"""
    try:
        data = request.get_json() or {}
        requested = data.get("preset")
        if not requested:
            return jsonify({"error": "Preset name required"}), 400

        # Resolve the request to the matching constant and carry that onward,
        # so nothing downstream — the script argument, the log line, the audit
        # entry — handles the caller's string.
        preset = next((p for p in SERVER_PROPERTY_PRESETS if p == requested), None)
        if preset is None:
            return (
                jsonify({"error": f"Invalid preset. Valid: {', '.join(SERVER_PROPERTY_PRESETS)}"}),
                400,
            )

        stdout, stderr, code = run_script("server-properties-manager.sh", "preset", preset)
        if code != 0:
            # stderr carries filesystem paths, so it goes to the log rather
            # than to the caller, and it is subprocess output going into a log
            # line, so it is stripped of newlines first — otherwise it could
            # forge entries of its own.
            app.logger.error("Preset '%s' failed: %s", preset, sanitize_string(stderr, max_length=200))
            return jsonify({"error": "Failed to apply preset"}), 500

        log_audit_event(get_username_from_request(), "server.properties.preset", {"preset": preset})
        return jsonify({"success": True, "message": f"Preset '{preset}' applied"}), 200
    except Exception as e:
        app.logger.error(f"Failed to apply server preset: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Player Statistics Endpoints
#
# These read <world>/stats/<uuid>.json and <world>/advancements/<uuid>.json,
# which the game writes and keeps current. There is no collection step: the
# number in the file is the answer, so a read is idempotent. The log-scraping
# tracker these replaced added its findings to the previous totals on every
# run, so the same unchanged log reported 1, then 2, then 3.
def _require_player_stats():
    """None when the module is importable, otherwise the error to return."""
    if PLAYER_STATS_AVAILABLE:
        return None
    return jsonify({"error": "Player statistics are unavailable"}), 503


@app.route("/api/players/stats", methods=["GET"])
@require_permission("players.view")
def get_all_player_stats():
    """Statistics for every player the world has a file for"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    try:
        players = [p.as_dict() for p in player_stats.read_all()]
        return jsonify({"success": True, "players": players, "count": len(players)}), 200
    except Exception as e:
        app.logger.error(f"Failed to read player stats: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/players/stats/leaderboard", methods=["GET"])
@require_permission("players.view")
def get_player_stats_leaderboard():
    """Rank players by one counter"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    metric = request.args.get("metric", "play_time_minutes")
    try:
        limit = int(request.args.get("limit", "10"))
    except ValueError:
        return jsonify({"error": "limit must be a number"}), 400

    try:
        return jsonify({"success": True, **player_stats.leaderboard(metric, limit)}), 200
    except ValueError:
        # An unknown metric is the caller's mistake, so name the ones that
        # exist. The message is built here from our own list rather than
        # passing the exception's text out, which would be a route for
        # internals to reach the caller.
        valid = ", ".join(sorted(player_stats.LEADERBOARD_METRICS))
        return jsonify({"error": f"Unknown metric. Valid: {valid}"}), 400
    except Exception as e:
        app.logger.error(f"Failed to build the leaderboard: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/players/stats/metrics", methods=["GET"])
@require_permission("players.view")
def get_player_stats_metrics():
    """The counters a leaderboard can be built on"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    return jsonify({"success": True, "metrics": player_stats.LEADERBOARD_METRICS}), 200


# Werkzeug matches static rules ahead of converters regardless of registration
# order, so /leaderboard and /metrics above are not captured by <player>. A
# test pins that, since it is the kind of thing that breaks silently.
@app.route("/api/players/stats/<player>", methods=["GET"])
@require_permission("players.view")
def get_player_stats(player):
    """One player's statistics, by name"""
    unavailable = _require_player_stats()
    if unavailable:
        return unavailable

    try:
        found = player_stats.find_by_name(player)
    except Exception as e:
        app.logger.error(f"Failed to read player stats: {e}")
        return jsonify({"error": "Internal server error"}), 500

    if found is None:
        return jsonify({"error": "Player not found"}), 404

    include_raw = request.args.get("raw", "").lower() in ("1", "true", "yes")
    return jsonify({"success": True, "player": found.name, "stats": found.as_dict(include_raw)}), 200


# Announcement Endpoints
@app.route("/api/announcements", methods=["GET"])
@require_permission("server.manage")
def get_announcements():
    """Get all announcements"""
    try:
        stdout, stderr, code = run_script("announcement-manager.sh", "list")
        if code == 0:
            data = json.loads(stdout)
            return jsonify({"success": True, "announcements": data.get("announcements", [])}), 200
        else:
            return jsonify({"error": stderr or "Failed to get announcements"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to get announcements: {str(e)}"}), 500


@app.route("/api/announcements", methods=["POST"])
@require_permission("server.manage")
def create_announcement():
    """Create a new announcement"""
    try:
        data = request.get_json() or {}
        message = data.get("message")
        ann_type = data.get("type", "say")
        schedule_type = data.get("schedule_type")
        schedule_time = data.get("schedule_time")
        enabled = data.get("enabled", True)

        if not message:
            return jsonify({"error": "Message required"}), 400

        stdout, stderr, code = run_script(
            "announcement-manager.sh",
            "create",
            message,
            ann_type,
            schedule_type or "",
            schedule_time or "",
            str(enabled),
        )
        if code == 0:
            import json

            announcement = json.loads(stdout)
            return jsonify({"success": True, "announcement": announcement}), 200
        else:
            return jsonify({"error": stderr or "Failed to create announcement"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to create announcement: {str(e)}"}), 500


@app.route("/api/announcements/<announcement_id>/send", methods=["POST"])
@require_permission("server.manage")
def send_announcement(announcement_id):
    """Send an announcement immediately"""
    try:
        stdout, stderr, code = run_script("announcement-manager.sh", "send", announcement_id)
        if code == 0:
            return jsonify({"success": True, "message": "Announcement sent"}), 200
        else:
            return jsonify({"error": stderr or "Failed to send announcement"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to send announcement: {str(e)}"}), 500


@app.route("/api/announcements/<announcement_id>", methods=["DELETE"])
@require_permission("server.manage")
def delete_announcement(announcement_id):
    """Delete an announcement"""
    try:
        stdout, stderr, code = run_script("announcement-manager.sh", "delete", announcement_id)
        if code == 0:
            return jsonify({"success": True, "message": "Announcement deleted"}), 200
        else:
            return jsonify({"error": stderr or "Failed to delete announcement"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to delete announcement: {str(e)}"}), 500


@app.route("/api/metrics", methods=["GET"])
@require_permission("metrics.view")
def get_metrics():
    """Get server metrics"""
    # Run monitor script
    _, _, _ = run_script("monitor.sh")

    metrics = {}

    # Try to get Docker stats
    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "minecraft-server",
                "--no-stream",
                "--format",
                "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                metrics["cpu_percent"] = parts[0].rstrip("%")
                metrics["memory_usage"] = parts[1]
                metrics["memory_percent"] = parts[2].rstrip("%")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # Metrics are best-effort; missing values are acceptable

    return jsonify({"metrics": metrics, "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/api/analytics/collect", methods=["POST"])
@require_permission("analytics.view")
def collect_analytics():
    """Trigger analytics data collection"""
    try:
        stdout, stderr, code = run_script("analytics-collector.sh")
        if code == 0:
            return jsonify({"success": True, "message": "Analytics data collected"}), 200
        else:
            return jsonify({"error": stderr or "Failed to collect analytics"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to collect analytics: {str(e)}"}), 500


@app.route("/api/analytics/report", methods=["GET"])
@require_permission("analytics.view")
def get_analytics_report():
    """Get analytics report"""
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "analytics-processor.py"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            return jsonify({"error": "Failed to generate report", "details": result.stderr}), 500

        # Load latest report
        report_file = PROJECT_ROOT / "analytics" / "processed" / "latest_report.json"
        if report_file.exists():
            with open(report_file, "r") as f:
                report = json.load(f)
            return jsonify({"report": report}), 200
        else:
            return jsonify({"error": "Report not available"}), 404

    except Exception as e:
        return jsonify({"error": f"Failed to get report: {str(e)}"}), 500


@app.route("/api/analytics/trends", methods=["GET"])
@require_permission("analytics.view")
def get_analytics_trends():
    """Get performance trends"""
    try:
        hours = int(request.args.get("hours", 24))
        metric_type = request.args.get("type", "performance")  # performance, players, network

        # Import analytics processor
        sys.path.insert(0, str(SCRIPTS_DIR))
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()

        if metric_type == "performance":
            trends = processor.analyze_performance_trends(hours)
        elif metric_type == "players":
            trends = processor.analyze_player_behavior(hours)
        else:
            trends = {}

        return jsonify({"trends": trends, "period_hours": hours}), 200

    except ImportError:
        # Fallback: return basic trends from metrics
        return jsonify({"trends": {}, "period_hours": hours, "note": "Full analytics not available"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get trends: {str(e)}"}), 500


@app.route("/api/analytics/anomalies", methods=["GET"])
@require_permission("analytics.view")
def get_analytics_anomalies():
    """Get detected anomalies"""
    try:
        hours = int(request.args.get("hours", 24))
        metric = request.args.get("metric", "tps")  # tps, cpu, memory

        # Import analytics processor
        sys.path.insert(0, str(SCRIPTS_DIR))
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()
        perf_data = processor.load_analytics_data("performance", hours)

        if not perf_data:
            return jsonify({"anomalies": [], "message": "No data available"}), 200

        anomalies = processor.detect_anomalies(perf_data, metric)
        return jsonify({"anomalies": anomalies, "metric": metric, "period_hours": hours}), 200

    except ImportError:
        return jsonify({"anomalies": [], "note": "Full analytics not available"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get anomalies: {str(e)}"}), 500


@app.route("/api/analytics/predictions", methods=["GET"])
@require_permission("analytics.view")
def get_analytics_predictions():
    """Get resource usage predictions"""
    try:
        hours_ahead = int(request.args.get("hours_ahead", 1))
        metric = request.args.get("metric", "memory")  # memory, tps, cpu

        # Import analytics processor
        sys.path.insert(0, str(SCRIPTS_DIR))
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()
        perf_data = processor.load_analytics_data("performance", hours=24)

        if not perf_data:
            return jsonify({"prediction": {}, "message": "No data available"}), 200

        prediction = processor.predict_future(perf_data, metric, hours_ahead)
        return jsonify({"prediction": prediction, "metric": metric, "hours_ahead": hours_ahead}), 200

    except ImportError:
        return jsonify({"prediction": {}, "note": "Full analytics not available"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get predictions: {str(e)}"}), 500


@app.route("/api/analytics/player-behavior", methods=["GET"])
@require_permission("analytics.view")
def get_player_behavior():
    """Get player behavior analytics"""
    try:
        hours = int(request.args.get("hours", 24))

        # Import analytics processor
        sys.path.insert(0, str(SCRIPTS_DIR))
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()
        behavior = processor.analyze_player_behavior(hours)

        return jsonify({"behavior": behavior, "period_hours": hours}), 200

    except ImportError:
        return jsonify({"behavior": {}, "note": "Full analytics not available"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get player behavior: {str(e)}"}), 500


@app.route("/api/analytics/custom-report", methods=["POST"])
@require_permission("analytics.generate")
def generate_custom_report():
    """Generate custom analytics report"""
    try:
        data = request.get_json() or {}
        hours = int(data.get("hours", 24))
        metrics = data.get("metrics", ["performance", "players"])

        # Import analytics processor
        sys.path.insert(0, str(SCRIPTS_DIR))
        from analytics_processor import AnalyticsProcessor

        processor = AnalyticsProcessor()

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_hours": hours,
            "requested_metrics": metrics,
        }

        if "performance" in metrics:
            report["performance"] = processor.analyze_performance_trends(hours)

        if "players" in metrics:
            report["player_behavior"] = processor.analyze_player_behavior(hours)

        # Save custom report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"custom_report_{timestamp}.json"
        processor.save_report(report, filename)

        return jsonify({"report": report, "saved_as": filename}), 200

    except ImportError:
        return jsonify({"error": "Analytics processor not available"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500


@app.route("/api/worlds", methods=["GET"])
@require_permission("worlds.view")
def list_worlds():
    """List all worlds"""
    stdout, _, _ = run_script("world-manager.sh", "list")

    # Parse world list (basic implementation)
    worlds = []
    if stdout:
        for line in stdout.split("\n"):
            if "world" in line.lower() and ("ACTIVE" in line or "○" in line or "✓" in line):
                # Extract world name (simplified parsing)
                parts = line.split()
                for part in parts:
                    if part.startswith("world") or part.isalnum():
                        worlds.append(part)
                        break

    return jsonify({"worlds": worlds, "count": len(worlds)})


@app.route("/api/plugins", methods=["GET"])
@require_permission("plugins.view")
def list_plugins():
    """List installed plugins"""
    stdout, _, _ = run_script("plugin-manager.sh", "list")

    plugins = []
    if stdout:
        # Parse plugin list (simplified)
        for line in stdout.split("\n"):
            if "✓" in line or "plugin" in line.lower():
                # Extract plugin name
                parts = line.split()
                for part in parts:
                    if part and not part.startswith("(") and not part.startswith("v"):
                        plugins.append(part)
                        break

    return jsonify({"plugins": plugins, "count": len(plugins)})


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# Configuration file management endpoints
CONFIG_ALLOWED_PATHS = {
    "server.properties": PROJECT_ROOT / "data" / "server.properties",
    "docker-compose.yml": PROJECT_ROOT / "docker-compose.yml",
    "api.conf": PROJECT_ROOT / "config" / "api.conf",
    "backup-schedule.conf": PROJECT_ROOT / "config" / "backup-schedule.conf",
    "backup-retention.conf": PROJECT_ROOT / "config" / "backup-retention.conf",
    "update-check.conf": PROJECT_ROOT / "config" / "update-check.conf",
    "ddns.conf": PROJECT_ROOT / "config" / "ddns.conf",
}

# File Browser - Allowed directories (for security)
ALLOWED_FILE_PATHS = [
    PROJECT_ROOT / "data",
    PROJECT_ROOT / "config",
    PROJECT_ROOT / "backups",
    PROJECT_ROOT / "scripts",
]


@app.route("/api/config/files", methods=["GET"])
@require_permission("config.view")
def list_config_files():
    """List available configuration files"""
    files = []
    for name, path in CONFIG_ALLOWED_PATHS.items():
        exists = path.exists() if path else False
        size = path.stat().st_size if exists and path.is_file() else 0
        files.append(
            {
                "name": name,
                "path": str(path.relative_to(PROJECT_ROOT)) if path else "",
                "exists": exists,
                "size": size,
            }
        )
    return jsonify({"files": files})


@app.route("/api/config/files/<path:filename>", methods=["GET"])
@require_permission("config.view")
def get_config_file(filename):
    """Get configuration file content"""
    if filename not in CONFIG_ALLOWED_PATHS:
        return jsonify({"error": "File not allowed"}), 403

    file_path = CONFIG_ALLOWED_PATHS[filename]

    # Also check if server.properties exists at root as fallback
    if filename == "server.properties":
        if not file_path.exists():
            # Try root directory
            root_path = PROJECT_ROOT / "server.properties"
            if root_path.exists():
                file_path = root_path
            else:
                # Use data directory (will be created if needed)
                data_dir = PROJECT_ROOT / "data"
                if not data_dir.exists():
                    data_dir.mkdir(parents=True, exist_ok=True)
                file_path = data_dir / "server.properties"

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify(
            {
                "name": filename,
                "path": str(file_path.relative_to(PROJECT_ROOT)),
                "content": content,
                "size": file_path.stat().st_size,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


@app.route("/api/config/files/<path:filename>", methods=["POST"])
@require_permission("config.edit")
def save_config_file(filename):
    """Save configuration file with automatic backup"""
    if filename not in CONFIG_ALLOWED_PATHS:
        return jsonify({"error": "File not allowed"}), 403

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Content required"}), 400

    file_path = CONFIG_ALLOWED_PATHS[filename]

    # Also check if server.properties exists at root as fallback
    if filename == "server.properties":
        if not file_path.exists():
            # Try root directory
            root_path = PROJECT_ROOT / "server.properties"
            if root_path.exists():
                file_path = root_path
            else:
                # Create in data directory if it doesn't exist
                data_dir = PROJECT_ROOT / "data"
                if not data_dir.exists():
                    data_dir.mkdir(parents=True, exist_ok=True)
                file_path = data_dir / "server.properties"

    # Create backup before saving
    backup_dir = PROJECT_ROOT / "backups" / "config"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        backup_path = backup_dir / f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
        try:
            import shutil

            shutil.copy2(file_path, backup_path)
        except Exception as e:
            return jsonify({"error": f"Failed to create backup: {str(e)}"}), 500

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
            return (
                jsonify(
                    {
                        "error": f"Invalid YAML format: {str(e)}",
                    }
                ),
                400,
            )

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
                "backup": str(backup_path.relative_to(PROJECT_ROOT)) if file_path.exists() else None,
            }
        )
    except Exception as e:
        # Restore from backup on failure
        if file_path.exists() and "backup_path" in locals() and backup_path.exists():
            try:
                import shutil

                shutil.copy2(backup_path, file_path)
            except Exception:
                pass  # Restore attempt is best-effort
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500


@app.route("/api/config/files/<path:filename>/validate", methods=["POST"])
@require_permission("config.edit")
def validate_config_file(filename):
    """Validate configuration file content"""
    if filename not in CONFIG_ALLOWED_PATHS:
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
            errors.append(
                {
                    "line": getattr(e, "problem_mark", {}).line if hasattr(e, "problem_mark") else 0,
                    "message": str(e),
                }
            )

    return jsonify(
        {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    )


# Dynamic DNS Management Endpoints
DDNS_CONFIG_FILE = PROJECT_ROOT / "config" / "ddns.conf"
DDNS_SCRIPT = PROJECT_ROOT / "scripts" / "ddns-updater.sh"


@app.route("/api/ddns/status", methods=["GET"])
@require_permission("settings.view")
def get_ddns_status():
    """Get DDNS configuration status and current IP"""
    try:
        # Run status command
        result = subprocess.run(
            [str(DDNS_SCRIPT), "status"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode == 0:
            # Parse status output
            status_output = result.stdout
            return jsonify({"success": True, "status": status_output}), 200
        else:
            return jsonify({"success": False, "error": result.stderr or "Failed to get status"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to get DDNS status: {str(e)}"}), 500


@app.route("/api/ddns/update", methods=["POST"])
@require_permission("settings.edit")
def update_ddns():
    """Manually trigger DDNS update"""
    try:
        result = subprocess.run(
            [str(DDNS_SCRIPT), "update"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode == 0:
            return jsonify({"success": True, "message": "DDNS updated successfully", "output": result.stdout}), 200
        else:
            return jsonify({"success": False, "error": result.stderr or "DDNS update failed"}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "DDNS update timed out"}), 504
    except Exception as e:
        return jsonify({"error": f"Failed to update DDNS: {str(e)}"}), 500


@app.route("/api/ddns/config", methods=["GET"])
@require_permission("config.view")
def get_ddns_config():
    """Get DDNS configuration file content"""
    try:
        config_file = DDNS_CONFIG_FILE
        if not config_file.exists():
            # Return example config
            example_file = PROJECT_ROOT / "config" / "ddns.conf.example"
            if example_file.exists():
                content = example_file.read_text()
                return jsonify({"content": content, "is_example": True}), 200
            return jsonify({"error": "DDNS configuration not found"}), 404

        content = config_file.read_text()
        return jsonify({"content": content, "is_example": False}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to read DDNS config: {str(e)}"}), 500


# File Browser Endpoints
def is_path_allowed(file_path):
    """Check if a file path is within allowed directories"""
    try:
        resolved_path = Path(file_path).resolve()
        for allowed_path in ALLOWED_FILE_PATHS:
            try:
                allowed_resolved = allowed_path.resolve()
                if resolved_path.is_relative_to(allowed_resolved):
                    return True
            except (ValueError, OSError):
                continue
        return False
    except (ValueError, OSError):
        return False


@app.route("/api/files/list", methods=["GET"])
@require_permission("config.view")
def list_files():
    """List files and directories in a given path"""
    try:
        path_param = request.args.get("path", "")
        if not path_param:
            # List allowed root directories
            roots = []
            for allowed_path in ALLOWED_FILE_PATHS:
                if allowed_path.exists():
                    roots.append(
                        {
                            "name": allowed_path.name,
                            "path": str(allowed_path.relative_to(PROJECT_ROOT)),
                            "type": "directory",
                            "size": 0,
                        }
                    )
            return jsonify({"success": True, "files": roots, "path": ""}), 200

        # Resolve path (canonicalises .., resolves symlinks — required before any FS operation)
        file_path = (PROJECT_ROOT / path_param).resolve()
        if not is_path_allowed(file_path):
            return jsonify({"error": "Path not allowed"}), 403

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
                            "path": str(item.relative_to(PROJECT_ROOT)),
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
                        "path": str(file_path.relative_to(PROJECT_ROOT)),
                    }
                ),
                200,
            )
        except PermissionError:
            return jsonify({"error": "Permission denied"}), 403
    except Exception as e:
        return jsonify({"error": f"Failed to list files: {str(e)}"}), 500


@app.route("/api/files/read", methods=["GET"])
@require_permission("config.view")
def read_file():
    """Read file content"""
    try:
        path_param = request.args.get("path", "")
        if not path_param:
            return jsonify({"error": "Path required"}), 400

        file_path = (PROJECT_ROOT / path_param).resolve()
        if not is_path_allowed(file_path):
            return jsonify({"error": "Path not allowed"}), 403

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
                        "path": str(file_path.relative_to(PROJECT_ROOT)),
                        "size": file_path.stat().st_size,
                    }
                ),
                200,
            )
        except UnicodeDecodeError:
            return jsonify({"error": "File is not a text file"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


@app.route("/api/files/write", methods=["POST"])
@require_permission("config.edit")
def write_file():
    """Write file content"""
    try:
        data = request.get_json() or {}
        path_param = data.get("path", "")
        content = data.get("content", "")

        if not path_param:
            return jsonify({"error": "Path required"}), 400

        file_path = (PROJECT_ROOT / path_param).resolve()
        if not is_path_allowed(file_path):
            return jsonify({"error": "Path not allowed"}), 403

        # Create backup if file exists
        backup_path = None
        if file_path.exists():
            backup_dir = PROJECT_ROOT / "backups" / "file-edits"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{file_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
            try:
                import shutil

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
                        "path": str(file_path.relative_to(PROJECT_ROOT)),
                        "backup": (
                            str(backup_path.relative_to(PROJECT_ROOT)) if backup_path and backup_path.exists() else None
                        ),
                    }
                ),
                200,
            )
        except Exception as e:
            # Restore from backup on failure
            if backup_path and backup_path.exists():
                try:
                    import shutil

                    shutil.copy2(backup_path, file_path)
                except Exception:
                    pass  # Restore attempt is best-effort
            return jsonify({"error": f"Failed to write file: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to write file: {str(e)}"}), 500


@app.route("/api/files/delete", methods=["DELETE"])
@require_permission("config.edit")
def delete_file():
    """Delete a file or directory"""
    try:
        path_param = request.args.get("path", "")
        if not path_param:
            return jsonify({"error": "Path required"}), 400

        file_path = (PROJECT_ROOT / path_param).resolve()
        if not is_path_allowed(file_path):
            return jsonify({"error": "Path not allowed"}), 403

        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404

        # Prevent deleting critical directories
        critical_paths = ["data", "config", "scripts"]
        if any(file_path.name == cp for cp in critical_paths) and file_path.is_dir():
            return jsonify({"error": "Cannot delete critical directory"}), 403

        try:
            if file_path.is_dir():
                import shutil

                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            return jsonify({"success": True, "message": "File deleted successfully"}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500


@app.route("/api/files/upload", methods=["POST"])
@require_permission("config.edit")
def upload_file():
    """Upload a file"""
    try:
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

        from werkzeug.utils import secure_filename

        safe_name = secure_filename(file.filename)
        if not safe_name:
            return jsonify({"error": "Invalid filename"}), 400
        file_path = (PROJECT_ROOT / path_param / safe_name).resolve()
        if not is_path_allowed(file_path):
            return jsonify({"error": "Path not allowed"}), 403

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        file.save(str(file_path))

        return (
            jsonify(
                {
                    "success": True,
                    "message": "File uploaded successfully",
                    "path": str(file_path.relative_to(PROJECT_ROOT)),
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to upload file: {str(e)}"}), 500


@app.route("/api/files/download", methods=["GET"])
@require_permission("config.view")
def download_file():
    """Download a file"""
    try:
        from flask import send_file

        path_param = request.args.get("path", "")
        if not path_param:
            return jsonify({"error": "Path required"}), 400

        file_path = (PROJECT_ROOT / path_param).resolve()
        if not is_path_allowed(file_path):
            return jsonify({"error": "Path not allowed"}), 403

        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404

        if not file_path.is_file():
            return jsonify({"error": "Path is not a file"}), 400

        return send_file(str(file_path), as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Failed to download file: {str(e)}"}), 500


@app.route("/api/ddns/config", methods=["POST"])
@require_permission("config.edit")
def save_ddns_config():
    """Save DDNS configuration file"""
    try:
        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"error": "Content required"}), 400

        content = data["content"]
        config_file = DDNS_CONFIG_FILE

        # Create backup if file exists
        backup_path = None
        if config_file.exists():
            backup_path = config_file.with_suffix(f".conf.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            import shutil

            shutil.copy2(config_file, backup_path)

        # Write new content
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(content)

        # Set restrictive permissions (600)
        import os

        os.chmod(config_file, 0o600)

        return jsonify(
            {
                "success": True,
                "message": "DDNS configuration saved successfully",
                "backup": str(backup_path.relative_to(PROJECT_ROOT)) if backup_path and backup_path.exists() else None,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to save DDNS config: {str(e)}"}), 500


# WebSocket event handlers for real-time log streaming
if SOCKETIO_AVAILABLE:
    # Session ids currently subscribed to the log stream
    active_log_streams = set()
    # sid -> the API key that opened that connection. The socket authenticates
    # once at connect, so later messages on the same connection are checked
    # against the key recorded here. The key itself is stored rather than its
    # permissions, so narrowing, disabling or deleting a key takes effect on
    # sockets it already opened instead of only on the next connection.
    _stream_keys = {}
    _log_streams_lock = threading.Lock()
    # Mutable holder rather than a module-level bool, so the reader and the
    # starter share one piece of state without `global` declarations. The
    # follower no longer stops when the last client disconnects, so `stop` is
    # what shutdown and the tests use to bring it down deliberately.
    _log_reader_state = {"running": False, "stop": False, "proc": None}

    LOG_BACKLOG_LINES = 200

    def get_log_tail(lines=100):
        """Get last N lines of server logs"""
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), "minecraft-server"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.split("\n")
            return []
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _publish_log_line(line):
        """Feed one log line to the event bus, returning the event or None.

        Persistence failures and handler errors are contained by the bus itself;
        this wrapper exists so that a bus problem can never stop log streaming.
        """
        if not EVENTS_AVAILABLE:
            return None
        try:
            return game_events.get_bus().handle_line(line)
        except Exception as exc:  # noqa: BLE001 - streaming must outlive the bus
            app.logger.error(f"Event bus failed on a log line: {exc}")
            return None

    def _log_reader():
        """Follow the container log, fan lines out, and drive the event bus.

        The previous implementation gave every client its own thread that ran
        `docker logs --tail 50` every second and diffed the result against the
        last batch, which scaled badly, missed lines that scrolled past between
        polls, and duplicated any line that legitimately repeated. One follower
        process streams the log instead, so lines arrive in order, exactly once.

        It now also runs whether or not anybody is watching. The log is the only
        real-time signal the Minecraft server produces, so a follower that
        started on the first browser connection and stopped on the last one
        meant every death, advancement and chat message that happened with the
        dashboard closed was lost. Events are parsed and recorded continuously;
        the WebSocket fanout is just one consumer of them.

        It attaches with `--tail 0` deliberately. Because every line read here
        is persisted as an event, replaying a backlog would record the same
        deaths and advancements again on every API restart and every re-attach,
        and the counts would climb with each one. New clients still get their
        scrollback: `handle_connect` sends `get_log_tail()` separately, and that
        path does not touch the bus. The trade is that events occurring while
        the API is down are not captured, which is far better than recording
        some of them repeatedly.
        """
        while not _log_reader_state["stop"]:
            proc = None
            try:
                proc = subprocess.Popen(
                    ["docker", "logs", "-f", "--tail", "0", "minecraft-server"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                with _log_streams_lock:
                    _log_reader_state["proc"] = proc

                for line in proc.stdout:
                    if _log_reader_state["stop"]:
                        break

                    line = line.rstrip("\n")
                    if not line.strip():
                        continue

                    # Parse and persist first, so an event is recorded even if
                    # no client is connected to receive it.
                    event = _publish_log_line(line)

                    with _log_streams_lock:
                        subscribers = list(active_log_streams)
                    for sid in subscribers:
                        socketio.emit("logs", {"logs": [line], "type": "update"}, room=sid)
                        if event is not None:
                            socketio.emit("game_event", event.to_dict(), room=sid)
            except FileNotFoundError:
                # Docker is not installed; there is nothing to stream
                with _log_streams_lock:
                    subscribers = list(active_log_streams)
                for sid in subscribers:
                    socketio.emit("error", {"message": "Docker is not available"}, room=sid)
                with _log_streams_lock:
                    _log_reader_state["running"] = False
                return
            except Exception as e:  # noqa: BLE001 - surfaced to the client below
                with _log_streams_lock:
                    subscribers = list(active_log_streams)
                for sid in subscribers:
                    socketio.emit("error", {"message": f"Log streaming error: {str(e)}"}, room=sid)
            finally:
                with _log_streams_lock:
                    _log_reader_state["proc"] = None
                if proc is not None:
                    try:
                        proc.kill()
                    except Exception:
                        # Best effort: the process has usually exited on its
                        # own by this point, and failing to reap it must not
                        # stop the reader from re-attaching.
                        pass

            if _log_reader_state["stop"]:
                break

            # The container may have stopped or restarted, and `docker logs -f`
            # exits when it does. Pause briefly, then re-attach, so the server
            # coming back up resumes the stream without anyone intervening.
            socketio.sleep(2)

        with _log_streams_lock:
            _log_reader_state["running"] = False

    def _ensure_log_reader():
        """Start the single follower thread if it is not already running"""
        with _log_streams_lock:
            if _log_reader_state["running"]:
                return
            _log_reader_state["running"] = True
            _log_reader_state["stop"] = False
        socketio.start_background_task(_log_reader)

    def stop_log_reader():
        """Stop the follower.

        Setting the flag alone is not enough. A quiet server leaves the reader
        blocked in `for line in proc.stdout`, where it never gets to check the
        flag, so `docker logs -f` is killed to break the read. The reader then
        unblocks, sees the flag and exits.
        """
        with _log_streams_lock:
            _log_reader_state["stop"] = True
            proc = _log_reader_state["proc"]

        if proc is not None:
            try:
                proc.kill()
            except Exception:
                # Already exited, which is the outcome we wanted anyway.
                pass

    @socketio.on("connect")
    def handle_connect(auth):
        """Handle WebSocket connection"""
        api_key = auth.get("api_key") if auth else None

        if not api_key:
            socketio.emit("error", {"message": "API key required"}, room=request.sid)
            socketio.disconnect(request.sid)
            return False

        if api_key not in API_KEYS:
            socketio.emit("error", {"message": "Invalid API key"}, room=request.sid)
            socketio.disconnect(request.sid)
            return False

        key_info = API_KEYS.get(api_key, {})
        if not key_info.get("enabled", True):
            socketio.emit("error", {"message": "API key disabled"}, room=request.sid)
            socketio.disconnect(request.sid)
            return False

        # The log stream is server output, so it needs the same permission the
        # REST log endpoints require. Any enabled key used to be enough.
        key_permissions = get_api_key_permissions(key_info)
        if "logs.view" not in key_permissions:
            socketio.emit("error", {"message": "Permission denied: logs.view"}, room=request.sid)
            socketio.disconnect(request.sid)
            return False

        with _log_streams_lock:
            active_log_streams.add(request.sid)
            _stream_keys[request.sid] = api_key

        # Send the backlog to this client only, then let the shared follower
        # deliver everything that arrives afterwards.
        socketio.emit("logs", {"logs": get_log_tail(LOG_BACKLOG_LINES), "type": "initial"}, room=request.sid)
        socketio.emit("connected", {"message": "Connected to log stream"}, room=request.sid)

        _ensure_log_reader()
        return True  # connection accepted

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        with _log_streams_lock:
            active_log_streams.discard(request.sid)
            _stream_keys.pop(request.sid, None)

    def _stream_may(permission):
        """Check the live scope of the key that opened this connection.

        Re-read rather than trusting what the key could do at connect time: a
        key revoked or narrowed through the management API would otherwise keep
        its old rights on an open socket for as long as it stayed connected.
        """
        with _log_streams_lock:
            api_key = _stream_keys.get(request.sid)

        key_info = API_KEYS.get(api_key) if api_key else None
        if not key_info or not key_info.get("enabled", True):
            return False
        return permission in get_api_key_permissions(key_info)

    @socketio.on("request_logs")
    def handle_request_logs(data):
        """Handle log request from client"""
        if not _stream_may("logs.view"):
            socketio.emit("error", {"message": "Permission denied: logs.view"}, room=request.sid)
            return
        lines = data.get("lines", 100) if data else 100
        logs = get_log_tail(lines)
        socketio.emit("logs", {"logs": logs, "type": "request"}, room=request.sid)

    @socketio.on("execute_command")
    def handle_execute_command(data):
        """Handle command execution from client"""
        # The connect handler only proved the key was valid, never that it was
        # allowed to run commands, so a read-only key could drive the console.
        if not _stream_may("server.command"):
            socketio.emit("command_error", {"message": "Permission denied: server.command"}, room=request.sid)
            return

        command = data.get("command") if data else None
        if not command:
            socketio.emit("command_error", {"message": "Command required"}, room=request.sid)
            return
        if not isinstance(command, str):
            # Raising inside the sanitizer happens before the try block below,
            # which would leave the client waiting with no error at all.
            socketio.emit("command_error", {"message": "Command must be a string"}, room=request.sid)
            return

        # Sanitise exactly as POST /api/server/command does. This path reached
        # RCON unvalidated, so the WebSocket was a way around the command
        # allowlist that the REST endpoint enforces.
        if SECURITY_AVAILABLE:
            is_valid, sanitized_command, _ = sanitize_minecraft_command(command)
            if not is_valid:
                log_audit_event(
                    "__api_key__",
                    "server.command.rejected",
                    {"original_command": sanitize_string(command[:100]), "source": "websocket"},
                )
                socketio.emit("command_error", {"message": "Invalid command format"}, room=request.sid)
                return
            command = sanitized_command

        log_audit_event("__api_key__", "server.command", {"command": sanitize_string(command[:100])})

        # Execute command via RCON
        try:
            stdout, stderr, code = run_rcon_command(command)
            if code == 0:
                socketio.emit(
                    "command_response", {"command": command, "response": stdout, "success": True}, room=request.sid
                )
            else:
                socketio.emit(
                    "command_response",
                    {"command": command, "response": stderr or "Command failed", "success": False},
                    room=request.sid,
                )
        except Exception as e:
            socketio.emit(
                "command_error",
                {"message": f"Failed to execute command: {str(e)}", "command": command},
                room=request.sid,
            )

else:
    # WebSocket not available
    warnings.warn("Flask-SocketIO not available. WebSocket support disabled.", stacklevel=1)


def start_event_capture():
    """Begin following the server log as soon as the API starts.

    Capture must not wait for a browser: events that happen while the dashboard
    is closed are exactly the ones worth recording. Tests skip this so no
    background thread or docker call escapes into the suite.
    """
    if not (SOCKETIO_AVAILABLE and socketio and EVENTS_AVAILABLE):
        return False

    bus = game_events.get_bus()
    bus.set_error_logger(app.logger.error)
    # Without this, the last few events on a quiet server stay buffered until
    # something else happens.
    bus.start_periodic_flush()

    if DEATHS_AVAILABLE:
        # The announcer is injected rather than imported by the hall, so the
        # hall stays testable without a server and without RCON.
        hall = hall_of_deaths.get_hall(announcer=_announce_in_game)
        hall.set_error_logger(app.logger.error)
        # Announcing makes a network call, and bus handlers run on the log
        # follower thread. The worker keeps an unreachable server from stalling
        # event processing behind each death.
        hall.start_worker()
        bus.subscribe(hall.handle_event)

    if BEDTIME_AVAILABLE:
        bed = bedtime_mode.get_bedtime(runner=_run_game_command, stopper=_stop_server_for_bedtime)
        bed.set_error_logger(app.logger.error)
        # Stopping the server is not enough on its own: a restart policy or the
        # update timer can bring it back and reopen the evening. Turning joins
        # away during the closed window is what actually holds the line.
        bus.subscribe(bed.on_player_join)
        bed.start()

    _ensure_log_reader()
    return True


if __name__ == "__main__":
    if not API_ENABLED:
        print("API is disabled in configuration")
        sys.exit(1)

    print(f"Starting Minecraft Server API on {API_HOST}:{API_PORT}")
    if SOCKETIO_AVAILABLE and socketio:
        print("WebSocket support enabled")
        if start_event_capture():
            print("Game event capture enabled")
        socketio.run(app, host=API_HOST, port=API_PORT, debug=False)
    else:
        print("WebSocket support disabled (Flask-SocketIO not available)")
        app.run(host=API_HOST, port=API_PORT, debug=False)
