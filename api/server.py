#!/usr/bin/env python3
"""
Minecraft Server REST API
Provides HTTP API for remote server management
"""

import json
import secrets
import subprocess
import sys
import urllib.parse
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
    from flask_socketio import SocketIO  # type: ignore[import-untyped]
    from flask_socketio import disconnect, emit

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

app = Flask(__name__)
app.config["SECRET_KEY"] = "minecraft-server-api-secret"

# Initialize SocketIO if available
if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
else:
    socketio = None

# Enable CORS if available
if CORS_AVAILABLE:
    CORS(app, supports_credentials=True)  # Enable CORS with credentials
else:
    # Fallback: Add CORS headers manually if needed
    @app.after_request
    def after_request(response):
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-API-Key")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response


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
SECRET_KEY = "minecraft-server-api-secret-change-in-production"

# Load configuration
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
        SECRET_KEY = config.get("SECRET_KEY", SECRET_KEY)

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

# Load users
USERS = {}
if USERS_FILE.exists():
    try:
        with open(USERS_FILE, "r") as f:
            USERS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        USERS = {}

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

        # Store key info in request context
        request.api_key_info = key_info
        # Set virtual admin user for permission checks (API keys have admin access)
        request.user = "__api_key__"
        request.user_info = {"role": "admin", "username": "__api_key__"}
        return f(*args, **kwargs)

    return decorated_function


