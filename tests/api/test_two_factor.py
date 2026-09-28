"""
Tests for two-factor authentication: /api/auth/2fa/* and the TOTP step of login.

Real pyotp secrets and codes are used throughout, so a change in how codes are
generated or checked shows up here rather than only on a phone.
"""

import json
import sys
from pathlib import Path

import pyotp
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402

app = api_module.app

CSRF = "test-csrf-token"
PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Login and the 2FA routes are rate limited per client address, and every
    test client shares one; without a reset these tests fail by running order."""
    if api_module.limiter is not None:
        api_module.limiter.reset()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def users_file(tmp_path, monkeypatch):
    path = tmp_path / "users.json"
    monkeypatch.setattr(api_module, "USERS_FILE", path)
    monkeypatch.setattr(api_module, "USERS", {})
    # Hashing is not what is under test, and real bcrypt is slow
    monkeypatch.setattr(api_module, "BCRYPT_AVAILABLE", True)
    monkeypatch.setattr(api_module, "hash_password", lambda p: f"hashed_{p}")
    monkeypatch.setattr(api_module, "verify_password", lambda p, h: h == f"hashed_{p}")
    return path


@pytest.fixture
def alice(users_file):
    api_module.USERS["alice"] = {
        "username": "alice",
        "password_hash": f"hashed_{PASSWORD}",
        "role": "user",
        "enabled": True,
    }
    return api_module.USERS["alice"]


@pytest.fixture
def logged_in(client, alice):
    with client.session_transaction() as session:
        session["username"] = "alice"
        session["csrf_token"] = CSRF
    return client


def _post(client, path, body=None):
    return client.post(path, json=body or {}, headers={"X-CSRF-Token": CSRF})


def _stored(users_file):
    return json.loads(users_file.read_text())["alice"]


def _enable_2fa(client):
    secret = _post(client, "/api/auth/2fa/setup").get_json()["secret"]
    response = _post(client, "/api/auth/2fa/verify", {"token": pyotp.TOTP(secret).now()})
    assert response.status_code == 200
    return secret


class TestSetup:
    def test_requires_a_session(self, client, alice):
        assert client.post("/api/auth/2fa/setup").status_code == 401

    def test_issues_a_secret_but_does_not_enable_2fa_yet(self, logged_in, users_file):
        response = _post(logged_in, "/api/auth/2fa/setup")

        assert response.status_code == 200
        data = response.get_json()
        assert data["uri"].startswith("otpauth://totp/")
        assert data["secret"] in data["uri"]
        assert data["qr_code"], "a base64 PNG for the authenticator app"

        stored = _stored(users_file)
        assert stored["totp_secret"] == data["secret"]
        assert stored["totp_enabled"] is False, "enabled only once a code is verified"

    def test_cannot_switch_off_active_2fa_with_only_a_session(self, logged_in, users_file):
        """Setup used to replace the secret and turn 2FA off, so a stolen
        session alone could remove it. Disabling needs the password."""
        secret = _enable_2fa(logged_in)

        response = _post(logged_in, "/api/auth/2fa/setup")

        assert response.status_code == 409
        stored = _stored(users_file)
        assert stored["totp_enabled"] is True
        assert stored["totp_secret"] == secret, "the working secret is untouched"


class TestVerify:
    def test_needs_a_token(self, logged_in):
        _post(logged_in, "/api/auth/2fa/setup")
        assert _post(logged_in, "/api/auth/2fa/verify").status_code == 400

    def test_refuses_before_setup(self, logged_in):
        response = _post(logged_in, "/api/auth/2fa/verify", {"token": "123456"})
        assert response.status_code == 400
        assert "set up" in response.get_json()["error"]

    def test_wrong_code_leaves_2fa_off(self, logged_in, users_file):
        secret = _post(logged_in, "/api/auth/2fa/setup").get_json()["secret"]
        wrong = str((int(pyotp.TOTP(secret).now()) + 1) % 1_000_000).zfill(6)

        response = _post(logged_in, "/api/auth/2fa/verify", {"token": wrong})

        assert response.status_code == 401
        assert _stored(users_file)["totp_enabled"] is False

    def test_correct_code_enables_and_persists(self, logged_in, users_file):
        _enable_2fa(logged_in)

        assert _stored(users_file)["totp_enabled"] is True
        status = logged_in.get("/api/auth/2fa/status").get_json()
        assert status == {"success": True, "enabled": True, "configured": True, "has_password": True}


class TestLoginWith2fa:
    def _login(self, client, **extra):
        return client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD, **extra})

    def test_password_alone_is_not_enough(self, logged_in):
        _enable_2fa(logged_in)

        response = self._login(logged_in)

        assert response.status_code == 401
        assert response.get_json()["requires_2fa"] is True

    def test_wrong_code_is_refused(self, logged_in):
        _enable_2fa(logged_in)

        response = self._login(logged_in, totp_token="000000")

        assert response.status_code == 401
        assert "2FA" in response.get_json()["error"]

    def test_current_code_logs_in(self, logged_in):
        secret = _enable_2fa(logged_in)

        response = self._login(logged_in, totp_token=pyotp.TOTP(secret).now())

        assert response.status_code == 200
        assert response.get_json()["user"]["username"] == "alice"

    def test_accounts_without_2fa_need_no_code(self, client, alice):
        assert self._login(client).status_code == 200


class TestDisable:
    def test_needs_the_password(self, logged_in):
        _enable_2fa(logged_in)
        assert _post(logged_in, "/api/auth/2fa/disable").status_code == 400

    def test_wrong_password_leaves_2fa_on(self, logged_in, users_file):
        _enable_2fa(logged_in)

        response = _post(logged_in, "/api/auth/2fa/disable", {"password": "guess"})

        assert response.status_code == 401
        assert _stored(users_file)["totp_enabled"] is True

    def test_correct_password_turns_it_off_and_forgets_the_secret(self, logged_in, users_file):
        _enable_2fa(logged_in)

        response = _post(logged_in, "/api/auth/2fa/disable", {"password": PASSWORD})

        assert response.status_code == 200
        stored = _stored(users_file)
        assert stored["totp_enabled"] is False
        assert "totp_secret" not in stored
        assert logged_in.get("/api/auth/2fa/status").get_json()["configured"] is False


class TestAccountsWithoutAPassword:
    """Accounts created by Google or Apple sign-in have no password_hash.

    Disabling 2FA used to index it and fail with a 500, so an account in that
    state could neither turn 2FA off nor, once setup refused while 2FA was on,
    replace it.
    """

    @pytest.fixture
    def oauth_only(self, logged_in):
        del api_module.USERS["alice"]["password_hash"]
        return logged_in

    def test_setup_explains_that_the_provider_handles_it(self, oauth_only):
        response = _post(oauth_only, "/api/auth/2fa/setup")

        assert response.status_code == 400
        assert "Google or Apple" in response.get_json()["error"]
        assert "totp_secret" not in api_module.USERS["alice"]

    def test_status_says_there_is_no_password(self, oauth_only):
        assert oauth_only.get("/api/auth/2fa/status").get_json()["has_password"] is False

    @pytest.fixture
    def stuck_with_2fa(self, oauth_only):
        """2FA left on from before setup refused these accounts"""
        secret = pyotp.random_base32()
        api_module.USERS["alice"].update(totp_secret=secret, totp_enabled=True)
        return secret

    def test_disable_needs_a_code(self, oauth_only, stuck_with_2fa):
        response = _post(oauth_only, "/api/auth/2fa/disable", {"password": "anything"})
        assert response.status_code == 400

    def test_disable_refuses_a_wrong_code(self, oauth_only, stuck_with_2fa):
        response = _post(oauth_only, "/api/auth/2fa/disable", {"token": "000000"})

        assert response.status_code == 401
        assert api_module.USERS["alice"]["totp_enabled"] is True

    def test_disable_accepts_a_current_code(self, oauth_only, stuck_with_2fa):
        code = pyotp.TOTP(stuck_with_2fa).now()

        response = _post(oauth_only, "/api/auth/2fa/disable", {"token": code})

        assert response.status_code == 200
        assert api_module.USERS["alice"]["totp_enabled"] is False
