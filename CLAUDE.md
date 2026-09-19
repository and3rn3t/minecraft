# CLAUDE.md — Claude Code Project Instructions

**Read `AGENTS.md` first — it is the single source of truth for stack, commands, code
style, testing, and conventions.** This file only holds Claude-specific additions;
don't duplicate AGENTS.md content here.

## Claude-specific notes

- Don't commit, push, or deploy unless explicitly asked.
- This repo uses **npm**, not pnpm. Web commands run from `web/`; Python tests run
  from `tests/api/`.
- Use `docker compose` (with a space) — never `docker-compose`.
- Run `make ci` before declaring a change done — it reproduces the CI jobs
  (lint, gitleaks, actionlint, tests, CodeQL) locally. `make doctor` says which
  supporting tools are missing.
- Most runtime state (`data/`, `backups/`, `config/*.conf`) is gitignored and lives
  only on the Raspberry Pi — don't assume those paths exist locally.
