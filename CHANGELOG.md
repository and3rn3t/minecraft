# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **BATS suites for `world-manager.sh` and `plugin-manager.sh`** — the two largest
  management scripts had no tests (`tests/unit/test-world-manager.sh`,
  `tests/unit/test-plugin-manager.sh`). They cover listing and the JSON the API
  reads, create/delete/switch/info/backup/templates, install/enable/disable/
  remove/update, dependency handling, config backup/restore and reload, with
  every prompt answered through stdin so nothing can hang. The sizes tests need
  GNU `du -b`, so they skip on macOS and run on the Pi and in CI.
- **Backups that actually get out of the house, and secrets to go with them**
  (O2, O3, O4, O5) — `backup-scheduler.sh` now uploads offsite automatically
  after a successful local backup, calling `cloud-backup-{r2,s3,b2}.sh` for
  any provider whose config has `AUTO_UPLOAD="true"` (the integration
  `docs/CLOUD_BACKUP.md` already documented but nothing called). New
  `scripts/backup-secrets.sh` archives everything the admin panel needs that
  isn't `./data` — accounts, API keys, the session-signing key, OAuth/RCON
  config, tunnel and playit credentials — encrypted with
  [age](https://age-encryption.org) against a key kept off the Pi, and runs
  automatically after every scheduled backup; see
  [`docs/CLOUD_BACKUP.md#secrets-backup`](docs/CLOUD_BACKUP.md#secrets-backup).
  `cleanup-backups.sh` now prunes secrets archives under the same retention
  pass as world backups, rather than letting them accumulate forever, and
  gained the portable date/stat/pattern-matching helpers it was missing
  entirely (it silently found zero backups to evaluate on macOS's BSD
  `find`/`grep`/`date`/`stat`, only working on the Pi's GNU userland) so
  `make bash-tests` exercises it for real on a Mac too.
  New `manage.sh restore <backup>` restores a world backup: holds the same
  update lock `deploy-agent.sh`/`auto-update.sh` hold while changing the
  container, moves the existing `./data` aside rather than deleting it, and
  fails loudly (exit nonzero) rather than reporting success when the log
  never shows a clean `Done (` load. New `scripts/lib/notify.sh` is a shared
  ntfy helper (`deploy-agent.sh`'s own copy now delegates to it). Health
  checks and `deploy-agent` deploy-refusals (dirty checkout or wrong branch)
  are debounced — a condition that persists across many runs of a frequently
  scheduled script notifies only once, via `notify_once`, which now also
  skips creating its marker at all when no `NTFY_URL` is configured, so
  enabling ntfy mid-episode doesn't permanently suppress that episode's
  alert. Backup, offsite-upload and secrets-upload failures are not
  debounced — each is a distinct scheduled event, not a continuous polled
  state, so every failed run notifies. Covered by new
  `tests/unit/test-backup-scheduler.sh`, `test-cleanup-backups.sh` and
  `test-manage-restore.sh`, plus new cases in `test-deploy-agent.sh`.
  Still open: confirming the Pi's first live timer runs cleanly, setting
  `AUTO_UPLOAD`/`AGE_RECIPIENT` on the Pi, and an actual restore drill against
  a downloaded backup (see [`docs/LOCAL_TESTING.md`](docs/LOCAL_TESTING.md)).

### Changed

- **`scripts/setup-docker-boot.sh` removed** — a 411-line generator for a generic
  `docker-app` systemd service (compose, `docker run` and a Minecraft mode). Nothing in
  the docs, tests, CI or Makefile used it; `systemd/minecraft.service` and the install
  guides already cover starting at boot, and its units pulled an image where this
  project's compose file builds one. It is in git history if it is ever wanted.
- **Tidying left over from the dependency work** — `api/server.py` loses its last
  self-contained piece: the code that wires the Hall of Deaths, pet cemetery, bedtime
  mode and the Oracle to the event bus moves to `api/event_capture.py` (about 100
  lines, read through `api.server` at call time like the other split-out modules), and
  it now has tests, which it had none of (`tests/api/test_event_capture.py`; each of
  five deliberate breakages of it is caught). The 32 test files that edited `sys.path`
  by hand no longer do: `tests/api/pytest.ini` already puts the project on the path, so
  the inserts, the `# noqa: E402` marks they needed and the unused imports are gone.
  `@axe-core/react`, a dev dependency nothing imported, is removed. In the web app, 64
  raw hex colours in `index.css` and `Layout.jsx` (`border-t-[#E0E0E0]`,
  `from-[#6D4C41]`, ...) now use the theme tokens they already equalled
  (`border-t-minecraft-text`, `from-minecraft-dirt`, ...), and so do 21 plain hex values in
  the rules of `index.css` itself (the toast gradients, scrollbar, skeleton, body
  background and so on, as `var(--color-minecraft-…)`). Every route renders
  bit-identically to before (24 of 24 screenshots compared), and a browser comparison of
  540 resolved values across the custom classes in every state (base, hover, active,
  focus, including the toasts, which screenshots cannot reach) found no difference. The danger button's hover
  shade, `#D32F2F`, becomes a new `minecraft-danger-hover` token. One raw value stays
  because no token has it: `#9C27B0`, a purple in the audit log.
  `make secrets` no longer fails on `.mypy_cache`, `.ruff_cache` and `.pytest_cache`:
  gitleaks scans the whole working tree, ignored files included, and a type checker's
  cache of a test file repeats that file's made-up credentials. Those three directories
  are allowlisted in `.gitleaks.toml`; a token anywhere else is still caught.
- **Tailwind CSS 3 → 4** — done with the official upgrade tool, then checked page by
  page. The theme moved from `web/tailwind.config.js` to an `@theme` block in
  `web/src/index.css`, PostCSS uses `@tailwindcss/postcss`, and `autoprefixer` is gone
  (Tailwind 4 prefixes itself). The upgrade also clears every `npm audit` finding, all
  of which came from Tailwind 3's dependencies. Needed by hand: `bg-opacity-*`, which
  the tool left behind and Tailwind 4 removed, became `bg-…/20` (three places); the
  tool's placement of the global `:root`/`body` rules in `@layer utilities` became
  `@layer base`; and Tailwind 4's changed defaults are put back so the look does not
  change: fixed line heights for the default text sizes (the new ratios shrank
  `.btn-minecraft` buttons from 16px to 13px wherever `text-[10px]` overrode the
  size), the gray placeholder color, and the pointer cursor on buttons. The login
  heading gets an explicit `lg:leading-8`, because Tailwind 4 now lets `leading-tight`
  win over a responsive text size where 3 let the responsive size win. All visual
  regression snapshots pass unchanged, and a pixel comparison of all 24 routes against
  Tailwind 3 found the same layout everywhere and no difference above 3/255 in any
  color channel, which is consistent with Tailwind 4's gradient and drop-shadow changes.
  Tailwind 4 needs Safari 16.4, Chrome 111 or Firefox 128 or newer.
- **`make ci` is about twice as fast** — the BATS suite was 157 of its 231 seconds, run
  one file after another. `scripts/run-tests.sh` now runs the files in parallel
  (`BATS_JOBS` sets the count, `1` is the old serial run) with each file's output
  buffered and printed in order, and `make ci` runs the suite in the background while
  the other steps run. A failing file or a failing step still fails the run, and an
  early failure stops the background suite. `CI_SERIAL=1 make ci` keeps the old order.
  The tests themselves are unchanged. The bash-tests CI job gets the parallel run too.
- **React 18 → 19** — `react` and `react-dom` 19.3, `@types/react` and `@types/react-dom`
  19. Nothing in the app used a removed API (no `ReactDOM.render`, `propTypes` or
  `defaultProps` on components); the `forwardRef` wrappers in `components/ui` still work
  and were left alone. The build, vendor-chunk check, lint and existing tests pass
  without code changes and without new warnings. `eslint-plugin-react-hooks` stays on 5;
  its 7.x adds React Compiler rules and is a separate change. The ESLint config now sets
  the React version (`detect`) in one global block instead of only for `.js`/`.jsx`
  files, which stops every lint run printing "React version not specified" for the
  `.mjs` build-chunk script.
- **Vite 6 → 8 and `@vitejs/plugin-react` 4 → 6** — Vite 8 bundles with Rolldown, which
  does not accept the object form of `build.rollupOptions.output.manualChunks`, so the
  vendor split in `web/vite.config.js` now uses `build.rolldownOptions.output.codeSplitting`
  groups and still produces the `react-vendor` and `socket-vendor` chunks. A lost
  group would not fail the build (the code just falls back into the main chunk), so
  `npm run check:chunks` (`web/scripts/check-build-chunks.mjs`) builds in memory and
  fails if either chunk is missing or their libraries land elsewhere; it runs in the
  frontend CI job and in `make ci` (`make check-web-build`), which previously never ran
  the web build at all. The build, lint and existing tests pass without other changes. `npm audit` findings are
  unchanged; Tailwind 3's dependencies still cause them.
- **Web test tooling brought up to date** — jsdom 23 → 29, jest-dom 6 → 7, jest-axe 8 → 11
  and Vitest 5.0.1 → 5.0.3. msw stays on 2.x: Vitest's mocker declares `msw ^2.4.9` as its
  peer, and `npm ci` rejects a lockfile with msw 3. The existing tests pass unchanged, and
  these are dev-only, so the app bundle is not affected. `npm audit` findings are
  unchanged by the upgrade; they come from Tailwind 3's dependencies, which the Tailwind
  4 upgrade is expected to remove. Playwright is left to its own pin
  (`scripts/check-playwright-pin.sh`). The declared Node range in `web/package.json`
  was `>=20.19`, which Vitest and jsdom already rule out; it is now
  `^22.13.0 || ^24.0.0 || >=26.0.0`, the overlap of what they support (CI runs Node 22).
- **Playwright 1.56.1 → 1.63.0** — `@playwright/test` and `playwright` are now pinned
  exactly in `web/package.json` (the version has to equal the CI container's tag, so a
  caret range only invited a lockfile that drifts ahead of it), the lockfile,
  `PLAYWRIGHT_IMAGE` in the `Makefile`, and the `playwright-tests` job's image all move
  to 1.63.0. The browser tests pass in the 1.63.0 image against the existing screenshot
  baselines, so none were re-rendered. The job's version check used to compare the
  lockfile with a second hard-coded copy of the version, so updating the image alone
  could still pass; it is now `scripts/check-playwright-pin.sh`, which reads the image
  tag from the workflow and the Makefile and compares them and `package.json` with the
  lockfile (also run by `make ci`, with its own BATS tests). `docs/CI_CD.md` lists the
  four places to change together, since Renovate bumps the npm packages but not the
  image tag.
- **Two more ruff rules, `subprocess.run` and swallowed exceptions** — `PLW1510`, `S110`
  and `S112` are enforced. All 14 `subprocess.run` calls already read `returncode`, so
  each now says `check=False` instead of leaving it implicit. Five classes (the event
  bus, Hall of Deaths, Pet Cemetery, Bedtime and the Oracle) each carried an identical
  copy of `set_error_logger` and `_log_error`, including the one deliberate `except
  Exception: pass` (reporting a failure must not raise on a worker thread); they now
  share a single `ErrorReporting` mixin in `api/error_reporting.py`, so that decision
  and its reason live in one place, with tests that fail if the swallow is removed.
- **More of ruff is enforced** — beyond pyflakes (`F`), the lint now enforces
  pycodestyle's error classes (`E4`, `E7`, `E9`), bugbear (`B`), isort (`I`), blind
  `except` (`BLE`) and stale `# noqa` comments (`RUF100`); the tree has no findings
  under any of them. Of the 30 `except Exception` handlers that said nothing about why,
  10 now catch only what can actually fail there (`OSError` for file and process
  cleanup, `ValueError` for unparseable schedules, `OSError`/`TypeError`/`ValueError`
  for saving users and keys) and 20 say why they must catch everything (`# noqa: BLE001`
  plus a reason, such as "route boundary: logged, generic 500 to the client"); the 26
  existing reasons, written for a rule that was not on, are now live. Narrowing means a
  genuine bug in those spots now surfaces instead of being turned into "returned False":
  `command-scheduler.py` documents an `UnboundLocalError` that a blanket `except` once
  hid until every schedule was skipped. Also: `zip(..., strict=True)` in the analytics
  anomaly check, and `tests/api/test_narrowed_exceptions.py` pins both halves of the
  narrowed handlers. Four test fixtures that made temp directories with
  `tempfile.mkdtemp()` and never removed them now use `tmp_path`. `scripts/lint.sh`'s
  flake8 fallback covers the part of this flake8 can do without plugins; ruff is the
  gate.
- **Setup docs consolidated** — `MINECRAFT_SERVER_SETUP.md`, `DOCKER_BOOT_SETUP.md`
  and `DOCKER_DEPLOYMENT_FLOW.md` are removed. The first two were a walkthrough and a
  generic "boot any Docker image" template that duplicated `INSTALL.md` and
  `RPI5_FULL_DEPLOYMENT.md` (and pasted a systemd unit that had drifted from the
  shipped `systemd/minecraft.service`); the third was a plan written before the deploy
  agent existed and said CI does not push images, which it does. `INSTALL.md` gains a
  "Start on Boot" section that installs the shipped unit. `UPDATE_DOCKER_IMAGE.md` is
  rewritten to match the repo: the compose file builds the image on the Pi, the deploy
  agent and the hourly `auto-update.sh` restart only when nobody is online, and pulling a
  prebuilt GHCR image is an opt-in (the old guide assumed a registry image, pointed at a
  script that does not exist, and logged to a path the unit cannot write).
  `SYSTEM_OPTIMIZATIONS.md` is cut to what `optimize-system.sh` applies: the generic code
  advice, the pasted cleanup script and its timer, and a reference to a
  `check-disk-space.sh` that was never written are gone.
- **Security dependencies are now required at startup** — `flask-cors`,
  `flask-limiter` and `api/security.py` used to be imported inside
  `try/except ImportError` with silent no-op fallbacks, so a broken install
  ran with no rate limiting or command sanitising and said nothing. A missing
  one now stops the API from starting (`tests/api/test_required_imports.py`).
  `POST /api/server/command` moved from the hand-rolled `rate_limit()` to
  Flask-Limiter (30/minute per client IP), which is removed along with its
  storage. Template TODOs in `.github/` and `CODE_OF_CONDUCT.md` are
  resolved, `start-all.sh` uses `lib/common.sh`, and web dev dependencies
  are updated within their ranges (Playwright stays pinned to match the
  browser image).

- **eventlet removed** (O7) — Flask-SocketIO now runs in threading mode with
  `simple-websocket`, so the API no longer monkey-patches the standard library
  at startup. Verified against a live server over both the polling and
  WebSocket transports. `eventlet` is dropped from `api/requirements.txt`.

- **ESLint 9** — the web app moves from ESLint 8 and `.eslintrc.cjs` to a flat
  `web/eslint.config.js`. The shared `@and3rn3t/eslint-config` was not used: it
  targets TypeScript files only and omits `eslint-plugin-react`, which this
  JSX codebase needs. ESLint's stricter defaults reported two unused `catch`
  bindings, now removed; Playwright specs get Node globals.

- **`api/server.py` split, part 1** — config redaction (`api/config_redaction.py`),
  file-browser path validation (`api/paths.py`) and the password/JWT/TOTP helpers
  (`api/auth_crypto.py`) move out of the app module. Callers and test patch
  targets use the new modules directly, with no re-exports left behind. The
  values that tests patch (`PROJECT_ROOT`, `ALLOWED_FILE_PATHS`, `SECRET_KEY`)
  stay on `api.server` and are read at call time. CodeQL totals are unchanged.
  Adds tests for the invalid-YAML error responses, which had none.

- **`api/server.py` split, part 2** — the permission model (`api/rbac.py`: the
  permission names, the role table, API-key scoping) and request authentication
  (`api/auth_guard.py`: `require_auth`, `require_permission`, `has_permission`,
  CSRF checks, `get_username_from_request`) move out of the app module. Routes
  use `@auth_guard.require_permission(...)`. `USERS` and `API_KEYS` stay on
  `api.server` and are read at call time. The unused `require_api_key`
  decorator is deleted. `auth_guard` imports `server` after its own definitions,
  so `import api.auth_guard` works whichever module is imported first (it failed
  with "partially initialized module" before); a test imports each module first.
  `_issue_csrf_token` is now the public `issue_csrf_token`, and `/api/status` no
  longer runs authentication twice.

- **`api/server.py` split, part 3** — the WebSocket log stream and console move to
  `api/realtime.py`: the single log-follower thread, the stream state, and the
  connect, disconnect, request-logs and execute-command handlers. It reads the
  Socket.IO instance, `USERS`, `API_KEYS`, the RCON runner and the audit logger
  from `api.server` at call time. `ensure_log_reader` is now public because
  `server.py` starts it with the event capture. Modules that used
  `server.sanitize_string` / `server.sanitize_minecraft_command` import them
  from `api.security` instead of going through `server`.
  `api.realtime` imports cleanly without Flask-SocketIO (its handlers are then
  simply not registered), so `server.py` imports it unconditionally.

### Fixed

- **`PROJECT_ROOT` is now a clean absolute path in every API module** — each derived it
  from `Path(__file__).parent.parent`, which keeps any `..` the module was imported
  through. Removing the tests' `sys.path` edits showed it: pytest's `pythonpath = ../..`
  gave `api/server.py` a root of `.../tests/api/../..`, and the file browser's
  `relative_to(PROJECT_ROOT)` check then raised `ValueError` and answered 500 for
  anything under it. The same would happen in production behind a symlinked or relative
  install path. All eight modules now resolve it (`tests/api/test_project_root.py` fails
  against the old code).
- **`GET /api/logs` no longer waits 30 seconds** — it ran `manage.sh logs` first and
  kept only its `stderr` as a fallback, but that script follows the log (`compose logs
  -f`), so every request waited for `run_script`'s 30-second timeout before it even
  asked Docker for the tail. The Logs page polls this endpoint. It now calls `docker
  logs --tail` directly, and when that fails it reports Docker's own message (or "Unable
  to retrieve logs" if Docker is missing or too slow) instead of the unrelated script's.
  Found through a code-review comment that was itself mistaken (it claimed `stderr` was
  undefined); the question it raised, where that `stderr` came from, was the real bug.
- **A crashed script's traceback no longer reaches an API client** — `GET
  /api/analytics/report` returned the processing script's raw `stderr` as `"details"`
  when it failed, which for a Python script is a traceback with file paths and source
  lines. It now returns a fixed message and logs the detail. `script_error()`, which
  about 25 endpoints use to surface a script's message, now does the same for any
  traceback it is given (readable messages such as "Player not found" still pass
  through), and the two DDNS routes that returned `stderr` directly go through it. The
  panel never read `details`. The detail that is logged goes through a new
  `sanitize_for_log()` (control characters dropped, continuation lines indented so text
  imitating a log entry cannot start a line, capped at 4,000 characters, indentation included) and uses lazy
  `%s` formatting. A script that will not compile prints a `SyntaxError` with only a
  `File "...", line N` frame and no "Traceback" header, so any such frame line counts as
  Python's own output. New tests in `tests/api/test_script_error.py`.
- **`cleanup-system.sh` no longer deletes what it should not** — it deleted every
  `*.tar.gz` backup older than 30 days as soon as there were more than 10 (its comment
  said "keep at least 10", but nothing enforced it, so it could leave one), including
  the `*.deleted.*` safety backups `world-manager.sh delete` writes and ignoring
  `config/backup-retention.conf`; backups are now left to `cleanup-backups.sh`, which
  `backup-scheduler.sh` already runs after every backup. It also ran `rm -rf /tmp/*`
  (live sockets, lock files and other programs' scratch space) and `docker system
  prune -af --volumes` (every unused image, so a stopped server's image had to be
  rebuilt, and every unused volume). It now prunes only dangling images and week-old
  build cache, and only the pip cache. New BATS suite
  (`tests/unit/test-cleanup-system.sh`); its `rm` and `sudo` are stubbed so a
  regression cannot touch the machine running the tests.
- **`world-manager.sh`: per-world config actually applies, and nothing moves a
  world aside** — `create` wrote `CREATED=2026-10-03 15:26:46` unquoted and
  `apply_world_config` then `source`d the file, so the shell tried to run
  `15:26:46`, failed, and `set -e` ended the script before the world type or seed
  was applied: `config` never worked, and `switch` stopped after it had already
  edited `level-name`. Config files are now read as plain data and never
  executed (a text seed such as `hello world`, or one holding `;` or `$()`, is
  stored literally). `config` and `switch` on a world with no config file (any
  world the server generated itself) used to call `create`, which asks whether to
  overwrite the world and, on yes, moved it into a `.backup.` directory; they now
  just write a default config. Also: `delete` no longer removes a world when its
  backup could not be written (the `tar` was followed by `|| true`, and the
  message claimed it was saved); values written into `server.properties` are
  escaped for `sed`, so a name or seed containing `/` or `&` no longer breaks the
  edit; world and template names that could leave `data/` or the template
  directory (`../x`) are refused; and the `tar` fallback used when `rsync` is
  missing now puts `--exclude` before the path, since after it GNU tar ignored it
  (player data ended up in templates) and BSD tar rejected it.
  `create` also refuses a type or seed containing a line break or other control
  character, which would otherwise have started another line in the config file.
- **Worlds are listed whatever they are called** — `list`, `list-json` (what
  `GET /api/worlds` returns) and `sizes` only looked at `data/world*`, so a world
  made with `create survival` never appeared, in the CLI or the web panel. Any
  directory under `data/` with a `level.dat` is now a world, except the
  `<name>.backup.<timestamp>` copies `create` leaves beside a world it replaces.
- **`plugin-manager.sh`: dependencies written as a YAML list** — `depend: [Vault,
  WorldEdit]` and the block form were read as one bogus name, so installs warned
  about missing dependencies that were present. A jar's declared `name:` is no
  longer trusted as a path component when its config directory is backed up or
  deleted, plugin names given to `enable`/`disable`/`remove`/`update` that point
  outside `plugins/` are refused, and a failed `unzip` no longer leaks a
  temporary directory.
- **A missing auth library no longer disables an unrelated feature** — bcrypt and
  PyJWT shared one `try/except`, so losing bcrypt also turned off JWTs and Apple
  sign-in. pyotp and qrcode did the same, which would have blocked 2FA logins
  when only qrcode (needed just for the setup QR image) was missing. Each is now
  imported on its own, with `PYOTP_AVAILABLE` and `QRCODE_AVAILABLE` replacing
  `TOTP_AVAILABLE`.

- **Deaths, joins, leaves and advancements are recognised again on 26.x** —
  Minecraft 26.x logs every broadcast system message as
  `System chat: <message>` instead of the bare sentence 1.20.4 wrote, so since
  the 26.3 upgrade the event bus matched none of them. The Hall of Deaths
  stayed empty, and bedtime's join check would never have fired. `parse_line`
  now strips the prefix, after the player-chat check, so a typed fake death
  still counts as chat.

- **Bans and unbans reach the live server again** — `ban-manager.sh`'s RCON
  notification was a stub that always returned success without sending
  anything, so a banned player already connected was never kicked and
  `pardon`/`pardon-ip` never lifted a ban in the running server's own memory
  until a restart. It now sources `rcon-client.sh` and calls its
  `check_rcon_available`/`send_rcon_command`, the same containerized RCON
  path the RCON CLI already uses, and the notification remains best-effort:
  a container that isn't running, doesn't have `rcon-cli`, or an RCON call
  that fails no longer stops the ban/unban from being recorded. Also fixes
  `ban-ip` raising `NameError: name 'sys' is not defined` on a fresh
  `banned-ips.json` (the heredoc called `sys.exit()` without importing
  `sys`), masked until something first banned an IP with no prior entries.
  Covered by new `tests/unit/test-ban-manager.sh`.

- **The admin panel's restore now gets the same safety net the CLI has** —
  `POST /api/backups/{filename}/restore` reimplemented restore in Python
  (extract in place, snapshot the old `data/` to a `.tar.gz`), a second,
  materially different safety model from `manage.sh restore`'s (stop, move
  `data/` aside rather than deleting it, extract, restart, and refuse to
  report success unless the log shows a clean world load). The route now
  delegates to `manage.sh restore` itself — `run_script()` gained an
  `input_text` parameter to feed its confirmation prompt — so there is one
  restore path instead of two, and the API gets the log-watch and
  automatic rollback-on-corrupt-archive behavior the CLI already had.
  `pre_restore_backup` in the response is now the moved-aside data
  directory rather than a tar.gz path. Also anchors `/api/status`'s
  `docker ps` filter to the exact container name (`^minecraft-server$`),
  matching `container_running()`'s exact-match convention, so a
  similarly-named container can't be mistaken for it.

- **Op/deop no longer show stale player state for up to 3 seconds** —
  `opPlayer`/`deopPlayer` in `web/src/services/api.js` mutate the same
  operator list `getPlayers`/`getOps` cache, but didn't clear that cache the
  way every other mutation in the file does, so the panel could show a
  player as still (or not yet) an operator until the 3s cache TTL expired.

- **A failed save could silently leave state only half-applied** — enabling
  an API key or user, disabling an API key, and unlinking an OAuth provider
  all mutated in-memory state and called `save_api_keys()`/`save_users()`
  without checking the result, unlike the sibling operations
  (`disable_user`, re-scoping or creating a key, linking an OAuth provider)
  that already roll back on a failed save. A disk write that failed (full
  disk, permissions) left the change live in memory and returning success,
  only to revert on the next restart with no record anything had gone wrong.
  `enable_api_key`, `disable_api_key`, `enable_user` (`api/blueprints/access.py`)
  and `unlink_oauth_account` (`api/blueprints/auth.py`) now roll back and
  return 500 the same way their siblings do.

- **Saving a config file for the first time could report failure even
  though it succeeded** — `save_config_file` only assigned `backup_path`
  when a prior version of the file existed, but then referenced it
  unconditionally in the response and the rollback-on-failure branch,
  raising `UnboundLocalError` for any file that didn't already exist yet.
  The write itself succeeded; the API still returned a 500. Now initializes
  `backup_path = None` up front, matching the pattern already used by
  `write_file` and `save_ddns_config`.

- **A scheduled command with a malformed field could silently stop firing
  forever** — the scheduler API accepted `interval_minutes`, `run_time` and
  `day_of_week` without validating their type or range. `command-scheduler.py`
  reads those three fields without a `try`/`except` (unlike
  `cron_expression`/`run_datetime`, which already are wrapped), so a bad
  value — a string where a number was expected, an out-of-range hour — made
  that schedule raise on every single pass rather than failing once, up
  front, at creation time. `api/blueprints/scheduler.py` now validates all
  five schedule-type fields before saving.

- **A mutation's cache invalidation could be silently undone by a slower,
  already-in-flight read** — `invalidateCache()` only clears resolved cache
  entries; a `getPlayers()`/`getOps()` GET issued just before an op/deop
  mutation could resolve just after it, with its `.then` callback
  re-caching the pre-mutation response. The dashboard could keep showing
  stale data for the rest of that GET's TTL despite the cache having just
  been cleared. `web/src/utils/apiCache.js` now tracks a cache generation,
  bumped on every `clearAllCache()`; `cachedGet` in `web/src/services/api.js`
  captures the generation before issuing a request and only caches the
  response if nothing invalidated the cache while it was in flight.

## [1.6.0] - 2026-09-28

### Added

- **Game access through CGNAT** — the home connection is behind carrier-grade
  NAT, so the port forward and DDNS A record behind `mine.andernet.dev` never
  reached the server; every login ever logged came from the LAN. Players now
  connect through a playit.gg tunnel, found running undocumented from an
  `@reboot` crontab line. New `systemd/minecraft-playit.service` runs the
  agent with a restart policy. playit had silently moved the tunnel from port
  33856 to 33903, leaving the Cloudflare SRV record pointing at a dead port,
  so new `scripts/playit-srv-sync.sh` (and `minecraft-playit-sync.timer`,
  every 15 minutes) copies the tunnel's current port from playit's own SRV
  record into Cloudflare's. It updates only the one existing record, and
  writes nothing it can't validate first. Configured in
  `config/playit.conf`. See [`docs/PLAYIT.md`](docs/PLAYIT.md).

- **The Oracle** (W1) — a Claude-powered companion that lives in chat. Every
  allowlisted player's chat message is triaged by `claude-haiku-4-5` into
  one of three outcomes (stay quiet, banter back, or generate a quest), using
  structured output rather than free-text parsing, so a jailbreak attempt is
  bounded to a short text field with no tool access. A quest request
  triggers a second, structured call to `claude-sonnet-5`, delivered via
  `tellraw` and persisted to `data/oracle/quests.jsonl` for a future bounty
  board (P11) to read, since P11 doesn't exist yet. New `api/oracle.py`
  module, mirroring `api/hall_of_deaths.py`'s worker-thread shape and
  `api/epitaphs.py`'s pluggable-writer interface. Off by default, twice
  over: `config/oracle.conf`'s `ENABLED=false`, and no responder is built at
  all without `ANTHROPIC_API_KEY` set as a real environment variable. Guarded
  by an exact-username allowlist, a per-player rate limit that gates the
  Claude call itself (not just the reply), and a live kill switch on a new
  `/oracle` dashboard page behind a dedicated `oracle.manage` permission,
  admin-only by default. See [`docs/ORACLE.md`](docs/ORACLE.md).
  - Ships as an always-on triager rather than a trigger-word bot: there's no
    "oracle, ..." prefix requirement, so the model itself has to choose
    silence for ordinary chat between the two kids. Chosen deliberately over
    a cheaper trigger-word design; the system prompt explicitly tells it to
    pick `no_reply` liberally.
  - Two deliberate v1 simplifications, not oversights: no per-player
    conversation memory (every message is triaged independently), and
    quests are generated on request rather than posted automatically once a
    day, since there is no bounty board yet for a daily post to go to.

- **`docs/LOCAL_TESTING.md`**: how to run a real vanilla server in Docker
  locally (not the Pi) to test game features before they ship — building
  and starting the image, enabling RCON, reloading a datapack and reading
  the reload output for real errors, exercising a mechanic without a
  connected player (a stand-in entity plus `execute as ... at ... run
  function ...`), and running the API server against it. Written while
  setting up exactly this to verify the Graves/Lucky Blocks datapack work,
  which is what turned up the three RCON bugs below.
- **Lucky Blocks, Graves, and the Pet Cemetery** (W7, W8, M6) — the first
  content built on the datapack pipeline beyond the family advancement tree.
  - **Lucky Blocks**: craft a player head, break it, roll a weighted loot
    table. Detected via tick-to-tick stat watching, the same technique Ten
    Thousand Blocks uses — there is no vanilla advancement trigger for "a
    specific block was mined." See
    [`docs/LUCKY_BLOCKS.md`](docs/LUCKY_BLOCKS.md).
  - **Graves**: a player's dropped items are gathered into a labeled chest
    at the death spot instead of scattering, with a 24-in-game-day
    auto-expiry. Ships as an unlocked chest and an honor system, not a real
    per-player lock — vanilla has no such thing. See
    [`docs/GRAVES.md`](docs/GRAVES.md).
  - **Pet Cemetery**: named (tamed) pets get a gentle obituary and a real
    gravestone, reusing `api.epitaphs`' cause classification but not its
    comedic tone. New `pet_death` event type in `api/events.py`, new
    `api/pet_cemetery.py` module (mirrors `api/hall_of_deaths.py`'s shape).
    See [`docs/PET_CEMETERY.md`](docs/PET_CEMETERY.md).

  Graves' item-vacuum and sign-text mechanics were verified against a real
  vanilla 1.20.4 server (see `docs/LOCAL_TESTING.md`), which caught two real
  bugs the initial implementation had gotten wrong: `item replace ...
  contents` (the command the Minecraft Wiki describes for copying a dropped
  item into a container slot) doesn't exist on 1.20.4, and a chest's
  `Items` list silently collapses duplicate entries unless each one's
  `Slot` is set atomically alongside its `id`/`Count` rather than in a
  follow-up command. Both fixed; see `docs/GRAVES.md` for the full story.

- **Upgraded the default Minecraft version from 1.20.4 to 26.3** (F7).
  Minecraft has moved to a year-based version scheme since the roadmap was
  written (1.21.x -> 26.x); every place `MINECRAFT_VERSION` was pinned --
  `Dockerfile`, both `docker-compose` files, `.env.example`, and the two CI
  workflows' build-args -- now defaults to 26.3. The family datapack is
  ported to match: `pack.mcmeta` carries `min_format`/`max_format` (the
  schema Minecraft moved to at 1.21.9) alongside `pack_format`, all four
  `data/family/` subdirectories are renamed to their singular forms (24w21a
  dropped the plural names), and the Lucky Block recipe/function use
  component syntax (`minecraft:custom_name`) instead of item NBT. Verified
  live against a local 26.3 server: with the directory rename alone,
  `/datapack list` reported the pack enabled while every function returned
  "Unknown function" -- the exact silent-failure mode `datapack-manager.sh`
  warned about. Two more breakages only turned up that way: shaped-recipe
  keys must now be plain item ids, not `{"item": "..."}`, and the same
  `item` -> `id` rename applies to every advancement's `display.icon`.
  `check_sibling_rivalry.mcfunction`'s day-change detection now uses
  `time query day`, since 26.1 replaced the bare `daytime` keyword with a
  data-driven timeline registry. `datapack-manager.sh validate` now warns
  (non-fatally) on a `pack_format` mismatch instead of staying silent.

- **Automatic deploys to the Pi.** `scripts/deploy-agent.sh`, run every five
  minutes by `systemd/minecraft-deploy.timer`, fast-forwards the Pi's checkout
  to the newest commit on `main` that passed CI and applies only what changed
  across every commit since the last deploy: it rebuilds or downloads the web
  panel, reinstalls API dependencies, restarts the API and waits for its
  health check, installs systemd units, reloads nginx, and rebuilds or pulls
  the game server image. A failed web build or health check rolls back to the
  previous commit and that commit is not retried. The game server is never
  restarted while anyone is online, and a stopped server is left stopped.
  Each run diffs from the last commit it finished applying rather than from
  the checkout, so a `git pull` by hand or a run that died half-way is
  completed on the next run; `deploy-agent.sh since ORIG_HEAD` hands a manual
  pull to it. It shares a lock with `auto-update.sh`, so the two never rebuild
  or recreate the container at the same time. Deploys and rollbacks go to the
  audit log and, optionally, to ntfy. It is off
  until `minecraft-deploy.timer` is enabled; see
  [docs/AUTO_DEPLOYMENT_SETUP.md](docs/AUTO_DEPLOYMENT_SETUP.md). CI now
  uploads the built panel as a `web-dist` artifact on pushes to `main` for it.
- **`scripts/player-count.py`** reports how many players are online using the
  server list ping, with no RCON password. It exits non-zero when the server
  does not answer, so callers treat silence as "unknown" rather than "empty".

- **`POST /api/server/properties/preset`** applies one of the performance
  presets in `scripts/server-properties-manager.sh` (`low-end`, `balanced`,
  `high-performance`), which set view distance, simulation distance, max
  players, network compression and entity broadcast range together (#29). The
  handler already existed with its permission decorator but no route, so it was
  unreachable and presets could only be applied from the shell.
- **`PUT /api/scheduler/schedules/<id>/enable` and `/disable`**, so a schedule
  can be paused without deleting it. These existed only on the duplicate API
  that has been removed, so the web interface had no way to do it.
- **`scripts/datapack-manager.sh`**, a `create`/`list`/`install`/`enable`/
  `disable`/`validate`/`delete`/`reload` pipeline for vanilla datapacks, plus
  `GET /api/datapacks`, `POST /api/datapacks/install`,
  `PUT /api/datapacks/<name>/enable`/`disable` and `DELETE /api/datapacks/<name>`.
  The tracked source of a datapack lives
  at `config/datapacks/<name>/`; `enable` deploys it into the current world's
  gitignored `data/<world>/datapacks/` and reloads, `disable` removes the
  deployed copy without touching the tracked source. New `datapacks.view`/
  `datapacks.manage` permissions, following the existing `plugins.*`
  precedent. See [`docs/DATAPACKS.md`](docs/DATAPACKS.md).
- **The family advancement tree**, the pipeline's first real datapack:
  five custom advancements (First Diamond, Neighbors, Ten Thousand Blocks,
  Sibling Rivalry, Night Shift) in their own tab in the game's own
  advancements screen. Four are granted by datapack tick functions; Night
  Shift is granted by RCON from a scheduled command, since a vanilla function
  has no access to the real-world clock. See
  [`docs/ADVANCEMENTS.md`](docs/ADVANCEMENTS.md) for how each one works and
  the one-time setup (Dad's house coordinates, the Night Shift schedule) it
  needs after enabling.

### Changed

- **The Oracle can answer where everyone sees it** — new `REPLY_TO` setting in
  `config/oracle.conf`. `player` (the default) keeps replies private to the
  player who asked, as before; `all` sends replies and quests to everyone
  online, tagged `[Oracle → name]` so it's clear who was answered. A typo
  keeps the private default rather than broadcasting. See
  [`docs/ORACLE.md`](docs/ORACLE.md).

- **Ruff's settings moved to `[tool.ruff]` in `pyproject.toml`**, which the
  editor extension, the pre-commit hook and `scripts/lint.sh` all discover.
  They previously carried three copies of the same flags. The editor copy used
  `ruff.lint.args`, which the native server that replaced `ruff-lsp` does not
  support and warns about; see
  [the migration guide](https://docs.astral.sh/ruff/editors/migration/).

- **`GET /api/players/stats` returns a list rather than a map**, with real
  counters: time played, blocks mined by type, distance walked, damage taken
  and dealt, advancements completed. `GET /api/players/stats/metrics` lists what
  a leaderboard can rank by, and `?raw=true` returns the game's full stats
  block. The metric names the old tracker invented (`login_count`,
  `blocks_broken`, `play_time`) still resolve onto the nearest real counter, so
  an existing caller gets a true answer instead of an empty leaderboard.

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

### Removed

- **`POST /api/players/stats/parse`** and `scripts/player-stats-tracker.sh`.
  The endpoint existed to trigger the log scrape; there is no collection step
  any more, because the counters are the game's own.

### Fixed

- **Scheduled backups** — `minecraft-backup.service` named `User=%i`
  without being a template unit, the timer carried a second
  `OnCalendar=daily` trigger (an extra midnight backup), and
  `backup-scheduler.sh` skipped any run whose clock didn't read exactly
  `03:00`, which the timer's randomized delay and catch-up runs almost never
  do. The unit now names `pi`, the timer has one trigger, and the
  exact-minute check applies only to cron runs. `install-backup-timer.sh`
  rewrites the user and path instead of the removed `%i`. The timer now runs
  every other day (odd-numbered days) rather than nightly, and is enabled on
  the Pi.
- **Backups include player data** — Minecraft writes each player's data
  file (inventory, position, XP) mode 600 as the container's uid 999, which
  the host's `pi` user can't read, so `manage.sh backup`'s host-side `tar`
  failed every scheduled run; its errors went to `/dev/null`. The archive is
  now made inside a throwaway container of the server image (`compose run`),
  as the files' owner, and compressed on the host. A failed run reports
  tar's own errors and deletes its partial archive; files the live server
  changes mid-read are reported as a warning rather than a failure.
- **The dashboard shows CPU usage as a percentage.** The API strips the `%`
  from `docker stats`, and the dashboard added it back for memory but not CPU,
  so CPU read "12.50". Found by the new screenshot tests.
- **The browser tests run, and gate pull requests.** They were schedule-only
  and could not fail (`continue-on-error` and `|| true`), which hid 24
  failures: screenshot baselines that were never committed, mocks for API
  routes the app doesn't call (so the app believed everyone was signed in and
  the sign-up journey could not start), and assertions made before the request
  they checked. They now share one API mock, run in Chromium in the Playwright
  image on every pull request, and have `make test-visual` /
  `make test-visual-update` for running them the way CI does.

- **User management keeps exactly the admins it should.** Deleting, demoting
  or disabling an admin counted the target itself among the remaining admins,
  so a *disabled* admin could not be removed while exactly one other admin was
  active. A save that failed during any of the three, or while linking a
  Google/Apple identity, now leaves the account as it was instead of changed
  in memory until the next restart.
- **The file browser protects its four root folders, and only those.**
  Protection matched folder names, so `backups/` could be deleted wholesale
  and any folder merely named `config` (a plugin's own settings folder under
  `data/`) could not.
- **The audit log records who ran a console command over the WebSocket**
  (the key's name or the user) rather than `__api_key__` for everyone, and
  linking a Google or Apple identity to an account is now audited. Audit-log
  paging is clamped: a negative `limit` used to slice from the end.

- **The Console runs commands with arguments.** The command sanitizer counted
  whitespace as a shell metacharacter, so `say hello`, `kick alice` and every
  other command with an argument was refused; it also matched blocked programs
  by prefix, so `su` refused `summon` and `subtitle`. Commands reach the
  server as a single argument and never pass through a shell.

- **`api/rcon.py` could get its connection closed by the real Minecraft
  server on the very first command.** `_send_command()` sent the command
  packet and a second "sentinel" packet (used to detect the end of a
  multi-packet response) back to back, with nothing read in between. Against
  the fake RCON server `tests/api/test_rcon.py` uses, that's fine; against a
  real vanilla 1.20.4 server, the two packets can be coalesced by the OS
  into one write, and vanilla's own packet reader can't handle two framed
  packets arriving in a single read — it drops the connection instead of
  parsing both, deterministically, every time. Found by actually running a
  command against a real server rather than only the test suite's mock one.
  Fixed by reading the command's first response packet before sending the
  sentinel, which forces a real round trip between the two writes and
  removes the coalescing risk entirely, rather than papering over it with an
  arbitrary delay.
- **`scripts/rcon-client.sh`'s Python fallback reimplemented the RCON wire
  protocol with two of its own bugs**: no length-prefix framing on the
  packets it sent, and an auth-failure check that only tripped on a
  suspiciously short reply instead of checking the protocol's own `-1`
  request id — so it could report "Authentication failed" for reasons that
  had nothing to do with authentication (exactly what the malformed packets
  it was sending would provoke). `api/rcon.py`'s own docstring already
  documented this exact class of bug in this script's *previous* approach;
  this script's fallback had drifted into repeating it independently. Now
  shells out to `api/rcon.py` instead of maintaining a second
  implementation.
- **`scripts/rcon-setup.sh` could silently generate an empty RCON
  password.** `generate_password()` piped `/dev/urandom`'s raw binary
  through `tr -dc` without forcing a `C` locale; under a UTF-8 locale, `tr`
  can hit an invalid byte sequence partway through and exit early, and
  because that failure was in the middle of a pipeline, `set -e` never saw
  it. The result: `RCON_PASSWORD=` written to both `config/rcon.conf` and
  `server.properties`, with no error shown. Fixed with `LC_ALL=C`, an
  `openssl` fallback if the length still comes up short, and an explicit
  error instead of continuing with a short/empty password.
- **A generated RCON password containing `&` or `$` broke both consumers
  that read it back.** `scripts/rcon-setup.sh`'s password alphabet included
  both characters: `&` is a shell control operator even with no surrounding
  whitespace (`a&b` tokenizes as three tokens), so `rcon-client.sh` sourcing
  `config/rcon.conf`'s unquoted `RCON_PASSWORD=...` line could silently
  truncate the password or run part of it as a command; `&` also means "the
  whole match" in a sed replacement, which is how the same password gets
  written into `server.properties`. `$` had the same problem for sourcing
  (parameter expansion). Fixed by dropping both from the generated
  alphabet — confirmed clean across 30 freshly generated passwords.
- **`scripts/api-key-manager.sh` had the identical locale bug as
  `rcon-setup.sh`'s password generator**, discovered while writing
  `docs/LOCAL_TESTING.md`'s "create an API key" instructions and finding
  they produced a 1-character key. Same fix: `LC_ALL=C` on the `tr`
  pipeline, plus an `openssl` fallback.
- **The hourly image updater never updated anything.** `scripts/auto-update.sh`
  passed the container name (`minecraft-server`) to compose commands that take
  the service name (`minecraft`), so compose found no such service and the
  script concluded the server was stopped on every run. Behind that, it
  detected a new image by comparing `docker compose images` before and after
  a pull, which reports the image the running container uses and so never
  changes on a pull. It now compares the running container's image with the
  image its tag points at, restarts only when nobody is online, and skips the
  pull when the image is built locally.
- **`docker-compose.registry.yml` had drifted from `docker-compose.yml`.** It
  set the container's memory limit equal to the Java heap, which causes the
  restart loop `docker-compose.yml` documents, and kept a health check that
  reported healthy before the server accepted connections. It is now the main
  file with only the image source changed, selected with `COMPOSE_FILE` in
  `.env` rather than by copying it over a tracked file, and a test fails if the
  two drift again.
- **`scripts/update-codebase.sh` missed changes when a pull brought in more than
  one commit.** It compared only the last commit with its parent, so a `web/` or
  `api/` change in an earlier commit was never rebuilt or restarted. The
  "automatic updates" recipes in `docs/UPDATE_CODEBASE.md` that scheduled it
  are replaced by a pointer to the deploy agent: the script prompts when the
  checkout has local edits, so it hangs when nobody is there to answer.

- **Player statistics no longer inflate on every run** (#28).
  `scripts/player-stats-tracker.sh` scraped the server log with three regular
  expressions and added what it found to the previous totals, so the same
  unchanged log reported 1, then 2, then 3 — for a player who had joined once.
  A restart replayed the whole file, and the death pattern matched the literal
  word `etc`. Replaced by `api/player_stats.py`, which reads the counters the
  game keeps in `<world>/stats/<uuid>.json` and
  `<world>/advancements/<uuid>.json`. There is nothing to accumulate, so
  reading is idempotent by construction, and it covers everything Minecraft
  tracks rather than the three things the log mentioned. See
  [docs/PLAYER_STATS.md](docs/PLAYER_STATS.md). Damage is reported in hearts to
  one decimal place, so half a heart is not floored away, and the leaderboard
  `limit` is clamped to 1-50 like `/api/deaths/leaderboard`.

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

- **The audit log is admin-only.** It records every account's IP addresses,
  failed sign-ins and the commands people ran, but needed only `logs.view`,
  which the `user` role holds. It now needs a new `audit.view` permission that
  only admins have; grant it to a key explicitly if something else reads it.

- **The file browser is admin-only; any "user" could read the admin API
  keys through it.** Browsing, reading and downloading files needed only
  `config.view`, which every role holds — including the default role for new
  API keys — so a plain user could read `config/api-keys.json` and act as an
  admin, or read `users.json`, `rcon.conf` and `rcon.password`. They now need
  a new `files.view` permission that no role but admin has; grant it to a key
  explicitly if something else needs it. File Browser moves to the admin
  section of the nav. **Rotate your API keys after upgrading**, and consider
  the RCON password: until then they were readable by any user-role
  credential.
- **Credentials are masked in the config viewer and the DDNS page for
  non-admins.** `config.view` still shows `server.properties`, `api.conf`,
  `ddns.conf` and the compose file, but values of keys like `rcon.password`,
  `SECRET_KEY`, `*_TOKEN`, `*_PASSWORD` and `*_API_KEY` read `********` unless
  the viewer can edit config — the only people who can save, so a masked value
  is never written back. Values spanning several lines (YAML blocks, quoted
  multi-line `.conf` values) are withheld entirely.
- **Google and Apple sign-in no longer create accounts while registration is
  closed.** A first-time OAuth sign-in is an account creation and now obeys
  `REGISTRATION_ENABLED` like `/api/auth/register`; it used to create a
  `user` account for anyone with a Google or Apple identity. Identities
  already linked to an account still sign in.
- **Disabling or deleting a user ends their access immediately.** Only
  password login checked `enabled`; an existing session or bearer token kept
  working until it expired, and OAuth sign-in ignored it. Every request now
  re-checks the account.
- **2FA can't be switched off with only a session.** Setting 2FA up on an
  account that already had it replaced the secret and turned it off; setup now
  refuses while 2FA is on, and turning it off still needs the password.
  Accounts created by Google or Apple sign-in have no password: 2FA setup
  points them to their provider, and one that already had 2FA can turn it off
  with a current code (disabling it used to fail with a 500).

- **Handlers no longer return exception text to the caller.** Fifty-six
  returned `f"...: {str(e)}"` with a 500, which can carry filesystem paths and
  internal state. They log the detail and return a generic message, as the
  newer handlers already did. `run_script()` did the same thing indirectly, by
  handing the exception text back as the script's stderr, which several
  handlers return verbatim; and two WebSocket error paths did it directly.
  CodeQL's count for this drops from 75 to 0. The YAML validator was going to
  be a deliberate exception, since it describes the content the caller just
  submitted, but exempting it would have meant exempting the whole rule for
  `api/server.py` — so it builds its message from the parser's own `problem`
  and `problem_mark` instead, which is safe and reads better.
- **A null byte in a file-browser path returned a 500** carrying the raw OS
  error, because `Path.resolve()` raises before the allowlist check runs. All
  six file-browser endpoints now share one `resolve_allowed_path()` helper that
  rejects it as a 400. Found by attacking the endpoints rather than reading
  them. Total CodeQL errors: 115 to 33 — 32 path-expression findings, reviewed
  as false positives and covered by `tests/api/test_path_traversal.py`, and one
  clear-text finding where the value written to the audit log is an API key's
  name rather than the key.

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

- **Apple Sign In accepted a forged login as any user.** `apple_oauth_callback()`
  and the account-linking path both decoded the Apple ID token with
  `verify_signature=False` and trusted its `sub` claim outright, so anyone who
  could POST to `/api/auth/oauth/apple/callback` could self-sign a JWT naming
  an arbitrary user and be logged in as them. `verify_apple_id_token()` now
  verifies the signature against Apple's published JWKS
  (`https://appleid.apple.com/auth/keys`) plus audience, issuer and expiry.
- **No rate limiting on any auth endpoint.** Login, registration, 2FA
  verify/disable, and both OAuth providers' URL/callback/link routes had no
  throttling at all — passwords and TOTP codes were guessable with no limit.
  Flask-Limiter now caps login at 5/minute + 20/hour per IP, 2FA and the
  OAuth callback/link routes at 10/minute, registration at 10/hour, and
  OAuth URL generation at 30/minute; nginx adds an independent second layer
  on `/api/auth/*`. Both layers key on the visitor's IP, which behind the
  documented Cloudflare Tunnel would otherwise always be cloudflared's own
  loopback address — nginx now recovers the real one from Cloudflare's
  `CF-Connecting-IP` header via `ngx_http_realip_module` before either layer
  sees it, and `api/server.py`'s `ProxyFix` trusts that corrected hop.
- **CORS defaulted to `*` with credentials allowed.** Combined with
  `supports_credentials=True`, this let any site make authenticated requests
  against the API — flask-cors reflects the request's `Origin` instead of a
  literal `*` once credentials are in play. The server now warns loudly on
  startup if `ALLOWED_ORIGINS` is still unset.
- **The session cookie had no `Secure`/`SameSite` flags, and nothing checked
  CSRF.** `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY` and
  `SESSION_COOKIE_SAMESITE="Strict"` are now set explicitly, and a
  synchronizer-token CSRF check is enforced on state-changing requests
  authenticated via the session cookie. The Bearer-JWT path is checked
  *before* the session cookie specifically so that the panel's own traffic
  (same-origin, so the cookie rides along automatically alongside the
  Bearer token it actually authenticates with) never gets routed through
  the CSRF check the SPA never learned to answer — a cross-site page can
  still only ever get the cookie sent for it, never a valid `Authorization`
  header, so this doesn't weaken the protection itself. The OAuth
  authorization flow (both login *and* account-linking) also gained a
  `state` parameter, closing a separate CSRF gap where nothing stopped an
  attacker from feeding their own OAuth code/id_token to a victim's
  browser; since that depends on the session cookie surviving between the
  authorization-URL request and the callback, the frontend's API client
  now sends credentials on cross-origin requests too (the documented local
  dev setup is cross-origin between Vite and Flask).
- **Breaking: `?api_key=...` in the URL is no longer accepted.** It leaked
  into nginx access logs, browser history, and any `Referer` header a
  follow-on request sends. The `X-API-Key` header is now the only accepted
  form — a request still using the query parameter gets a 401 instead of
  being authenticated. `docs/API.md` updated to match.
- **Login, logout, registration, 2FA and OAuth events were never audited**,
  despite `docs/SECURITY_HARDENING.md` claiming otherwise. `log_audit_event()`
  is now called from all of them (never logging the password itself).
- **Security headers tightened, and now actually reach the page that loads
  the app.** `Content-Security-Policy` moved from a bare `default-src 'self'`
  to explicit per-directive rules (no inline/eval scripts, `frame-ancestors
  'none'`), a `Permissions-Policy` header was added, and the deprecated,
  no-longer-meaningful `X-XSS-Protection` header was dropped — but these
  were only ever set on Flask's own JSON responses, never on `index.html` or
  the JS/CSS bundle nginx serves directly from disk, which is what a
  browser actually enforces CSP against. `config/nginx-minecraft.conf` now
  carries the same headers on its static-file locations too.
- **`systemd/minecraft-api.service` sandboxing**: added `ProtectSystem=strict`
  (scoped to the service's own directory via `ReadWritePaths=`),
  `CapabilityBoundingSet=`, and several other namespace/kernel-protection
  directives, on top of the `NoNewPrivileges`/`PrivateTmp` that were already
  there.
- Added a documented path to exposing the admin panel to the internet via a
  Cloudflare Tunnel (`config/cloudflared-config.yml.example`,
  `docs/SECURITY_HARDENING.md`) rather than a direct port-forward — nginx now
  binds to `127.0.0.1` only.
- **Apple Sign In never actually reached the app.** Apple requires
  `response_mode=form_post` whenever the requested scope includes
  name/email (this app's Apple flow always requests both), meaning Apple
  POSTs the callback result instead of redirecting with it in the URL —
  and the SPA's callback page only ever reads the URL's query string, with
  no way to see a POST body. Every Apple sign-in would load that page with
  nothing on it. `POST /oauth/callback` (`apple_oauth_form_post_relay()`
  in `api/server.py`) now catches that POST and re-issues it as a redirect
  to the same path with the same fields as query params, which the
  existing client-side handling already expects; `config/nginx-minecraft.conf`
  routes POST requests for that exact path there specifically, leaving GET
  to the SPA as before. Also fixed `config/oauth.conf.example`, which
  implied `APPLE_TEAM_ID`/`APPLE_KEY_ID`/`APPLE_PRIVATE_KEY` were required
  — none of the three are read anywhere in the Apple flow, which only
  verifies the ID token Apple hands back and never does a server-to-server
  exchange; only `APPLE_CLIENT_ID` (the Services ID) matters.

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
