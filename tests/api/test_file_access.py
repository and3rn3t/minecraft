"""
Who may read files through the API.

The file browser used to need only config.view, which every role holds, so a
plain "user" API key could read config/api-keys.json and become an admin. It
now needs files.view (admin only). The config-file viewer stays open to
config.view but masks credential values for anyone who cannot edit config.
"""

import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402
import api.rbac as rbac  # noqa: E402
from api.config_redaction import redact_config_secrets  # noqa: E402

ADMIN_KEYS_CONTENT = '{"the-real-admin-key": {"role": "admin"}}'


@pytest.fixture
def tree(monkeypatch):
    """A throwaway project root holding the files an attacker would want.

    resolve()d because macOS's /var is a symlink to /private/var, and the
    allowlist check compares real paths.
    """
    root = Path(tempfile.mkdtemp()).resolve()
    (root / "config").mkdir()
    (root / "data").mkdir()
    (root / "config" / "api-keys.json").write_text(ADMIN_KEYS_CONTENT)
    (root / "config" / "users.json").write_text('{"admin": {"password_hash": "$2b$12$hash"}}')
    (root / "data" / "server.properties").write_text("motd=Hello\nrcon.password=hunter2\nmax-players=10\n")

    monkeypatch.setattr(api_module, "PROJECT_ROOT", root)
    monkeypatch.setattr(api_module, "ALLOWED_FILE_PATHS", [root / "config", root / "data"])
    monkeypatch.setattr(api_module, "CONFIG_ALLOWED_PATHS", {"server.properties": root / "data" / "server.properties"})
    return root


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def key_for(monkeypatch):
    """Headers for an API key of the given role"""

    def make(role):
        key = f"file-access-{role}-key"
        monkeypatch.setitem(api_module.API_KEYS, key, {"name": role, "enabled": True, "role": role})
        return {"X-API-Key": key}

    return make


FILE_BROWSER_READS = [
    "/api/files/read?path=config/api-keys.json",
    "/api/files/download?path=config/api-keys.json",
    "/api/files/list?path=config",
]


class TestFileBrowserIsAdminOnly:
    @pytest.mark.parametrize("role", ["user", "operator"])
    @pytest.mark.parametrize("url", FILE_BROWSER_READS)
    def test_non_admins_are_refused(self, client, tree, key_for, role, url):
        response = client.get(url, headers=key_for(role))

        assert response.status_code == 403
        assert response.get_json()["required_permission"] == "files.view"
        assert "the-real-admin-key" not in response.get_data(as_text=True)

    @pytest.mark.parametrize("url", FILE_BROWSER_READS)
    def test_admins_still_have_it(self, client, tree, key_for, url):
        response = client.get(url, headers=key_for("admin"))
        assert response.status_code == 200

    def test_no_role_but_admin_holds_files_view(self):
        holders = [role for role, perms in rbac.ROLE_PERMISSIONS.items() if "files.view" in perms]
        assert holders == ["admin"]


class TestConfigViewerMasksSecrets:
    def test_a_user_sees_the_file_without_the_rcon_password(self, client, tree, key_for):
        response = client.get("/api/config/files/server.properties", headers=key_for("user"))

        assert response.status_code == 200
        data = response.get_json()
        assert "hunter2" not in data["content"]
        assert "rcon.password=********" in data["content"]
        assert "motd=Hello" in data["content"], "everything else is unchanged"
        assert data["redacted"] is True

    def test_an_admin_sees_the_real_value(self, client, tree, key_for):
        data = client.get("/api/config/files/server.properties", headers=key_for("admin")).get_json()

        assert "rcon.password=hunter2" in data["content"]
        assert data["redacted"] is False


# Filled in at runtime: a literal credential-shaped value in these templates
# trips secret scanners (GitGuardian) even though it is fake.
PLACEHOLDER = "-".join(["not", "a", "real", "value"])


class TestRedactConfigSecrets:
    @pytest.mark.parametrize(
        "template",
        [
            "rcon.password={}",
            "SECRET_KEY={}",
            "CLOUDFLARE_API_TOKEN={}",
            "NOIP_PASSWORD = {}",
            "export ANTHROPIC_API_KEY={}",
            "      RCON_PASSWORD: {}",
            "      - RCON_PASSWORD={}",
        ],
    )
    def test_credential_values_are_masked(self, template):
        line = template.format(PLACEHOLDER)
        assert redact_config_secrets(line) == (template.format("********"), True)

    @pytest.mark.parametrize(
        "line",
        [
            "motd=A Minecraft Server",
            "max-players=10",
            "enable-rcon=true",
            "      MEMORY: 4G",
            "# rcon.password=only-a-comment",
            "rcon.password=",
            "",
        ],
    )
    def test_everything_else_is_left_alone(self, line):
        assert redact_config_secrets(line) == (line, False)

    @pytest.mark.parametrize(
        "template, expected",
        [
            # YAML block scalars: every line of the value is withheld
            (
                "environment:\n  SECRET_KEY: |\n    {v}\n    {v}\n  MEMORY: 4G",
                "environment:\n  SECRET_KEY: ********\n  MEMORY: 4G",
            ),
            ("PRIVATE_KEY: >-\n  {v}\n  {v}\nport: 25565", "PRIVATE_KEY: ********\nport: 25565"),
            # A nested block under an empty sensitive key
            ("credentials:\n  - {v}\n  - {v}\nport: 25565", "credentials:\nport: 25565"),
            # A quoted .conf value running over several lines
            ('APPLE_PRIVATE_KEY="-----BEGIN\n{v}\n-----END"\nNEXT=1', "APPLE_PRIVATE_KEY=********\nNEXT=1"),
        ],
    )
    def test_values_spanning_lines_are_withheld_entirely(self, template, expected):
        content = template.format(v=PLACEHOLDER)

        result, redacted = redact_config_secrets(content)

        assert PLACEHOLDER not in result
        assert (result, redacted) == (expected, True)


class TestDdnsConfigMasksSecrets:
    """/api/ddns/config returned ddns.conf raw to config.view, which let every
    role read the Cloudflare token around the config viewer's masking."""

    @pytest.fixture
    def ddns_conf(self, tree, monkeypatch):
        path = tree / "config" / "ddns.conf"
        path.write_text(f"DDNS_PROVIDER=cloudflare\nCLOUDFLARE_API_TOKEN={PLACEHOLDER}\n")
        monkeypatch.setattr(api_module, "DDNS_CONFIG_FILE", path)
        return path

    def test_a_user_sees_the_token_masked(self, client, ddns_conf, key_for):
        data = client.get("/api/ddns/config", headers=key_for("user")).get_json()

        assert PLACEHOLDER not in data["content"]
        assert "CLOUDFLARE_API_TOKEN=********" in data["content"]
        assert "DDNS_PROVIDER=cloudflare" in data["content"]
        assert data["redacted"] is True

    def test_an_admin_sees_it_unmasked(self, client, ddns_conf, key_for):
        data = client.get("/api/ddns/config", headers=key_for("admin")).get_json()

        assert PLACEHOLDER in data["content"]
        assert data["redacted"] is False
