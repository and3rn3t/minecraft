#!/usr/bin/env python3
"""
Minecraft Server REST API
Provides HTTP API for remote server management
"""

import json
import os
import re
import secrets
import subprocess
import sys
import threading
import warnings
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

# Optional rate limiting support (brute-force protection on auth endpoints).
# The hand-rolled `rate_limit`/`is_rate_limit_exceeded` further below predates
# this and stays in place for the one route it already covers; anything new
# uses this, since per-minute counters shared safely across a threaded server
# are exactly what Flask-Limiter is for.
try:
    from flask_limiter import Limiter  # type: ignore[import-untyped]
    from flask_limiter.util import get_remote_address  # type: ignore[import-untyped]

    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    Limiter = None
    get_remote_address = None

# Optional WebSocket support
try:
    import eventlet  # type: ignore[import-untyped]
    from flask_socketio import (
        SocketIO,  # type: ignore[import-untyped]
        disconnect,  # type: ignore[import-untyped]
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

    def sanitize_string(s, max_length=1000, allow_newlines=False):
        return str(s)[:max_length] if s else ""

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

# Pet Cemetery. Gentle obituaries and gravestones for named (tamed) pets,
# separate from the Hall of Deaths' comedic player obituaries by design.
try:
    from api import pet_cemetery

    PET_CEMETERY_AVAILABLE = True
except ImportError:
    PET_CEMETERY_AVAILABLE = False
    pet_cemetery = None

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

# The Oracle. Sees every chat message, decides whether to answer, and can
# generate a structured quest. Off by default; needs ANTHROPIC_API_KEY.
try:
    from api import oracle

    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False
    oracle = None


app = Flask(__name__)

# nginx (config/nginx-minecraft.conf) is the only thing that ever talks to
# this process directly -- Flask otherwise sees every request as coming from
# nginx's own loopback address and scheme, not the real client's. Trusting
# exactly one proxy hop's X-Forwarded-* headers (which nginx already sets)
# fixes request.remote_addr for rate limiting (Flask-Limiter keys on it) and
# request.is_secure for anything scheme-dependent, without trusting headers
# an internet client could forge directly against Flask (there's no path to
# Flask that skips nginx).
#
# This one hop is only actually the real client's IP, though, if nginx's
# own $remote_addr is correct first -- behind the documented Cloudflare
# Tunnel deployment, nginx's literal peer is always cloudflared on
# 127.0.0.1, so config/nginx-minecraft.conf recovers the real visitor IP
# via Cloudflare's CF-Connecting-IP header (see its `real_ip_header`
# comment) before it ever builds the X-Forwarded-For chain read here.
# Without that, every visitor would look identical to Flask-Limiter.
from werkzeug.exceptions import HTTPException  # noqa: E402
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# SECRET_KEY is resolved further down, once config/api.conf has been read.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max request size
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

# The session cookie authenticates state-changing requests (see require_auth
# below), so it needs the same hardening any auth cookie does: HttpOnly so
# client-side JS/XSS can't read it, Secure so it's never sent over plain
# HTTP, SameSite=Strict so a cross-site request never carries it at all. The
# CSRF check in require_auth is defense in depth on top of SameSite, for
# browsers that don't enforce SameSite=Strict (or don't yet).
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

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


def _warn_if_cors_wildcard_with_credentials(allowed_origins):
    """Warn loudly if CORS is wide open while credentials are allowed.

    A wildcard origin combined with credentialed requests (session cookies,
    or the Authorization/X-API-Key headers CORS treats as credentialed) lets
    any site make authenticated calls against this API -- flask-cors
    reflects the request's actual Origin instead of a literal "*" once
    supports_credentials=True, so "*" doesn't mean "no site" here, it means
    "every site". Fine on a trusted local network; not once this is
    reachable from the internet.
    """
    if allowed_origins == ["*"]:
        warnings.warn(
            "ALLOWED_ORIGINS is unset (defaulting to '*') while CORS allows credentials. "
            "Set the ALLOWED_ORIGINS environment variable to your actual frontend origin(s) "
            "before exposing this API beyond a trusted local network -- see "
            "config/api.conf.example.",
            stacklevel=2,
        )


_warn_if_cors_wildcard_with_credentials(ALLOWED_ORIGINS)

# Rate limiting for brute-force-prone auth endpoints (login, register, 2FA,
# OAuth), applied per route below via @auth_rate_limit(...).
# storage_uri="memory://" is fine for this app's single-process deployment;
# a multi-worker/gunicorn setup would need a shared backend (e.g. Redis)
# instead, since in-memory counters aren't shared across processes.
if LIMITER_AVAILABLE:
    limiter = Limiter(get_remote_address, app=app, storage_uri="memory://", default_limits=[])
else:
    limiter = None


def auth_rate_limit(limit_string):
    """Rate-limit decorator for auth routes; a no-op if Flask-Limiter isn't installed."""

    def decorator(f):
        if limiter is None:
            return f
        return limiter.limit(limit_string)(f)

    return decorator


_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        # The React build uses inline `style={{...}}` props in a number of
        # places (actual `style="..."` attributes at runtime, not a
        # separate stylesheet), so style-src needs 'unsafe-inline' -- there
        # are no inline *scripts* or eval() anywhere in web/src, so
        # script-src stays tight.
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        # Same-origin API + Socket.IO calls only -- nginx proxies /api and
        # /socket.io on the same origin as the built frontend (see
        # config/nginx-minecraft.conf), nothing here calls out cross-origin.
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
)


