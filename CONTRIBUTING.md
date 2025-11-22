# Contributing to Minecraft Server for Raspberry Pi 5

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Issues

If you encounter a bug or have a feature request:

1. **Check existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information**:
   - Raspberry Pi model and RAM
   - OS version (run `cat /etc/os-release`)
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Relevant log output
   - Configuration files (server.properties, docker-compose.yml)

### Suggesting Enhancements

We welcome suggestions! When proposing enhancements:

1. **Explain the use case** - Why is this needed?
2. **Describe the solution** - How should it work?
3. **Consider alternatives** - What other approaches exist?
4. **Think about compatibility** - Will it work on all Pi models?

### Pull Requests

#### Before Submitting

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Test your changes** thoroughly
4. **Update documentation** as needed
5. **Follow coding standards** (see below)

#### Submitting

1. **Write clear commit messages**:
   ```
   Add feature: Brief description
   
   Longer explanation of what changed and why.
   Addresses any relevant issues.
   ```

2. **Keep changes focused** - One feature/fix per PR
3. **Include tests** if applicable
4. **Update CHANGELOG.md**
5. **Ensure all scripts pass syntax checks**

#### Review Process

- Maintainers will review your PR
- Address feedback and requested changes
- Once approved, your PR will be merged

## Development Guidelines

### Code Style

#### Shell Scripts
- Use `#!/bin/bash` shebang
- Use 4-space indentation
- Quote variables: `"$VAR"` not `$VAR`
- Use functions for repeated code
- Add comments for complex logic
- Check syntax: `bash -n script.sh`

Example:
```bash
#!/bin/bash
set -e

function example_function() {
    local param="$1"
    echo "Processing: $param"
}

# Main logic
if [ -z "$VARIABLE" ]; then
    echo "Variable not set"
    exit 1
fi
```

#### Docker
- Use official base images when possible
- Minimize layers
- Clean up in the same layer
- Use multi-stage builds if needed
- Add labels for metadata

#### Documentation
- Use clear, concise language
- Include code examples
- Keep formatting consistent
- Update all relevant docs
- Verify markdown syntax

### Testing

Before submitting changes:

1. **Syntax checks**:
   ```bash
   # Shell scripts
   bash -n script.sh
   
   # Docker Compose
   docker-compose config
   
   # Dockerfile
   docker build -t test .
   ```

2. **Functional tests**:
   - Start server: `./manage.sh start`
   - Check logs: `./manage.sh logs`
   - Connect with Minecraft client
   - Test all management commands
   - Verify backup/restore

3. **Performance tests**:
   - Monitor with `htop`
   - Check memory usage
   - Test with multiple players
   - Measure TPS in-game

### Documentation Updates

When making changes, update:

- **README.md** - If adding features or changing setup
- **INSTALL.md** - If changing installation steps
- **QUICK_REFERENCE.md** - If adding commands
- **CONFIGURATION_EXAMPLES.md** - If adding config options
- **TROUBLESHOOTING.md** - If solving new issues
- **CHANGELOG.md** - For all changes

## Project Structure

```
minecraft-server/
├── README.md                    # Main documentation
├── INSTALL.md                   # Installation guide
├── QUICK_REFERENCE.md          # Command reference
├── CONFIGURATION_EXAMPLES.md   # Config examples
├── TROUBLESHOOTING.md          # Problem solving
├── CONTRIBUTING.md             # This file
├── CHANGELOG.md                # Version history
├── LICENSE                     # MIT License
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Service configuration
├── start.sh                    # Server startup script
├── setup-rpi.sh               # Raspberry Pi setup
├── manage.sh                   # Management commands
├── server.properties           # Default config
├── eula.txt                    # EULA acceptance
└── .gitignore                  # Git exclusions
```

## Types of Contributions

### Documentation
- Fix typos and grammar
- Improve clarity
- Add examples
- Translate to other languages
- Update screenshots

### Bug Fixes
- Fix script errors
- Resolve configuration issues
- Improve error handling
- Fix compatibility issues

### Features
- New management commands
- Additional configuration options
- Performance improvements
- Monitoring tools
- Automation scripts

### Testing
- Test on different Pi models
- Test different Minecraft versions
- Performance benchmarking
- Load testing
- Documentation testing

## Areas for Contribution

### High Priority
- [ ] Automated testing framework
- [ ] Performance benchmarking
- [ ] Alternative server implementations (Paper/Spigot)
- [ ] Web-based admin panel
- [ ] Automatic backup scheduling
- [ ] Dynamic DNS integration

### Medium Priority
- [ ] Plugin management
- [ ] Multi-server support
- [ ] Advanced monitoring
- [ ] Cloud backup integration
- [ ] Mobile app for management
- [ ] Discord bot integration

### Low Priority
- [ ] Custom themes for docs
- [ ] Video tutorials
- [ ] Community mod packs
- [ ] Alternative architectures
- [ ] Kubernetes manifests

## Version Guidelines

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Process

1. Update CHANGELOG.md
2. Update version in relevant files
3. Test thoroughly
4. Create git tag: `git tag -a v1.0.0 -m "Version 1.0.0"`
5. Push tag: `git push origin v1.0.0`
6. Create GitHub release
7. Update documentation

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Focus on the issue, not the person
- Help others learn

### Communication

- **GitHub Issues**: Bug reports and features
- **Pull Requests**: Code contributions
- **Discussions**: Questions and ideas
- Be patient - maintainers are volunteers

## Recognition

Contributors will be:
- Listed in CHANGELOG.md
- Mentioned in release notes
- Credited in documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open a GitHub issue with tag `question`
- Check existing documentation
- Review closed issues for similar questions

## Thank You!

Every contribution, no matter how small, helps improve this project. Thank you for taking the time to contribute!

---

## Quick Start for Contributors

1. **Fork and clone**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/minecraft.git
   cd minecraft
   ```

2. **Create branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make changes and test**:
   ```bash
   # Edit files
   bash -n *.sh  # Check syntax
   # Test functionality
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "Add feature: description"
   git push origin feature/my-feature
   ```

5. **Create Pull Request** on GitHub

Happy contributing! 🎮⛏️
