#!/usr/bin/env python3
"""Path traversal defences for every endpoint that takes a path.

CodeQL reports "Uncontrolled data used in path expression" across these
handlers. All of them are false positives: the file browser resolves a path
with ``os.path.realpath`` and checks it against an allowlist, the config
endpoints use the request value only as a dictionary key, and the backup
endpoints reject separators outright.

"Reviewed and judged safe" is worth very little on its own, though — the next
person to simplify ``is_path_allowed`` would not hear about it. These tests are
the durable half of that triage: they attack the endpoints rather than reading
them, so the defences cannot be removed quietly.

The symlink cases matter most. Rejecting ".." is easy; following a symlink out
of an allowed directory is what defeats naive implementations, and it works here
only because the path is resolved *before* the allowlist check.
"""

import sys
import tempfile
import uuid
from io import BytesIO
from pathlib import Path as PathLib

import pytest
from unittest.mock import patch

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402

# Payloads that defeat a naive check. Encoded forms are included because a
# check running before URL decoding sees different bytes than the filesystem.
TRAVERSAL_PAYLOADS = [
    "../../../../etc/passwd",
    "....//....//etc/passwd",
    "/etc/passwd",
    "..%2f..%2f..%2fetc%2fpasswd",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "data/../../../etc/passwd",
    "config/../../etc/passwd",
    "..\\..\\..\\etc\\passwd",
    "data/./../../etc/passwd",
    "\\..\\..\\etc\\passwd",
    "data/..%00/../etc/passwd",
]

# Anything that reaches /etc/passwd contains this.
PASSWD_MARKER = "root:"


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as client:
        yield client


@pytest.fixture
def auth(monkeypatch):
    key = "traversal-test-key"
    monkeypatch.setitem(api_module.API_KEYS, key, {"name": "t", "enabled": True, "role": "admin"})
    return {"X-API-Key": key}


@pytest.fixture
def escaping_symlink():
    """A symlink inside an allowed directory pointing outside every allowed root.

    The name is unique per test. CI runs `pytest -n auto`, and a fixed name
    means one worker's teardown can unlink the link another worker is about to
    follow — which would make these tests flaky, and worse, could have one
    worker checking a link it did not create.
    """
    allowed_root = api_module.PROJECT_ROOT / "data"
    allowed_root.mkdir(parents=True, exist_ok=True)

    outside = PathLib(tempfile.mkdtemp()) / "secret.txt"
    outside.write_text("SENSITIVE-CONTENT-OUTSIDE-ALLOWED-ROOTS\n")

    name = f"traversal-test-symlink-{uuid.uuid4().hex}"
    link = allowed_root / name
    link.symlink_to(outside)

    yield f"data/{name}", outside

    if link.is_symlink() or link.exists():
        link.unlink()


def _leaked(response):
    return PASSWD_MARKER in response.get_data(as_text=True)


class TestFileBrowserReads:
    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
    def test_read_refuses_to_escape(self, client, auth, payload):
        response = client.get(f"/api/files/read?path={payload}", headers=auth)

        assert response.status_code in (400, 403, 404)
        assert not _leaked(response)

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
    def test_download_refuses_to_escape(self, client, auth, payload):
        response = client.get(f"/api/files/download?path={payload}", headers=auth)

        assert response.status_code in (400, 403, 404)
        assert not _leaked(response)

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
    def test_list_refuses_to_escape(self, client, auth, payload):
        response = client.get(f"/api/files/list?path={payload}", headers=auth)

        assert response.status_code in (400, 403, 404)


class TestFileBrowserWrites:
    """A write that escapes is worse than a read that does."""

    @pytest.mark.parametrize("payload", ["../../../../tmp/pwned.txt", "/tmp/pwned.txt", "data/../../tmp/pwned.txt"])
    def test_write_refuses_to_escape(self, client, auth, payload, tmp_path):
        canary = PathLib("/tmp/pwned.txt")
        existed = canary.exists()

        response = client.post("/api/files/write", headers=auth, json={"path": payload, "content": "x"})

        assert response.status_code in (400, 403, 404)
        if not existed:
            assert not canary.exists(), "a write escaped the allowed roots"

    @pytest.mark.parametrize("payload", ["../../../../etc/passwd", "/etc/passwd"])
    def test_delete_refuses_to_escape(self, client, auth, payload):
        response = client.delete(f"/api/files/delete?path={payload}", headers=auth)

        assert response.status_code in (400, 403, 404)


