# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **Enhanced Testing Framework**

  - End-to-end (E2E) tests for critical workflows (`tests/e2e/`)
  - Test utilities and helpers (`tests/helpers/test-utils.sh`)
  - Mock server for testing (`tests/helpers/mock-server.sh`)
  - E2E test runner integration
  - Enhanced test documentation

- **Mod Support (Complete)**

  - Mod loader detection script (`scripts/mod-loader-detector.sh`)
  - Support for Forge, Fabric, and Quilt detection
  - Mod pack installer script (`scripts/mod-pack-installer.sh`)
  - Mod dependency resolution
  - Mod compatibility verification
  - Mod support documentation (`docs/MOD_SUPPORT.md`)

- **Static Code Analysis Infrastructure**

  - Comprehensive linting script (`scripts/lint.sh`) for bash, Python, JavaScript/React, and YAML
  - ShellCheck configuration (`.shellcheckrc`) for bash script linting
  - ESLint already configured for React frontend
  - Makefile targets for linting (`make lint`, `make lint-bash`, etc.)
  - CI/CD integration with GitHub Actions for automated linting
  - Linting documentation (`docs/LINTING.md`) with best practices and troubleshooting

- **Docker Image Optimization**

  - Optimized Dockerfile with multi-stage builds
  - Reduced image size through layer optimization
  - Improved build caching strategy
  - `.dockerignore` file to exclude unnecessary files from build context
  - Docker optimization documentation (`docs/DOCKER_OPTIMIZATION.md`)
  - Support for build arguments (MINECRAFT_VERSION, BUILD_TYPE)

- **Cloud Backup Planning**

  - Added Cloudflare R2 to cloud backup integration tasks (S3-compatible, no egress fees)
  - Updated roadmap to prioritize R2 for Raspberry Pi users

- **Performance Benchmarking Suite**

  - Comprehensive benchmark script (`scripts/benchmark.sh`) for performance measurement
  - Startup time, TPS, memory, and CPU benchmarks
  - Baseline creation and comparison functionality
  - Regression detection capabilities
  - Performance benchmarking documentation (`docs/PERFORMANCE_BENCHMARKING.md`)

- **Multi-Architecture Support**

  - Multi-architecture Docker build script (`scripts/build-multiarch.sh`)
  - Support for ARM64 (Raspberry Pi 5), ARM32 (Raspberry Pi 4), and x86_64
  - Docker Buildx integration for cross-platform builds
  - Multi-architecture documentation (`docs/MULTI_ARCHITECTURE.md`)
  - Updated Dockerfile to support multiple architectures

- **CI/CD Pipeline Enhancements**

  - Automated release workflow (`.github/workflows/release.yml`)
  - Version tagging automation
  - Release notes generation from CHANGELOG.md
  - Docker image publishing to GitHub Container Registry
  - Multi-architecture image builds in CI/CD
  - Release documentation (`docs/CI_CD.md`)
  - Release notes generation script (`scripts/generate-release-notes.sh`)

- **Code Coverage Enhancements**

  - Coverage threshold enforcement (60% minimum)
  - Coverage reporting workflow (`.github/workflows/coverage.yml`)
  - Coverage check script (`scripts/check-coverage.sh`)
  - Coverage configuration (`.coverage-config.ini`)
  - Coverage badges and trend tracking
  - Makefile targets for coverage (`make coverage`, `make coverage-check`)

- **Cloud Backup Integration (Complete - v1.6.0)**

  - **Cloudflare R2** - R2 backup client script (`scripts/cloud-backup-r2.sh`) ✅
  - **AWS S3** - S3 backup client script (`scripts/cloud-backup-s3.sh`) ✅
  - **Backblaze B2** - B2 backup client script (`scripts/cloud-backup-b2.sh`) ✅
  - All providers support upload, download, list, and delete
  - S3-compatible API integration for R2 and B2
  - Configuration management for all providers
  - Comprehensive cloud backup documentation (`docs/CLOUD_BACKUP.md`)
  - Provider comparison and cost analysis
  - Cloudflare R2 recommended for Raspberry Pi (no egress fees)
  - Configuration examples for all providers

- **API Documentation (OpenAPI/Swagger)**
  - Complete OpenAPI 3.0 specification (`api/openapi.yaml`)
  - Interactive API documentation support
  - API documentation guide (`docs/API_DOCUMENTATION.md`)
  - Documentation serving script (`scripts/serve-api-docs.sh`)
  - All 40+ endpoints documented with schemas and examples

### Changed

- Updated GitHub Actions workflow to include frontend linting
- Enhanced Makefile with linting targets
- Optimized Dockerfile structure for better caching and smaller images
- Updated TASKS.md and ROADMAP.md to include Cloudflare R2 as recommended cloud backup option

## [1.4.0] - 2025-01-27

### Added

- **Web Admin Panel** - Complete React-based web interface for server management

  - Server status dashboard with real-time metrics
  - Real-time log viewer with WebSocket support and filtering
  - Player management interface (view, whitelist, ban, op)
  - Backup management UI with create, restore, and delete functionality
  - Server configuration file editor with syntax highlighting
  - Worlds and plugins management interfaces
  - Minecraft-themed pixel art UI design

