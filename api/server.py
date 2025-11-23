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
    from flask_socketio import (SocketIO,  # type: ignore[import-untyped]
                                disconnect, emit)

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
    """Decorator to require API key authentication"""

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


def require_auth(f):
    """Decorator to require user authentication (session or token)"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For OAuth routes, check provider validity first (if provider in args)
        # This allows provider validation errors to return 400 instead of 401
        if len(kwargs) > 0 and "provider" in kwargs:
            provider = kwargs["provider"]
            if provider not in ["google", "apple"]:
                return jsonify({"error": "Invalid OAuth provider"}), 400

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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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


@app.route("/api/status", methods=["GET"])
@require_api_key
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
@require_api_key
def start_server():
    """Start the server"""
    stdout, stderr, code = run_script("manage.sh", "start")

    if code == 0:
        return jsonify({"success": True, "message": "Server starting", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Failed to start server"}), 500


@app.route("/api/server/stop", methods=["POST"])
@require_api_key
def stop_server():
    """Stop the server"""
    stdout, stderr, code = run_script("manage.sh", "stop")

    if code == 0:
        return jsonify({"success": True, "message": "Server stopping", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Failed to stop server"}), 500


@app.route("/api/server/restart", methods=["POST"])
@require_api_key
def restart_server():
    """Restart the server"""
    stdout, stderr, code = run_script("manage.sh", "restart")

    if code == 0:
        return jsonify({"success": True, "message": "Server restarting", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Failed to restart server"}), 500


@app.route("/api/server/command", methods=["POST"])
@require_api_key
def send_command():
    """Send a command to the server via RCON"""
    data = request.get_json()
    command = data.get("command")

    if not command:
        return jsonify({"error": "Command required"}), 400

    stdout, stderr, code = run_script("rcon-client.sh", "command", command)

    if code == 0:
        return jsonify({"success": True, "response": stdout, "command": command}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Command failed", "command": command}), 500


@app.route("/api/backup", methods=["POST"])
@require_api_key
def create_backup():
    """Create a server backup"""
    stdout, stderr, code = run_script("manage.sh", "backup")

    if code == 0:
        return jsonify({"success": True, "message": "Backup created", "output": stdout}), 200
    else:
        return jsonify({"success": False, "error": stderr or "Backup failed"}), 500


@app.route("/api/backups", methods=["GET"])
@require_api_key
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


@app.route("/api/backups/<path:filename>/restore", methods=["POST"])
@require_api_key
def restore_backup(filename):
    """Restore a backup"""
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
@require_api_key
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
@require_api_key
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
@require_api_key
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


@app.route("/api/metrics", methods=["GET"])
@require_api_key
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
@require_api_key
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
@require_api_key
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
}


@app.route("/api/config/files", methods=["GET"])
@require_api_key
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
@require_api_key
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
@require_api_key
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
@require_api_key
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
        socketio.run(app, host=API_HOST, port=API_PORT, debug=False)
    else:
        print("WebSocket support disabled (Flask-SocketIO not available)")
        app.run(host=API_HOST, port=API_PORT, debug=False)
