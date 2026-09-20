# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **`POST /api/server/properties/preset`** applies one of the performance
  presets in `scripts/server-properties-manager.sh` (`low-end`, `balanced`,
  `high-performance`), which set view distance, simulation distance, max
  players, network compression and entity broadcast range together (#29). The
  handler already existed with its permission decorator but no route, so it was
  unreachable and presets could only be applied from the shell.
- **`PUT /api/scheduler/schedules/<id>/enable` and `/disable`**, so a schedule
  can be paused without deleting it. These existed only on the duplicate API
  that has been removed, so the web interface had no way to do it.

### Changed

- **The event bus can write somewhere other than the SD card.** `MC_EVENTS_DIR`
  moves `data/events/` — the one directory the server writes to continuously —
  onto an attached SSD, and `MC_EVENTS_RETENTION_DAYS` raises the 30-day prune
  that existed to bound what the card absorbs. A malformed retention value
  falls back to 30 rather than reading as zero, so a typo cannot quietly turn
  pruning off. See [docs/EVENT_BUS.md](docs/EVENT_BUS.md).

- **Local checks now reproduce the CI jobs.** `make ci` runs lint, actionlint,
  gitleaks, the test suites and CodeQL; `make doctor` reports which supporting
  tools are installed; `make hooks` installs the pre-commit hooks, which were
  configured but had never been installed. Two "passing" checks were not
  checking anything: `lint_python` reported success with no Python linter
  present, and `lint_bash` piped shellcheck into `tee`, so the pipeline
  reported `tee`'s exit status and shellcheck's findings were invisible. Both
  now fail honestly, a missing tool fails `make ci` rather than being skipped,
  and the twelve known gitleaks findings are allowlisted individually in
  `.gitleaks.toml`, each scoped to its file, so the scan blocks on anything
  new. See "Checks that mirror CI" in `AGENTS.md`.

- **One API now fronts the command schedule** (#30). `/api/commands/schedule*`
  and `/api/scheduler/schedules` both wrote `config/command-schedule.json`;
  the first has been removed and the second is the whole surface. It gains the
  `cron` and `once` types and `condition` support that only the removed one
  claimed to offer, and validates them: an unknown type, a `cron` with no
  expression or a `once` with no datetime is rejected rather than written to a
  file where the scheduler would skip it forever without saying so.

- **Consolidated every roadmap and feature-planning document into a single
  [docs/ROADMAP.md](docs/ROADMAP.md).** `docs/TASKS.md`,
  `docs/FAMILY_SERVER_ROADMAP.md`, `docs/MINECRAFT_ENHANCEMENTS.md` and
  `docs/MINECRAFT_GAMEPLAY_ENHANCEMENTS.md` are removed. The four disagreed
  with each other and with the code: the old roadmap opened by calling v1.3.0
  current and v1.4.0 "60% complete" while v1.4.0 through v1.6.0 had all
  shipped, and three of them listed the same work at different priorities.
  Completed work is no longer restated in the roadmap at all — that record is
  this file. What remains is what is not done, ordered, with the items that
  were decided against kept in a "Ruled out" section so they stop being
  reproposed.

### Fixed

- **Four test scripts piped data into a heredoc that discarded it**, at five
  call sites.
  `echo "$json" | python3 << EOF ... json.load(sys.stdin) ... EOF` reads the
  heredoc, not the pipe, so those assertions were parsing the Python source
  instead of the response they meant to check. The data is passed in the
  environment now. Found by making the shellcheck gate report its real exit
  status (SC2259).

- **A cron schedule ran once and was then skipped forever.** The cron branch of
  `should_run_schedule()` read a `last_run_time` that only the other branches
  assign, so once `last_run` was set it raised `UnboundLocalError` into its own
  `except Exception`, which returned False. It now works back from the present
  to the slot that most recently came due, which also lets a cron catch up
  after a missed tick instead of stalling permanently.
- **One malformed schedule stopped every other one.** A `condition` that was
  not an object raised on `.get()`, out of `should_run_schedule()` and through
  the timer loop, so no later schedule was evaluated and the save at the end of
  the pass never ran — losing the `last_run` of commands that had already been
  executed. Each schedule is now evaluated in isolation, a non-object condition
  is ignored with a warning, and the API rejects one outright.
- **The API and the scheduler could overwrite each other.** Both do a
  read-modify-write of `config/command-schedule.json`, and the daemon rewrites
  it on every pass to record `last_run`. They now take the same exclusive lock
  and write by renaming a sibling file into place, so a concurrent reader sees
  either the old file or the new one rather than a half-written document.
- **Scheduled commands silently ignored every option they were given.**
  `POST /api/commands/schedule` passed its options as JSON on standard input to
  `scripts/command-scheduler.py`, which never reads standard input, so a
  5-minute interval was stored as the 60-minute default; the same endpoint
  returned the script's `Schedule created: <uuid>` chatter where callers
  expected an id, and `DELETE` reported success for ids that were never there.
  Removed in favour of `/api/scheduler/*`, which does not have these faults.
- **Deleting an unknown schedule reported success.**
  `DELETE /api/scheduler/schedules/<id>` filtered the list and saved it either
  way; it now returns 404 when nothing matched.
- **Changing a schedule's type left the old type's fields behind**, so a daily
  schedule switched to an interval kept a stale `run_time`.

- **Admin-scoped API keys were refused the `server.manage` endpoints.** Scoping
  API keys (#27) checked a key's permissions by membership, with no admin
  short-circuit of the kind users get. `server.manage` was enforced by 14
  endpoints but never declared in `PERMISSIONS`, so it was in no role's list and
  an admin-scoped key was refused announcements, server presets and command
  schedules that an admin user could reach. `server.manage` is now declared, and
  an admin-scoped key matches an admin user; a key carrying an explicit
  `permissions` array is still held to that array whatever its role. A test now
  fails if any enforced permission is missing from `PERMISSIONS`.

### Security

- **Registration no longer mints every user as an administrator** (#26).
  `POST /api/auth/register` hardcoded `"role": "admin"` beneath a comment
  claiming the first user was admin and everyone else defaulted to `user`, so
  open registration handed full control to anyone who could reach the endpoint.
  The first account still bootstraps the server as an admin; every later one
  starts as `user`. Registration also closes once that first account exists —
  set `REGISTRATION_ENABLED=true` to keep it open — and the new
  `POST /api/users` (`users.manage`) is how an admin adds everyone else.

- **API keys are scoped instead of being universal admin credentials** (#27).
  `has_permission()` returned `True` unconditionally for the `__api_key__`
  caller, so every key could do everything regardless of what it was created
  for. Keys now carry a `role` from the same ladder users use, or an explicit
  `permissions` allowlist, and are checked the same way; new keys default to
  `user`. The WebSocket log stream is scoped too — connecting requires
  `logs.view` and `execute_command` requires `server.command`, which it
  previously never checked despite a comment saying otherwise. Keys created
  before this are kept as `admin` with a startup warning, and can be narrowed
  from the API Keys page or with the new `PUT /api/keys/<key_id>`.

<!-- Everything from here down is released history, which repeats
     "### Added" and friends within a single version. It is not being
     rewritten. MD024 stays on for [Unreleased] above, which is the section
     that changes — it is what caught that section accumulating three
     "### Fixed" blocks, one per pull request. -->
<!-- markdownlint-disable MD024 -->

## [1.5.0] - 2026-09-19

### Added

- **Bedtime mode** (`api/bedtime.py`) — see [docs/BEDTIME.md](docs/BEDTIME.md)

  - A scheduled, warned end to the evening: a bossbar countdown, titles at the
    configured marks, a goodnight message, then save and stop, remove everyone,
    or just announce.
  - Bedtime is a window rather than a moment. Between bedtime and the wake time,
    anyone who joins is sent back out with a message saying when the server
    opens again. Stopping the server is not enough on its own, because a restart
    policy or an update timer reopens the evening.
  - Separate weeknight and weekend bedtimes, chosen by the evening rather than
    the day, so Friday and Saturday nights get the later one. The window spans
    midnight correctly.
  - New page at `/bedtime` with the countdown and three controls: extend by a
    configured amount, skip tonight, or start bedtime now. A refused control
    returns `409` with the reason, since the request was well-formed.
  - New endpoints `GET /api/bedtime` (`server.view`) and `POST /api/bedtime/extend`,
    `/skip` and `/now` (`server.control`), with matching OpenAPI paths and schemas.
  - Configured through `config/bedtime.conf`; see `config/bedtime.conf.example`.
    Disabled unless the config says otherwise.
  - Enforcement is idempotent. The bedtime thread and an API request can both
    reach it, so closing the evening twice would mean two goodnights, two kicks
    and two attempts to stop the server.

- **`systemd/minecraft-scheduler.{service,timer}`** — nothing executed the
  scheduled commands the web UI creates. The Scheduler page wrote entries to
  `config/command-schedule.json` and `scripts/command-scheduler.py run` was never
  invoked by any timer, cron entry or loop, so every schedule was stored and
  silently ignored. The timer runs it once a minute.

- **`scripts/auto-update.sh`** — pulls and restarts only when the image actually
  changed, and leaves a stopped server stopped.

### Fixed

- **The hourly update timer restarted the server every hour regardless of
  whether a new image existed.** `systemd/minecraft-update.service` ran
  `docker compose up -d --force-recreate` unconditionally, which recreates
  containers even when nothing has changed, so everyone online was kicked on the
  hour. It also restarted servers that had been stopped deliberately, which would
  have reopened the server after bedtime closed it. It now calls
  `scripts/auto-update.sh run`.

### Added

- **Hall of Deaths** (`api/hall_of_deaths.py`, `api/epitaphs.py`) — see
  [docs/HALL_OF_DEATHS.md](docs/HALL_OF_DEATHS.md)

  - Every death gets a one-line obituary, announced in game with `tellraw` and
    kept for the dashboard. The first feature built on the event bus.
  - Deaths are classified into 18 categories, each with several lines, so the
    same death does not read the same way twice in an evening. Where the message
    names a culprit it is used, with the weapon dropped.
  - Epitaph writing is behind a small interface. The default writer runs
    offline, costs nothing and needs no API key; a language-model-backed writer
    can be dropped in by implementing `write()`.
  - New page at `/deaths` with recent obituaries, summary tiles and a
    leaderboard of who dies most and how they usually manage it.
  - New endpoints `GET /api/deaths` and `GET /api/deaths/leaderboard`, both
    requiring `players.view`, plus `getDeaths()` and `getDeathsLeaderboard()` in
    `web/src/services/api.js`.
  - Configured through `config/deaths.conf`; see `config/deaths.conf.example`.
    In-game announcements can be turned off while keeping the dashboard.
  - Announcing runs on a worker thread rather than on the log follower, so an
    unreachable game server cannot stall event processing behind each death.

### Added

- **In-process RCON client** (`api/rcon.py`)

  - Replaces the per-command shell-out to `scripts/rcon-client.sh`, which opened a
    new TCP connection and re-authenticated for every command. One authenticated
    connection is now held open and shared, so command batches are practical.
  - Fixes two defects in the previous Python fallback: a single unframed `recv`
    truncated or split responses over 4096 bytes, and any reply of four or more
    bytes was treated as a successful login instead of checking for the `-1`
    request id that signals auth failure.
  - Reassembles the multi-packet responses Minecraft sends for output over 4096
    bytes, reconnects automatically after a server restart, and rejects commands
    long enough that the server would silently truncate them.
  - `api/server.py` calls it through a new `run_rcon_command()` helper that falls
    back to `scripts/rcon-client.sh` when RCON is unconfigured or unreachable, so
    the `rcon-cli`-inside-the-container path still works.

- **Game event bus** (`api/events.py`) — see [docs/EVENT_BUS.md](docs/EVENT_BUS.md)

  - Parses the server log into typed events: chat, connect, join, leave, death,
    advancement, command, server ready and server stopping.
  - Events are appended to `data/events/YYYY-MM-DD.jsonl`. Writes are batched and
    files older than 30 days are pruned, to limit SD-card wear on the Pi.
  - Features subscribe with a handler function instead of parsing raw log text.
    A handler that raises is logged and skipped rather than stopping the bus.
  - New endpoints `GET /api/events` and `GET /api/events/types`, both requiring
    `logs.view`, plus a `game_event` WebSocket message alongside the existing raw
    `logs` stream. `getEvents()` and `getEventTypes()` added to
    `web/src/services/api.js`.

- **Feature roadmap** (`docs/FAMILY_SERVER_ROADMAP.md`) covering gameplay and
  integration features, as distinct from the management product planned in
  `docs/ROADMAP.md`. Both were folded into a single `docs/ROADMAP.md` after
  this release.

### Fixed

- **The WebSocket `execute_command` handler reached RCON without sanitising its
  input**, so it bypassed the command allowlist that `POST /api/server/command`
  enforces. It now runs the same validation and writes the same audit entries.
- **A non-string `command` value crashed inside the sanitiser** on both the REST
  and WebSocket paths. The REST endpoint returned a 500 instead of a 400, and the
  WebSocket raised before its error handler, leaving the client with no response
  at all. Both now reject the value explicitly.

### Changed

- **The log follower now runs from API startup rather than from the first browser
  connection**, and no longer stops when the last client disconnects. Events that
  occur while the dashboard is closed were previously lost entirely. The follower
  can be brought down deliberately with `stop_log_reader()`, which kills the
  `docker logs` process so a quiet server cannot leave the reader parked in a
  blocking read.
- **The follower attaches with `--tail 0`.** Because every line it reads is now
  persisted as an event, replaying a backlog recorded the same events again on
  every restart and re-attach. Connecting clients still receive scrollback, which
  is sent separately and does not reach the bus.
- **RCON retries are limited to commands that provably never reached the
  server.** Minecraft commands are not idempotent, so a lost response is now
  reported as an unknown outcome rather than retried or re-run through the shell
  fallback, which could otherwise apply a `give` or a `kill` twice.
- **The RCON config is re-read when it changes on disk**, so rotating the
  password with `scripts/rcon-setup.sh` no longer needs an API restart.
- **Buffered events are flushed on a timer as well as on publish**, so the last
  few events on a quiet server are not left in memory indefinitely.

- **Repository and documentation cleanup**

  - Consolidated AI assistant configuration on `AGENTS.md` as the single source of
    truth, following the `ai-template-repo` convention. `AGENT_INSTRUCTIONS.md` and
    the 317-line `.cursorrules` (which duplicated each other) were merged into it.
    `CLAUDE.md`, `.cursorrules`, `.cursor/rules/project.mdc`, `.clinerules`,
    `.windsurfrules` and `.github/copilot-instructions.md` are now thin pointers.
  - Rewrote `README.md`: fixed broken links, corrected every `./manage.sh` and
    `./setup-rpi.sh` path to `./scripts/...`, replaced the hand-written systemd unit
    with the one shipped in `systemd/`, and documented `.env` configuration.
  - Rewrote `docs/INDEX.md` as a task-oriented index of all 48 guides;
    `docs/README.md` and `tests/README.md` are now short pointers to it.
  - Merged `RESTART_LOOP_TROUBLESHOOTING.md` and `DOCKER_COMPOSE_FIX.md` into
    `docs/TROUBLESHOOTING.md`, and `TEST_COVERAGE.md` into `docs/TESTING.md`.
  - Replaced `docker-compose` with `docker compose` throughout the documentation to
    match the Compose v2 plugin the `Makefile` and systemd units actually use.
  - Added `.env.example` (referenced by the `Makefile` but previously missing).
  - Synced the pytest markers in `pyproject.toml` with `tests/api/pytest.ini`, and
    removed the duplicate `[tool.coverage]` block so `.coverage-config.ini` is the
    only coverage config. Added the matching `--cov-config` to
    `tests/api/pytest.ini`, since that filename is not auto-discovered by
    coverage.py — `make test-api` and a bare `cd tests/api && pytest` had been
    running with no exclusions and no `fail_under` at all.
  - Tightened `.gitignore`: added `.mypy_cache/`, `playwright-report/`,
    `test-results/`; fixed an inline comment that made a negation pattern literal.

### Removed

- **Dead configuration and build artifacts**

  - Root `.eslintrc.json` and `.eslintignore` — unused; linting runs inside `web/`,
    whose `.eslintrc.cjs` sets `root: true`.
  - Root `playwright.config.js` and `tests/e2e/browser/` — stale duplicates of the
    live `web/playwright.config.js` and `web/tests/e2e/`.
  - `web/playwright-report/index.html` — a 520 KB generated report that had been
    committed.

- **Historical process documentation** (preserved in git history)

  - `docs/archive/` (17 files), plus `ADVANCED_OPTIMIZATIONS.md`,
    `CLEANUP_OPTIMIZATIONS_SUMMARY.md`, `CONSOLIDATION_SUMMARY.md`,
    `DOCUMENTATION_CONSOLIDATION_PLAN.md`, `OPTIMIZATION_COMPLETE.md`,
    `OPTIMIZATION_SUMMARY.md`, `WORKSPACE_ENHANCEMENTS.md`, `SETUP_CHECKLIST.md`.
  - `tests/ANALYTICS_TESTS.md`, `tests/COMPLETE_TEST_SUMMARY.md`,
    `tests/TEST_SUMMARY.md`.

### Added

- **Comprehensive Test Suite - Complete Implementation**

  - **Analytics Processor Unit Tests** (`tests/api/test_analytics_processor.py`)

    - 30+ unit tests for analytics algorithms
    - Trend calculation tests (increasing, decreasing, stable)
    - Anomaly detection tests (Z-score algorithm)
    - Prediction algorithm tests
    - Player behavior analysis tests
    - Report generation tests
    - Performance trends analysis tests

  - **Component Tests** (Backups, Players, Worlds)

    - `web/src/pages/__tests__/Backups.test.jsx` - 12+ tests
    - `web/src/pages/__tests__/Players.test.jsx` - 8+ tests
    - `web/src/pages/__tests__/Worlds.test.jsx` - 6+ tests
    - Complete coverage for user interactions, loading states, error handling

  - **Visual Regression Tests** (`tests/e2e/browser/visual-regression.spec.js`)

    - Playwright-based visual snapshot tests
    - Dashboard, Analytics, Backups, Players, Worlds, Login page snapshots
    - Screenshot comparison for UI consistency

  - **Accessibility Tests** (`web/src/test/a11y.test.jsx`)

    - WCAG compliance testing using jest-axe
    - Tests for all major pages (Analytics, Dashboard, Backups, Players, Worlds, Login)
    - Form label validation
    - Accessibility violation detection

  - **Browser Automation** (Playwright)

    - `playwright.config.js` - Playwright configuration
    - `tests/e2e/browser/analytics.spec.js` - Analytics browser tests
    - `tests/e2e/browser/user-journey.spec.js` - Complete user journey tests
    - Cross-browser testing (Chromium, Firefox, WebKit)
    - CI/CD integration (`.github/workflows/playwright.yml`)

  - **Enhanced Testing Framework**

  - End-to-end (E2E) tests for critical workflows (`tests/e2e/`)
  - Test utilities and helpers (`tests/helpers/test-utils.sh`)
  - Mock server for testing (`tests/helpers/mock-server.sh`)
  - E2E test runner integration
  - Enhanced test documentation
  - Complete test coverage: ~70%+ overall (exceeds 60% target)
  - 250+ comprehensive test cases across all test types

- **Mod Support (Complete)**

  - Mod loader detection script (`scripts/mod-loader-detector.sh`)
  - Support for Forge, Fabric, and Quilt detection
  - Mod pack installer script (`scripts/mod-pack-installer.sh`)
  - Mod dependency resolution
  - Mod compatibility verification
  - Mod support documentation (`docs/MOD_SUPPORT.md`)

- **Minecraft-Specific Enhancements (Complete)**

  - **Server Properties Manager** (`scripts/server-properties-manager.sh`)
    - Get/set individual properties with validation
    - Performance presets (low-end, balanced, high-performance)
    - Property validation (ranges, enums)
    - Automatic backups before changes
    - API endpoints for programmatic access
  - **Player Management Scripts**
    - Whitelist Manager (`scripts/whitelist-manager.sh`) - Add/remove, import/export, enable/disable
    - Ban Manager (`scripts/ban-manager.sh`) - Ban/unban with reasons, IP bans
    - OP Manager (`scripts/op-manager.sh`) - Grant/revoke operator status with levels (1-4)
    - Complete API endpoints for all player management operations
  - **JVM Arguments Optimizer** (`scripts/jvm-optimizer.sh`)
    - Aikar's Flags integration
    - Raspberry Pi 5 optimizations
    - Memory and CPU-based optimization
    - Multiple presets (aikar, basic, rpi)
  - **Performance Presets** (`scripts/performance-presets.sh`)
    - Low-end preset (4GB Pi) - View distance 6, max players 5
    - Balanced preset (8GB Pi) - View distance 10, max players 10
    - High-performance preset - View distance 12, max players 20
    - Preset comparison and current settings display
  - **Documentation**
    - Minecraft enhancements guide (`docs/MINECRAFT_ENHANCEMENTS.md`)
    - Minecraft management guide (`docs/MINECRAFT_MANAGEMENT.md`)

- **Static Code Analysis Infrastructure**

  - Comprehensive linting script (`scripts/lint.sh`) for bash, Python, JavaScript/React, and YAML
  - ShellCheck configuration (`.shellcheckrc`) for bash script linting
  - ESLint already configured for React frontend
  - Makefile targets for linting (`make lint`, `make lint-bash`, etc.)
  - CI/CD integration with GitHub Actions for automated linting
  - Linting documentation (`docs/LINTING.md`) with best practices and troubleshooting

- **Docker Image Optimization**

  - Optimized Dockerfile with multi-stage builds
  - Reduced image size through layer optimization
  - Improved build caching strategy
  - `.dockerignore` file to exclude unnecessary files from build context
  - Docker optimization documentation (`docs/DOCKER_OPTIMIZATION.md`)
  - Support for build arguments (MINECRAFT_VERSION, BUILD_TYPE)

- **Cloud Backup Planning**

  - Added Cloudflare R2 to cloud backup integration tasks (S3-compatible, no egress fees)
  - Updated roadmap to prioritize R2 for Raspberry Pi users

- **Performance Benchmarking Suite**

  - Comprehensive benchmark script (`scripts/benchmark.sh`) for performance measurement
  - Startup time, TPS, memory, and CPU benchmarks
  - Baseline creation and comparison functionality
  - Regression detection capabilities
  - Performance benchmarking documentation (`docs/PERFORMANCE_BENCHMARKING.md`)

- **Multi-Architecture Support**

  - Multi-architecture Docker build script (`scripts/build-multiarch.sh`)
  - Support for ARM64 (Raspberry Pi 5), ARM32 (Raspberry Pi 4), and x86_64
  - Docker Buildx integration for cross-platform builds
  - Multi-architecture documentation (`docs/MULTI_ARCHITECTURE.md`)
  - Updated Dockerfile to support multiple architectures

- **CI/CD Pipeline Enhancements**

  - Automated release workflow (`.github/workflows/release.yml`)
  - Version tagging automation
  - Release notes generation from CHANGELOG.md
  - Docker image publishing to GitHub Container Registry
  - Multi-architecture image builds in CI/CD
  - Release documentation (`docs/CI_CD.md`)
  - Release notes generation script (`scripts/generate-release-notes.sh`)

- **Code Coverage Enhancements**

  - Coverage threshold enforcement (60% minimum)
  - Coverage reporting workflow (`.github/workflows/coverage.yml`)
  - Coverage check script (`scripts/check-coverage.sh`)
  - Coverage configuration (`.coverage-config.ini`)
  - Coverage badges and trend tracking
  - Makefile targets for coverage (`make coverage`, `make coverage-check`)

- **Cloud Backup Integration (Complete - v1.6.0)**

  - **Cloudflare R2** - R2 backup client script (`scripts/cloud-backup-r2.sh`) ✅
  - **AWS S3** - S3 backup client script (`scripts/cloud-backup-s3.sh`) ✅
  - **Backblaze B2** - B2 backup client script (`scripts/cloud-backup-b2.sh`) ✅
  - All providers support upload, download, list, and delete
  - S3-compatible API integration for R2 and B2
  - Configuration management for all providers
  - Comprehensive cloud backup documentation (`docs/CLOUD_BACKUP.md`)
  - Provider comparison and cost analysis
  - Cloudflare R2 recommended for Raspberry Pi (no egress fees)
  - Configuration examples for all providers

- **API Documentation (OpenAPI/Swagger)**
  - Complete OpenAPI 3.0 specification (`api/openapi.yaml`)
  - Interactive API documentation support
  - API documentation guide (`docs/API_DOCUMENTATION.md`)
  - Documentation serving script (`scripts/serve-api-docs.sh`)
  - All 40+ endpoints documented with schemas and examples

### Changed

- Updated GitHub Actions workflow to include frontend linting
- Enhanced Makefile with linting targets
- Optimized Dockerfile structure for better caching and smaller images
- Updated TASKS.md and ROADMAP.md to include Cloudflare R2 as recommended cloud backup option

## [1.4.0] - 2025-01-27

### Added

- **Web Admin Panel** - Complete React-based web interface for server management

  - Server status dashboard with real-time metrics
  - Real-time log viewer with WebSocket support and filtering
  - Player management interface (view, whitelist, ban, op)
  - Backup management UI with create, restore, and delete functionality
  - Server configuration file editor with syntax highlighting
  - Worlds and plugins management interfaces
  - Minecraft-themed pixel art UI design

- **Authentication & Security System**

  - User registration and login with password hashing
  - Session-based authentication with JWT support
  - OAuth integration (Google, Apple)
  - Role-Based Access Control (RBAC) with three roles:
    - **Admin**: Full system access
    - **Operator**: Server management and player control
    - **User**: Read-only access
  - Permission system with fine-grained control (25+ permissions)
  - User management interface (list, update roles, enable/disable, delete)
  - API key management with secure generation and storage
  - API key rotation (enable/disable) functionality

- **REST API Enhancements**

  - User management endpoints (`/api/users/*`)
  - Role and permission endpoints (`/api/roles`, `/api/permissions`)
  - API key management endpoints (`/api/keys/*`)
  - Permission-based access control on all endpoints
  - API key authentication support in `require_auth` decorator

- **Testing**

  - Comprehensive RBAC test suite (32 tests, all passing)
  - Permission system validation tests
  - User management tests
  - API key access tests
  - Config file permission tests

- **Documentation**
  - RBAC documentation (`docs/RBAC.md`)
  - API key management guide (`docs/API_KEYS.md`)
  - Updated documentation index with new guides
  - Security best practices documentation

### Changed

- Updated `require_auth` decorator to support API keys
- Fixed JSON serialization for bytes in API responses
- Improved error handling in permission checks
- Enhanced API key authentication flow

### Fixed

- Fixed role permissions (removed `backup.create` from user role, `config.edit` from operator role)
- Fixed API key authentication in permission-based endpoints
- Fixed JSON serialization issues with subprocess output
- Fixed MagicMock serialization in tests

### Security

- Implemented role-based permission system
- Added protection against disabling/deleting last admin user
- Secure API key storage with file permissions (600)
- Password hashing with bcrypt
- Session management with secure cookies

## [1.0.0] - 2025-11-22

### Added

- Initial release of Minecraft Server for Raspberry Pi 5
- Docker-based deployment system
- Automated setup script for Raspberry Pi (`setup-rpi.sh`)
- Server management script (`manage.sh`) with commands for start, stop, restart, status, logs, backup, and console
- Optimized Dockerfile for ARM64/Raspberry Pi 5
- Docker Compose configuration for easy deployment
- Default server configuration optimized for Raspberry Pi 5
- Startup script with Aikar's optimized JVM flags
- Comprehensive documentation:
  - README.md - Main documentation and feature overview
  - INSTALL.md - Detailed installation guide
  - QUICK_REFERENCE.md - Quick command reference
  - CONFIGURATION_EXAMPLES.md - Various configuration examples
- Default server.properties configured for small family server
- EULA acceptance configuration
- .gitignore for common files and directories
- Backup functionality in management script

### Configuration

- Default Minecraft version: 1.20.4
- Default memory allocation: 1G-2G (suitable for 4GB Pi)
- Default max players: 10
- Default view distance: 10
- Default simulation distance: 10
- Default difficulty: Normal
- Default game mode: Survival
- PvP enabled by default

### Features

- One-command server deployment
- Automatic Minecraft server jar download
- Persistent data storage
- Backup and restore functionality
- Easy configuration management
- Optimized JVM settings for Raspberry Pi
- Support for ARM64 architecture
- Docker networking for isolation
- Volume mounting for data persistence

### Documentation

- Step-by-step installation guide
- Quick reference for common tasks
- Configuration examples for different scenarios
- Performance tuning guidelines
- Troubleshooting section
- Port forwarding instructions
- Security best practices

## Planned Features

### [1.5.0] - Planned

- [ ] Dynamic DNS integration (DuckDNS, No-IP, Cloudflare)
- [ ] Cloud backup integration (S3, Backblaze)
- [ ] Performance monitoring dashboard enhancements
- [ ] Mobile app for server management
- [ ] Discord bot integration

### [1.2.0] - Planned

- [ ] Kubernetes deployment option
- [ ] Cloud backup integration (S3, Backblaze)
- [ ] Advanced security features
- [ ] Multi-server orchestration
- [ ] Load balancing support
- [ ] Metrics and analytics
- [ ] Mobile app for server management
- [ ] Discord bot integration

## Version Support

- **Minecraft Version**: 1.20.4 (default, configurable)
- **Java Version**: OpenJDK 21
- **Docker Version**: 20.10+
- **Docker Compose Version**: 2.0+
- **Raspberry Pi OS**: Bookworm (64-bit) or newer
- **Raspberry Pi Model**: Raspberry Pi 5 (4GB/8GB)

## Breaking Changes

None (initial release)

## Security Updates

None (initial release)

## Known Issues

1. First startup takes 5-10 minutes for world generation
2. Performance may vary based on number of players and view distance
3. Dynamic DNS not included (requires manual setup)
4. No automatic update mechanism yet

## Compatibility Notes

- Designed specifically for Raspberry Pi 5
- May work on other ARM64 devices with modifications
- Requires 64-bit operating system
- Minimum 4GB RAM recommended
- SSD storage recommended for better performance

## Migration Notes

For users upgrading from previous Minecraft server setups:

1. Stop your old server
2. Backup your world data
3. Copy world folders to `./data/` directory
4. Update `server.properties` as needed
5. Start the new server

## Contributors

- Initial development and documentation

## Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check documentation in README.md and INSTALL.md
- Review QUICK_REFERENCE.md for common tasks

---

[1.0.0]: https://github.com/and3rn3t/minecraft/releases/tag/v1.0.0
