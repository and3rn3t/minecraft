# Minecraft Server for Raspberry Pi 5

A custom Minecraft server setup optimized for Raspberry Pi 5, providing easy control over settings and customization. This setup uses Docker for easy deployment and management.

## Features

- 🎮 Optimized for Raspberry Pi 5 (ARM64 architecture)
- 🐳 Docker-based deployment for easy management
- ⚙️ Easy customization of server settings
- 💾 Automatic backup support
- 🔄 Simple update mechanism
- 📊 Resource-efficient configuration

## Requirements

- Raspberry Pi 5 (4GB or 8GB RAM recommended)
- MicroSD card (32GB or larger recommended)
- Raspberry Pi OS (64-bit)
- Internet connection for initial setup

## Quick Start

### 1. Flash Raspberry Pi OS

> **📘 For detailed image preparation instructions, see [RASPBERRY_PI_IMAGE_PREPARATION.md](docs/RASPBERRY_PI_IMAGE_PREPARATION.md).**  
> **📋 For a quick checklist, see [IMAGE_PREP_CHECKLIST.md](docs/IMAGE_PREP_CHECKLIST.md).**

Quick steps:

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert your microSD card into your computer
3. Open Raspberry Pi Imager
4. Choose OS: **Raspberry Pi OS (64-bit)**
5. Choose Storage: Select your microSD card
6. Click on the gear icon (⚙️) for advanced options:
   - Set hostname (e.g., `minecraft-server`)
   - Enable SSH
   - Set username and password
   - Configure WiFi (optional)
7. Click **Write** and wait for the process to complete

### 2. Initial Setup on Raspberry Pi

1. Insert the microSD card into your Raspberry Pi 5
2. Power on the Raspberry Pi
3. SSH into your Raspberry Pi:

   ```bash
   ssh pi@minecraft-server.local
   ```

   Or use the IP address if hostname doesn't work

4. Clone this repository:

   ```bash
   cd ~
   git clone https://github.com/and3rn3t/minecraft.git minecraft-server
   cd minecraft-server
   ```

5. Run the setup script:

   ```bash
   chmod +x setup-rpi.sh
   ./setup-rpi.sh
   ```

6. **Important**: Log out and log back in for Docker permissions to take effect:

   ```bash
   exit
   # SSH back in
   ssh pi@minecraft-server.local
   cd ~/minecraft-server
   ```

### 3. Start the Minecraft Server

```bash
# Make management script executable
chmod +x manage.sh

# Start the server
./manage.sh start

# View logs
./manage.sh logs
```

## Server Management

The `manage.sh` script provides easy server management:

```bash
./manage.sh start              # Start the server
./manage.sh stop               # Stop the server
./manage.sh restart            # Restart the server
./manage.sh status             # Check server status
./manage.sh logs               # View server logs
./manage.sh backup             # Create a backup
./manage.sh console            # Attach to server console (Ctrl+P, Ctrl+Q to detach)
./manage.sh update [version]   # Update server to latest or specified version
./manage.sh check-version      # Check for available updates
./manage.sh check-compatibility # Check compatibility before updating
```

## Customization

### Server Properties

Edit `server.properties` to customize your server:

```properties
# Common settings to adjust
max-players=10              # Maximum number of players
difficulty=normal           # easy, normal, hard, peaceful
gamemode=survival          # survival, creative, adventure
view-distance=10           # Render distance (lower = better performance)
motd=My Minecraft Server   # Server name in multiplayer list
```

After changing settings, restart the server:

```bash
./manage.sh restart
```

### Memory Allocation

Edit `docker-compose.yml` to adjust memory settings:

```yaml
environment:
  - MEMORY_MIN=1G # Minimum memory (1G for 4GB Pi, 2G for 8GB Pi)
  - MEMORY_MAX=2G # Maximum memory (2G for 4GB Pi, 4G for 8GB Pi)
```

**Recommended Memory Settings:**

- Raspberry Pi 5 (4GB): MIN=1G, MAX=2G
- Raspberry Pi 5 (8GB): MIN=2G, MAX=4G

### Minecraft Version

To change Minecraft version, edit `docker-compose.yml`:

```yaml
environment:
  - MINECRAFT_VERSION=1.20.4 # Change to desired version
```

Then rebuild and restart:

```bash
docker-compose down
docker-compose up -d --build
```

## Port Forwarding

To allow players outside your local network to connect:

1. Find your Raspberry Pi's local IP address:

   ```bash
   hostname -I
   ```

2. Log into your router's admin panel
3. Set up port forwarding:

   - External Port: 25565
   - Internal Port: 25565
   - Internal IP: Your Raspberry Pi's IP address
   - Protocol: TCP

