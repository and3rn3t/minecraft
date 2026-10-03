"""
The file browser's ordinary behaviour: listing, reading, writing, uploading
and deleting inside the allowed roots.

Attacks on these routes (traversal, symlinks, null bytes) are in
test_path_traversal.py and who may use them is in test_file_access.py; this
file is what they do for an admin who is allowed to.
"""

import io
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402


@pytest.fixture
def root(monkeypatch, tmp_path):
    """A throwaway project root with the four allowed directories.

    resolve()d because macOS's /var is a symlink to /private/var, and the
    allowlist compares real paths.
    """
    root = tmp_path.resolve()
    for name in ("data", "config", "backups", "scripts"):
        (root / name).mkdir()
    monkeypatch.setattr(api_module, "PROJECT_ROOT", root)
    monkeypatch.setattr(api_module, "ALLOWED_FILE_PATHS", [root / n for n in ("data", "config", "backups", "scripts")])
    return root


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api_module.API_KEYS, "browser-admin", {"name": "a", "enabled": True, "role": "admin"})
    api_module.app.config["TESTING"] = True
    test_client = api_module.app.test_client()
    test_client.environ_base["HTTP_X_API_KEY"] = "browser-admin"
    return test_client


class TestList:
    def test_without_a_path_lists_the_roots_that_exist(self, client, root):
        (root / "scripts").rmdir()

        data = client.get("/api/files/list").get_json()

        assert [f["name"] for f in data["files"]] == ["data", "config", "backups"]
        assert all(f["type"] == "directory" for f in data["files"])

    def test_directories_come_first_then_files_alphabetically(self, client, root):
        (root / "data" / "world").mkdir()
        (root / "data" / "Zeta.txt").write_text("z")
        (root / "data" / "alpha.txt").write_text("abc")
        (root / "data" / "logs").mkdir()

        data = client.get("/api/files/list?path=data").get_json()

        assert [f["name"] for f in data["files"]] == ["logs", "world", "alpha.txt", "Zeta.txt"]
        alpha = next(f for f in data["files"] if f["name"] == "alpha.txt")
        assert alpha == {**alpha, "path": "data/alpha.txt", "type": "file", "size": 3}
        assert data["path"] == "data"

    def test_a_missing_directory_is_404(self, client, root):
        response = client.get("/api/files/list?path=data/nope")
        assert response.status_code == 404

    def test_a_file_is_not_a_directory(self, client, root):
        (root / "data" / "server.properties").write_text("motd=x")
        response = client.get("/api/files/list?path=data/server.properties")
        assert response.status_code == 400


class TestRead:
    def test_returns_the_content_and_size(self, client, root):
        (root / "data" / "server.properties").write_text("motd=Hello\n")

        data = client.get("/api/files/read?path=data/server.properties").get_json()

        assert data == {"success": True, "content": "motd=Hello\n", "path": "data/server.properties", "size": 11}

    def test_undecodable_bytes_are_replaced_rather_than_failing(self, client, root):
        (root / "data" / "level.dat").write_bytes(b"ok\xff\xfe")

        response = client.get("/api/files/read?path=data/level.dat")

        assert response.status_code == 200
        assert response.get_json()["content"].startswith("ok")

    def test_files_over_1mb_are_refused(self, client, root):
        (root / "data" / "big.log").write_bytes(b"x" * (1024 * 1024 + 1))

        response = client.get("/api/files/read?path=data/big.log")

        assert response.status_code == 400
        assert "too large" in response.get_json()["error"]

    @pytest.mark.parametrize("query, status", [("", 400), ("?path=data/nope.txt", 404), ("?path=data", 400)])
    def test_bad_requests(self, client, root, query, status):
        response = client.get(f"/api/files/read{query}")
        assert response.status_code == status


