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

✅ **60+ API tests passing** (including new feature tests)

- Health endpoint tests: ✅
- Authentication tests: ✅
- Server control tests: ✅
- Backup endpoint tests: ✅
- Logs endpoint tests: ✅
- Error handling tests: ✅
- Configuration file management tests: ✅ (NEW)
- Backup restore/delete tests: ✅ (NEW)
- User authentication tests: ✅ (NEW)
- OAuth integration tests: ✅ (NEW)

**Code Coverage**: ~60%+ (increased with new tests)

**Frontend Tests**: ~30+ React component tests

- ConfigEditor component tests: ✅ (NEW)
- OAuthButtons component tests: ✅ (NEW)
- AuthContext tests: ✅ (NEW)
- Login/Register page tests: ✅ (NEW)
- ConfigFiles page tests: ✅ (NEW)

## Test Structure

```text
tests/
├── api/                          # API endpoint tests
│   ├── test_api.py              # Main API test suite
│   ├── test_config_files.py     # Config file management tests (NEW)
│   ├── test_auth.py             # User authentication tests (NEW)
│   ├── test_backup_management.py # Backup restore/delete tests (NEW)
│   ├── test_oauth.py            # OAuth integration tests (NEW)
│   ├── conftest.py              # Pytest configuration and fixtures
│   └── pytest.ini               # Pytest settings
├── unit/                         # Unit tests for scripts
│   ├── test-manage.sh
│   ├── test-backup-scheduler.sh
│   └── test-log-manager.sh
├── integration/                  # Integration tests
│   ├── test-backup-system.sh
│   ├── test-monitoring.sh
│   ├── test-plugin-management.sh
│   ├── test-world-management.sh
│   └── test-rcon.sh
└── helpers/                      # Test helper libraries
    ├── bats-support/
    └── bats-assert/

web/src/
├── components/__tests__/         # React component tests
│   ├── ConfigEditor.test.jsx    # ConfigEditor tests (NEW)
│   ├── OAuthButtons.test.jsx    # OAuthButtons tests (NEW)
│   └── ...
├── contexts/__tests__/           # Context tests
│   └── AuthContext.test.jsx     # AuthContext tests (NEW)
├── pages/__tests__/              # Page component tests
│   ├── Login.test.jsx           # Login page tests (NEW)
│   ├── Register.test.jsx        # Register page tests (NEW)
│   ├── ConfigFiles.test.jsx     # ConfigFiles page tests (NEW)
│   └── ...
└── services/__tests__/           # Service tests
    └── api.test.js              # API service tests (updated)
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

**Example - Config Files:**

```python
import pytest
import json
from api.server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_list_config_files(client, mock_api_keys):
    response = client.get(
        '/api/config/files',
        headers={'X-API-Key': mock_api_keys}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'files' in data
```

**Example - Authentication:**

```python
def test_register_user(client, temp_users_file, mock_bcrypt):
    response = client.post('/api/auth/register', json={
        'username': 'newuser',
        'password': 'password123',
        'email': 'test@example.com'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
```

### React Component Tests

Create a new test file: `web/src/components/__tests__/<Component>.test.jsx`

**Example:**

```javascript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfigEditor from '../ConfigEditor';

describe('ConfigEditor', () => {
  it('renders filename', () => {
    render(<ConfigEditor filename="test.properties" content="" />);
    expect(screen.getByText('test.properties')).toBeInTheDocument();
  });
});
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
- **Current**: ~60%+ coverage (increased from 51%)
- **Priority**: Critical paths first
- **Focus**: Authentication, error handling, core endpoints, configuration management

### New Test Coverage (This Session)

**Backend API Tests:**

- Configuration file management endpoints (list, get, save, validate)
- Backup restore and delete endpoints
- User authentication endpoints (register, login, logout, me)
- OAuth endpoints (get URL, link, unlink)

**Frontend Component Tests:**

- ConfigEditor component (rendering, editing, saving, error handling)
- OAuthButtons component (Google/Apple buttons, popup handling, callbacks)
- AuthContext (authentication state, login, register, logout)
- Login page (form rendering, validation, error handling)
- Register page (form rendering, password validation, error handling)
- ConfigFiles page (file list, loading, error handling)

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

## Testing Framework Enhancements

The testing framework includes several enhancements to improve test quality, coverage, and developer experience.

### Test Data Factories

**Location**: `tests/api/factories.py`

Reusable factories for creating test data:

- `generate_api_key()` - Generate random API keys
- `create_user_data()` - Create test user data
- `create_api_key_data()` - Create test API key data
- `create_backup_metadata()` - Create backup metadata
- `create_server_properties()` - Generate server.properties content
- `create_whitelist_entry()` - Create whitelist entries
- `create_ban_entry()` - Create ban entries
- `create_world_data()` - Create world data
- `create_plugin_data()` - Create plugin data

**Usage**:

```python
from tests.api.factories import create_user_data, create_api_key_data

user = create_user_data(username="testuser", role="admin")
api_key = create_api_key_data(name="test-key")
```

### Enhanced Test Fixtures

**Location**: `tests/api/conftest.py`

Additional fixtures for better test isolation:

- `test_user_data` - Factory-generated user data
- `test_api_key_data` - Factory-generated API key data
- `test_backup_metadata` - Factory-generated backup metadata
- `test_server_properties` - Server.properties content
- `test_data_dir` - Temporary data directory with subdirectories
- `test_backup_dir` - Temporary backup directory
- `mock_docker` - Mock Docker operations
- `mock_file_system` - Mock file system operations
- `mock_network` - Mock network operations
- `isolated_test_env` - Isolated test environment with directories

### Test Parallelization

Tests can run in parallel using `pytest-xdist`:

```bash
# Run tests in parallel (auto-detects CPU count)
pytest -n auto

# Or specify number of workers
pytest -n 4
```

### Performance Testing Utilities

**Location**: `tests/api/performance_utils.py`

Utilities for performance and load testing:

- `PerformanceTimer` - Context manager for timing operations
- `measure_execution_time()` - Measure function execution time
- `run_load_test()` - Run load tests with threading
- `print_performance_report()` - Format and print performance results
- `benchmark_endpoint()` - Benchmark API endpoints

**Usage**:

```python
from tests.api.performance_utils import PerformanceTimer, run_load_test

# Time a single operation
with PerformanceTimer("Operation") as timer:
    do_something()
print(f"Duration: {timer.get_duration()}s")

# Load test
results = run_load_test(my_function, num_requests=100, num_threads=10)
print_performance_report(results)
```

### API Contract Testing

**Location**: `tests/api/contract_test_utils.py`

Utilities for validating API contracts against OpenAPI schema:

- `load_openapi_schema()` - Load OpenAPI schema from file
- `validate_response_schema()` - Validate API response against schema
- `validate_request_schema()` - Validate API request against schema
- `get_endpoint_schema()` - Get schema definition for endpoint

**Usage**:

```python
from tests.api.contract_test_utils import validate_response_schema

response = client.get('/api/health')
data = json.loads(response.data)
is_valid, error = validate_response_schema(data, '/api/health', 'GET', 200)
assert is_valid
```

### Coverage Gap Analysis

**Location**: `scripts/analyze-coverage-gaps.sh`

Tool to identify untested code paths:

```bash
# Analyze coverage gaps
./scripts/analyze-coverage-gaps.sh analyze

# Show detailed gaps
./scripts/analyze-coverage-gaps.sh detailed

# Get improvement suggestions
./scripts/analyze-coverage-gaps.sh suggest
```

### Enhanced Test Markers

Tests can be organized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.contract` - Contract tests
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.e2e` - End-to-end tests

**Run specific test types**:

```bash
# Run only performance tests
pytest -m performance

# Run only contract tests
pytest -m contract

# Skip slow tests
pytest -m "not slow"
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [BATS Documentation](https://bats-core.readthedocs.io/)
- [Test Coverage Guide](TEST_COVERAGE.md) - Detailed coverage analysis
- [Web UI Testing Guide](WEB_UI_TESTING.md) - Frontend testing guide
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [JSON Schema Validation](https://python-jsonschema.readthedocs.io/)

---

For questions or issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue.
