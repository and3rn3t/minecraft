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
- **Strict-Transport-Security**: Forces HTTPS (meaningful once something in front of the API actually terminates TLS, e.g. Cloudflare for a tunneled deployment -- see below)
- **Content-Security-Policy**: `default-src 'self'`, with tighter per-directive rules (`script-src 'self'` with no `unsafe-inline`/`unsafe-eval`; `style-src` allows `unsafe-inline` since the React build uses inline `style={{...}}` props; `frame-ancestors 'none'`; `connect-src 'self'` since the API and Socket.IO are same-origin behind nginx)
- **Permissions-Policy**: `geolocation=(), microphone=(), camera=()` - opts out of browser features this app doesn't use
- **Referrer-Policy**: Controls referrer information

The deprecated `X-XSS-Protection` header was removed -- modern browsers ignore it, and it offered no real protection the CSP above doesn't already provide.

**Location**: `api/server.py` - `security_headers()` function; tested in `tests/api/test_security_headers.py`. This only ever runs for Flask's own JSON responses, though -- in the documented deployment, nginx serves `web/dist/index.html` and its JS/CSS bundle directly from disk, and a browser enforces CSP/frame-ancestors/etc. from the response that delivered the *document*, not from later API calls the page happens to make. `config/nginx-minecraft.conf`'s `location /` and `location /assets/` blocks carry the same header values (kept in sync by hand) so the page that actually loads the React app is covered too; `/api`, `/api/auth` and `/socket.io` are deliberately left out there since Flask already sets its own copy on those responses.

### 3. Rate Limiting

Two independent layers:

