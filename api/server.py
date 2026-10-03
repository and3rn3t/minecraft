#!/usr/bin/env python3
"""
Minecraft Server REST API
Provides HTTP API for remote server management
"""

import json
import os
import secrets
import subprocess
import sys
import threading
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, jsonify, request

# CORS, rate limiting and the security helpers are required, not optional: a
# missing one used to be swallowed and replaced with a no-op, which left the
# API running with no brute-force protection or command sanitising and nothing
# to say so. They are pinned in requirements.txt, so an ImportError here means
# a broken install and should stop the service at startup.
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Optional WebSocket support. Runs in Flask-SocketIO's threading mode (with
# simple-websocket for the upgrade), which needs no monkey-patching. eventlet
# was used before and is deprecated upstream.
try:
    from flask_socketio import (
        SocketIO,  # type: ignore[import-untyped]
        disconnect,  # type: ignore[import-untyped]
    )

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    SocketIO = None  # Placeholder for type checking
    emit = None
    disconnect = None

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# The service runs this file as a script (`python api/server.py`), so it is
# loaded as `__main__`. The blueprints do `from api import server`; without an
# alias that would load this file a second time as `api.server`, re-enter the
# blueprint imports below while they are half-initialised, and fail with a
# circular ImportError (and, if it did not, leave two copies of the app and
# its state). Registering this module under its package name makes both names
# the same module. Tests import `api.server` normally and are unaffected.
if __name__ == "__main__":
    sys.modules.setdefault("api.server", sys.modules[__name__])

from api import auth_crypto, auth_guard, rbac  # noqa: E402
from api.security import sanitize_minecraft_command, sanitize_string

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

# The session cookie authenticates state-changing requests (see auth_guard.require_auth
# below), so it needs the same hardening any auth cookie does: HttpOnly so
# client-side JS/XSS can't read it, Secure so it's never sent over plain
# HTTP, SameSite=Strict so a cross-site request never carries it at all. The
# CSRF check in auth_guard.require_auth is defense in depth on top of SameSite, for
# browsers that don't enforce SameSite=Strict (or don't yet).
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

# CORS configuration - restrict to specific origins in production
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# Initialize SocketIO if available
if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, async_mode="threading")
else:
    socketio = None

CORS(app, supports_credentials=True, origins=ALLOWED_ORIGINS)


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
# OAuth) and for RCON command submission, applied per route via
# @auth_rate_limit(...).
# storage_uri="memory://" is fine for this app's single-process deployment;
# a multi-worker/gunicorn setup would need a shared backend (e.g. Redis)
# instead, since in-memory counters aren't shared across processes.
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://", default_limits=[])


def auth_rate_limit(limit_string):
    """Per-route rate limit (per client IP) using the shared Flask-Limiter instance."""
    return limiter.limit(limit_string)


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
    as admins by ``auth_guard.has_permission()``. Silently demoting them would break
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
ALLOWED_FILE_PATHS = [
    PROJECT_ROOT / "data",
    PROJECT_ROOT / "config",
    PROJECT_ROOT / "backups",
    PROJECT_ROOT / "scripts",
]


# File Browser Endpoints
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

        Accepts either an API key or a JWT, mirroring auth_guard.require_auth's REST
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
            username = auth_crypto.verify_token(token)
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
            return permission in rbac.get_api_key_permissions(key_info)
        if kind == "user":
            if value not in USERS or not USERS[value].get("enabled", True):
                return False
            return auth_guard.has_permission(value, permission)
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
        """Who opened this socket, named as auth_guard.get_username_from_request() names
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
        # Threading mode serves through Werkzeug, which Flask-SocketIO only
        # runs outside debug if told it is intended. That is the case here: a
        # single process behind nginx, which is also what the in-memory rate
        # limiter assumes.
        socketio.run(app, host=API_HOST, port=API_PORT, debug=False, allow_unsafe_werkzeug=True)
    else:
        print("WebSocket support disabled (Flask-SocketIO not available)")
        app.run(host=API_HOST, port=API_PORT, debug=False)
