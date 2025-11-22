# Agent Instructions for Minecraft Server Management Project

This document provides comprehensive instructions for AI agents working on this codebase to ensure consistency across development sessions.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Code Standards](#code-standards)
4. [Development Workflow](#development-workflow)
5. [File Structure](#file-structure)
6. [Testing Requirements](#testing-requirements)
7. [Documentation Standards](#documentation-standards)
8. [Common Patterns](#common-patterns)
9. [Important Considerations](#important-considerations)
10. [Quick Reference](#quick-reference)

---

## Project Overview

This is a **Minecraft Server Management System** optimized for **Raspberry Pi 5 (ARM64)**. The project provides:

- Docker-based server deployment and management
- Automated backup scheduling and retention
- Plugin management system
- Multi-world support
- REST API for remote server control
- React web interface for server administration
- RCON integration
- Log management and analysis
- Update management system

**Target Platform**: Raspberry Pi 5 (4GB/8GB RAM), but also supports x86_64

---

## Architecture & Technology Stack

### Backend

- **API Server**: Python 3 with Flask
- **Server Management**: Bash scripts
- **Containerization**: Docker & Docker Compose
- **Configuration**: INI-style config files

### Frontend

- **Framework**: React with Vite
- **Styling**: Tailwind CSS
- **Testing**: Vitest
- **Build Tool**: Vite

### Testing

- **Python**: pytest
- **React**: Vitest
- **Shell Scripts**: BATS (Bash Automated Testing System)

### Infrastructure

- **Container Runtime**: Docker
- **Orchestration**: Docker Compose
- **OS**: Raspberry Pi OS (64-bit) / Linux

---

## Code Standards

### Shell Scripts

**Requirements:**

- Always use `#!/bin/bash` shebang
- Use `set -e` for error handling
- 4-space indentation (no tabs)
- Always quote variables: `"$VAR"` not `$VAR`
- Use functions for repeated code
- Include color output for user feedback
- Add comments for complex logic
- Include usage/help functions

**Example:**

```bash
#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

function example_function() {
    local param="$1"
    echo -e "${GREEN}Processing: $param${NC}"
}

# Main logic
if [ -z "$VARIABLE" ]; then
    echo -e "${RED}Error: Variable not set${NC}"
    exit 1
fi
```

**Validation:**

- Run `bash -n script.sh` to check syntax
- Test on actual Raspberry Pi 5 when possible

### Python Code

**Requirements:**

- Follow PEP 8 style guide
- Use type hints where appropriate
- Include docstrings for functions and classes
- Use `pathlib.Path` for file operations
- Handle exceptions specifically
- Group imports: stdlib, third-party, local

**Example:**

```python
#!/usr/bin/env python3
"""
Module description.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

def example_function(param: str) -> Optional[Path]:
    """
    Function description.

    Args:
        param: Parameter description

    Returns:
        Path object or None
    """
    try:
        path = Path(param)
        if path.exists():
            return path
        return None
    except Exception as e:
        print(f"Error processing {param}: {e}")
        return None
```

**Validation:**

- Run `pytest tests/api/ -v` for tests
- Use `mypy` for type checking (if configured)
- Run `flake8` or `pylint` for linting

### React/JavaScript

**Requirements:**

- Use functional components with hooks
- Use Tailwind CSS for styling
- Keep components small and focused
- Use `services/api.js` for API calls
- Include PropTypes or TypeScript types
- Write tests for components

**Example:**

```jsx
import { useState, useEffect } from 'react';
import { api } from '../services/api';

export function StatusCard() {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getStatus()
            .then(setStatus)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div>Loading...</div>;

    return (
        <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-xl font-bold">Server Status</h2>
            <p>{status?.status || 'Unknown'}</p>
        </div>
    );
}
```

**Validation:**

- Run `npm test` for unit tests
- Run `npm run lint` for linting
- Test in browser

### Docker

**Requirements:**

- Use official base images when possible
- Minimize layers
- Clean up in the same layer
- Use multi-stage builds for optimization
- Include health checks
- Use environment variables for configuration

**Example:**

```dockerfile
FROM eclipse-temurin:17-jre-alpine

# Install dependencies
RUN apk add --no-cache bash

# Set working directory
WORKDIR /minecraft/server

# Copy scripts
COPY scripts/ /minecraft/scripts/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD pgrep -f java || exit 1

# Default command
CMD ["/minecraft/scripts/start.sh"]
```

### YAML Files

**Requirements:**

- 2-space indentation
- Use environment variables: `${VAR:-default}`
- Keep lines under 120 characters
- Validate with `docker-compose config`

---

## Development Workflow

### Making Changes

1. **Create Feature Branch**

   ```bash
   git checkout -b feature/feature-name
   ```

2. **Make Changes**
   - Follow code standards
   - Write tests
   - Update documentation

3. **Test Changes**

   ```bash
   # Shell scripts
   bash -n script.sh

   # Python
   pytest tests/api/ -v

   # React
   npm test

   # Docker
   docker-compose config
   ```

4. **Commit Changes**

   ```bash
   git commit -m "Add feature: description"
   ```

5. **Push and Create PR**

   ```bash
   git push origin feature/feature-name
   ```

### Testing Requirements

**Before Committing:**

- [ ] Shell scripts pass syntax check (`bash -n`)
- [ ] Python tests pass (`pytest`)
- [ ] React tests pass (`npm test`)
- [ ] Docker config validates (`docker-compose config`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

**Integration Testing:**

- Test on Raspberry Pi 5 when possible
- Test server startup/shutdown
- Test backup/restore
- Test plugin management
- Test API endpoints

---

## File Structure

```
minecraft/
├── api/                          # Python Flask REST API
│   ├── server.py                # Main API server
│   └── requirements.txt         # Python dependencies
├── web/                          # React frontend
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API service layer
│   │   └── test/                # Test utilities
│   ├── package.json
│   └── vite.config.js
├── scripts/                      # Shell scripts
│   ├── manage.sh               # Main management script
│   ├── backup-scheduler.sh      # Backup scheduling
│   ├── plugin-manager.sh        # Plugin management
│   ├── world-manager.sh         # World management
│   ├── rcon-client.sh           # RCON client
│   └── ...
├── config/                       # Configuration files
│   ├── api.conf                 # API configuration
│   ├── backup-schedule.conf     # Backup schedule
│   ├── backup-retention.conf    # Backup retention
│   └── ...
├── docs/                         # Documentation
│   ├── API.md                   # API documentation
│   ├── DEVELOPMENT.md           # Development guide
│   ├── INSTALL.md               # Installation guide
│   └── ...
├── tests/                        # Test suites
│   ├── api/                     # Python API tests
│   │   ├── test_api.py
│   │   └── conftest.py
│   ├── integration/             # Integration tests
│   └── unit/                    # Unit tests
├── systemd/                      # Systemd service files
├── docker-compose.yml            # Docker Compose config
├── Dockerfile                    # Docker image definition
├── Makefile                      # Convenience commands
├── README.md                     # Main documentation
├── CONTRIBUTING.md               # Contribution guidelines
├── TASKS.md                      # Development tasks
└── CHANGELOG.md                  # Version history
```

---

## Testing Requirements

### Unit Tests

- **Python**: Test individual functions in `tests/api/`
- **React**: Test components in `__tests__/` directories
- **Shell**: Test functions in `tests/unit/`

### Integration Tests

- Test script interactions in `tests/integration/`
- Test API endpoints with real server
- Test Docker container operations

### Test Coverage

- **Current**: 51% for Python API
- **Goal**: >50% coverage minimum
- **Target**: 80%+ for critical paths

### Running Tests

```bash
# Python API tests
pytest tests/api/ -v
pytest tests/api/ -v --cov=api --cov-report=term-missing

# React tests
cd web && npm test

# Shell script tests
bats tests/unit/
```

---

## Documentation Standards

### When to Update Documentation

- **README.md**: User-facing features, setup changes
- **docs/INSTALL.md**: Installation procedure changes
- **docs/API.md**: API endpoint changes
- **docs/DEVELOPMENT.md**: Development workflow changes
- **CHANGELOG.md**: All changes (required)
- **QUICK_REFERENCE.md**: New commands or features

### Documentation Format

- Use Markdown format
- Include code examples
- Use clear headings
- Keep internal links relative
- Update all related docs when making changes

### Example Documentation Update

```markdown
## New Feature

### Description
Brief description of the feature.

### Usage
```bash
./manage.sh new-command
```

### Configuration

Add to `config/feature.conf`:

```ini
setting=value
```

### Examples

[Include examples]

```

---

## Common Patterns

### Script Structure Pattern

```bash
#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
CONFIG_FILE="${SCRIPT_DIR}/../config/script.conf"

# Functions
function usage() {
    echo "Usage: $0 {command}"
    exit 1
}

function main_function() {
    local param="$1"
    echo -e "${GREEN}Processing: $param${NC}"
}

# Main execution
if [ "$#" -eq 0 ]; then
    usage
    exit 1
fi

case "$1" in
    command)
        main_function "$2"
        ;;
    *)
        usage
        exit 1
        ;;
esac
```

### API Endpoint Pattern

```python
@app.route('/api/endpoint', methods=['GET', 'POST'])
@require_api_key
def endpoint():
    """
    Endpoint description.

    Returns:
        JSON response with status and data
    """
    try:
        if request.method == 'GET':
            data = get_data()
            return jsonify({"status": "success", "data": data})
        elif request.method == 'POST':
            data = request.get_json()
            result = process_data(data)
            return jsonify({"status": "success", "result": result})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error in endpoint: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
```

### React Component Pattern

```jsx
import { useState, useEffect } from 'react';
import { api } from '../services/api';

export function Component({ prop1, prop2 }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        api.getData()
            .then(setData)
            .catch(setError)
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error.message}</div>;

    return (
        <div className="component">
            {/* Component content */}
        </div>
    );
}
```

---

## Important Considerations

### Raspberry Pi 5 Optimization

**Memory Constraints:**

- 4GB model: Use MIN=1G, MAX=2G
- 8GB model: Use MIN=2G, MAX=4G
- Monitor memory usage carefully
- Implement memory-efficient algorithms

**CPU Considerations:**

- ARM64 architecture
- Optimize for efficiency, not just speed
- Consider CPU temperature monitoring
- Use multi-core processing when beneficial

**Storage:**

- SD card write limits
- Implement log rotation
- Use efficient backup compression
- Monitor disk space

### Docker Best Practices

**Resource Management:**

- Set appropriate memory limits
- Configure CPU limits if needed
- Use health checks
- Implement proper logging

**Volume Management:**

- Use bind mounts for data persistence
- Configure volume permissions
- Implement backup strategies

**Networking:**

- Use custom networks
- Expose only necessary ports
- Implement proper security

### Security

**API Security:**

- Use API keys for authentication
- Store keys securely (config/api-keys.json)
- Never commit secrets
- Validate all inputs

**RCON Security:**

- Generate secure random passwords
- Store passwords securely
- Use strong passwords

**File Permissions:**

- Set appropriate permissions on scripts
- Protect configuration files
- Secure backup files

### Error Handling

**Graceful Degradation:**

- Handle missing dependencies
- Provide fallback options
- Don't crash on non-critical errors

**User Feedback:**

- Provide clear error messages
- Use color coding (red for errors)
- Log errors with context

**Recovery:**

- Implement rollback mechanisms
- Create backups before major operations
- Validate operations before execution

---

## Quick Reference

### Common Commands

```bash
# Server Management
./manage.sh start              # Start server
./manage.sh stop               # Stop server
./manage.sh restart            # Restart server
./manage.sh status             # Check status
./manage.sh logs               # View logs
./manage.sh backup             # Create backup
./manage.sh console            # Attach to console

# Development
make test                      # Run tests
make build                     # Build Docker image
make start                     # Start server
make logs                      # View logs

# Testing
pytest tests/api/ -v           # Run API tests
cd web && npm test             # Run React tests
bash -n script.sh              # Check script syntax
docker-compose config          # Validate Docker config
```

### Key Files

- `scripts/manage.sh` - Main management script
- `api/server.py` - REST API server
- `docker-compose.yml` - Docker configuration
- `README.md` - Main documentation
- `TASKS.md` - Development tasks
- `CONTRIBUTING.md` - Contribution guidelines
- `docs/DEVELOPMENT.md` - Development guide

### File Naming Conventions

- **Scripts**: `kebab-case.sh` (e.g., `backup-scheduler.sh`)
- **Python**: `snake_case.py` (e.g., `server.py`)
- **React**: `PascalCase.jsx` (e.g., `StatusCard.jsx`)
- **Config**: `kebab-case.conf` (e.g., `backup-schedule.conf`)
- **Documentation**: `UPPERCASE.md` (e.g., `README.md`)

### When Adding New Features

1. Check `TASKS.md` for related tasks
2. Follow existing patterns in similar features
3. Add tests for new functionality
4. Update documentation (README, relevant docs/)
5. Update `CHANGELOG.md` with changes
6. Test on Raspberry Pi 5 if hardware-specific

### Git Workflow

- **Branches**: Use `feature/`, `fix/`, `docs/` prefixes
- **Commits**: Clear, descriptive messages
- **PRs**: One feature/fix per PR
- **Reviews**: Address feedback before merging

---

## Remember

✅ **Always:**

- Test on Raspberry Pi 5 when possible
- Keep memory usage in mind (4GB/8GB models)
- Follow existing code patterns
- Update documentation with changes
- Write tests for new features
- Use clear, descriptive names
- Handle errors gracefully
- Provide user feedback

❌ **Never:**

- Commit secrets or API keys
- Break backward compatibility without notice
- Skip testing
- Ignore error handling
- Use tabs instead of spaces
- Forget to update documentation
- Hardcode paths (use variables)

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0