# Add security headers to all responses
@app.after_request
def security_headers(response):
    """Add security headers to all responses"""
    # config/nginx-minecraft.conf's `location = /oauth/callback` adds this
    # same set of headers unconditionally, covering both the GET (SPA) and
    # POST (proxied here) cases in one place -- nginx's `add_header`
    # doesn't replace an upstream header of the same name, it appends
    # another copy of it, so setting these here too would duplicate every
    # one of them on this route specifically.
    if request.path == "/oauth/callback":
        response.headers.pop("Server", None)
        return response
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = _CSP
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Opt out of browser features this app has no use for.
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
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
DDNS_CONFIG_FILE = PROJECT_ROOT / "config" / "ddns.conf"
DDNS_SCRIPT = PROJECT_ROOT / "scripts" / "ddns-updater.sh"

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


_analytics_processor_load_lock = threading.Lock()


def _ensure_analytics_processor_module():
    """Make `analytics_processor` importable.

    The on-disk file is scripts/analytics-processor.py -- the hyphen makes it
    unimportable via a plain `import`/`from` statement, so on first use we load
    it from its file path and register it in sys.modules under the name
    callers (and tests, which pre-populate sys.modules with a mock) expect.

    Loading is serialized and registration only happens after exec_module
    succeeds, so concurrent first callers can't observe a half-initialized
    module, and a failed load doesn't leave a broken entry cached forever.
    """
    if "analytics_processor" in sys.modules:
        return

    with _analytics_processor_load_lock:
        if "analytics_processor" in sys.modules:
            return

        import importlib.util

        module_path = SCRIPTS_DIR / "analytics-processor.py"
        spec = importlib.util.spec_from_file_location("analytics_processor", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load analytics processor from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["analytics_processor"] = module


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
        # Header only -- see the matching comment in require_auth.
        api_key = request.headers.get("X-API-Key")

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


def run_script(script_name, *args, timeout=DEFAULT_SCRIPT_TIMEOUT, input_text=None):
    """Run a management script and return (stdout, stderr, returncode).

    A timed-out script yields returncode 504. Callers that wrap long-running
    operations should pass a larger timeout rather than letting a backup of a
    real-sized world look like a failure. ``input_text``, when given, is
    written to the script's stdin and the pipe closed -- for scripts (like
    ``manage.sh restore``) that read a confirmation prompt.
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
            input=input_text,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return None, f"Script execution timeout after {timeout}s", 504
    except Exception as e:
        # The second element is treated as the script's stderr by callers, and
        # several return it to the client, so the exception text would reach
        # them by that route. It goes to the log instead.
        app.logger.error(f"Script {script_name} failed: {e}")
        return None, "Script execution failed", 500


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


def script_error(stderr, fallback, *, status=500, include_success_flag=False):
    """The `else` branch most run_script() callers repeat: surface stderr, or
    a route-specific fallback message when the script printed nothing to it.
    """
    body = {"error": stderr or fallback}
    if include_success_flag:
        body["success"] = False
    return jsonify(body), status


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


# Cached client for Apple's public signing keys (https://appleid.apple.com/auth/keys).
# Built lazily so importing this module never makes a network call, and reused across
# requests so verifying an Apple ID token doesn't refetch the JWKS every login.
_apple_jwk_client = None


def _get_apple_jwk_client():
    global _apple_jwk_client
    if _apple_jwk_client is None:
        _apple_jwk_client = jwt.PyJWKClient("https://appleid.apple.com/auth/keys")
    return _apple_jwk_client


def verify_apple_id_token(id_token):
    """Verify an Apple Sign In ID token and return its decoded claims.

    Checks the RS256 signature against Apple's published JWKS, plus audience
    (our OAuth client id) and issuer. Returns None if the token is missing,
    expired, mis-scoped, or simply not signed by Apple. Callers must never
    trust an Apple ID token's claims (e.g. `sub`, `email`) without going
    through this first -- a caller-supplied id_token is untrusted input.
    """
    if not JWT_AVAILABLE:
        return None
    client_id = OAUTH_CONFIG["apple"].get("client_id")
    if not client_id:
        return None
    try:
        signing_key = _get_apple_jwk_client().get_signing_key_from_jwt(id_token)
        return jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer="https://appleid.apple.com",
        )
    except jwt.PyJWTError:
        return None
    except Exception as e:
        app.logger.error(f"Failed to verify Apple ID token: {e}")
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
    # Check API key. Header only -- see the matching comment in require_auth.
    api_key = request.headers.get("X-API-Key")
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
    # Deliberately granted to no role below except admin. The file browser
    # reads anything under data/, config/, backups/ and scripts/, which is
    # where every secret lives: users.json, api-keys.json, rcon.conf,
    # rcon.password in server.properties. While it only needed config.view,
    # any "user" account or key could read the admin API keys.
    "files.view": "Browse and download files in the file browser",
    # Player management
    "players.view": "View player list",
    "players.manage": "Manage players (ban/whitelist/op)",
    # World management
    "worlds.view": "View world list",
    "worlds.manage": "Manage worlds (create/delete/switch)",
    # Plugin management
    "plugins.view": "View plugin list",
    "plugins.manage": "Manage plugins (install/remove/enable/disable)",
    # Datapack management
    "datapacks.view": "View datapack list",
    "datapacks.manage": "Manage datapacks (install/remove/enable/disable)",
    # User management
    "users.view": "View user list",
    "users.manage": "Manage users (create/edit/delete/roles)",
    # API key management
    "api_keys.view": "View API keys",
    "api_keys.manage": "Manage API keys (create/delete/enable/disable)",
    # Logs
    "logs.view": "View server logs",
    # Admin only, like files.view: the audit log holds every account's IP
    # addresses, failed sign-ins and the commands people ran. It needed
    # logs.view, which the "user" role holds.
    "audit.view": "View the audit log",
    # Metrics
    "metrics.view": "View server metrics",
    "analytics.view": "View analytics and reports",
    "analytics.generate": "Generate analytics reports",
    # Settings
    "settings.view": "View application settings",
    "settings.edit": "Edit application settings",
    # The Oracle -- deliberately not granted to any role below except admin.
    # It spends real money on every allowlisted chat message and talks
    # directly to children; who can flip its kill switch or edit its
    # allowlist is a decision that should be made explicitly, not inherited
    # from a broader role's existing grants.
    "oracle.view": "View Oracle status and chat/quest log",
    "oracle.manage": "Manage the Oracle (enable/disable, allowlist, rate limit)",
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
        "datapacks.view",
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
        "datapacks.view",
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


def _issue_csrf_token():
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
    user = USERS.get(username)
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
            username = verify_token(token)
            if username and _account_active(username):
                request.user = username
                request.user_info = USERS.get(username, {})
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
            request.user_info = USERS.get(session.get("username"), {})
            return f(*args, **kwargs)

        return jsonify({"error": "Authentication required"}), 401

    return decorated_function


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """The generic fallback every route used to repeat in its own try/except.

    Registered for Exception itself, not just 500: Flask only routes an
    unhandled exception to the 500 handler above when PROPAGATE_EXCEPTIONS is
    unset or false, which is not the case under TESTING (every test client
    fixture sets it) or DEBUG -- there, it re-raises instead, which this
    would otherwise never see. HTTPExceptions (404s, aborts, ...) already
    have their own more specific handlers or Flask defaults; this only
    handles what nothing else claimed.
    """
    if isinstance(error, HTTPException):
        return error
    # request.path is attacker-controlled; stripped of newlines before it
    # reaches the log so a URL carrying one can't forge entries of its own.
    safe_path = request.path[:500].replace("\r", "").replace("\n", "")
    app.logger.error(f"Unhandled exception on {safe_path}: {error}", exc_info=error)
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
def describe_yaml_error(error):
    """Describe a YAML parse failure using only the parser's own fields.

    str(a YAMLError) formats the problem together with the surrounding context
    and the stream name. Taking `problem` and `problem_mark` keeps what the
    caller needs — what is wrong and where — without passing the exception's
    rendering through to the response.
    """
    problem = getattr(error, "problem", None) or "could not be parsed"
    mark = getattr(error, "problem_mark", None)
    if mark is not None:
        # Marks are zero-based; editors are not.
        return f"Invalid YAML: {problem} (line {mark.line + 1}, column {mark.column + 1})"
    return f"Invalid YAML: {problem}"


ALLOWED_FILE_PATHS = [
    PROJECT_ROOT / "data",
    PROJECT_ROOT / "config",
    PROJECT_ROOT / "backups",
    PROJECT_ROOT / "scripts",
]


# Keys whose values are credentials: rcon.password, SECRET_KEY,
# CLOUDFLARE_API_TOKEN, NOIP_PASSWORD, ANTHROPIC_API_KEY and the like.
_SECRET_KEY_PATTERN = re.compile(r"pass|secret|token|api[_.-]?key|private[_.-]?key|credential", re.IGNORECASE)
# `key=value` (.properties, .conf, compose list entries) or `key: value` (YAML).
# The value may be empty: in YAML that opens a nested block.
_CONFIG_LINE_PATTERN = re.compile(r"^(\s*(?:-\s*)?(?:export\s+)?)([A-Za-z0-9_.\-]+)(\s*[=:])(\s*)(.*)$")
# A YAML block scalar header: `|`, `>`, optionally with chomping/indent indicators
_YAML_BLOCK_SCALAR = re.compile(r"^[|>][0-9+-]*\s*(#.*)?$")
REDACTED_VALUE = "********"


def _indent(line):
    return len(line) - len(line.lstrip())


def redact_config_secrets(content):
    """Replace credential values in config text, leaving everything else intact.

    Returns ``(content, redacted)``. config.view is held by every role, and
    these files carry the RCON password, the session signing key and the
    Cloudflare token; reading them used to be enough to take over the server.

    A value can span lines, and all of it is withheld: a YAML block scalar
    (``KEY: |``) or nested block under ``KEY:``, whose lines are those indented
    deeper than the key; or a quoted .conf value (``KEY="...``) running to its
    closing quote. Those continuation lines are dropped, leaving the masked key.
    """
    redacted = False
    lines = []
    block_indent = None  # indent of a masked key whose indented block is being skipped
    open_quote = None  # quote character of a masked value still running on

    for line in content.split("\n"):
        if open_quote is not None:
            if open_quote in line:
                open_quote = None
            continue

        if block_indent is not None:
            if not line.strip():
                continue
            if _indent(line) > block_indent:
                redacted = True
                continue
            block_indent = None

        match = _CONFIG_LINE_PATTERN.match(line)
        # Comments never match: "#" is not a key character
        if match and _SECRET_KEY_PATTERN.search(match.group(2)):
            prefix, key, separator, space, value = match.groups()
            value = value.strip()
            if not value or _YAML_BLOCK_SCALAR.match(value):
                # The value is whatever is indented below, if anything is
                block_indent = _indent(line)
                if value:
                    lines.append(f"{prefix}{key}{separator}{space}{REDACTED_VALUE}")
                    redacted = True
                else:
                    lines.append(line)
                continue
            if value[0] in "\"'" and value[1:].find(value[0]) == -1:
                open_quote = value[0]
            lines.append(f"{prefix}{key}{separator}{space}{REDACTED_VALUE}")
            redacted = True
            continue

        lines.append(line)

    return "\n".join(lines), redacted


# File Browser Endpoints
def _within_allowed_roots(real_path):
    """Whether an already-resolved path sits inside one of the allowed roots.

    Written with os.path and a separator-terminated prefix rather than
    ``Path.is_relative_to``: the two are equivalent, but this form is one
    CodeQL recognises as a path sanitizer, so the file browser gets real
    analysis instead of a standing exemption.

    The trailing separator is what stops ``/srv/data-evil`` passing because it
    begins with ``/srv/data``.
    """
    for allowed_path in ALLOWED_FILE_PATHS:
        try:
            root = os.path.realpath(str(allowed_path))
        except (ValueError, OSError):
            continue
        if real_path == root or real_path.startswith(root + os.sep):
            return True
    return False


def is_path_allowed(file_path):
    """Check if a file path is within allowed directories"""
    try:
        return _within_allowed_roots(os.path.realpath(str(file_path)))
    except (ValueError, OSError):
        return False


def resolve_allowed_path(path_param):
    """Resolve a caller-supplied path and confirm it is inside an allowed root.

    Returns ``(path, None)`` when the path is usable, or ``(None, response)``
    with the refusal to return.

    Resolving first matters: ``.resolve()`` collapses ``..`` and follows
    symlinks, so a link inside an allowed directory pointing outside one is
    checked at its destination rather than by its name. Checking the string
    before resolving would miss that.

    The explicit rejections below are the paths that never reach the allowlist
    check at all, because resolving them raises first — a null byte used to
    surface as a 500 carrying the raw OS error.
    """
    if not isinstance(path_param, str) or "\x00" in path_param:
        return None, (jsonify({"error": "Invalid path"}), 400)

    try:
        candidate = os.path.realpath(os.path.join(str(PROJECT_ROOT), path_param))
    except (ValueError, OSError):
        return None, (jsonify({"error": "Invalid path"}), 400)

    if not _within_allowed_roots(candidate):
        return None, (jsonify({"error": "Path not allowed"}), 403)

    return Path(candidate), None


# WebSocket event handlers for real-time log streaming
if SOCKETIO_AVAILABLE:
    # Session ids currently subscribed to the log stream
    active_log_streams = set()
    # sid -> the identity that opened that connection, as ("api_key", key) or
    # ("user", username). The socket authenticates once at connect, so later
    # messages on the same connection are checked against the identity
    # recorded here. The identity itself is stored rather than its resolved
    # permissions, so narrowing, disabling or deleting a key or user takes
    # effect on sockets it already opened instead of only on the next
    # connection.
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
                app.logger.error(f"Log streaming error: {e}")
                for sid in subscribers:
                    socketio.emit("error", {"message": "Log streaming error"}, room=sid)
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
        """Handle WebSocket connection.

        Accepts either an API key or a JWT, mirroring require_auth's REST
        behavior — without the token path, any user who logged in with a
        username/password (no API key ever issued) could use every REST
        endpoint but not the log/console stream.
        """
        api_key = auth.get("api_key") if auth else None
        token = auth.get("token") if auth else None

        identity = None  # ("api_key", key) or ("user", username)

        if api_key:
            if api_key not in API_KEYS:
                socketio.emit("error", {"message": "Invalid API key"}, room=request.sid)
                disconnect(request.sid)
                return False

            key_info = API_KEYS.get(api_key, {})
            if not key_info.get("enabled", True):
                socketio.emit("error", {"message": "API key disabled"}, room=request.sid)
                disconnect(request.sid)
                return False

            identity = ("api_key", api_key)
        elif token:
            username = verify_token(token)
            if not username or username not in USERS:
                socketio.emit("error", {"message": "Invalid or expired token"}, room=request.sid)
                disconnect(request.sid)
                return False

            if not USERS[username].get("enabled", True):
                socketio.emit("error", {"message": "Account disabled"}, room=request.sid)
                disconnect(request.sid)
                return False

            identity = ("user", username)
        else:
            socketio.emit("error", {"message": "API key or token required"}, room=request.sid)
            disconnect(request.sid)
            return False

        # The log stream is server output, so it needs the same permission the
        # REST log endpoints require. Any enabled key used to be enough.
        if not _identity_has_permission(identity, "logs.view"):
            socketio.emit("error", {"message": "Permission denied: logs.view"}, room=request.sid)
            disconnect(request.sid)
            return False

        with _log_streams_lock:
            active_log_streams.add(request.sid)
            _stream_keys[request.sid] = identity

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

    def _identity_has_permission(identity, permission):
        """Resolve a stream identity from handle_connect to a live permission check."""
        if not identity:
            return False
        kind, value = identity
        if kind == "api_key":
            key_info = API_KEYS.get(value)
            if not key_info or not key_info.get("enabled", True):
                return False
            return permission in get_api_key_permissions(key_info)
        if kind == "user":
            if value not in USERS or not USERS[value].get("enabled", True):
                return False
            return has_permission(value, permission)
        return False

    def _stream_may(permission):
        """Check the live scope of the identity that opened this connection.

        Re-read rather than trusting what the key or user could do at connect
        time: a key revoked, a user disabled, or a role narrowed through the
        management API would otherwise keep its old rights on an open socket
        for as long as it stayed connected.
        """
        with _log_streams_lock:
            identity = _stream_keys.get(request.sid)

        return _identity_has_permission(identity, permission)

    def _stream_actor():
        """Who opened this socket, named as get_username_from_request() names
        REST callers, for the audit log. Commands sent over the socket were all
        recorded as "__api_key__", whoever sent them."""
        with _log_streams_lock:
            identity = _stream_keys.get(request.sid)
        if not identity:
            return "unknown"
        kind, value = identity
        if kind == "api_key":
            return f"api_key:{API_KEYS.get(value, {}).get('name', 'unknown')}"
        return value

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
                    _stream_actor(),
                    "server.command.rejected",
                    {"original_command": sanitize_string(command[:100]), "source": "websocket"},
                )
                socketio.emit("command_error", {"message": "Invalid command format"}, room=request.sid)
                return
            command = sanitized_command

        log_audit_event(_stream_actor(), "server.command", {"command": sanitize_string(command[:100])})

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
            app.logger.error(f"Failed to execute command over the socket: {e}")
            socketio.emit(
                "command_error",
                {"message": "Failed to execute command", "command": command},
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

    if PET_CEMETERY_AVAILABLE:
        # Same injection pattern as the hall above: the runner is passed in
        # rather than imported, so the cemetery stays testable without RCON.
        cemetery = pet_cemetery.get_cemetery(runner=_run_game_command)
        cemetery.set_error_logger(app.logger.error)
        cemetery.start_worker()
        bus.subscribe(cemetery.handle_event)

    if BEDTIME_AVAILABLE:
        bed = bedtime_mode.get_bedtime(runner=_run_game_command, stopper=_stop_server_for_bedtime)
        bed.set_error_logger(app.logger.error)
        # Stopping the server is not enough on its own: a restart policy or the
        # update timer can bring it back and reopen the evening. Turning joins
        # away during the closed window is what actually holds the line.
        bus.subscribe(bed.on_player_join)
        bed.start()

    if ORACLE_AVAILABLE:
        # Same injection pattern as pet_cemetery above. The audit logger is
        # its own callable, not a direct log_audit_event() call from inside
        # oracle.py: that function reads Flask's request proxy when
        # ip_address isn't passed explicitly, and the Oracle's worker thread
        # has no request context, so the sentinel below is passed here.
        orc = oracle.get_oracle(runner=_run_game_command)
        orc.set_error_logger(app.logger.error)
        orc.set_audit_logger(
            lambda player, action, details: log_audit_event(player, action, details, ip_address="minecraft-chat")
        )
        orc.start_worker()
        bus.subscribe(orc.handle_event)

    _ensure_log_reader()
    return True


# Blueprints, split out of this file by feature area. Each imports what it
# needs from this module by name; importing them only here, after everything
# above is defined, is what keeps that import one-directional instead of
# circular (Python has already registered this partially-executed module in
# sys.modules, so `from api.server import ...` in a blueprint resolves fine
# as long as the names it asks for already exist above this line).
from api.blueprints.access import bp as access_bp  # noqa: E402
from api.blueprints.analytics import bp as analytics_bp  # noqa: E402
from api.blueprints.announcements import bp as announcements_bp  # noqa: E402
from api.blueprints.audit import bp as audit_bp  # noqa: E402
from api.blueprints.auth import bp as auth_bp  # noqa: E402
from api.blueprints.backups import bp as backups_bp  # noqa: E402
from api.blueprints.config_files import bp as config_files_bp  # noqa: E402
from api.blueprints.content import bp as content_bp  # noqa: E402
from api.blueprints.ddns import bp as ddns_bp  # noqa: E402
from api.blueprints.files import bp as files_bp  # noqa: E402
from api.blueprints.oracle import bp as oracle_bp  # noqa: E402
from api.blueprints.players import bp as players_bp  # noqa: E402
from api.blueprints.scheduler import bp as scheduler_bp  # noqa: E402
from api.blueprints.server_control import bp as server_control_bp  # noqa: E402

app.register_blueprint(access_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(announcements_bp)
app.register_blueprint(audit_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(backups_bp)
app.register_blueprint(config_files_bp)
app.register_blueprint(content_bp)
app.register_blueprint(ddns_bp)
app.register_blueprint(files_bp)
app.register_blueprint(oracle_bp)
app.register_blueprint(players_bp)
app.register_blueprint(scheduler_bp)
app.register_blueprint(server_control_bp)


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
