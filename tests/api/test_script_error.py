"""What an API client may see when a management script fails.

Scripts print messages meant to be read, so script_error passes them through. A Python
traceback is the one thing that must not reach a client: it carries file paths and
source lines. It is logged, and the route's fallback message is returned instead.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

import api.server as api_module
from api.security import sanitize_for_log

TRACEBACK = """Traceback (most recent call last):
  File "/home/pi/minecraft-server/scripts/analytics-processor.py", line 212, in <module>
    main()
  File "/home/pi/minecraft-server/scripts/analytics-processor.py", line 88, in main
    data = json.load(open("/home/pi/minecraft-server/analytics/raw/secret-path.json"))
FileNotFoundError: [Errno 2] No such file or directory
"""


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api_module.API_KEYS, "stderr-admin", {"name": "t", "enabled": True, "role": "admin"})
    api_module.app.config["TESTING"] = True
    test_client = api_module.app.test_client()
    test_client.environ_base["HTTP_X_API_KEY"] = "stderr-admin"
    return test_client


class TestScriptError:
    def _call(self, stderr, fallback="Something failed", **kwargs):
        with api_module.app.test_request_context():
            response, status = api_module.script_error(stderr, fallback, **kwargs)
            return response.get_json(), status

    def test_a_readable_message_passes_through(self):
        assert self._call("Player not found: ghost") == ({"error": "Player not found: ghost"}, 500)

    def test_no_message_gives_the_fallback(self):
        assert self._call("") == ({"error": "Something failed"}, 500)
        assert self._call(None) == ({"error": "Something failed"}, 500)

    def test_status_and_the_success_flag_are_kept(self):
        assert self._call("nope", status=404, include_success_flag=True) == (
            {"error": "nope", "success": False},
            404,
        )

    def test_a_traceback_is_replaced_by_the_fallback_and_logged(self, caplog):
        with caplog.at_level(logging.ERROR, logger=api_module.app.logger.name):
            body, status = self._call(TRACEBACK, "Failed to collect analytics")

        assert (body, status) == ({"error": "Failed to collect analytics"}, 500)
        assert "/home/pi" not in str(body)
        assert "secret-path.json" in caplog.text  # the detail is kept where an operator can read it

    def test_the_logged_traceback_is_sanitised(self, caplog):
        hostile = "Traceback (most recent call last):\n  boom\x00\x1b[2J\n2026-10-03 ERROR forged" + "y" * 9000
        with caplog.at_level(logging.ERROR, logger=api_module.app.logger.name):
            self._call(hostile, "Failed")

        assert "\x00" not in caplog.text and "\x1b" not in caplog.text
        assert "\n2026-10-03 ERROR forged" not in caplog.text
        assert "more characters]" in caplog.text

    def test_bytes_are_decoded_before_the_check(self):
        """Callers pass text, but bytes must not make the filter raise or leak."""
        assert self._call(b"Player not found: ghost") == ({"error": "Player not found: ghost"}, 500)
        assert self._call(TRACEBACK.encode(), "Failed") == ({"error": "Failed"}, 500)
        assert self._call(b"bad byte \xff here") == ({"error": "bad byte \ufffd here"}, 500)

    def test_a_message_that_ends_with_a_traceback_is_replaced_too(self):
        body, _ = self._call("Error: processing failed\n" + TRACEBACK, "Failed")

        assert body == {"error": "Failed"}


class TestSanitizeForLog:
    def test_a_multi_line_traceback_stays_readable_and_indented(self):
        out = sanitize_for_log("Traceback (most recent call last):\n  File \"x.py\", line 1\nValueError: no")

        assert out.splitlines()[0] == "Traceback (most recent call last):"
        assert all(line.startswith("    ") for line in out.splitlines()[1:])
        assert "ValueError: no" in out

    def test_text_that_imitates_a_log_entry_cannot_start_a_line(self):
        out = sanitize_for_log("boom\n2026-10-03 12:00:00 ERROR api: forged entry")

        assert "\n2026" not in out
        assert "\n    2026-10-03 12:00:00 ERROR api: forged entry" in out

    def test_control_characters_are_dropped_but_tabs_are_kept(self):
        out = sanitize_for_log("a\x00b\rc\x1b[31md\te")

        assert out == "abc[31md\te"

    def test_long_text_is_capped_with_a_note(self):
        out = sanitize_for_log("x" * 5000, limit=100)

        assert out.startswith("x" * 100)
        assert out.endswith("... [4900 more characters]")

    def test_bytes_and_other_types_are_accepted(self):
        assert sanitize_for_log(b"caf\xc3\xa9 \xff") == "caf\u00e9 \ufffd"
        assert sanitize_for_log(42) == "42"


class TestRoutesNeverSendATraceback:
    @staticmethod
    def _failed_run(stderr=TRACEBACK):
        return MagicMock(returncode=1, stdout="", stderr=stderr)

    def test_the_analytics_report_failure_is_generic_and_logged(self, client, caplog):
        with patch("api.server.subprocess.run", return_value=self._failed_run()):
            with caplog.at_level(logging.ERROR, logger=api_module.app.logger.name):
                response = client.get("/api/analytics/report")

        assert response.status_code == 500
        assert response.get_json() == {"error": "Failed to generate report"}
        assert "/home/pi" not in response.get_data(as_text=True)
        assert "secret-path.json" in caplog.text

    def test_the_analytics_collect_failure_goes_through_script_error(self, client):
        with patch("api.server.run_script", return_value=("", TRACEBACK, 1)):
            response = client.post("/api/analytics/collect")

        assert response.status_code == 500
        assert response.get_json() == {"error": "Failed to collect analytics"}

    @pytest.mark.parametrize(
        "method, path, fallback",
        [
            ("get", "/api/ddns/status", "Failed to get status"),
            ("post", "/api/ddns/update", "DDNS update failed"),
        ],
    )
    def test_ddns_failures_do_not_leak_a_traceback(self, client, method, path, fallback):
        with patch("api.server.subprocess.run", return_value=self._failed_run()):
            response = getattr(client, method)(path)

        assert response.status_code == 500
        assert response.get_json() == {"success": False, "error": fallback}

    @pytest.mark.parametrize(
        "method, path",
        [("get", "/api/ddns/status"), ("post", "/api/ddns/update")],
    )
    def test_ddns_still_shows_a_readable_script_message(self, client, method, path):
        with patch("api.server.subprocess.run", return_value=self._failed_run("DuckDNS configuration incomplete")):
            response = getattr(client, method)(path)

        assert response.status_code == 500
        assert response.get_json() == {"success": False, "error": "DuckDNS configuration incomplete"}
