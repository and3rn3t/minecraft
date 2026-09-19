# Project Guidelines (AGENTS.md)

<!--
  SINGLE SOURCE OF TRUTH for AI assistant instructions.
  CLAUDE.md, .cursorrules, .cursor/rules/project.mdc, .clinerules, .windsurfrules
  and .github/copilot-instructions.md are thin pointers to this file — edit HERE,
  not there.
-->

## Project Overview

A Minecraft server management system for **Raspberry Pi 5 (ARM64)**, also usable on
x86_64. It provides Docker-based deployment, automated and cloud backups, plugin and
mod management, multi-world support, RCON, log management, analytics, a Flask REST
API, and a React web admin panel.

## Stack

| Layer | Technology |
| --- | --- |
| Server management | Bash scripts in `scripts/`, shared helpers in `scripts/lib/common.sh` |
| REST API | Python 3.11+ / Flask (`api/server.py`) |
| Web admin panel | React 18 + Vite + Tailwind CSS (`web/`) |
| Containers | Docker + Docker Compose v2 |
| Service management | systemd units in `systemd/` |
| Tests | pytest (API), Vitest (React), Playwright (browser E2E), BATS (shell) |
| Package manager | **npm** (this repo is not on pnpm) |

## Repository Layout

```
api/          Flask REST API (server.py, security.py) + OpenAPI spec in api/openapi.yaml
web/          React admin panel; its own package.json, ESLint, Vite and Playwright configs
scripts/      Bash management scripts; scripts/lib/common.sh holds shared helpers
config/       Runtime config; only *.example files are committed (real .conf files are gitignored)
systemd/      Unit and timer files for the Pi
tests/        api/ (pytest), unit/ integration/ e2e/ (BATS), helpers/
web/tests/e2e Playwright browser tests (driven by web/playwright.config.js)
docs/         All documentation; docs/INDEX.md is the navigation hub
analytics/    Collected analytics reports
```

## Commands

Everything routes through the `Makefile`; prefer it over raw commands.

```bash
make help              # list all targets
make start|stop|restart|status|logs|backup|console
make test              # syntax checks + pytest + vitest
make test-api          # pytest only
make test-web          # vitest only
make test-playwright   # browser E2E
make test-e2e          # BATS end-to-end (needs a running server)
make lint              # shellcheck + eslint + python + yaml + compose validate
make coverage          # pytest with coverage report
make coverage-check    # enforce the threshold in .coverage-config.ini
make build             # docker compose build
```

Direct equivalents when you need them:

```bash
bash -n scripts/foo.sh               # shell syntax check
cd tests/api && pytest -v            # API tests (pytest.ini lives here)
cd web && npm test                   # Vitest
cd web && npm run lint               # ESLint (must pass with --max-warnings 0)
docker compose config                # validate compose files
```

**Use `docker compose` (with a space), never `docker-compose`.** The standalone
binary conflicts with the plugin on Raspberry Pi OS; the `Makefile` detects which
form is available via its `COMPOSE` variable, and scripts use the `compose()`
wrapper from `scripts/lib/common.sh`.

## Code Standards

### Bash (`scripts/`)

- `#!/bin/bash` shebang, `set -e` near the top.
- 4-space indent, no tabs. Always quote variables: `"$VAR"`.
- Resolve the script's own directory, then source the shared library:

  ```bash
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source-path=SCRIPTDIR
  # shellcheck source=lib/common.sh
  source "${SCRIPT_DIR}/lib/common.sh"
  ```

  `common.sh` provides the colour variables (`RED`, `GREEN`, `YELLOW`, `BLUE`, `NC`),
  `PROJECT_DIR`, `SCRIPTS_DIR` and the `compose()` wrapper. Do not redefine them.
- Every script takes a subcommand and has a `usage()` function; dispatch with `case`.
- Must pass `shellcheck` (see `.shellcheckrc`).

### Python (`api/`, `scripts/*.py`)

- PEP 8, formatted with Black at **line-length 120** (`pyproject.toml`).
- Type hints where they help; docstrings on functions and classes.
- `pathlib.Path` for filesystem work; catch specific exceptions.
- Imports grouped stdlib / third-party / local.
- Flask endpoints: decorate with `@app.route(...)` then `@require_permission("<scope>")`
  for anything privileged. Return `jsonify({...})` with an explicit status code on
  error paths:

  ```python
  @app.route("/api/keys", methods=["GET"])
  @require_permission("api_keys.view")
  def list_api_keys():
      """List all API keys (without showing full key values)."""
      try:
          ...
          return jsonify({"keys": keys_list})
      except Exception as e:
          app.logger.error(f"Error listing keys: {e}")
          return jsonify({"error": "Internal server error"}), 500
  ```

