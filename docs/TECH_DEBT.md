# Technical Debt

Maintenance work that is not product planning: dependency pins, lint baselines and test gaps. Product work is in [ROADMAP.md](ROADMAP.md). The lint, CodeQL and shellcheck baselines are in [`../AGENTS.md`](../AGENTS.md#known-baselines).

Delete an entry when it is done and describe it in
[`../CHANGELOG.md`](../CHANGELOG.md), as the roadmap does.

- **Web UI pages for what already exists.** The API has endpoints with no page: events, announcements, gamerules once they land. Check `api/openapi.yaml` against `web/src/pages/` before adding anything new.
- **Test coverage gaps.** The weakest API modules are the `ddns`, `players` and `announcements` blueprints and `api/auth_crypto.py`; `make coverage` has the current numbers. Fifteen BATS suites cover the backup, restore, deploy, world and plugin scripts among others, but most of the rest of `scripts/` has no test that names it: `ddns-updater.sh`, `cloud-backup-s3.sh`, `cloud-backup-b2.sh`,
  `whitelist-manager.sh`, `op-manager.sh`, `health-check.sh` and the monitors.
  Close the gaps alongside the feature that touches them, not as a separate project.
- **`api/server.py` is still the biggest file, but no longer very large.** It went from 5,554 lines to 732 as the permission model, request authentication,
  config redaction, path checks, the WebSocket console, error reporting, the
  event-bus wiring and fourteen blueprints moved out. Each reads the shared state
  through `api.server` at call time, which is what lets a test patch it in one
  place. What is left is the app and its CORS and security-header setup, config
  and secret loading, user and API-key persistence, the script and RCON runners,
  the error handlers and the startup block. Keep doing what worked: new features
  get their own module, and a block of `server.py` follows when it is touched
  anyway, not as a project of its own.
- **Architecture diagrams.** One diagram of log → event bus → feature handlers →
  RCON would save more explaining than any amount of prose.
- **`eslint-plugin-react-hooks` 5 → 7.** Version 7 adds the React Compiler lint
  rules, so it is a triage, not a drop-in bump: turn them on, then decide per
  finding whether the code changes or the rule is switched off. React 19 is in
  and ESLint 9 is allowed, so nothing blocks it. Do it as its own change so the
  findings are not mixed with anything else.
- **ESLint 9 → 10, with `@eslint/js` 10.** Blocked: the newest
  `eslint-plugin-react` (7.37.5) only supports ESLint up to 9. Check its
  releases before starting. `eslint-plugin-react-refresh` 0.5 already allows both
  and can move whenever it is convenient.
- **`msw` 2 → 3.** Blocked: Vitest 5's mocker declares `msw ^2.4.9` as its peer,
  and `npm ci` rejects a lockfile that has msw 3 (it broke CI when the test
  tooling was last upgraded). Revisit when Vitest widens the range.
- **`jsdom` 29 → 30 and `globals` 16 → 17.** `globals` has no known blocker.
  `jsdom` 30 needs Node `^22.22.2` or `^24.15.0`, which is stricter than the
  `engines.node` in `web/package.json` (`^22.13.0 || ^24.0.0 || >=26.0.0`), so it
  also means raising that floor and checking the Node version CI runs.
- **One raw colour left in the web app: `#9C27B0`.** It is the audit log's colour
  for `user.*` actions (`getActionColor` in `AuditLogs.jsx`), and no theme token
  has it. Either add a token for it (the other four categories already use
  `minecraft-*` tokens) or reuse an existing one. The keyboard-focus yellow and
  the placeholder fallback in `index.css` are literals on purpose.
- **Run the BATS suite on Linux before pushing.** `make ci` reproduces CI on a
  Mac, but the shell tests run under macOS's bash 3.2 and BSD tools there and
  under bash 5 and GNU tools in CI. That has already bitten twice: a test of a
  corrupt archive passed locally and failed in CI because GNU `tar` lists a
  stream shorter than one 512-byte block as an empty archive, and on bash 3.2 a
  failing bare `[[ ]]` in the middle of a test does not fail it. A
  `make bash-tests-linux` that runs the suite in an Ubuntu container, the way
  `make test-visual` does for Playwright, would catch both before a push. The
  same gap exists for gitleaks: `make secrets` runs a newer version than the one
  CI pins (8.24.3), which ignores top-level `[[allowlists]]` blocks, so
  `docs/OAUTH_SETUP.md` is still reported on a full working-tree scan with that
  version.