- **Auth endpoints** (`/api/auth/login`, `/register`, `/2fa/*`, OAuth URL/callback/link routes): Flask-Limiter (`api/requirements.txt`), applied per route via the `@auth_rate_limit(...)` decorator in `api/server.py`. Login is limited to 5/minute + 20/hour per IP, 2FA and the OAuth callback/link routes to 10/minute, registration to 10/hour, and `GET /api/auth/oauth/<provider>/url` (which only returns an authorization URL, not a credential check) to 30/minute. `storage_uri="memory://"`, appropriate for this app's single-process deployment -- a multi-worker/gunicorn setup would need `storage_uri` pointed at something shared (e.g. Redis) instead, since in-memory counters aren't shared across processes.
- **`/api/server/command`**: the original hand-rolled `rate_limit()` decorator (`api/security.py`'s `is_rate_limit_exceeded()`), 30 requests/minute, kept as-is since that route already required authentication and wasn't part of the brute-force surface the Flask-Limiter work above addresses.
- **nginx** (`config/nginx-minecraft.conf`): a `limit_req_zone` on `/api/auth/*` (10r/m, burst 5) as an independent second layer that holds even if the app-layer limiter is ever misconfigured or bypassed.

Both layers key on the visitor's IP, which only works if that IP is actually correct by the time it reaches nginx/Flask. Behind the documented Cloudflare Tunnel, cloudflared's connection to nginx is always from `127.0.0.1` -- without correcting for that, every visitor would look identical and the per-IP limits above would collapse into one bucket shared by everyone. `config/nginx-minecraft.conf` recovers the real IP from Cloudflare's `CF-Connecting-IP` header (set at their edge on every request, tunnel or not) via `ngx_http_realip_module`, trusted only from the loopback connection cloudflared makes; `api/server.py` then trusts that one corrected hop via Werkzeug's `ProxyFix`. If you're exposing this some other way (not the tunnel), review both of those before relying on the per-IP limits.

Before this, **no auth endpoint had any rate limiting at all** -- passwords, TOTP codes, and OAuth callbacks were all guessable with no throttle.

### 4. CORS Configuration

- `ALLOWED_ORIGINS` environment variable (not read from `config/api.conf` -- see `config/api.conf.example`), comma-separated, defaults to `*` if unset.
- Used with `supports_credentials=True`, which means the `*` default is a real misconfiguration once this API is reachable beyond a trusted network: flask-cors reflects the request's actual `Origin` instead of a literal `*` when credentials are allowed, so the default effectively permits **any** site to make authenticated requests. `api/server.py` logs a `UserWarning` on startup (`_warn_if_cors_wildcard_with_credentials`) if `ALLOWED_ORIGINS` is still `*`.
- Set it before exposing the API beyond a LAN:

```bash
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

For the systemd deployment, set it via a systemd override (`sudo systemctl edit minecraft-api.service`) rather than editing `systemd/minecraft-api.service` directly -- that file is reinstalled from the repo on every `scripts/update-codebase.sh` pull, which would silently discard a direct edit. See `config/api.conf.example` for the exact commands.

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

### 8. Session Security & CSRF Protection

- **Lifetime**: 24 hours (`PERMANENT_SESSION_LIFETIME`)
- **Cookie flags**: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Strict"` -- explicitly set in `api/server.py`; previously relied entirely on Flask's own defaults, which don't include `Secure`.
- **`ProxyFix`**: `api/server.py` wraps `app.wsgi_app` in Werkzeug's `ProxyFix` (trusting exactly one hop -- nginx) so the app sees the real client IP (`X-Forwarded-For`, used by Flask-Limiter's per-IP keying) and scheme (`X-Forwarded-Proto`) instead of nginx's own loopback address and whatever scheme the nginx-to-Flask hop happens to use.
- **CSRF tokens**: a synchronizer token (`session["csrf_token"]`, issued by `_issue_csrf_token()` on login/register/OAuth-login and returned in the response body) is required via an `X-CSRF-Token` header on any state-changing request authenticated via the session cookie -- checked in `require_auth`'s session branch (`_csrf_check_failed()`). Only the cookie path is checked: a browser attaches cookies to a cross-site request automatically (the actual CSRF vector), but never attaches a custom header, `Authorization`, or `X-API-Key` on its own, so Bearer-JWT and API-key auth aren't exploitable the same way. `GET /api/auth/csrf-token` returns the current session's token for a client that already has a cookie session (e.g. right after an OAuth redirect) but hasn't seen the token yet.
- **Bearer token checked before the session cookie**: the web panel is same-origin behind nginx, so the browser attaches the session cookie to *every* request automatically -- including the ones the panel is actually authenticating with its Bearer JWT (stored in `localStorage`, attached by `web/src/services/api.js`'s request interceptor). `require_auth` checks the `Authorization` header before the session branch specifically so that ordinary panel traffic never gets routed through the CSRF check above just because a cookie also happens to be present; the SPA never learned to send `X-CSRF-Token` anywhere, so checking session first would have 403'd every mutating action in the panel after login. This doesn't weaken CSRF protection -- a cross-site page can ride a cookie automatically but can't attach a custom `Authorization` header the same way, so trusting a *valid* Bearer token ahead of the cookie doesn't open anything up. Regression test: `tests/api/test_auth.py::TestCsrfProtection::test_bearer_token_wins_over_a_stray_session_cookie`.
- **OAuth state parameter**: `GET /api/auth/oauth/<provider>/url` issues a one-time `state` value (`_issue_oauth_state()`, stored in the session) embedded in the provider's authorization URL; the login callbacks *and* the account-linking callback (`POST /api/auth/oauth/<provider>/link`) reject the request if the `state` they're given doesn't match (`_verify_oauth_state()`). Before this, nothing stopped an attacker from starting their own OAuth flow, capturing the resulting code/id_token, and feeding it to a victim's browser to link or hijack an identity. Because this depends on the session cookie surviving between the `/url` call and the callback, `web/src/services/api.js`'s axios client sets `withCredentials: true` -- the documented dev setup (Vite on `:5173` calling the API on `:8080` directly, bypassing Vite's own `/api` proxy since `API_BASE_URL` defaults to an absolute URL) is cross-origin, and axios drops cookies cross-origin unless told otherwise.
- **Not yet done**: session/JWT revocation on logout -- `logout()` only clears the cookie; a JWT issued before logout remains valid for its full 7-day lifetime. Would need a revocation store (e.g. Redis or a denylist file); tracked as a follow-up.

Tested in `tests/api/test_auth.py` (`TestSessionCookieHardening`, `TestCsrfProtection`) and `tests/api/test_oauth.py` (state-mismatch cases for both login and account-linking).

### 9. API Key Security

- **Storage**: Restricted file permissions (600) on Unix systems
- **Generation**: Cryptographically secure random generation
- **Validation**: Enabled/disabled state checking
- **Audit**: All API key usage logged
- **Header only**: `X-API-Key` header is the only accepted form -- the `?api_key=...` query-string fallback was removed (it leaked into nginx access logs, browser history, and any `Referer` header a follow-on request sent).

