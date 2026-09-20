# Tests

The full testing guide lives in [docs/TESTING.md](../docs/TESTING.md); web-specific
details are in [docs/WEB_UI_TESTING.md](../docs/WEB_UI_TESTING.md). This file just
maps the directory.

## Layout

```text
tests/
├── api/            pytest suite for the Flask API — run from THIS directory
│                   (tests/api/pytest.ini holds the coverage flags and markers)
├── unit/           BATS unit tests for individual shell scripts
├── integration/    BATS integration tests across scripts
├── e2e/            BATS end-to-end workflows (need a running server)
└── helpers/        Shared test utilities, mock server, BATS support libraries
```

Playwright browser tests live in [`web/tests/e2e/`](../web/tests/e2e/), and React
unit tests sit beside their components in `web/src/**/__tests__/`.

## Running

```bash
make test              # syntax checks + pytest + vitest
make test-api          # pytest only
make test-web          # vitest only
make test-playwright   # Playwright browser tests
make test-e2e          # BATS end-to-end
make coverage          # pytest with a coverage report
```

Or directly:

```bash
./scripts/run-tests.sh [unit|integration|api|e2e]
cd tests/api && pytest -v
cd tests/api && pytest -v -m performance     # markers: unit, integration, api,
                                             # slow, performance, contract, e2e
bats tests/unit/test-manage.sh
```

## Requirements

- `bats` plus `bats-support` / `bats-assert` (vendored in `helpers/`) for shell tests
- Python dependencies from `api/requirements-test.txt`
- `cd web && npm install` for Vitest and Playwright

`--strict-markers` is enabled, so a new pytest marker must be registered in
`tests/api/pytest.ini` and `pyproject.toml` before it can be used.
