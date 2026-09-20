# Minecraft Server Management Makefile
# Provides convenient commands for server management

# Prefer the Docker Compose v2 plugin, fall back to the legacy v1 binary
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

.PHONY: help start stop restart status logs backup console update install clean test lint lint-bash lint-python lint-js lint-yaml lint-docker coverage coverage-check coverage-report benchmark build-multiarch ci hooks pre-commit secrets actionlint codeql doctor shell-syntax bash-tests

# Default target
help:
	@echo "Minecraft Server Management Commands:"
	@echo ""
	@echo "  make install     - Install dependencies and setup"
	@echo "  make start       - Start the server"
	@echo "  make stop        - Stop the server"
	@echo "  make restart     - Restart the server"
	@echo "  make status      - Check server status"
	@echo "  make logs        - View server logs"
	@echo "  make backup      - Create a backup"
	@echo "  make console     - Attach to server console"
	@echo "  make update      - Update server configuration"
	@echo "  make clean       - Clean up Docker resources"
	@echo "  make test        - Run all tests"
	@echo "  make test-api    - Run API tests only"
	@echo "  make test-web    - Run web UI tests only"
	@echo "  make test-web-a11y - Run accessibility tests"
	@echo "  make test-playwright - Run browser tests"
	@echo "  make test-e2e    - Run E2E tests"
	@echo "  make lint        - Run all linting checks"
	@echo "  make lint-bash   - Lint bash scripts"
	@echo "  make lint-python - Lint Python code"
	@echo "  make lint-js     - Lint JavaScript/React"
	@echo "  make coverage   - Run tests with coverage report"
	@echo "  make coverage-check - Check coverage threshold"
	@echo "  make benchmark  - Run performance benchmarks"
	@echo "  make build       - Build Docker image"
	@echo "  make build-multiarch - Build for multiple architectures"
	@echo "  make shell       - Open shell in container"
	@echo ""
	@echo "Checks that mirror CI:"
	@echo ""
	@echo "  make ci          - Run everything CI runs, before you push"
	@echo "  make hooks       - Install the pre-commit hooks"
	@echo "  make pre-commit  - Run the pre-commit hooks, as the CI job runs them"
	@echo "  make secrets     - Scan for secrets (same as the Gitleaks workflow)"
	@echo "  make actionlint  - Lint the GitHub Actions workflows"
	@echo "  make codeql      - CodeQL, same query suite as the CodeQL workflow"
	@echo "  make shell-syntax - Syntax-check every shell script, as CI does"
	@echo "  make bash-tests  - BATS suite, as CI runs it"
	@echo "  make doctor      - Report which of these tools are installed"
	@echo ""

# Installation
install:
	@echo "Installing dependencies..."
	@chmod +x scripts/setup-rpi.sh scripts/manage.sh scripts/start.sh
	@./scripts/setup-rpi.sh

# Server management
start:
	@./scripts/manage.sh start

stop:
	@./scripts/manage.sh stop

restart:
	@./scripts/manage.sh restart

status:
	@./scripts/manage.sh status

logs:
	@./scripts/manage.sh logs

backup:
	@./scripts/manage.sh backup

console:
	@./scripts/manage.sh console

update:
	@./scripts/manage.sh update

# Docker operations
build:
	@echo "Building Docker image..."
	@$(COMPOSE) build

clean:
	@echo "Cleaning up Docker resources..."
	@$(COMPOSE) down -v
	@docker system prune -f

shell:
	@docker exec -it minecraft-server /bin/bash

# Testing
test:
	@echo "Running all tests..."
	@bash -n scripts/manage.sh
	@bash -n scripts/start.sh
	@bash -n scripts/setup-rpi.sh
	@$(COMPOSE) config > /dev/null
	@cd tests/api && pytest -v --cov=../../api --cov-config=../../.coverage-config.ini --cov-report=term-missing
	@cd web && npm test
	@echo "All tests passed!"

test-api:
	@echo "Running API tests..."
	@cd tests/api && pytest -v

test-api-parallel:
	@echo "Running API tests in parallel..."
	@cd tests/api && pytest -v -n auto

test-api-performance:
	@echo "Running API performance tests..."
	@cd tests/api && pytest -v -m performance

test-api-contract:
	@echo "Running API contract tests..."
	@cd tests/api && pytest -v -m contract

test-web:
	@echo "Running web UI tests..."
	@cd web && npm test

test-web-a11y:
	@echo "Running accessibility tests..."
	@cd web && npm run test:a11y

test-playwright:
	@echo "Running Playwright browser tests..."
	@cd web && npm run test:playwright

test-e2e:
	@echo "Running E2E tests..."
	@bats tests/e2e/test-complete-user-journey.sh || echo "E2E tests require running server"
	@bats tests/e2e/test-web-ui-workflow.sh || echo "E2E tests require running server"
	@bats tests/e2e/test-analytics-workflow.sh || echo "E2E tests require running server"

