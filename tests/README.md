# Tests

The full testing guide lives in [docs/TESTING.md](../docs/TESTING.md); web-specific
details are in [docs/WEB_UI_TESTING.md](../docs/WEB_UI_TESTING.md). This file just
maps the directory.

## Layout

```text
tests/
├── api/            pytest suite for the Flask API — run from THIS directory
│                   (tests/api/pytest.ini holds the coverage flags and markers)
├── unit/           BATS tests for shell scripts, with docker/curl/etc. stubbed on PATH
└── helpers/        BATS support libraries, and a flock stand-in for macOS
```

Playwright browser tests live in [`web/tests/e2e/`](../web/tests/e2e/), and React
unit tests sit beside their components in `web/src/**/__tests__/`.

## Running

```bash
make test              # syntax checks + pytest + vitest
make test-api          # pytest only
make test-web          # vitest only
make test-playwright   # Playwright browser tests
make coverage          # pytest with a coverage report
```

Or directly:

```bash
./scripts/run-tests.sh [all|bash|api]
cd tests/api && pytest -v
cd tests/api && pytest -v -m performance     # markers: unit, integration, api,
                                             # slow, performance, contract, e2e
bats tests/unit/test-auto-update.sh
```

## Requirements

- `bats` plus `bats-support` / `bats-assert` (vendored in `helpers/`) for shell tests
- Python dependencies from `api/requirements-test.txt`
- `cd web && npm install` for Vitest and Playwright

`--strict-markers` is enabled, so a new pytest marker must be registered in
`tests/api/pytest.ini` and `pyproject.toml` before it can be used.

## Rules the suites enforce

- **No real processes in API tests.** An autouse fixture in `api/conftest.py` fails
  any test that starts one. Unmocked, tests waited on docker timeouts (one took 30s)
  and one sent a command to whatever RCON server the machine could reach. Patch
  `api.server.subprocess.run` / `api.server.run_script`, use the `mock_docker`
  fixture, or mark a test `real_subprocess` if it truly needs a process.
- **Coverage is a ratchet.** `fail_under` in `.coverage-config.ini` sits a few
  points under the measured total. Raise it when coverage grows; never lower it.
- **A skipped test is not a passing test.** Don't add `skip` placeholders; add the
  scenario to the backlog below instead.

## Backlog: scenarios with no test yet

These were BATS files in `tests/unit`, `tests/integration` and `tests/e2e` whose
every test called `skip` on its first line, so they reported as passing without
running. They were removed (see git history for the drafts); the scenarios are
still worth covering, ideally as stubbed BATS tests like `test-auto-update.sh`.
The web user journeys are already covered by Playwright in `web/tests/e2e/`.

| Script / area | Scenarios |
| --- | --- |
| `manage.sh` | usage with no arguments; start / status / stop / restart |
| `backup-scheduler.sh` | honours `BACKUP_ENABLED=false`; daily schedule |
| `manage.sh backup`, `cleanup-backups.sh` | creates a tar.gz with world data; verification; old backups removed; restore; delete |
| `log-manager.sh` | index creates index files; rotate archives large logs; errors detects error patterns |
| `monitor.sh`, `prometheus-exporter.sh` | writes metrics files; CPU and memory tracked; exporter output |
| `plugin-manager.sh` | list; install from file; enable / disable |
| `rcon-setup.sh`, `rcon-client.sh` | setup enables RCON; sends a command; connection test |
| `world-manager.sh` | list; create; switch; size monitoring |
| `analytics-collector.sh`, `analytics-processor.py` | JSONL written; report generated; anomalies detected; data retention |
| API over HTTP (live stack) | register → login → status; unauthorized and invalid-endpoint errors |