- **Authentication & Security System**

  - User registration and login with password hashing
  - Session-based authentication with JWT support
  - OAuth integration (Google, Apple)
  - Role-Based Access Control (RBAC) with three roles:
    - **Admin**: Full system access
    - **Operator**: Server management and player control
    - **User**: Read-only access
  - Permission system with fine-grained control (25+ permissions)
  - User management interface (list, update roles, enable/disable, delete)
  - API key management with secure generation and storage
  - API key rotation (enable/disable) functionality

- **REST API Enhancements**

  - User management endpoints (`/api/users/*`)
  - Role and permission endpoints (`/api/roles`, `/api/permissions`)
  - API key management endpoints (`/api/keys/*`)
  - Permission-based access control on all endpoints
  - API key authentication support in `require_auth` decorator

- **Testing**

  - Comprehensive RBAC test suite (32 tests, all passing)
  - Permission system validation tests
  - User management tests
  - API key access tests
  - Config file permission tests

- **Documentation**
  - RBAC documentation (`docs/RBAC.md`)
  - API key management guide (`docs/API_KEYS.md`)
  - Updated documentation index with new guides
  - Security best practices documentation

### Changed

- Updated `require_auth` decorator to support API keys
- Fixed JSON serialization for bytes in API responses
- Improved error handling in permission checks
- Enhanced API key authentication flow

### Fixed

- Fixed role permissions (removed `backup.create` from user role, `config.edit` from operator role)
- Fixed API key authentication in permission-based endpoints
- Fixed JSON serialization issues with subprocess output
- Fixed MagicMock serialization in tests

### Security

- Implemented role-based permission system
- Added protection against disabling/deleting last admin user
- Secure API key storage with file permissions (600)
- Password hashing with bcrypt
- Session management with secure cookies

## [1.0.0] - 2025-11-22

### Added

- Initial release of Minecraft Server for Raspberry Pi 5
- Docker-based deployment system
- Automated setup script for Raspberry Pi (`setup-rpi.sh`)
- Server management script (`manage.sh`) with commands for start, stop, restart, status, logs, backup, and console
- Optimized Dockerfile for ARM64/Raspberry Pi 5
- Docker Compose configuration for easy deployment
- Default server configuration optimized for Raspberry Pi 5
- Startup script with Aikar's optimized JVM flags
- Comprehensive documentation:
  - README.md - Main documentation and feature overview
  - INSTALL.md - Detailed installation guide
  - QUICK_REFERENCE.md - Quick command reference
  - CONFIGURATION_EXAMPLES.md - Various configuration examples
- Default server.properties configured for small family server
- EULA acceptance configuration
- .gitignore for common files and directories
- Backup functionality in management script

### Configuration

- Default Minecraft version: 1.20.4
- Default memory allocation: 1G-2G (suitable for 4GB Pi)
- Default max players: 10
- Default view distance: 10
- Default simulation distance: 10
- Default difficulty: Normal
- Default game mode: Survival
- PvP enabled by default

### Features

- One-command server deployment
- Automatic Minecraft server jar download
- Persistent data storage
- Backup and restore functionality
- Easy configuration management
- Optimized JVM settings for Raspberry Pi
- Support for ARM64 architecture
- Docker networking for isolation
- Volume mounting for data persistence

### Documentation

- Step-by-step installation guide
- Quick reference for common tasks
- Configuration examples for different scenarios
- Performance tuning guidelines
- Troubleshooting section
- Port forwarding instructions
- Security best practices

## Planned Features

### [1.5.0] - Planned

- [ ] Dynamic DNS integration (DuckDNS, No-IP, Cloudflare)
- [ ] Cloud backup integration (S3, Backblaze)
- [ ] Performance monitoring dashboard enhancements
- [ ] Mobile app for server management
- [ ] Discord bot integration

### [1.2.0] - Planned

- [ ] Kubernetes deployment option
- [ ] Cloud backup integration (S3, Backblaze)
- [ ] Advanced security features
- [ ] Multi-server orchestration
- [ ] Load balancing support
- [ ] Metrics and analytics
- [ ] Mobile app for server management
- [ ] Discord bot integration

## Version Support

- **Minecraft Version**: 1.20.4 (default, configurable)
- **Java Version**: OpenJDK 21
- **Docker Version**: 20.10+
- **Docker Compose Version**: 2.0+
- **Raspberry Pi OS**: Bookworm (64-bit) or newer
- **Raspberry Pi Model**: Raspberry Pi 5 (4GB/8GB)

## Breaking Changes

None (initial release)

## Security Updates

None (initial release)

## Known Issues

1. First startup takes 5-10 minutes for world generation
2. Performance may vary based on number of players and view distance
3. Dynamic DNS not included (requires manual setup)
4. No automatic update mechanism yet

## Compatibility Notes

- Designed specifically for Raspberry Pi 5
- May work on other ARM64 devices with modifications
- Requires 64-bit operating system
- Minimum 4GB RAM recommended
- SSD storage recommended for better performance

## Migration Notes

For users upgrading from previous Minecraft server setups:

1. Stop your old server
2. Backup your world data
3. Copy world folders to `./data/` directory
4. Update `server.properties` as needed
5. Start the new server

## Contributors

- Initial development and documentation

## Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check documentation in README.md and INSTALL.md
- Review QUICK_REFERENCE.md for common tasks

---

[1.0.0]: https://github.com/and3rn3t/minecraft/releases/tag/v1.0.0