class TestUpload:
    """Upload builds its path from a form field and a filename, which is a
    different construction from the other endpoints and needs its own tests."""

    @pytest.mark.parametrize("payload", ["../../../../tmp", "/tmp", "data/../../tmp"])
    def test_upload_refuses_a_destination_outside_the_roots(self, client, auth, payload):
        canary = PathLib("/tmp/uploaded-canary.txt")
        existed = canary.exists()

        response = client.post(
            "/api/files/upload",
            headers=auth,
            data={"path": payload, "file": (BytesIO(b"x"), "uploaded-canary.txt")},
            content_type="multipart/form-data",
        )

        assert response.status_code in (400, 403, 404)
        if not existed:
            assert not canary.exists(), "an upload escaped the allowed roots"

    def test_upload_refuses_a_traversing_filename(self, client, auth):
        """The filename is the other half of the path.

        ``secure_filename`` flattens it, so the upload either lands inside the
        requested directory under a harmless name, or is refused. What must not
        happen is a file appearing anywhere else.
        """
        marker = f"escaped-{uuid.uuid4().hex}.txt"
        outside = PathLib("/tmp") / marker
        data_dir = api_module.PROJECT_ROOT / "data"

        try:
            response = client.post(
                "/api/files/upload",
                headers=auth,
                data={"path": "data", "file": (BytesIO(b"x"), f"../../../../tmp/{marker}")},
                content_type="multipart/form-data",
            )

            assert not outside.exists(), "the upload filename escaped the allowed roots"

            if response.status_code == 200:
                # Accepted, so it must be inside data/ with the traversal gone.
                landed = list(data_dir.glob(f"*{marker}"))
                assert landed, "a successful upload should have written inside data/"
                for path in landed:
                    assert ".." not in path.name
                    assert api_module.is_path_allowed(str(path))
            else:
                assert response.status_code in (400, 403, 404)
        finally:
            for path in data_dir.glob(f"*{marker}"):
                path.unlink()
            if outside.exists():
                outside.unlink()


class TestConfigValidate:
    """/api/config/files/<path:filename>/validate takes a path of its own."""

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS[:6])
    def test_validate_refuses_anything_not_on_the_allowlist(self, client, auth, payload):
        response = client.post(f"/api/config/files/{payload}/validate", headers=auth, json={"content": "a: 1"})

        assert response.status_code in (308, 400, 403, 404)
        assert not _leaked(response)


class TestSymlinkEscape:
    """Rejecting ".." is the easy half. A symlink out of an allowed directory
    is what defeats a check that looks at the string instead of the resolved
    path, and it is only caught here because .resolve() runs first."""

    def test_reading_through_a_symlink_is_refused(self, client, auth, escaping_symlink):
        path, outside = escaping_symlink

        response = client.get(f"/api/files/read?path={path}", headers=auth)

        assert response.status_code in (400, 403, 404)
        assert "SENSITIVE-CONTENT" not in response.get_data(as_text=True)

    def test_writing_through_a_symlink_is_refused(self, client, auth, escaping_symlink):
        path, outside = escaping_symlink
        before = outside.read_text()

        response = client.post("/api/files/write", headers=auth, json={"path": path, "content": "OVERWRITTEN"})

        assert response.status_code in (400, 403, 404)
        assert outside.read_text() == before, "a write followed the symlink out"

    def test_deleting_through_a_symlink_is_refused(self, client, auth, escaping_symlink):
        path, outside = escaping_symlink

        response = client.delete(f"/api/files/delete?path={path}", headers=auth)

        assert response.status_code in (400, 403, 404)
        assert outside.exists(), "a delete followed the symlink out"

    def test_downloading_through_a_symlink_is_refused(self, client, auth, escaping_symlink):
        path, outside = escaping_symlink

        response = client.get(f"/api/files/download?path={path}", headers=auth)

        assert response.status_code in (400, 403, 404)
        assert "SENSITIVE-CONTENT" not in response.get_data(as_text=True)


class TestConfigFiles:
    """These take the request value as a dictionary key, so the path never
    comes from the caller at all."""

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
    def test_read_refuses_anything_not_on_the_allowlist(self, client, auth, payload):
        response = client.get(f"/api/config/files/{payload}", headers=auth)

        assert response.status_code in (308, 400, 403, 404)
        assert not _leaked(response)

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS[:5])
    def test_write_refuses_anything_not_on_the_allowlist(self, client, auth, payload):
        response = client.post(f"/api/config/files/{payload}", headers=auth, json={"content": "x"})

        assert response.status_code in (308, 400, 403, 404)


