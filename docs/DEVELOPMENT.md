# Development Guide

This guide provides information for developers contributing to the Minecraft Server project.

## Development Environment Setup

### Prerequisites
- Docker and Docker Compose
- Git
- A text editor (VS Code recommended)
- Bash shell

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/and3rn3t/minecraft.git
   cd minecraft
   ```

2. **Install pre-commit hooks** (optional but recommended)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

3. **Copy environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Install VS Code extensions** (if using VS Code)
   - Open VS Code
   - Install recommended extensions (prompt will appear)

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow coding standards (see CONTRIBUTING.md)
   - Write tests if applicable
   - Update documentation

3. **Test your changes**
   ```bash
   make test  # Run all tests
   make build # Build Docker image
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

### Testing

#### Local Testing
```bash
# Test shell scripts
bash -n manage.sh
bash -n start.sh

# Test docker-compose
docker-compose config

# Test server startup (requires Docker)
make build
make start
make logs
```

#### Automated Testing
- CI runs on every push and PR
- Check GitHub Actions for test results
- Fix any failing tests before requesting review

## Code Standards

### Shell Scripts
- Use `#!/bin/bash` shebang
- 4-space indentation
- Quote all variables: `"$VAR"`
- Use `set -e` for error handling
- Add comments for complex logic
- Include usage/help functions

### YAML Files
- 2-space indentation
- Use environment variables
- Keep lines under 120 characters
- Validate with `docker-compose config`

### Documentation
- Markdown format
- Clear, concise language
- Include code examples
- Update all relevant docs

## Project Structure

```
minecraft/
├── .github/          # GitHub workflows and templates
├── .vscode/          # VS Code settings
├── config/           # Configuration files
├── scripts/          # Utility scripts
├── data/             # Server data (gitignored)
├── backups/          # Backups (gitignored)
├── plugins/          # Plugins (gitignored)
├── *.sh              # Shell scripts
├── *.yml             # Docker Compose config
├── Dockerfile        # Docker image definition
└── *.md              # Documentation
```

## Common Tasks

### Adding a New Script

1. Create script in `scripts/` directory
2. Add shebang and error handling
3. Make executable: `chmod +x scripts/new-script.sh`
4. Document in `scripts/README.md`
5. Add tests if applicable

### Adding a New Feature

1. Create feature branch
2. Implement feature
3. Add tests
4. Update documentation
5. Update CHANGELOG.md
6. Create PR

### Updating Documentation

1. Edit relevant `.md` file
2. Check markdown syntax
3. Verify links work
4. Test code examples
5. Commit with message: "docs: update [file]"

## Debugging

### Server Issues
```bash
# View logs
make logs

# Check status
make status

# Access container shell
make shell

# View Docker logs
docker logs minecraft-server
```

### Script Issues
```bash
# Run with debug output
bash -x manage.sh start

# Check syntax
bash -n manage.sh

# Run shellcheck
shellcheck manage.sh
```

## Performance Testing

### Benchmarking
```bash
# Monitor resources
htop
docker stats minecraft-server

# Check temperature
vcgencmd measure_temp

# Monitor TPS (in-game)
/forge tps
```

## Release Process

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create git tag: `git tag -a v1.0.0 -m "Version 1.0.0"`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release
6. Update documentation

## Getting Help

- Check existing documentation
- Review CONTRIBUTING.md
- Open a GitHub issue
- Ask in GitHub Discussions

## Resources

- [Shell Script Best Practices](https://github.com/koalaman/shellcheck/wiki)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Markdown Guide](https://www.markdownguide.org/)
- [Semantic Versioning](https://semver.org/)

---

Happy coding! 🎮⛏️