def run_script(script_name, *args):
    """Run a management script and return output"""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        return None, f"Script not found: {script_name}", 404

    try:
        result = subprocess.run(
            [str(script_path)] + list(args), capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT)
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return None, "Script execution timeout", 504
    except Exception as e:
        return None, str(e), 500


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
        "settings.view",
    ],
    "operator": [
        "server.view",
        "server.control",
        "server.command",
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


def get_user_permissions(username):
    """Get list of permissions for a user based on their role"""
    if username not in USERS:
        return []
    user_role = USERS[username].get("role", "user")
    return ROLE_PERMISSIONS.get(user_role, ROLE_PERMISSIONS["user"])


def has_permission(username, permission):
    """Check if user has a specific permission"""
    # API keys have admin access
    if username == "__api_key__":
        return True
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
                request.user = "__api_key__"
                request.user_info = {"role": "admin", "username": "__api_key__"}
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

    # Check if user already exists
    if username in USERS:
        return jsonify({"error": "Username already exists"}), 400

    # Create user
    hashed_password = hash_password(password)
    USERS[username] = {
        "username": username,
        "password_hash": hashed_password,
        "email": email,
        "role": "admin",  # First user is admin, others default to "user"
        "enabled": True,
        "created": datetime.now(timezone.utc).isoformat(),
    }

    if not save_users():
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

        if not name:
            return jsonify({"error": "Key name is required"}), 400

        # Generate new API key
        api_key = generate_api_key()

        # Create key entry
        API_KEYS[api_key] = {
            "name": name,
            "description": description,
            "enabled": True,
            "created": datetime.now(timezone.utc).isoformat(),
        }

        if not save_api_keys():
            return jsonify({"error": "Failed to save API key"}), 500

        return (
            jsonify(
                {
                    "success": True,
                    "key": api_key,  # Return full key only on creation
                    "id": api_key[:8] + "..." + api_key[-4:],
                    "name": name,
                    "description": description,
                    "message": "API key created. Save this key securely - it will not be shown again.",
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to create API key: {str(e)}"}), 500


@app.route("/api/keys/<key_id>", methods=["DELETE"])
@require_permission("api_keys.manage")
def delete_api_key(key_id):
    """Delete an API key"""
    try:
        # Find the full key by preview
        key_to_delete = None
        for key in API_KEYS:
            if key.startswith(key_id) or key.endswith(key_id) or key == key_id:
                key_to_delete = key
                break

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
        # Find the full key by preview
        key_to_enable = None
        for key in API_KEYS:
            if key.startswith(key_id) or key.endswith(key_id) or key == key_id:
                key_to_enable = key
                break

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
        # Find the full key by preview
        key_to_disable = None
        for key in API_KEYS:
            if key.startswith(key_id) or key.endswith(key_id) or key == key_id:
                key_to_disable = key
                break

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

    stdout, stderr, code = run_script("manage.sh", "start")

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
    stdout, stderr, code = run_script("manage.sh", "stop")

    if code == 0:
        return jsonify({"success": True, "message": "Server stopping", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Failed to stop server"}), 500


@app.route("/api/server/restart", methods=["POST"])
@require_permission("server.control")
def restart_server():
    """Restart the server"""
    stdout, stderr, code = run_script("manage.sh", "restart")

    if code == 0:
        return jsonify({"success": True, "message": "Server restarting", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Failed to restart server"}), 500


@app.route("/api/server/command", methods=["POST"])
@require_permission("server.command")
def send_command():
    """Send a command to the server via RCON"""
    data = request.get_json()
    command = data.get("command")

    if not command:
        return jsonify({"error": "Command required"}), 400

    username = get_username_from_request()
    log_audit_event(username, "server.command", {"command": command})

    stdout, stderr, code = run_script("rcon-client.sh", "command", command)

    if code == 0:
        return jsonify({"success": True, "response": stdout, "command": command}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Command failed", "command": command}), 500


@app.route("/api/backup", methods=["POST"])
@require_permission("backup.create")
def create_backup():
    """Create a server backup"""
    username = get_username_from_request()
    log_audit_event(username, "backup.create", {"action": "create_backup"})

    stdout, stderr, code = run_script("manage.sh", "backup")

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
        if not SCHEDULE_FILE.exists():
            return jsonify({"success": True, "schedules": []}), 200

        with open(SCHEDULE_FILE, "r") as f:
            schedule_data = json.load(f)
        return jsonify({"success": True, "schedules": schedule_data.get("schedules", [])}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to list schedules: {str(e)}"}), 500


@app.route("/api/scheduler/schedules", methods=["POST"])
@require_permission("server.command")
def create_schedule():
    """Create a new scheduled command"""
    try:
        data = request.get_json() or {}
        command = data.get("command")
        schedule_type = data.get("type", "interval")  # interval, daily, weekly
        enabled = data.get("enabled", True)

        if not command:
            return jsonify({"error": "Command required"}), 400

        # Load existing schedules
        schedule_data = {"schedules": []}
        if SCHEDULE_FILE.exists():
            with open(SCHEDULE_FILE, "r") as f:
                schedule_data = json.load(f)

        # Generate ID
        import uuid

        schedule_id = str(uuid.uuid4())

        # Create schedule entry
        schedule = {
            "id": schedule_id,
            "command": command,
            "type": schedule_type,
            "enabled": enabled,
            "created": datetime.now(timezone.utc).isoformat(),
            "last_run": None,
        }

        # Add type-specific fields
        if schedule_type == "interval":
            schedule["interval_minutes"] = data.get("interval_minutes", 60)
        elif schedule_type == "daily":
            schedule["run_time"] = data.get("run_time", "00:00")
        elif schedule_type == "weekly":
            schedule["day_of_week"] = data.get("day_of_week", 0)
            schedule["run_time"] = data.get("run_time", "00:00")

        schedule_data["schedules"].append(schedule)

        # Save
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(schedule_data, f, indent=2)

        username = get_username_from_request()
        log_audit_event(username, "scheduler.create", {"schedule_id": schedule_id, "command": command})

        return jsonify({"success": True, "schedule": schedule}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create schedule: {str(e)}"}), 500


@app.route("/api/scheduler/schedules/<schedule_id>", methods=["PUT"])
@require_permission("server.command")
def update_schedule(schedule_id):
    """Update a scheduled command"""
    try:
        data = request.get_json() or {}

        if not SCHEDULE_FILE.exists():
            return jsonify({"error": "Schedule not found"}), 404

        with open(SCHEDULE_FILE, "r") as f:
            schedule_data = json.load(f)

        schedules = schedule_data.get("schedules", [])
        schedule = None
        for s in schedules:
            if s.get("id") == schedule_id:
                schedule = s
                break

        if not schedule:
            return jsonify({"error": "Schedule not found"}), 404

        # Update fields
        if "command" in data:
            schedule["command"] = data["command"]
        if "type" in data:
            schedule["type"] = data["type"]
        if "enabled" in data:
            schedule["enabled"] = data["enabled"]
        if "interval_minutes" in data:
            schedule["interval_minutes"] = data["interval_minutes"]
        if "run_time" in data:
            schedule["run_time"] = data["run_time"]
        if "day_of_week" in data:
            schedule["day_of_week"] = data["day_of_week"]

        # Save
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(schedule_data, f, indent=2)

        username = get_username_from_request()
        log_audit_event(username, "scheduler.update", {"schedule_id": schedule_id})

        return jsonify({"success": True, "schedule": schedule}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update schedule: {str(e)}"}), 500


@app.route("/api/scheduler/schedules/<schedule_id>", methods=["DELETE"])
@require_permission("server.command")
def delete_schedule(schedule_id):
    """Delete a scheduled command"""
    try:
        if not SCHEDULE_FILE.exists():
            return jsonify({"error": "Schedule not found"}), 404

        with open(SCHEDULE_FILE, "r") as f:
            schedule_data = json.load(f)

        schedules = schedule_data.get("schedules", [])
        schedule_data["schedules"] = [s for s in schedules if s.get("id") != schedule_id]

        # Save
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(schedule_data, f, indent=2)

        username = get_username_from_request()
        log_audit_event(username, "scheduler.delete", {"schedule_id": schedule_id})

        return jsonify({"success": True, "message": "Schedule deleted"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete schedule: {str(e)}"}), 500


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
        run_script("manage.sh", "stop")

        # Create a backup of current state before restoring
        current_backup = backups_dir / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        if data_dir.exists() and any(data_dir.iterdir()):
            import tarfile

            with tarfile.open(current_backup, "w:gz") as tar:
                tar.add(data_dir, arcname=".")

        # Extract backup
        import tarfile

        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=data_dir)

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


@app.route("/api/players", methods=["GET"])
@require_permission("players.view")
def get_players():
    """Get list of online players"""
    stdout, _, _ = run_script("rcon-client.sh", "command", "list")

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


@app.route("/api/server/properties/preset", methods=["POST"])
@require_permission("server.manage")
def apply_server_preset():
    """Apply server properties preset"""
    try:
        data = request.get_json() or {}
        preset = data.get("preset")
        if not preset:
            return jsonify({"error": "Preset name required"}), 400

        valid_presets = ["low-end", "balanced", "high-performance"]
        if preset not in valid_presets:
            return jsonify({"error": f"Invalid preset. Valid: {', '.join(valid_presets)}"}), 400

        stdout, stderr, code = run_script("server-properties-manager.sh", "preset", preset)
        if code == 0:
            return jsonify({"success": True, "message": f"Preset '{preset}' applied"}), 200
        else:
            return jsonify({"error": stderr or "Failed to apply preset"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to apply preset: {str(e)}"}), 500


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
        pass

    return jsonify({"metrics": metrics, "timestamp": datetime.now(timezone.utc).isoformat()})


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
                pass
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

        # Resolve path
        file_path = PROJECT_ROOT / path_param
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

        file_path = PROJECT_ROOT / path_param
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

        file_path = PROJECT_ROOT / path_param
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
                pass

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
                    pass
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

        file_path = PROJECT_ROOT / path_param
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

        file_path = PROJECT_ROOT / path_param / file.filename
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

        file_path = PROJECT_ROOT / path_param
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
    import time
    from collections import deque

    # Store active log stream connections
    active_log_streams = set()

    def get_log_tail(lines=100):
        """Get last N lines of server logs"""
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), "minecraft-server"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.split("\n")
            return []
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def stream_logs_task(sid, api_key):
        """Background task to stream logs to connected client"""
        if api_key not in API_KEYS:
            socketio.emit("error", {"message": "Invalid API key"}, room=sid)
            return

        # Send initial logs
        initial_logs = get_log_tail(200)
        socketio.emit("logs", {"logs": initial_logs, "type": "initial"}, room=sid)

        last_lines = deque(initial_logs[-50:] if len(initial_logs) > 50 else initial_logs, maxlen=50)

        # Stream new logs
        while sid in active_log_streams:
            try:
                current_logs = get_log_tail(50)
                if current_logs and current_logs != list(last_lines):
                    # Find new lines
                    new_lines = []
                    for log in current_logs:
                        if log not in last_lines and log.strip():
                            new_lines.append(log)

                    if new_lines:
                        socketio.emit("logs", {"logs": new_lines, "type": "update"}, room=sid)
                        last_lines.extend(new_lines)

                time.sleep(1)  # Check every second
            except Exception as e:
                socketio.emit("error", {"message": f"Log streaming error: {str(e)}"}, room=sid)
                break

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

        # Add to active streams
        active_log_streams.add(request.sid)

        # Start log streaming task
        socketio.start_background_task(stream_logs_task, request.sid, api_key)
        socketio.emit("connected", {"message": "Connected to log stream"}, room=request.sid)

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        if request.sid in active_log_streams:
            active_log_streams.remove(request.sid)

    @socketio.on("request_logs")
    def handle_request_logs(data):
        """Handle log request from client"""
        lines = data.get("lines", 100) if data else 100
        logs = get_log_tail(lines)
        socketio.emit("logs", {"logs": logs, "type": "request"}, room=request.sid)

    @socketio.on("execute_command")
    def handle_execute_command(data):
        """Handle command execution from client"""
        command = data.get("command") if data else None
        if not command:
            socketio.emit("command_error", {"message": "Command required"}, room=request.sid)
            return

        # Check if user has permission (api_key already validated in connect)
        # Execute command via RCON
        try:
            stdout, stderr, code = run_script("rcon-client.sh", "command", command)
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
    # WebSocket not available - log warning
    print("Warning: Flask-SocketIO not available. WebSocket support disabled.")


if __name__ == "__main__":
    if not API_ENABLED:
        print("API is disabled in configuration")
        sys.exit(1)

    print(f"Starting Minecraft Server API on {API_HOST}:{API_PORT}")
    if SOCKETIO_AVAILABLE and socketio:
        print("WebSocket support enabled")
        socketio.run(app, host=API_HOST, port=API_PORT, debug=False)
    else:
        print("WebSocket support disabled (Flask-SocketIO not available)")
        app.run(host=API_HOST, port=API_PORT, debug=False)