test-factories:
	@echo "Running factory tests..."
	@cd tests/api && pytest -v test_factories.py

coverage-gaps:
	@echo "Analyzing coverage gaps..."
	@./scripts/analyze-coverage-gaps.sh analyze

coverage-gaps-detailed:
	@echo "Showing detailed coverage gaps..."
	@./scripts/analyze-coverage-gaps.sh detailed

coverage-suggestions:
	@echo "Getting test improvement suggestions..."
	@./scripts/analyze-coverage-gaps.sh suggest

# Linting
lint:
	@echo "Running all linting checks..."
	@./scripts/lint.sh all

lint-bash:
	@echo "Linting bash scripts..."
	@./scripts/lint.sh bash

lint-python:
	@echo "Linting Python code..."
	@./scripts/lint.sh python

lint-js:
	@echo "Linting JavaScript/React code..."
	@./scripts/lint.sh js

lint-yaml:
	@echo "Linting YAML files..."
	@./scripts/lint.sh yaml

lint-docker:
	@echo "Validating Docker Compose..."
	@./scripts/lint.sh docker

# Coverage
coverage:
	@echo "Running tests with coverage..."
	@cd tests/api && pytest -v --cov=../../api --cov-config=../../.coverage-config.ini --cov-report=term-missing --cov-report=html

coverage-check:
	@echo "Checking coverage threshold..."
	@./scripts/check-coverage.sh check

coverage-report:
	@echo "Generating coverage report..."
	@./scripts/check-coverage.sh report

# Benchmarking
benchmark:
	@echo "Running performance benchmarks..."
	@./scripts/benchmark.sh all

benchmark-baseline:
	@echo "Creating performance baseline..."
	@./scripts/benchmark.sh baseline

benchmark-compare:
	@echo "Comparing against baseline..."
	@./scripts/benchmark.sh compare

# Multi-architecture builds
build-multiarch:
	@echo "Building for multiple architectures..."
	@./scripts/build-multiarch.sh all

build-multiarch-setup:
	@echo "Setting up multi-architecture builder..."
	@./scripts/build-multiarch.sh setup

# Development
dev-start:
	@echo "Starting in development mode..."
	@$(COMPOSE) up

dev-stop:
	@echo "Stopping development mode..."
	@$(COMPOSE) down

# Backup management
backup-list:
	@ls -lh backups/ | tail -n +2

backup-clean:
	@echo "Cleaning old backups (keeping last 7 days)..."
	@find backups -name "minecraft_backup_*.tar.gz" -mtime +7 -delete
	@echo "Backup cleanup complete"

# System information
info:
	@echo "=== Server Information ==="
	@echo "Docker version:"
	@docker --version
	@echo ""
	@echo "Docker Compose version:"
	@$(COMPOSE) --version
	@echo ""
	@echo "System resources:"
	@free -h
	@echo ""
	@echo "Disk usage:"
	@df -h
	@echo ""
	@echo "Server status:"
	@./scripts/manage.sh status

# Quick setup
quick-setup: install
	@echo "Quick setup complete!"
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make start' to start the server"
	@echo "  3. Run 'make logs' to view server logs"
	@echo "  4. Run 'make perf-preset' to apply performance preset"

# Minecraft management
server-props:
	@./scripts/server-properties-manager.sh help

whitelist:
	@./scripts/whitelist-manager.sh help

ban:
	@./scripts/ban-manager.sh help

op:
	@./scripts/op-manager.sh help

jvm-optimize:
	@./scripts/jvm-optimizer.sh generate

perf-preset:
	@./scripts/performance-presets.sh help


# ---------------------------------------------------------------------------
# Local parity with CI
#
# Everything below reproduces a GitHub Actions job, so a failure shows up on
# this machine instead of three minutes into a pull request.
# ---------------------------------------------------------------------------

hooks:
	@echo "Installing pre-commit hooks..."
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "pre-commit is not installed. Install it with:"; \
		echo "  uv tool install pre-commit   (or pipx install pre-commit)"; \
		exit 1; \
	}
	@pre-commit install
	@echo "Hooks installed. Run 'make doctor' to see what else is missing."

# Same command the "Lint (pre-commit)" CI job runs. Covers ruff, shellcheck,
# yamllint, markdownlint, gitleaks, actionlint and the whitespace/EOF/compose
# checks — all versioned in .pre-commit-config.yaml, the one place they're
# declared, so this and the CI job cannot drift apart.
pre-commit:
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "pre-commit is not installed. Install it with:"; \
		echo "  uv tool install pre-commit   (or pipx install pre-commit)"; \
		exit 1; \
	}
	@pre-commit run --all-files

