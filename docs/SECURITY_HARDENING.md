# Security Hardening Documentation

This document outlines the security improvements implemented to harden the Minecraft Server Management API and web interface.

## 🔒 Security Improvements Implemented

### 1. Input Validation & Sanitization

#### Command Injection Prevention

- **File**: `api/security.py`
- **Implementation**: `sanitize_minecraft_command()`
- **Features**:
  - Blocks dangerous shell metacharacters (`&`, `|`, `;`, `` ` ``, `$`, etc.)
  - Prevents path traversal attempts (`..`)
  - Blocks system directory access (`/etc/`, `/proc/`, `/sys/`)
  - Prevents dangerous commands (rm -rf, mkfs, dd, wget, curl)
  - Command length limiting (256 characters max)
  - Whitelist validation for Minecraft commands

#### File Path Sanitization

- **Implementation**: `sanitize_file_path()`
- **Features**:
  - Prevents directory traversal attacks
  - Validates paths are within allowed directories
  - Normalizes paths safely
  - Prevents access to system directories

#### String Sanitization

- **Implementation**: `sanitize_string()`
- **Features**:
  - Removes null bytes
  - Removes control characters
  - Configurable length limits
  - Optional newline handling

### 2. Security Headers

All API responses now include security headers:

- **X-Content-Type-Options**: `nosniff` - Prevents MIME type sniffing
- **X-Frame-Options**: `DENY` - Prevents clickjacking
- **X-XSS-Protection**: `1; mode=block` - Enables XSS filtering
- **Strict-Transport-Security**: Forces HTTPS (when deployed)
- **Content-Security-Policy**: Restricts resource loading
- **Referrer-Policy**: Controls referrer information

**Location**: `api/server.py` - `security_headers()` function

### 3. Rate Limiting

- **Implementation**: `rate_limit()` decorator
- **Default**: 60 requests per minute per IP/user
- **Customizable**: Can set different limits per endpoint
- **Example**: Command endpoint limited to 30 requests/minute
- **Storage**: In-memory (use Redis in production for distributed systems)

**Usage**:

```python
@app.route("/api/endpoint", methods=["POST"])
@rate_limit(max_per_minute=30, per_endpoint=True)
def endpoint():
    ...
```

### 4. CORS Configuration

- **Before**: Allowed all origins (`*`)
- **After**: Configurable via `ALLOWED_ORIGINS` environment variable
- **Default**: Allows all (maintains compatibility)
- **Production**: Set specific origins only

**Environment Variable**:

```bash
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 5. Secure Secret Key Management

- **Before**: Hardcoded weak secret key
- **After**:
  - Uses environment variable `SECRET_KEY`
  - Generates secure random key if not provided
  - 32-byte hex token (64 characters)
  - Stored securely, never exposed

**Environment Variable**:

```bash
SECRET_KEY=your-secure-random-64-character-hex-string
```

### 6. Request Size Limits

- **Limit**: 16MB maximum request size
- **Prevents**: DoS attacks via large payloads
- **Configurable**: Via Flask `MAX_CONTENT_LENGTH`

### 7. Error Message Sanitization

- **Before**: Detailed error messages exposed internal details
- **After**: Generic error messages for clients
- **Details**: Logged to audit log, not returned to client
- **Prevents**: Information leakage about system structure

**Example**:

- ❌ Before: `"Failed to execute command: FileNotFoundError: rcon-client.sh"`
- ✅ After: `"Command execution failed"`

### 8. Session Security

- **Lifetime**: 24 hours (configurable)
- **Secure**: Uses secure secret key for signing
- **HTTPOnly**: Cookie flags (handled by Flask)
- **SameSite**: Protection against CSRF

### 9. API Key Security

- **Storage**: Restricted file permissions (600) on Unix systems
- **Generation**: Cryptographically secure random generation
- **Validation**: Enabled/disabled state checking
- **Audit**: All API key usage logged

### 10. Authentication Enhancements

- **Password Hashing**: bcrypt with automatic salt generation
- **JWT Tokens**: Secure token generation with expiration
- **2FA Support**: TOTP-based two-factor authentication
- **OAuth Security**: Proper redirect URI validation

## 🛡️ Security Best Practices

### Environment Configuration

Create a `.env` file or set environment variables:

```bash
# Required for production
SECRET_KEY=generate-a-secure-64-character-hex-string
ALLOWED_ORIGINS=https://yourdomain.com

# Optional
API_HOST=127.0.0.1
API_PORT=8080
```

### Production Deployment Checklist

- [ ] Set `SECRET_KEY` environment variable
- [ ] Configure `ALLOWED_ORIGINS` with specific domains
- [ ] Enable HTTPS/TLS
- [ ] Set up reverse proxy (nginx/Apache)
- [ ] Use Redis for rate limiting (instead of in-memory)
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Monitor audit logs
- [ ] Regular backups of configuration files
- [ ] Restrict API port access via firewall

### Rate Limiting in Production

For production deployments with multiple servers, use Redis:

```python
# Example with Redis (future enhancement)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

### Security Monitoring

1. **Audit Logs**: All security-relevant actions logged to `config/audit.log`
2. **Failed Authentication**: Tracked and rate-limited
3. **Command Rejections**: Logged with reasons
4. **Rate Limit Violations**: Tracked per IP/user

## 🔍 Security Testing

### Manual Testing

1. **Command Injection**:

   ```bash
   curl -X POST http://localhost:8080/api/server/command \
     -H "X-API-Key: your-key" \
     -d '{"command": "kick player; rm -rf /"}'
   ```

   Expected: Command rejected

2. **Path Traversal**:

   ```bash
   curl "http://localhost:8080/api/files/read?path=../../etc/passwd"
   ```

   Expected: Access denied

3. **Rate Limiting**:
   ```bash
   for i in {1..100}; do curl -X POST http://localhost:8080/api/server/command ...; done
   ```
   Expected: Rate limit after 30 requests

### Automated Testing

Security tests should be added to `tests/api/test_security.py` (future enhancement).

## 📋 Security Audit Log

The following actions are logged for security auditing:

- API key creation/deletion/enable/disable
- User authentication (success and failure)
- Permission changes
- Server commands (executed and rejected)
- File access operations
- Configuration changes

**Location**: `config/audit.log`

**Format**: JSON Lines (one JSON object per line)

## 🚨 Known Limitations

1. **In-Memory Rate Limiting**: Currently uses in-memory storage. Use Redis for distributed systems.
2. **CORS Wildcard Default**: Defaults to `*` for compatibility. Must be configured for production.
3. **WebSocket Security**: WebSocket connections use same authentication but may need additional hardening.
4. **File Upload Limits**: Currently limited by Flask's MAX_CONTENT_LENGTH. Consider additional validation.

## 📚 References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Python Security Guide](https://python.readthedocs.io/en/stable/library/security.html)

---

**Last Updated**: 2025-01-27
**Status**: ✅ Security hardening implemented