4. Find your public IP address: Visit [whatismyipaddress.com](https://whatismyipaddress.com/)
5. Share your public IP with your friends to connect

## Backups

### Manual Backup

```bash
./manage.sh backup
```

Backups are stored in the `backups/` directory.

### Restore from Backup

```bash
# Stop the server
./manage.sh stop

# Extract backup to data directory
tar -xzf backups/minecraft_backup_YYYYMMDD_HHMMSS.tar.gz -C ./data/

# Start the server
./manage.sh start
```

## Troubleshooting

### Server won't start

1. Check if Docker is running:

   ```bash
   sudo systemctl status docker
   ```

2. View detailed logs:

   ```bash
   docker-compose logs
   ```

3. Check available memory:

   ```bash
   free -h
   ```

### Performance Issues

1. Reduce view distance in `server.properties`:

   ```properties
   view-distance=6
   simulation-distance=6
   ```

2. Lower max players:

   ```properties
   max-players=5
   ```

3. Reduce memory if system is struggling:

   ```yaml
   MEMORY_MAX=1G
   ```

### Cannot connect from outside network

1. Verify port forwarding is set up correctly
2. Check if server is running: `./manage.sh status`
3. Ensure firewall allows port 25565:

   ```bash
   sudo ufw allow 25565/tcp
   ```

## Performance Tips

1. **Use Ethernet**: Wired connection is more stable than WiFi
2. **Proper Cooling**: Ensure your Pi 5 has adequate cooling (case with fan recommended)
3. **Quality Power Supply**: Use the official Raspberry Pi 5 power supply
4. **Fast Storage**: Use a high-quality microSD card (Class 10, A2 rating)
5. **Regular Backups**: Back up your world regularly

## Advanced Configuration

### Installing Plugins (For Bukkit/Spigot/Paper)

If you want to use plugins, you'll need to use Paper or Spigot instead of vanilla:

1. Switch to Paper or Spigot:

   ```bash
   ./scripts/switch-server-type.sh paper
   ```

2. Install plugins:

   ```bash
   ./scripts/plugin-manager.sh install /path/to/plugin.jar
   ```

3. Restart the server:
   ```bash
   ./scripts/manage.sh restart
   ```

See [PLUGIN_MANAGEMENT.md](docs/PLUGIN_MANAGEMENT.md) for detailed plugin management guide.

### Automatic Startup on Boot

To start the server automatically when the Pi boots:

```bash
# Create systemd service
sudo nano /etc/systemd/system/minecraft.service
```

Add:

```ini
[Unit]
Description=Minecraft Server
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/minecraft-server
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=pi

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl enable minecraft.service
sudo systemctl start minecraft.service
```

## Testing

The project includes comprehensive automated tests:

```bash
# Run API tests
python -m pytest tests/api/ -v

# Run with coverage
python -m pytest tests/api/ -v --cov=api --cov-report=term-missing
```

**Current Status**: ✅ 60+ API tests passing (~60% coverage)

See [Testing Guide](docs/TESTING.md) for more information.

## Code Quality

The project uses static code analysis to ensure code quality:

```bash
# Run all linting checks
make lint

# Or use the linting script directly
./scripts/lint.sh all
```

**Linting Tools**:

- **ShellCheck** - Bash script linting
- **ESLint** - JavaScript/React linting
- **flake8/pylint** - Python code analysis (optional)
- **yamllint** - YAML file validation (optional)

See [Linting Guide](docs/LINTING.md) for more information.

## Docker Optimization

The project uses optimized Docker images for Raspberry Pi 5:

- **Multi-stage builds** - Reduced image size
- **Layer optimization** - Better build caching
- **Minimal base image** - Security and performance
- **Build arguments** - Flexible configuration

```bash
# Build with custom version
docker build --build-arg MINECRAFT_VERSION=1.21.0 -t minecraft-server .

# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker build -t minecraft-server .
```

See [Docker Optimization Guide](docs/DOCKER_OPTIMIZATION.md) for details.

## Documentation

📚 **Start here**: [Documentation Index](docs/INDEX.md) - Complete navigation guide

### Quick Links

**Getting Started:**

- **[Installation Guide](docs/INSTALL.md)** - Complete setup instructions
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet
- **[Configuration Examples](docs/CONFIGURATION_EXAMPLES.md)** - Config file examples

**User Guides:**

- **[Backup & Monitoring](docs/BACKUP_AND_MONITORING.md)** - Automated backups and metrics
- **[Update Management](docs/UPDATE_MANAGEMENT.md)** - Server updates and versions
- **[Plugin Management](docs/PLUGIN_MANAGEMENT.md)** - Installing and managing plugins
- **[Multi-World Support](docs/MULTI_WORLD.md)** - Managing multiple worlds
- **[Log Management](docs/LOG_MANAGEMENT.md)** - Log rotation and analysis
- **[RCON Guide](docs/RCON.md)** - Remote console setup
- **[REST API](docs/API.md)** - API documentation
- **[Web Interface](docs/WEB_INTERFACE.md)** - Web admin panel

**Developer Guides:**

- **[Development Guide](docs/DEVELOPMENT.md)** - Setup and workflow
- **[Testing Guide](docs/TESTING.md)** - Testing best practices
- **[Cursor Configuration](docs/CURSOR_CONFIGURATION.md)** - IDE setup
- **[Contributing](CONTRIBUTING.md)** - Contribution guidelines
- **[Agent Instructions](AGENT_INSTRUCTIONS.md)** - AI agent consistency guide

**Project Planning:**

- **[Roadmap](docs/ROADMAP.md)** - Development roadmap
- **[Tasks](TASKS.md)** - Detailed task breakdown
- **[Changelog](CHANGELOG.md)** - Version history

**Troubleshooting:**

- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common problems and solutions

For complete documentation navigation, see [docs/INDEX.md](docs/INDEX.md).

## Resources

- [Minecraft Server Documentation](https://minecraft.fandom.com/wiki/Server)
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [Docker Documentation](https://docs.docker.com/)
- [Server Properties Guide](https://minecraft.fandom.com/wiki/Server.properties)

## Development

### Quick Start for Developers

```bash
# Clone repository
git clone https://github.com/and3rn3t/minecraft.git
cd minecraft

# Setup environment
cp .env.example .env  # Edit with your settings
make install

# Test
make test
make build

# Start development
make start
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development guide.

### Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Roadmap

Check out [ROADMAP.md](ROADMAP.md) for planned features and development phases.

## License

This project is open source and available for personal use.

## Support

For issues and questions, please open an issue on GitHub.
