"""Password hashing, JWTs, TOTP and Apple ID-token verification.

bcrypt, PyJWT, pyotp and qrcode are each imported optionally and each function
raises, or returns ``None``, when its library is missing; the ``*_AVAILABLE``
flags record which loaded. The signing key, the OAuth config and the app
logger live on ``api.server`` and are read through it at call time, so a
value patched there is the one used here.
"""

import base64
import io
from datetime import datetime, timedelta, timezone

from api import server

# Imported separately so that one missing library does not switch off the
# other's feature (a missing bcrypt must not disable JWTs or Apple sign-in).
try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    bcrypt = None

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None

# Two-Factor Authentication. pyotp does the code generation and verification;
# qrcode is only needed to draw the setup QR image, so a missing qrcode must
# not stop existing 2FA users from logging in.
try:
    import pyotp

    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False
    pyotp = None

try:
    import qrcode

    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
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
    return jwt.encode(payload, server.SECRET_KEY, algorithm="HS256")


def verify_token(token):
    """Verify JWT token"""
    if not JWT_AVAILABLE:
        return None
    try:
        payload = jwt.decode(token, server.SECRET_KEY, algorithms=["HS256"])
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
    client_id = server.OAUTH_CONFIG["apple"].get("client_id")
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
    except Exception as e:  # noqa: BLE001 - a failed key fetch or a malformed token must deny, not raise
        server.app.logger.error(f"Failed to verify Apple ID token: {e}")
        return None


def generate_totp_secret():
    """Generate a TOTP secret for 2FA"""
    if not PYOTP_AVAILABLE:
        raise ImportError("pyotp not available")
    return pyotp.random_base32()


def generate_totp_uri(username, secret, issuer="Minecraft Server"):
    """Generate TOTP URI for QR code"""
    if not PYOTP_AVAILABLE:
        raise ImportError("pyotp not available")
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def generate_qr_code(uri):
    """Generate QR code image from URI"""
    if not QRCODE_AVAILABLE:
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
    if not PYOTP_AVAILABLE:
        raise ImportError("pyotp not available")
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # Allow 1 time step window


# Audit Logging
