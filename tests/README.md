# Testing Guide

This directory contains automated tests for the Minecraft Server project.

## Test Structure

```
tests/
├── unit/           # Unit tests for individual scripts
├── integration/    # Integration tests
├── api/            # API endpoint tests
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

@test "script does something" {
    run ./scripts/script.sh command
    [ "$status" -eq 0 ]
    [ "$output" = "expected output" ]
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

## CI/CD Integration

Tests run automatically on:

- Pull requests
- Pushes to main branch
- Manual workflow dispatch

See `.github/workflows/tests.yml` for configuration.
