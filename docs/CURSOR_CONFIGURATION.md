# Cursor IDE Configuration Guide

This document explains the configuration files used by Cursor IDE (and VS Code) to enhance the development experience for this project.

## Overview

Cursor IDE uses various configuration files to provide:

- Code formatting and linting
- Debugging capabilities
- Task automation
- Extension recommendations
- Language-specific settings

## Configuration Files

### `.cursorrules`

**Purpose**: AI agent instructions for consistent development across sessions.

**Location**: Project root

**Usage**: Automatically loaded by Cursor IDE to guide AI assistants.

**See Also**: [AGENT_INSTRUCTIONS.md](../AGENT_INSTRUCTIONS.md)

---

### `.vscode/settings.json`

**Purpose**: Workspace-specific editor settings for Cursor/VS Code.

**Key Features**:

- Format on save enabled
- Language-specific formatters (Python: Black, JS: Prettier)
- Tab size and indentation settings
- File associations
- Exclude patterns for search/files
- Python linting and testing configuration
- Shell script linting (ShellCheck)

**Usage**: Automatically applied when opening the workspace.

---

### `.vscode/extensions.json`

**Purpose**: Recommends useful extensions for this project.

**Recommended Extensions**:

- **Python**: Python, Pylance, Black Formatter, Flake8
- **JavaScript/React**: ESLint, Prettier, Tailwind CSS IntelliSense
- **Shell**: ShellCheck, Bash IDE
- **Docker**: Docker extension
- **YAML**: YAML language support
- **Markdown**: Markdown tools
- **Git**: GitLens

**Usage**: Cursor/VS Code will prompt to install recommended extensions when opening the workspace.

---

### `.vscode/launch.json`

**Purpose**: Debug configurations for running and debugging code.

**Available Debug Configurations**:

1. **Python: Flask API Server** - Debug the Flask API server
2. **Python: Current File** - Debug the currently open Python file
3. **Python: Pytest** - Debug pytest test suite
4. **Python: Pytest Current File** - Debug tests in current file
5. **Debug React App** - Debug React application in Chrome
6. **Attach to Chrome** - Attach debugger to running Chrome instance

**Usage**: Press `F5` or use Debug panel to select and run configurations.

---

### `.vscode/tasks.json`

**Purpose**: Task definitions for common development tasks.

**Available Tasks**:

- **Shell: Syntax Check** - Check shell script syntax
- **Shell: Run Script** - Execute shell script
- **Python: Run Tests** - Run pytest test suite
- **Python: Run Tests with Coverage** - Run tests with coverage report
- **React: Run Tests** - Run Vitest tests
- **React: Lint** - Lint React code
- **Docker: Validate Compose** - Validate docker-compose.yml
- **Docker: Build** - Build Docker images
- **Make: Test** - Run make test
- **Make: Build** - Run make build

**Usage**: Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) → "Tasks: Run Task" → Select task.

---

### `.prettierrc.json`

**Purpose**: Prettier code formatter configuration for JavaScript/JSX/JSON/YAML.

**Settings**:

- Single quotes for JavaScript
- 100 character line width
- 2-space indentation
- Semicolons enabled
- LF line endings

**Usage**: Automatically used by Prettier extension when formatting files.

---

### `.eslintrc.json`

**Purpose**: ESLint configuration for JavaScript/React code quality.

**Rules**:

- React hooks rules enforced
- Unused variables warnings
- Console warnings (except warn/error)
- React prop-types warnings

**Usage**: Automatically used by ESLint extension for linting.

---

### `jsconfig.json`

**Purpose**: JavaScript project configuration for IntelliSense and path aliases.

**Features**:

- Path alias `@/*` → `./web/src/*`
- React JSX support
- ES2020 target
- Module resolution

**Usage**: Provides better autocomplete and path resolution in JavaScript files.

---

### `.shellcheckrc`

**Purpose**: ShellCheck configuration for shell script linting.

**Settings**:

- All checks enabled
- Customizable warning suppressions

**Usage**: Used by ShellCheck extension and pre-commit hooks.

---