### 10. Authentication Enhancements

- **Password Hashing**: bcrypt with automatic salt generation
- **JWT Tokens**: Secure token generation with expiration
- **2FA Support**: TOTP-based two-factor authentication
- **OAuth Security**:
  - Google: full authorization-code exchange + userinfo fetch, now with `state` verification (see above).
  - Apple: **the ID token's signature is now verified** against Apple's published JWKS (`https://appleid.apple.com/auth/keys`, via `PyJWKClient`, checking signature/audience/issuer/expiry in `verify_apple_id_token()`). Previously the code decoded the token with `verify_signature=False` and trusted its `sub` claim outright -- a full authentication bypass, since anyone could POST a self-signed JWT naming an arbitrary user and be logged in as them. Fixed and covered by `tests/api/test_oauth.py`'s `TestVerifyAppleIdToken`/`TestAppleOAuthCallback`.
  - Apple's `response_mode=form_post` callback delivery to a client-side SPA route is a separate, pre-existing question this pass didn't attempt to verify end-to-end -- confirm on a real deployment that `state`/`id_token` actually reach `web/src/pages/OAuthCallback.jsx` before relying on Apple sign-in in production.

### 11. Audit Logging of Authentication Events

`log_audit_event()` (`api/server.py`) previously wasn't called from any `/api/auth/*` route at all, despite this document claiming success/failure was tracked. It now is: `login_success`, `login_failure` (with a reason, never the password), `logout`, `user_registered`, `2fa_enabled`, `2fa_verify_failed`, `2fa_disabled`, `2fa_disable_failed`, `oauth_login_success`, and `oauth_login_failure` (with provider and reason) are all logged. Tested in `tests/api/test_auth.py`'s `TestAuthAuditLogging`.

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
- [ ] Configure `ALLOWED_ORIGINS` with your actual frontend origin(s) -- not `*`
- [ ] Set up a Cloudflare Tunnel (recommended -- see below) or otherwise terminate TLS in front of the API
- [ ] Set up the reverse proxy (`config/nginx-minecraft.conf`)
- [ ] Apply the systemd hardening in `systemd/minecraft-api.service` and confirm with `systemd-analyze security minecraft-api.service` plus a functional smoke test (sandboxing directives can silently break file writes if scoped wrong)
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Monitor `config/audit.log`
- [ ] Regular backups of configuration files
- [ ] If running multiple API workers/processes, point Flask-Limiter's `storage_uri` at Redis instead of the default in-memory store (see below) -- in-memory counters aren't shared across processes

### Cloudflare Tunnel Deployment

The recommended way to expose the admin panel: `cloudflared` makes an outbound-only connection from the Pi to Cloudflare's edge, which terminates TLS for your chosen hostname and proxies traffic down that connection to nginx. No port-forward is needed on your router for the admin panel itself, and no certificate management happens on the Pi.

1. Copy `config/cloudflared-config.yml.example` to `~/.cloudflared/config.yml` and follow the setup steps in its header comment (`cloudflared tunnel login` / `create` / `route dns`, then `cloudflared service install`).
2. `config/nginx-minecraft.conf` already listens on `127.0.0.1:80` rather than every interface -- cloudflared reaches it over loopback, and nothing else needs to.
3. Set `ALLOWED_ORIGINS` (see above) to `https://<your-tunnel-hostname>`.
4. Verify: `curl -I https://<your-tunnel-hostname>/api/health` from outside your network should return a 200 with `Strict-Transport-Security` set.
5. **Optional second auth layer**: Cloudflare Access (part of Cloudflare Zero Trust) can require a login (e.g. via a Cloudflare-managed identity provider, or a one-time PIN to an allowed email) before a request ever reaches the tunnel, independent of this app's own auth. Worth considering for extra defense in depth, but the app-layer hardening in this document is designed to stand on its own regardless.

If you instead port-forward a port directly to the Pi (not recommended over the tunnel approach above), you're responsible for your own TLS termination and certificate renewal, and for firewalling everything except the ports you intend to expose -- `docs/RPI5_FULL_DEPLOYMENT.md`'s "Security Considerations" section has `ufw` examples for that path.

