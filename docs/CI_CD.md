# CI/CD Pipeline Guide

This guide covers the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Minecraft Server project.

## Overview

The project uses GitHub Actions for CI/CD, providing:

- **Automated Testing** - Runs on every push and pull request
- **Code Quality Checks** - Linting and static analysis
- **Automated Releases** - Version tagging and Docker image publishing
- **Multi-Architecture Builds** - ARM64, ARM32, and x86_64 support

## Workflows

### 1. Tests Workflow (`.github/workflows/tests.yml`)

Runs on:

- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Jobs:**

- **Bash Tests** - Runs BATS tests for shell scripts
- **Python Tests** - Runs pytest for API tests with coverage
- **Integration Tests** - Runs integration test suite
- **Lint** - Runs linting for bash, Python, and JavaScript

### 2. Release Workflow (`.github/workflows/release.yml`)

Runs on:

- Push of version tags (e.g., `v1.4.0`)
- Manual workflow dispatch with version input

**Jobs:**

- **Release** - Creates GitHub release with notes from CHANGELOG.md
- **Build and Push** - Builds multi-architecture Docker images and pushes to GitHub Container Registry

## Automated Releases

### Creating a Release

#### Method 1: Tag-Based Release (Recommended)

1. **Update CHANGELOG.md**:

   ```bash
   # Move Unreleased changes to new version section
   # Update version number
   ```

2. **Commit and push**:

   ```bash
   git add CHANGELOG.md
   git commit -m "chore: prepare release v1.4.0"
   git push
   ```

3. **Create and push version tag**:

   ```bash
   git tag -a v1.4.0 -m "Release v1.4.0"
   git push origin v1.4.0
   ```

4. **GitHub Actions automatically**:
   - Creates GitHub release
   - Generates release notes from CHANGELOG.md
   - Builds multi-architecture Docker images
   - Publishes images to GitHub Container Registry

#### Method 2: Manual Workflow Dispatch

1. Go to **Actions** → **Release** workflow
2. Click **Run workflow**
3. Enter version number (e.g., `1.4.0`)
4. Click **Run workflow**

### Release Notes Generation

Release notes are automatically generated from `CHANGELOG.md`:

- Extracts the section for the version being released
- Falls back to `[Unreleased]` section if version not found
- Includes installation and documentation links

**Manual generation**:

```bash
./scripts/generate-release-notes.sh 1.4.0
./scripts/generate-release-notes.sh 1.4.0 release-notes.md
```

## Docker Image Publishing

### GitHub Container Registry

Images are published to: `ghcr.io/<username>/minecraft-server`

**Tags created:**

- `v1.4.0` - Specific version
- `1.4.0` - Version without 'v' prefix
- `1.4` - Major.minor version
- `1` - Major version
- `latest` - Latest release (if on default branch)

### Pulling Images

```bash
# Pull specific version
docker pull ghcr.io/<username>/minecraft-server:v1.4.0

# Pull latest
docker pull ghcr.io/<username>/minecraft-server:latest
```

### Multi-Architecture Support

Images are built for:

- `linux/arm64` - Raspberry Pi 5, Apple Silicon
- `linux/arm/v7` - Raspberry Pi 4 and earlier
- `linux/amd64` - Intel/AMD x86_64

Docker automatically selects the correct architecture when pulling.

## CI/CD Configuration

### Required Secrets

No secrets required for public repositories. GitHub automatically provides:

- `GITHUB_TOKEN` - For creating releases and pushing images

For private repositories or custom registries, configure:

- `DOCKER_USERNAME` - Docker registry username
- `DOCKER_PASSWORD` - Docker registry password/token

### Workflow Permissions

The release workflow requires:

- `contents: write` - To create releases
- `packages: write` - To push Docker images

These are automatically granted for GitHub Actions.

## Testing Locally

### Run Tests

```bash
# Run all tests
make test

# Run specific test suite
python -m pytest tests/api/ -v
./scripts/run-tests.sh bash
```

### Run Linting

```bash
# Run all linting
make lint

# Run specific linting
make lint-bash
make lint-python
make lint-js
```

### Validate Release Notes

```bash
# Generate release notes for testing
./scripts/generate-release-notes.sh 1.4.0 test-notes.md
cat test-notes.md
```

## Best Practices

### 1. Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.4.0)
- **MAJOR** - Breaking changes
- **MINOR** - New features (backward compatible)
- **PATCH** - Bug fixes

### 2. Changelog Maintenance

- Update `CHANGELOG.md` with every change
- Use clear, descriptive change descriptions
- Group changes by type (Added, Changed, Fixed, etc.)
- Move `[Unreleased]` changes to version section before release

### 3. Release Process

1. **Update CHANGELOG.md** - Move Unreleased to version section
2. **Update version numbers** - In code/docs if needed
3. **Test thoroughly** - Run all tests locally
4. **Create tag** - Use `v` prefix (e.g., `v1.4.0`)
5. **Push tag** - Triggers automated release
6. **Verify release** - Check GitHub releases page
7. **Verify images** - Check container registry

### 4. Pre-Release Checklist

- [ ] All tests passing
- [ ] Linting passes
- [ ] CHANGELOG.md updated
- [ ] Version numbers updated
- [ ] Documentation reviewed
- [ ] Release notes reviewed

## Troubleshooting

### Release Not Created

**Issue**: Tag pushed but release not created

**Solutions**:

- Check workflow run in Actions tab
- Verify tag format (must start with `v`)
- Check workflow permissions
- Review workflow logs for errors

### Docker Image Not Published

**Issue**: Release created but image not published

**Solutions**:

- Check build job in Actions
- Verify Docker Buildx setup
- Check registry permissions
- Review build logs for errors

### Release Notes Empty

**Issue**: Release notes are empty or incorrect

**Solutions**:

- Verify CHANGELOG.md has version section
- Check version format matches tag
- Use manual release notes generation to test
- Review CHANGELOG.md format

### Multi-Architecture Build Fails

**Issue**: Build fails for specific architecture

**Solutions**:

- Check if architecture is supported
- Verify base images exist for architecture
- Review build logs for architecture-specific errors
- Test single-architecture build first

## Advanced Configuration

### Custom Docker Registry

To use a different registry (Docker Hub, etc.):

```yaml
- name: Login to Docker Hub
  uses: docker/login-action@v2
  with:
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}

- name: Build and push
  uses: docker/build-push-action@v4
  with:
    tags: docker.io/username/minecraft-server:${{ steps.version.outputs.tag }}
```

### Release Branch Strategy

To release only from `main` branch:

```yaml
on:
  push:
    tags:
      - 'v*.*.*'
    branches:
      - main # Only release from main
```

### Pre-Release Testing

Add a pre-release workflow:

```yaml
name: Pre-Release Tests
on:
  push:
    tags:
      - 'v*.*.*-*' # Pre-release tags

jobs:
  test:
    # Run extended test suite
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Buildx](https://docs.docker.com/build/buildx/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

## See Also

- [Testing Guide](TESTING.md) - Test framework details
- [Docker Optimization Guide](DOCKER_OPTIMIZATION.md) - Image optimization
- [Multi-Architecture Guide](MULTI_ARCHITECTURE.md) - Multi-arch builds
