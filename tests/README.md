# Testing Guide

This directory contains automated tests for the Minecraft Server project.

## Test Structure

```
tests/
├── unit/           # Unit tests for individual scripts
├── integration/    # Integration tests
├── api/            # API endpoint tests
├── e2e/            # End-to-end tests for complete workflows
├── helpers/        # Test utilities and helpers
│   ├── test-utils.sh    # Common test functions
│   ├── mock-server.sh   # Mock server for testing
│   ├── bats-support/    # BATS support library
│   └── bats-assert/     # BATS assertion library
└── fixtures/       # Test data and fixtures
```

## Running Tests

### Run All Tests

```bash
./scripts/run-tests.sh
```

### Run Specific Test Suite

```bash
# Unit tests only
./scripts/run-tests.sh unit

# Integration tests only
./scripts/run-tests.sh integration

# API tests only
./scripts/run-tests.sh api

# E2E tests only
./scripts/run-tests.sh e2e
```

### Run Individual Test

```bash
# Bash test
bash tests/unit/test-manage.sh

# Python test
python3 -m pytest tests/api/test_api.py
```

## Test Requirements

### Bash Tests

- `bats` (Bash Automated Testing System) - for bash script tests
- Standard bash utilities

### Python Tests

- `pytest` - Python testing framework
- `requests` - For API testing

Install dependencies:

```bash
./scripts/run-tests.sh install-deps
```

## Writing Tests

### Bash Script Tests

Create test file: `tests/unit/test-<script-name>.sh`

```bash
#!/usr/bin/env bats

load 'helpers/bats-support/load'
load 'helpers/bats-assert/load'

@test "script does something" {
    run ./scripts/script.sh command
    assert_success
    assert_output --partial "expected output"
}
```

### End-to-End Tests

Create E2E test file: `tests/e2e/test-<workflow>.sh`

```bash
#!/usr/bin/env bats

load 'helpers/bats-support/load'
load 'helpers/bats-assert/load'
load 'helpers/test-utils.sh'

@test "complete workflow test" {
    # Test complete workflow
    run some_command
    assert_success
}
```

### Python Tests

Create test file: `tests/api/test_<module>.py`

```python
import pytest
from api.server import app

def test_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
```

## Test Utilities

### test-utils.sh

Common test functions:

- `create_test_dir()` - Create temporary test directory
- `wait_for_server()` - Wait for server to be ready
- `create_test_backup()` - Create test backup file
- `api_request()` - Make authenticated API request
- `assert_file_exists()` - Assert file exists
- `assert_file_contains()` - Assert file contains text

### mock-server.sh

Mock Minecraft server for testing:

- `start_mock_server` - Start mock server
- `stop_mock_server` - Stop mock server
- `status_mock_server` - Check server status

Usage:

```bash
source tests/helpers/mock-server.sh
start_mock_server
# Run tests
stop_mock_server
```

## CI/CD Integration

Tests run automatically on:

- Pull requests
- Pushes to main branch
- Manual workflow dispatch

See `.github/workflows/tests.yml` for configuration.

## Test Coverage

Run tests with coverage:

```bash
# Python tests with coverage
pytest tests/api/ --cov=api --cov-report=html

# View coverage report
open htmlcov/index.html

# Web UI tests with coverage
cd web
npm run test:coverage

# Check coverage threshold
./scripts/check-coverage.sh check
```

## Current Coverage Status

- **API Tests**: ~65% coverage
- **Web UI Component Tests**: ~50% coverage
- **E2E Workflows**: ~40% coverage
- **Overall Coverage**: ~65%+ (target: 70%)

See [TEST_COVERAGE.md](../docs/TEST_COVERAGE.md) for detailed coverage information.