class TestBackups:
    """These reject separators outright, so a filename can only name something
    directly inside backups/."""

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS[:6])
    def test_delete_refuses_to_escape(self, client, auth, payload):
        response = client.delete(f"/api/backups/{payload}", headers=auth)

        assert response.status_code in (308, 400, 403, 404)

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS[:6])
    def test_restore_refuses_to_escape(self, client, auth, payload):
        response = client.post(f"/api/backups/{payload}/restore", headers=auth)

        assert response.status_code in (308, 400, 403, 404)


class TestTheAllowlistItself:
    """is_path_allowed is the single point the file browser depends on."""

    def test_paths_inside_an_allowed_root_are_allowed(self):
        assert api_module.is_path_allowed(api_module.PROJECT_ROOT / "data" / "anything.txt")

    @pytest.mark.parametrize(
        "outside",
        ["/etc/passwd", "/tmp", "/", "/usr/bin/python3"],
    )
    def test_paths_outside_every_root_are_refused(self, outside):
        assert not api_module.is_path_allowed(PathLib(outside))

    def test_a_sibling_with_a_shared_prefix_is_refused(self):
        """data-evil/ must not pass because it starts with data/. The check
        appends a separator to each root for exactly this reason."""
        assert not api_module.is_path_allowed(PROJECT_ROOT.parent / "data-evil" / "x")

    def test_the_project_root_itself_is_refused(self):
        """The allowlist is four subdirectories, not the whole checkout."""
        assert not api_module.is_path_allowed(api_module.PROJECT_ROOT)


class TestAuditLogDoesNotStoreSecrets:
    """CodeQL reports "Clear-text storage of sensitive information" where the
    audit log is written, because it classifies the API_KEYS dict as sensitive
    and follows anything derived from it.

    What is actually derived is the key's *name* — the label someone typed,
    like "dashboard" — via ``API_KEYS[key]["name"]``. The key itself never
    reaches the log. That is worth an assertion rather than an argument.
    """

    def test_the_key_value_is_never_written_to_the_audit_log(self, client, auth, tmp_path, monkeypatch):
        # Built rather than written out: a literal that looks like a
        # credential trips the secret scanners, and the test only needs a
        # value it can later assert is absent from the log.
        secret_key = "mc_" + uuid.uuid4().hex + uuid.uuid4().hex[:8]
        monkeypatch.setitem(api_module.API_KEYS, secret_key, {"name": "dashboard", "enabled": True, "role": "admin"})
        audit_log = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", audit_log)

        # Any audited action performed with the key. run_rcon_command is
        # stubbed: the audit entry is written before the command runs, so the
        # real runner is unnecessary here and would otherwise let this test
        # issue "list" to whatever server happens to be reachable.
        with patch.object(api_module, "run_rcon_command", return_value=("", "", 0)):
            client.post(
                "/api/server/command",
                headers={"X-API-Key": secret_key},
                json={"command": "list"},
            )

        assert audit_log.exists(), "the action should have been audited"
        written = audit_log.read_text()
        assert secret_key not in written, "the API key value reached the audit log"
        # The key's label is what identifies the actor, and that is the point.
        assert "dashboard" in written

    def test_passwords_are_not_written_to_the_audit_log(self, client, auth, tmp_path, monkeypatch):
        """An audited route that receives a password must not record it.

        This drives POST /api/users rather than registration -- either audits
        now, but this one doesn't also need REGISTRATION_ENABLED wired up.
        """
        audit_log = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", audit_log)
        monkeypatch.setattr(api_module, "USERS", {"admin": {"role": "admin", "enabled": True}})
        monkeypatch.setattr(api_module, "USERS_FILE", tmp_path / "users.json")
        monkeypatch.setattr(api_module, "BCRYPT_AVAILABLE", True)
        monkeypatch.setattr(api_module, "hash_password", lambda value: f"hashed_{value}")

        # Constructed for the same reason as the key above.
        password = "pw-" + uuid.uuid4().hex

        response = client.post(
            "/api/users",
            headers=auth,
            json={"username": "silas", "password": password},
        )

        assert response.status_code == 201, "the audited route should have succeeded"
        assert audit_log.exists(), "users.create is audited; without an entry this proves nothing"
        written = audit_log.read_text()
        assert "users.create" in written
        assert password not in written
        assert f"hashed_{password}" not in written
