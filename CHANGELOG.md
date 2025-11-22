# Changelog

All notable changes to this project will be documented in this file.

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

### [1.1.0] - Planned
- [ ] Automatic backup scheduling
- [ ] Web-based admin panel
- [ ] Plugin support (Paper/Spigot)
- [ ] Dynamic DNS integration
- [ ] Performance monitoring dashboard
- [ ] Automatic updates
- [ ] Multiple world support
- [ ] Mod support options

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
