# Testing Framework Enhancements

This document describes the comprehensive enhancements made to the testing framework.

## Overview

The testing framework has been significantly enhanced with new utilities, tools, and capabilities to improve test quality, coverage, and developer experience.

## New Features

### 1. Test Data Factories

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

### 2. Enhanced Test Fixtures

**Location**: `tests/api/conftest.py`

New fixtures added:

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

**Usage**:

```python
def test_something(test_user_data, test_data_dir, mock_docker):
    # Use fixtures in tests
    user = test_user_data
    data_path = test_data_dir / "world"
```

### 3. Test Parallelization

**Configuration**: `tests/api/pytest.ini`

Tests can now run in parallel using `pytest-xdist`:

```bash
# Run tests in parallel (auto-detects CPU count)
pytest -n auto

# Or specify number of workers
pytest -n 4
```

**Makefile command**:

```bash
make test-api-parallel
```

### 4. Enhanced Test Reporting

**Configuration**: `tests/api/pytest.ini`

Multiple report formats now available:

- **Terminal**: `--cov-report=term-missing` (default)
- **HTML**: `--cov-report=html:htmlcov`
- **JSON**: `--cov-report=json:coverage.json`
- **XML**: `--cov-report=xml:coverage.xml` (for CI/CD)
- **JUnit**: Built-in JUnit XML support

Reports are automatically generated when running tests with coverage.

### 5. Performance Testing Utilities

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

**Example Test**:

```python
@pytest.mark.performance
def test_endpoint_performance(client):
    results = benchmark_endpoint(
        client, 'GET', '/api/health',
        num_requests=100, num_threads=10
    )
    assert results['avg_duration'] < 0.1
```

### 6. API Contract Testing

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

**Example Test**:

```python
@pytest.mark.contract
def test_endpoint_contract(client):
    response = client.get('/api/health')
    data = json.loads(response.data)
    is_valid, error = validate_response_schema(data, '/api/health', 'GET', 200)
    assert is_valid, error
```

### 7. Coverage Gap Analysis

**Location**: `scripts/analyze-coverage-gaps.sh`

Tool to identify untested code paths and suggest improvements:

```bash
# Analyze coverage gaps
./scripts/analyze-coverage-gaps.sh analyze

# Show detailed gaps
./scripts/analyze-coverage-gaps.sh detailed

# Get improvement suggestions
./scripts/analyze-coverage-gaps.sh suggest
```

**Makefile commands**:

```bash
make coverage-gaps
make coverage-gaps-detailed
make coverage-suggestions
```

The tool:

- Identifies files with coverage < 80%
- Shows missing line numbers
- Suggests test improvements
- Generates detailed reports

### 8. Enhanced Test Isolation

**Location**: `tests/api/conftest.py`

Improved test isolation with:

- Automatic cleanup via `tmp_path` fixture
- Isolated test environments with `isolated_test_env` fixture
- Mock fixtures that don't interfere with each other
- Better teardown between tests

## New Test Files

### Performance Tests

**Location**: `tests/api/test_performance.py`

Performance tests for API endpoints:

- Health endpoint performance
- Load testing
- Response time validation
- Throughput measurement

Run with:

```bash
pytest -m performance
# or
make test-api-performance
```

### Contract Tests

**Location**: `tests/api/test_contract.py`

API contract validation tests:

- Response schema validation
- Request schema validation
- OpenAPI compliance

Run with:

```bash
pytest -m contract
# or
make test-api-contract
```

### Factory Tests

**Location**: `tests/api/test_factories.py`

Tests for test data factories to ensure they work correctly.

## Updated Configuration

### pytest.ini

Enhanced with:

- Multiple coverage report formats
- New test markers (performance, contract, e2e)
- Better error reporting

### Makefile

New commands:

- `make test-api-parallel` - Run tests in parallel
- `make test-api-performance` - Run performance tests
- `make test-api-contract` - Run contract tests
- `make test-factories` - Test factory utilities
- `make coverage-gaps` - Analyze coverage gaps
- `make coverage-gaps-detailed` - Detailed gap analysis
- `make coverage-suggestions` - Get improvement suggestions

### Test Requirements

**Location**: `api/requirements-test.txt`

New testing dependencies:

- `pytest-xdist` - Parallel test execution
- `pytest-mock` - Enhanced mocking
- `pytest-timeout` - Test timeout support
- `jsonschema` - Schema validation
- `pyyaml` - YAML parsing for OpenAPI

Install with:

```bash
pip install -r api/requirements-test.txt
```

## Usage Examples

### Running Tests with New Features

```bash
# Run all tests with parallel execution
make test-api-parallel

# Run performance tests
make test-api-performance

# Run contract tests
make test-api-contract

# Analyze coverage gaps
make coverage-gaps

# Generate all coverage reports
make coverage
```

### Writing Tests with New Utilities

```python
import pytest
from tests.api.factories import create_user_data
from tests.api.performance_utils import PerformanceTimer

@pytest.mark.performance
def test_user_creation_performance(client, test_user_data):
    with PerformanceTimer("User creation") as timer:
        response = client.post('/api/auth/register', json=test_user_data)
        assert response.status_code == 200
    assert timer.get_duration() < 0.5
```

## Benefits

1. **Faster Test Execution**: Parallel execution reduces test time
2. **Better Coverage Analysis**: Gap analysis identifies untested code
3. **Performance Monitoring**: Built-in performance testing utilities
4. **API Contract Validation**: Ensures API compliance with OpenAPI
5. **Reusable Test Data**: Factories reduce test setup code
6. **Better Reporting**: Multiple report formats for different needs
7. **Improved Isolation**: Better test isolation prevents interference

## Migration Guide

### Existing Tests

No changes required for existing tests. New utilities are optional.

### New Tests

Use new utilities for:

- Creating test data (use factories)
- Performance testing (use performance utilities)
- Contract validation (use contract utilities)
- Load testing (use load test functions)

## Future Enhancements

Potential future improvements:

1. **Mutation Testing**: Add mutation testing for test quality
2. **Visual Regression**: Enhanced visual regression testing
3. **API Fuzzing**: Automated API fuzzing tests
4. **Database Testing**: Database-specific test utilities
5. **Integration Test Helpers**: More integration test utilities

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [JSON Schema Validation](https://python-jsonschema.readthedocs.io/)
