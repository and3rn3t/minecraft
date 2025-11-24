# CI/CD Pipeline Guide

Complete guide to the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Minecraft Server project.

## Overview

The project uses GitHub Actions for CI/CD, providing:

- **Automated Testing** - Runs on every push and pull request
- **Code Quality Checks** - Linting and static analysis
- **Automated Releases** - Version tagging and Docker image publishing
- **Multi-Architecture Builds** - ARM64, ARM32, and x86_64 support
- **Raspberry Pi Image Building** - Automated pre-configured image creation

## Pipeline Structure

### Unified Pipeline (`.github/workflows/main.yml`)

The unified CI/CD pipeline combines all testing, building, and deployment workflows into a single comprehensive pipeline.

### Jobs Overview

1. **Lint** - Syntax and validation checks (blocking)
2. **Python Tests** - API tests with coverage (blocking)
3. **Bash Tests** - Shell script tests (blocking)
4. **Frontend Tests** - Vitest unit tests (non-blocking)
5. **Playwright Tests** - E2E browser tests (non-blocking)
6. **Build Docker** - Docker image build (blocking)
7. **Build RPi Image** - Raspberry Pi image creation (conditional)
8. **Summary** - Pipeline status summary

### Job Dependencies

```
lint ──┐
       ├──> build-docker ──> build-rpi-image
python-tests ──┘
bash-tests ───┘

frontend-tests (parallel, non-blocking)
playwright-tests (parallel, non-blocking)

All jobs ──> summary
```

### Non-Blocking Tests

#### Frontend Tests

- **Status**: Non-blocking (`continue-on-error: true`)
- **Purpose**: Unit tests for React components
- **Failure Impact**: Pipeline continues, failure is reported in summary

#### Playwright Tests

- **Status**: Non-blocking (`continue-on-error: true`)
- **Purpose**: End-to-end browser automation tests
- **Timeout**: 60 minutes
- **Failure Impact**: Pipeline continues, test report uploaded as artifact
- **Artifacts**: Playwright HTML report (retained for 30 days)

### Critical vs Non-Critical Jobs

#### Critical (Must Pass)

- ✅ Lint
- ✅ Python Tests
- ✅ Bash Tests
- ✅ Docker Build

#### Non-Critical (Can Fail)

- ⚠️ Frontend Tests
- ⚠️ Playwright Tests

## Pipeline Triggers

### Automatic Triggers

- **Push to main/develop**: Runs all tests and builds
- **Pull Request**: Runs all tests (no image build)
- **Push to main**: Builds Raspberry Pi image

### Manual Triggers

Use GitHub Actions UI to manually trigger:

- Run all tests
- Build image (set `build_image: true`)

## Enhanced Testing

### Python Tests Job

#### Test Requirements Installation

Installs all testing dependencies including:

- `pytest-xdist` for parallel execution
- `pytest-mock` for enhanced mocking
- `jsonschema` for contract testing
- `pyyaml` for OpenAPI schema parsing

#### Parallel Test Execution

**Features**:

- `-n auto` - Automatically detects CPU count and runs tests in parallel
- Multiple coverage report formats (HTML, JSON, XML)
- Detailed test output with `-ra` (show all test info)

**Benefits**:

- Faster test execution (typically 2-4x faster)
- Better resource utilization
- Multiple report formats for different tools

#### Performance Tests

Runs all tests marked with `@pytest.mark.performance`:

- Endpoint response time tests
- Load testing
- Throughput measurement

**Note**: Non-blocking to prevent job failure if performance tests have issues

#### Contract Tests

Runs all tests marked with `@pytest.mark.contract`:

- API response schema validation
- Request schema validation
- OpenAPI compliance checks

**Note**: Non-blocking to allow CI to continue even if schema validation has issues

#### Coverage Gap Analysis

Analyzes test coverage and identifies:

- Files with coverage < 80%
- Missing line numbers
- Test improvement suggestions

Generates `coverage-gaps.txt` report.

#### Coverage Report Artifacts

Uploads all coverage reports as GitHub Actions artifacts:

- **coverage.json** - JSON format for programmatic access
- **coverage.xml** - XML format for Codecov and other tools
- **htmlcov/** - HTML report for visual inspection
- **coverage-gaps.txt** - Gap analysis report

#### Codecov Integration

Uploads coverage to Codecov for:

- Coverage tracking over time
- PR coverage comments
- Coverage badges
- Coverage trends

## Pipeline Optimizations

### Dependency Caching

#### Python Dependencies

- **Implementation**: Uses GitHub Actions built-in pip caching
- **Benefit**: Avoids re-downloading Python packages on every run
- **Cache Key**: Based on `api/requirements.txt` hash

#### Node.js Dependencies

- **Implementation**: Uses GitHub Actions built-in npm caching
- **Benefit**: Faster frontend test execution
- **Cache Key**: Based on `web/package-lock.json` hash

#### BATS Installation

- **Implementation**: Custom cache for BATS binary
- **Benefit**: Skips BATS installation when cached
- **Cache Key**: `bats-${{ runner.os }}-v1`

#### APT Packages

- **Implementation**: Caches `/var/cache/apt` directory
- **Benefit**: Faster package installation in image builds
- **Cache Key**: `apt-${{ runner.os }}-rpi-build-tools`

#### Raspberry Pi OS Base Image

- **Implementation**: Caches downloaded and extracted base image
- **Benefit**: Skips 5-15 minute download on cache hits
- **Cache Key**: `rpi-os-lite-2024-01-11-arm64`

### Docker Build Optimizations

#### Build Cache

- **Implementation**: GitHub Actions cache for Docker layers
- **Benefit**: Reuses layers from previous builds
- **Cache Scope**: `build-docker` to isolate cache per job
- **Mode**: `max` for maximum cache utilization

#### Build Context

- **Implementation**: `.dockerignore` file excludes unnecessary files
- **Benefit**: Smaller build context = faster uploads
- **Excluded**: Documentation, tests, web frontend, CI/CD files

### Image Build Optimizations

#### Reduced Wait Times

- **Before**: 3 seconds wait after partition operations
- **After**: 1 second wait with timeout-based verification
- **Benefit**: Faster image customization step

#### Compression Optimization

- **Before**: `xz -9` (maximum compression, slow)
- **After**: `xz -6` (good compression, faster)
- **Benefit**: 2-3x faster compression with minimal size increase

#### Artifact Optimization

- **Implementation**: Only upload compressed `.img.xz` files
- **Benefit**: Smaller artifacts, faster uploads
- **Compression Level**: 6 (balanced)

### Performance Improvements

#### Estimated Time Savings

| Optimization             | Time Saved   | Frequency                 |
| ------------------------ | ------------ | ------------------------- |
| Python pip cache         | 30-60s       | Every run                 |
| Node.js cache            | 20-40s       | Every run                 |
| BATS cache               | 10-20s       | Every run                 |
| APT cache                | 15-30s       | Image builds              |
| RPi OS image cache       | 5-15 min     | Image builds (cache hits) |
| Compression optimization | 2-5 min      | Image builds              |
| Reduced wait times       | 4-6s         | Image builds              |
| **Total (typical run)**  | **1-2 min**  | Every run                 |
| **Total (image build)**  | **7-20 min** | Image builds              |

#### Cache Hit Rates

- **Python/Node caches**: ~95% hit rate (changes only when dependencies update)
- **BATS cache**: ~100% hit rate (rarely changes)
- **APT cache**: ~80% hit rate (changes with workflow updates)
- **RPi OS image cache**: ~50% hit rate (changes with base image updates)

## Raspberry Pi Image Building

### When Images Are Built

Images are automatically built when:

- Pushing to `main` branch
- Manual workflow dispatch with `build_image: true`
- Creating a release tag

### Image Contents

The generated `.img` file includes:

1. **Base System**: Raspberry Pi OS Lite (64-bit)
2. **Pre-configured Services**:
   - SSH enabled
   - Hostname: `minecraft-server`
   - WiFi configuration (optional)
3. **First-Boot Script**:
   - Updates system packages
   - Installs Docker and Docker Compose
   - Installs Node.js for web interface
   - Clones repository
   - Runs setup script
   - Configures Minecraft server

### Image Specifications

- **Format**: Compressed `.img.xz` file
- **Size**: ~4GB (expandable on first boot)
- **Architecture**: ARM64 (Raspberry Pi 5)
- **Base OS**: Raspberry Pi OS Lite (Bookworm)

### Using the Image

1. **Download** the `.img.xz` file from:

   - Workflow artifacts (for main branch builds)
   - GitHub Releases (for tagged releases)

2. **Extract** the image:

   ```bash
   xz -d minecraft-server-rpi5-YYYYMMDD.img.xz
   ```

3. **Flash** to microSD card:

   ```bash
   # On Linux/macOS
   sudo dd if=minecraft-server-rpi5-YYYYMMDD.img of=/dev/sdX bs=4M status=progress

   # Or use Raspberry Pi Imager
   ```

4. **Boot** the Raspberry Pi:

   - Insert microSD card
   - Connect power and network
   - Wait 10-20 minutes for first-boot setup
   - SSH into `minecraft-server.local` or check IP

5. **Verify** setup:
   ```bash
   ssh pi@minecraft-server.local
   cd ~/minecraft-server
   ./manage.sh status
   ```

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

**Tags created**:

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

## Artifacts

### Playwright Report

- **Location**: `web/playwright-report/`
- **Retention**: 30 days
- **Access**: Download from workflow run

### Coverage Reports

- **Location**: `coverage-reports` artifact
- **Contents**: HTML, JSON, XML reports, gap analysis
- **Retention**: 30 days
- **Access**: Download from workflow run

### Raspberry Pi Image

- **Location**: Root directory
- **Format**: `.img.xz` (compressed)
- **Retention**: 90 days
- **Access**:
  - Artifacts (main branch)
  - GitHub Releases (tags)

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

### 5. Cache Key Management

- Use stable cache keys for rarely-changing dependencies
- Include version numbers in cache keys for base images
- Use hash-based keys for frequently-changing dependencies

### 6. Compression Trade-offs

- Use `-6` for xz compression (good balance)
- Use `-9` only if file size is critical
- Consider gzip for faster compression if size isn't critical

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

### Playwright Tests Failing

Since Playwright tests are non-blocking, failures won't block the pipeline. To investigate:

1. Download the Playwright report artifact
2. Open `index.html` in a browser
3. Review test failures and screenshots
4. Check test logs for errors

### Image Build Failing

Common issues:

1. **Download timeout**: Raspberry Pi OS download may timeout

   - **Solution**: Workflow will retry, or manually trigger

2. **Disk space**: Image building requires ~10GB free space

   - **Solution**: GitHub Actions runners have sufficient space

3. **QEMU issues**: ARM emulation may fail
   - **Solution**: Check QEMU setup step logs

### Cache Issues

**Problem**: Cache not being used

- **Solution**: Check cache key matches
- **Solution**: Verify cache path is correct
- **Solution**: Check cache size limits

**Problem**: Stale cache causing failures

- **Solution**: Update cache key
- **Solution**: Clear cache manually
- **Solution**: Add cache version to key

### Performance Issues

**Problem**: Slow builds

- **Solution**: Check cache hit rates
- **Solution**: Verify optimizations are applied
- **Solution**: Consider larger runners

**Problem**: Timeouts

- **Solution**: Increase timeout values
- **Solution**: Optimize slow operations
- **Solution**: Split long-running jobs

### Tests Failing in CI

1. Check test output in GitHub Actions
2. Download coverage reports artifact
3. Review coverage-gaps.txt for missing tests
4. Check performance test thresholds

### Coverage Not Uploading

1. Verify `coverage.xml` is generated
2. Check Codecov token is configured
3. Review Codecov action logs

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

## Future Enhancements

Potential improvements:

1. **Matrix builds**: Test on multiple Python/Node versions
2. **Docker registry push**: Push images to GHCR (already implemented)
3. **Image signing**: Sign images for security
4. **Automated testing**: Test the built image in QEMU
5. **Multi-architecture**: Support Raspberry Pi 4 (ARM32) - partially implemented
6. **Larger runners**: Use 4-core runners for image builds
7. **Parallel operations**: Further parallelize image customization
8. **Test Result Caching**: Cache test results for faster runs
9. **Coverage Badges**: Auto-update coverage badges
10. **PR Comments**: Auto-comment coverage on PRs
11. **Performance Baselines**: Track performance over time

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Buildx](https://docs.docker.com/build/buildx/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.com/)
- [GitHub Actions Caching](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows)
- [Docker Build Cache](https://docs.docker.com/build/cache/)
- [XZ Compression Options](https://tukaani.org/xz/manual/xz.html)

## See Also

- [Testing Guide](TESTING.md) - Test framework details
- [Docker Optimization Guide](DOCKER_OPTIMIZATION.md) - Image optimization
- [Multi-Architecture Guide](MULTI_ARCHITECTURE.md) - Multi-arch builds
- [Performance Benchmarking Guide](PERFORMANCE_BENCHMARKING.md) - Performance testing