- Never return raw exception text to the client on a 500.

### React (`web/src/`)

- Functional components with hooks; no class components.
- Tailwind utility classes for styling — no separate CSS modules.
- All HTTP goes through `web/src/services/api.js`; components never call `axios` directly.
- Reuse the existing hooks (`usePolling`, `useErrorHandler`, `useAutoDismiss`,
  `useDebounce`, `useThrottle`) instead of re-implementing them.
- Routes are lazy-loaded in `App.jsx` via `LazyRoute`; keep new pages lazy.
- `npm run lint` runs with `--max-warnings 0`, so warnings break the build.

### Docker / YAML

- 2-space YAML indent; `${VAR:-default}` for environment substitution.
- Multi-stage builds, minimal layers, clean up within the same `RUN`.
- Keep the healthcheck in `docker-compose.yml` accurate — a too-short
  `start_period` causes restart loops on a Pi.

### Naming

| Kind | Convention | Example |
| --- | --- | --- |
| Shell scripts | `kebab-case.sh` | `backup-scheduler.sh` |
| Python | `snake_case.py` | `server.py` |
| React components | `PascalCase.jsx` | `StatusCard.jsx` |
| Hooks | `useCamelCase.js` | `usePolling.js` |
| Config files | `kebab-case.conf` | `backup-schedule.conf` |
| Docs | `UPPERCASE.md` | `TROUBLESHOOTING.md` |

## Testing

- Python tests live in `tests/api/` and are run **from that directory** —
  `tests/api/pytest.ini` holds the coverage flags, timeouts and markers.
- Registered markers: `unit`, `integration`, `api`, `slow`, `performance`,
  `contract`, `e2e`. `--strict-markers` is on, so add new markers to
  `tests/api/pytest.ini` *and* `pyproject.toml` before using them.
- React unit tests sit next to the code in `__tests__/`; integration tests in
  `web/src/test/integration/`; MSW handlers in `web/src/test/mocks/`.
- Playwright specs belong in `web/tests/e2e/` only.
- BATS suites in `tests/unit/`, `tests/integration/`, `tests/e2e/`.
- Coverage threshold is enforced at **40%** in `.coverage-config.ini`. That file is
  not auto-discovered by coverage.py, so every entry point passes `--cov-config`
  explicitly; run pytest from `tests/api` so the relative path resolves.

See [docs/TESTING.md](docs/TESTING.md) for the full guide.

## Raspberry Pi Constraints

These shape most design decisions — do not optimise them away:

- **Memory**: 4GB model → `MEMORY_MIN=1G`, `MEMORY_MAX=2G`; 8GB model → `2G`/`4G`.
- **CPU**: ARM64. Images must build for `linux/arm64` (see `scripts/build-multiarch.sh`).
- **Storage**: SD cards have finite writes — keep log rotation on and compress backups.
- **Thermals**: sustained load throttles the Pi; long-running work should be chunked.

Test on real hardware when a change is hardware-specific.

## Security

- Never commit secrets. `config/*.conf` is gitignored; only `*.example` files are tracked.
- API keys live in `config/api-keys.json` (gitignored); RCON passwords are generated randomly.
- Validate and sanitise all API input; `api/security.py` holds the shared helpers and
  security headers.
- Gitleaks and CodeQL run in CI — do not work around them.

## Git Conventions

- Branch prefixes: `feature/`, `fix/`, `docs/`.
- One logical change per PR; fill in `.github/pull_request_template.md`.
- Update `CHANGELOG.md` for anything user-facing.
- Pre-commit hooks are configured in `.pre-commit-config.yaml` — install with
  `pre-commit install`.

## Before You Call It Done

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] `docker compose config` validates
- [ ] Docs updated (`README.md` for user-facing changes, the relevant `docs/` guide otherwise)
- [ ] `CHANGELOG.md` updated
- [ ] No secrets, no hardcoded absolute paths

## Documentation Rules

- `docs/INDEX.md` is the navigation hub — add new docs there or they will not be found.
- Keep internal links relative.
- Don't create "summary", "complete" or "implementation notes" documents; that history
  belongs in `CHANGELOG.md` and git.
- Don't state coverage percentages or test counts in prose — they go stale immediately.
  Point at `make coverage` or CI instead.