class TestWrite:
    def test_creates_a_new_file_and_its_parents(self, client, root):
        response = client.post("/api/files/write", json={"path": "data/plugins/Foo/config.yml", "content": "a: 1\n"})

        assert response.status_code == 200
        assert response.get_json()["backup"] is None, "nothing existed to back up"
        assert (root / "data" / "plugins" / "Foo" / "config.yml").read_text() == "a: 1\n"

    def test_overwriting_keeps_a_backup_of_the_old_content(self, client, root):
        target = root / "data" / "server.properties"
        target.write_text("motd=Old\n")

        data = client.post(
            "/api/files/write", json={"path": "data/server.properties", "content": "motd=New\n"}
        ).get_json()

        assert target.read_text() == "motd=New\n"
        assert data["backup"].startswith("backups/file-edits/server.properties.")
        assert (root / data["backup"]).read_text() == "motd=Old\n"

    def test_needs_a_path(self, client, root):
        response = client.post("/api/files/write", json={"content": "x"})
        assert response.status_code == 400


class TestUpload:
    def _upload(self, client, path, name, content=b"data"):
        return client.post(
            "/api/files/upload",
            data={"path": path, "file": (io.BytesIO(content), name)},
            content_type="multipart/form-data",
        )

    def test_saves_into_the_given_directory(self, client, root):
        response = self._upload(client, "data/plugins", "Essentials.jar", b"jar-bytes")

        assert response.status_code == 200
        assert (root / "data" / "plugins" / "Essentials.jar").read_bytes() == b"jar-bytes"

    def test_the_filename_is_sanitised(self, client, root):
        response = self._upload(client, "data", "../../evil name.sh")

        assert response.status_code == 200
        assert response.get_json()["path"] == "data/evil_name.sh"

    def test_files_over_10mb_are_refused(self, client, root):
        response = self._upload(client, "data", "huge.bin", b"x" * (10 * 1024 * 1024 + 1))
        assert response.status_code == 400

    def test_needs_a_file_and_a_path(self, client, root):
        response = client.post("/api/files/upload", data={"path": "data"})
        assert response.status_code == 400
        response = self._upload(client, "", "a.txt")
        assert response.status_code == 400


class TestDelete:
    def test_deletes_a_file(self, client, root):
        (root / "data" / "old.log").write_text("x")

        response = client.delete("/api/files/delete?path=data/old.log")
        assert response.status_code == 200
        assert not (root / "data" / "old.log").exists()

    def test_deletes_a_directory_tree(self, client, root):
        (root / "data" / "world_old" / "region").mkdir(parents=True)
        (root / "data" / "world_old" / "region" / "r.0.0.mca").write_text("x")

        response = client.delete("/api/files/delete?path=data/world_old")
        assert response.status_code == 200
        assert not (root / "data" / "world_old").exists()

    @pytest.mark.parametrize("name", ["data", "config", "backups", "scripts"])
    def test_the_roots_themselves_are_protected(self, client, root, name):
        """backups/ used to be deletable: protection matched a list of names
        that left it out."""
        response = client.delete(f"/api/files/delete?path={name}")

        assert response.status_code == 403
        assert (root / name).is_dir()

    def test_a_folder_merely_named_like_a_root_can_be_deleted(self, client, root):
        """Matching by name also refused a plugin's own config folder."""
        folder = root / "data" / "plugins" / "Foo" / "config"
        folder.mkdir(parents=True)

        response = client.delete("/api/files/delete?path=data/plugins/Foo/config")
        assert response.status_code == 200
        assert not folder.exists()

    def test_a_missing_file_is_404(self, client, root):
        response = client.delete("/api/files/delete?path=data/nope")
        assert response.status_code == 404


class TestDownload:
    def test_sends_the_file_as_an_attachment(self, client, root):
        (root / "backups" / "notes.txt").write_text("hello")

        response = client.get("/api/files/download?path=backups/notes.txt")

        assert response.status_code == 200
        assert response.data == b"hello"
        assert "attachment" in response.headers["Content-Disposition"]
        assert "notes.txt" in response.headers["Content-Disposition"]