# Both scans are blocking. The twelve pre-existing findings are documentation
# placeholders, allowlisted individually in .gitleaks.toml and each scoped to
# the file it appears in, so a real credential in those same files still fails.
secrets:
	@echo "Scanning for secrets..."
	@command -v gitleaks >/dev/null 2>&1 || { \
		echo "gitleaks is not installed: brew install gitleaks"; exit 1; \
	}
	@echo "  working tree (includes files you have not committed yet):"
	@gitleaks detect --no-git --no-banner --redact
	@echo "  commits not yet on main (what the workflow scans):"
	@gitleaks detect --no-banner --redact --log-opts="origin/main..HEAD"

actionlint:
	@echo "Linting GitHub Actions workflows..."
	@command -v actionlint >/dev/null 2>&1 || { \
		echo "actionlint is not installed: brew install actionlint"; exit 1; \
	}
	@actionlint

# The workflow analyses Python with the security-and-quality suite, which is
# where the information-exposure, log-injection and assert-side-effect alerts
# come from. Matching the suite matters: the default one reports far less.
CODEQL_DB := .codeql-db

codeql:
	@command -v codeql >/dev/null 2>&1 || { \
		echo "codeql is not installed: brew install codeql"; \
		echo "(a large download; everything else in 'make ci' works without it)"; \
		exit 1; \
	}
	@codeql pack download codeql/python-queries >/dev/null
	@echo "Building CodeQL database (a minute or so)..."
	@rm -rf $(CODEQL_DB)
	@codeql database create $(CODEQL_DB) --language=python --source-root=. --overwrite >/dev/null 2>&1
	@echo "Analysing with python-security-and-quality..."
	@codeql database analyze $(CODEQL_DB) \
		codeql/python-queries:codeql-suites/python-security-and-quality.qls \
		--format=sarif-latest --output=codeql-results.sarif --sarif-add-snippets >/dev/null 2>&1
	@echo ""
	@python3 scripts/show-codeql-results.py codeql-results.sarif --changed-since origin/main

doctor:
	@echo "Tools that back the CI-parity targets:"
	@printf "  %-12s " "pre-commit"; command -v pre-commit >/dev/null 2>&1 && echo "installed" || echo "MISSING  (uv tool install pre-commit)"
	@printf "  %-12s " "ruff";       command -v ruff       >/dev/null 2>&1 && echo "installed" || echo "MISSING  (uv tool install ruff)"
	@printf "  %-12s " "gitleaks";   command -v gitleaks   >/dev/null 2>&1 && echo "installed" || echo "MISSING  (brew install gitleaks)"
	@printf "  %-12s " "actionlint"; command -v actionlint >/dev/null 2>&1 && echo "installed" || echo "MISSING  (brew install actionlint)"
	@printf "  %-12s " "shellcheck"; command -v shellcheck >/dev/null 2>&1 && echo "installed" || echo "MISSING  (brew install shellcheck)"
	@printf "  %-12s " "codeql";     command -v codeql     >/dev/null 2>&1 && echo "installed" || echo "MISSING  (brew install codeql)"
	@printf "  %-12s " "git hook";   test -f .git/hooks/pre-commit && echo "installed" || echo "MISSING  (make hooks)"

# `make test` syntax-checks three scripts by name; the workflow checks every
# shell file in scripts/ and tests/. This is that pass.
shell-syntax:
	@echo "Checking shell script syntax..."
	@find scripts tests -name "*.sh" -type f -print0 \
		| xargs -0 ./scripts/check-shell-syntax.sh
	@echo "All shell scripts parse."

# The workflow's bash-tests job. BATS is not always installed locally, and a
# missing test runner is a gap in the gate rather than a pass, so say so.
bash-tests:
	@command -v bats >/dev/null 2>&1 || { \
		echo "BATS is not installed, so the bash-tests job was not reproduced."; \
		echo "  brew install bats-core"; \
		exit 1; \
	}
	@./scripts/run-tests.sh bash

# The order is deliberate: the fast, cheap checks fail first.
#
# A tool that is missing fails this target rather than being skipped quietly.
# A gate that reports success while silently omitting a job is how the checks
# in this repo came to be trusted without running. Opt out deliberately with
# SKIP_CODEQL=1 or SKIP_BATS=1 if you need to.
ci:
	@echo "=== Running the checks CI runs ==="
	@$(MAKE) --no-print-directory pre-commit
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory shell-syntax
	@$(MAKE) --no-print-directory actionlint
	@$(MAKE) --no-print-directory secrets
	@$(MAKE) --no-print-directory test
	@if [ -n "$(SKIP_BATS)" ]; then \
		echo "Skipping the bash-tests job (SKIP_BATS set)."; \
	else \
		$(MAKE) --no-print-directory bash-tests; \
	fi
	@if [ -n "$(SKIP_CODEQL)" ]; then \
		echo "Skipping CodeQL (SKIP_CODEQL set)."; \
	else \
		$(MAKE) --no-print-directory codeql; \
	fi
	@echo ""
	@echo "All CI-parity checks passed."