### Security Monitoring

1. **Audit Logs**: All security-relevant actions logged to `config/audit.log`, including authentication success/failure (see "Audit Logging of Authentication Events" above)
2. **Failed Authentication**: Tracked in the audit log and rate-limited (see "Rate Limiting" above)
3. **Command Rejections**: Logged with reasons
4. **Rate Limit Violations**: A 429 response; not currently written to the audit log separately (Flask-Limiter's own counters are the record)

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
   for i in {1..10}; do curl -X POST http://localhost:8080/api/auth/login \
     -H "Content-Type: application/json" -d '{"username":"nope","password":"nope"}'; done
   ```

   Expected: 429 after the 5th request within a minute

4. **CORS**:

   ```bash
   curl -I -H "Origin: https://evil.example" http://localhost:8080/api/health
   ```

   Expected: no `Access-Control-Allow-Origin: https://evil.example` in the response once `ALLOWED_ORIGINS` is set to something other than `*`

### Automated Testing

- `cd tests/api && pytest -v test_auth.py test_oauth.py test_cors.py test_security_headers.py` -- auth, session/CSRF, OAuth (including the Apple signature-verification and state-parameter cases), CORS, and security-header coverage.
- `cd web && npm test` -- includes the OAuth flow's frontend plumbing (`OAuthButtons.test.jsx`, `api.test.js`).

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

1. **In-Memory Rate Limiting**: Flask-Limiter's default `storage_uri="memory://"` isn't shared across processes -- fine for this app's single-process deployment, but a multi-worker/gunicorn setup would need Redis instead.
2. **CORS Wildcard Default**: Still defaults to `*` for local/LAN convenience; `api/server.py` warns loudly on startup if it's still `*`, but nothing stops an operator from ignoring the warning.
3. **WebSocket Security**: Socket.IO connections use the same `ALLOWED_ORIGINS`/auth as the REST API but haven't been separately audited beyond that.
4. **File Upload Limits**: Currently limited by Flask's `MAX_CONTENT_LENGTH`. Consider additional validation.
5. **JWT/session revocation**: `logout()` clears the session cookie but can't invalidate an already-issued JWT -- it remains valid for its full 7-day lifetime. Needs a revocation store (Redis or a denylist file) to fix properly.
6. **JWT/API key storage in the browser**: `web/src/services/api.js` stores the JWT and API key in `localStorage`, which is readable by any script running on the page (i.e. exposed to XSS). A tighter design would use an httpOnly cookie for the SPA's own auth too, which would also broaden the CSRF protection above to cover it -- a larger frontend change, not done in this pass.
7. **Legacy API keys default to admin**: keys created before role/permission scoping existed are auto-migrated to the `admin` role on load rather than failing closed, for backward compatibility (`_migrate_api_key_roles`). Worth a deliberate audit of existing keys rather than an automatic behavior change.
8. **Backup encryption at rest**: local backups and R2/B2 cloud backups are unencrypted; only the S3 cloud-backup path has an optional server-side encryption flag. Not addressed here since backups aren't the internet-facing attack surface.
9. **`ALLOWED_MINECRAFT_COMMANDS` allowlist is defined but unenforced**: `sanitize_minecraft_command()` (`api/security.py`) uses a blacklist, not the allowlist also defined in that file. Enforcing the allowlist would be a behavior change worth its own review.
10. **systemd sandboxing isn't maximal**: `systemd/minecraft-api.service` has `ProtectSystem=strict` and several other hardening directives, but deliberately omits `SystemCallFilter=` and `MemoryDenyWriteExecute=` -- the former risks breaking the app's subprocess/docker/RCON calls in ways that need real-hardware testing to get right, and the latter is a known friction point with eventlet/greenlet's stack-switching on some platforms. Verify with `systemd-analyze security minecraft-api.service` and a full functional smoke test before tightening further.
11. **Apple Sign In's `response_mode=form_post`**: delivers the callback to a client-side SPA route as a POST, which the current frontend routing may not actually receive correctly (see the OAuth section above) -- not verified end-to-end against real Apple credentials in this pass.

## 📚 References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Python Security Guide](https://python.readthedocs.io/en/stable/library/security.html)

---

**Last Updated**: 2026-09-22
**Status**: ✅ Security hardening implemented
