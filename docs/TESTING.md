# Testing Guide

This document provides comprehensive information about the automated testing framework for the Minecraft Server project.

## Quick Start

### Install Dependencies

```bash
# Install Python test dependencies
pip install -r api/requirements.txt
pip install pytest pytest-cov requests

# For bash tests (Linux/macOS/WSL)
# Install BATS: https://github.com/bats-core/bats-core
```

### Run Tests

```bash
# Run all API tests
python -m pytest tests/api/ -v

# Run with coverage
python -m pytest tests/api/ -v --cov=api --cov-report=term-missing

# Run specific test
python -m pytest tests/api/test_api.py::TestHealthEndpoint -v
```

## Test Results

### Current Status

✅ **18/18 API tests passing**

- Health endpoint tests: ✅
- Authentication tests: ✅
- Server control tests: ✅
- Backup endpoint tests: ✅
- Logs endpoint tests: ✅
- Error handling tests: ✅

**Code Coverage**: 51% (215 statements, 106 covered)

## Test Structure

```text
tests/
├── api/                    # API endpoint tests
│   ├── test_api.py        # Main API test suite
│   ├── conftest.py        # Pytest configuration and fixtures
│   └── pytest.ini         # Pytest settings
├── unit/                   # Unit tests for scripts
│   ├── test-manage.sh
│   ├── test-backup-scheduler.sh
│   └── test-log-manager.sh
├── integration/           # Integration tests
│   ├── test-backup-system.sh
│   ├── test-monitoring.sh
│   ├── test-plugin-management.sh
│   ├── test-world-management.sh
│   └── test-rcon.sh
└── helpers/               # Test helper libraries
    ├── bats-support/
    └── bats-assert/
```

## Test Types

### 1. API Tests (Python/pytest)

**Location**: `tests/api/test_api.py`

**Coverage**:

- Health check endpoint (no auth required)
- All authenticated endpoints
- Error handling
- CORS headers

**Run**:

```bash
python -m pytest tests/api/ -v
```

### 2. Unit Tests (Bash/BATS)

**Location**: `tests/unit/`

**Coverage**:

- Management scripts
- Backup scheduler
- Log manager

**Run** (requires BATS):

```bash
bats tests/unit/test-manage.sh
```

### 3. Integration Tests (Bash/BATS)

**Location**: `tests/integration/`

**Coverage**:

- Backup system
- Monitoring system
- Plugin management
- World management
- RCON integration

**Run** (requires BATS and Docker):

```bash
bats tests/integration/test-backup-system.sh
```

## Writing Tests

### Python API Tests

Create a new test file: `tests/api/test_<feature>.py`

```python
import pytest
from api.server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_endpoint(client):
    response = client.get('/api/endpoint')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'key' in data
```

### Bash Script Tests

Create a new test file: `tests/unit/test-<script>.sh`

```bash
#!/usr/bin/env bats

@test "script does something" {
    run ./scripts/script.sh command
    [ "$status" -eq 0 ]
    [ "$output" = "expected" ]
}
```

## CI/CD Integration

Tests run automatically on GitHub Actions:

- **On Push**: Runs all tests on main/develop branches
- **On PR**: Runs tests and linting
- **Manual**: Can be triggered via workflow_dispatch

See `.github/workflows/tests.yml` for configuration.

## Test Coverage

### Current Coverage

- **API Endpoints**: 51% coverage
- **Authentication**: ✅ Fully tested
- **Error Handling**: ✅ Fully tested
- **Health Checks**: ✅ Fully tested

### Coverage Goals

- **Target**: 80%+ coverage for API
- **Priority**: Critical paths first
- **Focus**: Authentication, error handling, core endpoints

### Viewing Coverage

```bash
# Terminal report
python -m pytest tests/api/ --cov=api --cov-report=term-missing

# HTML report
python -m pytest tests/api/ --cov=api --cov-report=html
open htmlcov/index.html
```

## Continuous Improvement

### Adding New Tests

1. **For New Features**: Add tests alongside feature development
2. **For Bug Fixes**: Add regression test first
3. **For Refactoring**: Ensure existing tests pass

### Test Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should describe what they test
3. **Coverage**: Aim for high coverage of critical paths
4. **Speed**: Keep tests fast (< 1 second per test)
5. **Maintainability**: Keep tests simple and readable

## Troubleshooting

### Tests Fail Locally

1. **Check Dependencies**:

   ```bash
   pip install -r api/requirements.txt
   pip install pytest pytest-cov requests
   ```

2. **Check Python Version**: Requires Python 3.9+

3. **Check Path**: Ensure you're in project root

### BATS Tests Not Running

1. **Install BATS**: See installation guide above
2. **Check Permissions**: `chmod +x tests/**/*.sh`
3. **Check Dependencies**: Some tests require Docker

### Coverage Not Showing

1. **Install Coverage**: `pip install pytest-cov`
2. **Check Report**: Use `--cov-report=term-missing`
3. **Verify Path**: Coverage path should match source

## Next Steps

1. ✅ **API Tests**: Complete (18/18 passing)
2. 🔄 **Unit Tests**: Framework ready, add more tests
3. 🔄 **Integration Tests**: Framework ready, add more tests
4. 📊 **Coverage**: Increase to 80%+
5. 🚀 **CI/CD**: Fully integrated with GitHub Actions

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [BATS Documentation](https://bats-core.readthedocs.io/)
- [Test Coverage Guide](https://coverage.readthedocs.io/)

---

For questions or issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue.