### `pyproject.toml`

**Purpose**: Python project configuration for multiple tools.

**Tools Configured**:

- **Black**: Code formatter (120 char line length)
- **Pytest**: Test configuration
- **Coverage**: Coverage settings
- **Flake8**: Linter settings (120 char line length)
- **Mypy**: Type checker settings

**Usage**: Automatically used by Python tools when installed.

---

### `.editorconfig`

**Purpose**: Cross-editor configuration for consistent formatting.

**Settings**:

- LF line endings
- UTF-8 encoding
- Language-specific indentation (4 spaces for shell, 2 for YAML/JSON)

**Usage**: Supported by most modern editors including Cursor/VS Code.

---

### `.pre-commit-config.yaml`

**Purpose**: Pre-commit hooks for code quality checks.

**Hooks**:

- Trailing whitespace removal
- End of file fixes
- YAML/JSON validation
- ShellCheck linting
- Markdown linting
- Docker Compose validation
- Shell syntax checking

**Usage**: Install with `pip install pre-commit && pre-commit install`

---

## Ignore Files

### `.prettierignore`

Files and directories to exclude from Prettier formatting.

### `.eslintignore`

Files and directories to exclude from ESLint linting.

---

## Quick Reference

### Format Code

- **JavaScript/React**: `Shift+Alt+F` (or `Shift+Option+F` on Mac)
- **Python**: `Shift+Alt+F` (uses Black formatter)
- **All Files**: Format on save is enabled

### Run Tasks

1. `Ctrl+Shift+P` → "Tasks: Run Task"
2. Select task from list
3. Or use `Ctrl+Shift+B` for default build task

### Debug

1. Press `F5` to start debugging
2. Select configuration from dropdown
3. Set breakpoints by clicking left of line numbers

### Install Recommended Extensions

1. `Ctrl+Shift+X` to open Extensions panel
2. Look for "Recommended" section
3. Click "Install All" or install individually

---

## Customization

### Adding New Tasks

Edit `.vscode/tasks.json` and add new task definitions.

### Adding New Debug Configurations

Edit `.vscode/launch.json` and add new configuration objects.

### Changing Formatting Rules

- **JavaScript/React**: Edit `.prettierrc.json`
- **Python**: Edit `pyproject.toml` under `[tool.black]`
- **Shell**: Edit `.editorconfig` for indentation

### Changing Linting Rules

- **JavaScript/React**: Edit `.eslintrc.json`
- **Python**: Edit `pyproject.toml` under `[tool.flake8]`
- **Shell**: Edit `.shellcheckrc`

---

## Troubleshooting

### Formatting Not Working

1. Check if formatter extension is installed
2. Verify file type is recognized
3. Check `.prettierignore` or `.eslintignore` for exclusions

### Linting Not Working

1. Ensure ESLint/Pylint/ShellCheck extensions are installed
2. Check extension output for errors
3. Verify configuration files are valid JSON

### Debug Not Starting

1. Check if Python/Node.js is installed
2. Verify launch configuration paths
3. Check terminal output for errors

### Tasks Not Running

1. Verify task command exists in PATH
2. Check task working directory
3. Review task output in terminal

---

## Best Practices

1. **Keep Configurations in Sync**: Update related configs together (e.g., `.editorconfig` and formatter configs)

2. **Version Control**: Commit all configuration files to git (except user-specific settings)

3. **Team Consistency**: Use shared workspace settings (`.vscode/settings.json`) for team consistency

4. **Document Changes**: Update this document when adding new configurations

5. **Test Configurations**: Verify configurations work after changes

---

## Additional Resources

- [Cursor IDE Documentation](https://cursor.sh/docs)
- [VS Code Settings](https://code.visualstudio.com/docs/getstarted/settings)
- [Prettier Configuration](https://prettier.io/docs/en/configuration.html)
- [ESLint Configuration](https://eslint.org/docs/user-guide/configuring/)
- [Python Black Configuration](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html)
- [ShellCheck Documentation](https://github.com/koalaman/shellcheck)

---

**Last Updated**: 2025-01-XX
