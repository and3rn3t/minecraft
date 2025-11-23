# Changelog

All notable changes to this project will be documented in this file.

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
