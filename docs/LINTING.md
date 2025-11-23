# Code Linting Guide

This document provides information about the static code analysis and linting setup for the Minecraft Server project.

## Overview

The project uses multiple linting tools to ensure code quality across different languages:

- **ShellCheck** - For bash script linting
- **ESLint** - For JavaScript/React code
- **flake8** - For Python code (optional)
- **pylint** - For Python code analysis (optional)
- **yamllint** - For YAML file validation (optional)

## Quick Start

### Run All Linting Checks

```bash
# Using the linting script
./scripts/lint.sh all

# Or using Make
make lint
```

### Run Specific Linting Checks

```bash
# Bash scripts only
./scripts/lint.sh bash
make lint-bash

# Python code only
./scripts/lint.sh python
make lint-python

# JavaScript/React only
./scripts/lint.sh js
make lint-js

# YAML files only
./scripts/lint.sh yaml
make lint-yaml

# Docker Compose validation
./scripts/lint.sh docker
make lint-docker
```

## Installation

### ShellCheck

**Linux (Debian/Ubuntu):**

```bash
sudo apt-get update
sudo apt-get install -y shellcheck
```

**macOS:**

```bash
brew install shellcheck
```

**Windows (WSL/Git Bash):**

```bash
# Use apt-get in WSL or install via Chocolatey
choco install shellcheck
```

**Verify installation:**

```bash
shellcheck --version
```

### ESLint (Frontend)

ESLint is already configured for the React frontend. Install dependencies:

```bash
cd web
npm install
```

ESLint will run automatically with:

```bash
npm run lint
```

### Python Linters (Optional)

```bash
pip install flake8 pylint
```

### YAML Linter (Optional)

```bash
pip install yamllint
```

## Configuration Files

### ShellCheck Configuration

The project uses `.shellcheckrc` in the root directory:

```bash
# Enable all checks
enable=all

# Disable specific warnings if needed
# disable=SC2034,SC2086
```

### ESLint Configuration

ESLint is configured in `web/.eslintrc.cjs`:

```javascript
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  // ... additional configuration
};
```

## Linting Script

The main linting script is located at `scripts/lint.sh`. It provides:

- **Automatic tool detection** - Checks if linting tools are installed
- **Comprehensive reporting** - Shows issues with file locations
- **Exit codes** - Returns non-zero on failures for CI/CD
- **Color-coded output** - Easy to read results

### Usage

```bash
./scripts/lint.sh [type]

# Types:
#   all      - Run all linting checks (default)
#   bash     - Lint bash scripts only
#   python   - Lint Python code only
#   js       - Lint JavaScript/React only
#   yaml     - Lint YAML files only
#   docker   - Validate Docker Compose only
```

## CI/CD Integration

Linting runs automatically in GitHub Actions on:

- Pull requests
- Pushes to main/develop branches
- Manual workflow dispatch

See `.github/workflows/tests.yml` for the linting job configuration.

## Common Issues and Solutions

### ShellCheck Issues

**SC2086: Double quote to prevent globbing and word splitting**

```bash
# Bad
rm $file

# Good
rm "$file"
```

**SC2034: Variable appears unused**

```bash
# Suppress warning if variable is intentionally unused
# shellcheck disable=SC2034
UNUSED_VAR="value"
```

**SC1091: Not following source**

```bash
# If sourcing external files, disable the check
# shellcheck source=/dev/null
source external-script.sh
```

### ESLint Issues

**React Hooks exhaustive-deps warning**

```javascript
// Add missing dependencies to useEffect
useEffect(() => {
  // ...
}, [dependency1, dependency2]); // Add all dependencies
```

**Unused variables**

```javascript
// Prefix with underscore if intentionally unused
const _unusedVar = value;
```

### Python Linting Issues

**Line too long (E501)**

```python
# Break long lines or configure max-line-length
# flake8 --max-line-length=120
```

**Too many arguments (R0913)**

```python
# Consider refactoring into a configuration object
def function(config):
    # Use config.arg1, config.arg2, etc.
    pass
```

## Best Practices

### Bash Scripts

1. **Always quote variables**: `"$VAR"` not `$VAR`
2. **Use `set -e`**: Exit on error
3. **Check command existence**: `command -v cmd || { echo "Error"; exit 1; }`
4. **Use local variables**: `local var="value"`
5. **Handle errors**: Use `||` and `&&` appropriately

### JavaScript/React

1. **Follow React hooks rules**: Only call hooks at the top level
2. **Use meaningful variable names**: Avoid abbreviations
3. **Remove unused imports**: Keep imports clean
4. **Handle errors**: Use try/catch for async operations
5. **Use TypeScript types** (if available): Better type safety

### Python

1. **Follow PEP 8**: Python style guide
2. **Use type hints**: Better code documentation
3. **Keep functions small**: Single responsibility
4. **Document complex logic**: Add docstrings
5. **Handle exceptions**: Use specific exception types

## Disabling Linting (When Necessary)

### ShellCheck

```bash
# Disable for a specific line
# shellcheck disable=SC2034
UNUSED_VAR="value"

# Disable for a block
# shellcheck disable=SC2086
command $unquoted_vars
# shellcheck enable=SC2086
```

### ESLint

```javascript
// Disable for a line
// eslint-disable-next-line no-console
console.log('Debug message');

// Disable for a block
/* eslint-disable react-hooks/exhaustive-deps */
useEffect(() => {
  // ...
}, []);
/* eslint-enable react-hooks/exhaustive-deps */
```

### Python (flake8)

```python
# Disable for a line
long_line = "..."  # noqa: E501

# Disable for a block
# flake8: noqa
def function_with_many_issues():
    # ...
    pass
```

## Integration with Editors

### VS Code

Install extensions:

- **ShellCheck** - For bash linting
- **ESLint** - For JavaScript/React
- **Python** - For Python linting
- **YAML** - For YAML validation

### Cursor

The project includes Cursor configuration in `docs/CURSOR_CONFIGURATION.md` with linting setup.

## Continuous Improvement

### Adding New Linting Rules

1. Update configuration files (`.shellcheckrc`, `.eslintrc.cjs`, etc.)
2. Test locally with `./scripts/lint.sh`
3. Update CI/CD workflow if needed
4. Document new rules in this guide

### Fixing Issues

1. Run linting: `./scripts/lint.sh all`
2. Fix issues one by one
3. Test that fixes don't break functionality
4. Commit fixes with clear messages

## Resources

- [ShellCheck Documentation](https://github.com/koalaman/shellcheck/wiki)
- [ESLint Documentation](https://eslint.org/docs/latest/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [pylint Documentation](https://pylint.pycqa.org/)
- [yamllint Documentation](https://yamllint.readthedocs.io/)

## See Also

- [Development Guide](DEVELOPMENT.md) - Development workflow
- [Testing Guide](TESTING.md) - Testing framework
- [Contributing Guide](../CONTRIBUTING.md) - Contribution guidelines
- [Code Quality Standards](../AGENT_INSTRUCTIONS.md) - Code standards
