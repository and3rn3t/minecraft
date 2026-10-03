# CI/CD Pipeline Guide

Complete guide to the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Minecraft Server project.

## Overview

The project uses GitHub Actions for CI/CD, providing:

- **Automated Testing** - Runs on every push and pull request
- **Code Quality Checks** - Linting and static analysis
- **Automated Releases** - Version tagging and Docker image publishing
- **Multi-Architecture Builds** - ARM64 and x86_64 support
- **Raspberry Pi Image Building** - Automated pre-configured image creation

## Pipeline Structure

### Unified Pipeline (`.github/workflows/main.yml`)

The unified CI/CD pipeline combines all testing, building, and deployment workflows into a single comprehensive pipeline.

### Jobs Overview

Every test job gates the Docker build; none is allowed to fail.

1. **Lint (pre-commit)** - ruff, shellcheck, yamllint, markdownlint, gitleaks, actionlint
2. **Lint and Syntax Check** - `bash -n` on every script, `docker compose config`
3. **Python API Tests** - pytest in parallel, with coverage held to `fail_under`
4. **Bash Script Tests** - the BATS suite in `tests/unit/`
5. **Frontend Tests** - ESLint, production build, Vitest with coverage thresholds
6. **Playwright Tests** - the built app in Chromium, including screenshot comparisons
7. **Build Docker Image** - ARM64 image; pushed to ghcr.io only on a push to main
8. **Pipeline Summary** - status table; fails if any job above did not succeed

### Job Dependencies

```text
pre-commit ───────┐
lint ─────────────┤
python-tests ─────┤
bash-tests ───────┼──> build-docker
frontend-tests ───┤
playwright-tests ─┘

all of the above ──> summary
```

The six test jobs run in parallel. `build-docker` starts only when all of them
succeed, so nothing that failed a check can be pushed to the registry.

### Playwright Tests

- **Runs in**: the `mcr.microsoft.com/playwright` container. The screenshot
  baselines in `web/tests/e2e/visual-regression.spec.js-snapshots/` were rendered
  in that image, and a screenshot only matches the environment that drew it. The
  image tag must equal `@playwright/test` in `web/package-lock.json`; the job's
  first step fails if they differ.
- **Browsers**: Chromium on CI. Firefox and WebKit are opt-in locally
  (`PW_ALL_BROWSERS=1`).
- **Retries**: one; a test that needed it is reported as flaky.
- **Timeout**: 15 minutes.
- **Artifacts on failure**: the HTML report and `test-results/` (the actual,
  expected and diff images for a screenshot mismatch), kept 14 days.
- **Locally**: `make test-visual` runs the suite exactly as CI does, and
  `make test-visual-update` re-renders baselines after an intended UI change.
- **Bumping Playwright**: the version lives in four places that must agree:
  `@playwright/test` and `playwright` in `web/package.json` (pinned exactly, so the
  coupling shows), the lockfile, `PLAYWRIGHT_IMAGE` in the `Makefile`, and the
  `playwright-tests` job's `container.image` plus its version check in
  `.github/workflows/main.yml`. Renovate groups the npm packages but does not touch
  the image tag, so a bump arrives as an npm PR that fails the check in that job
  until the image is updated too. Change all four, run `make test-visual`, and only
  if screenshots differ run `make test-visual-update` and look at the new images
  before committing them.

## Pipeline Triggers

- **Pull request** to main or develop: every job; the image is built but not pushed.
- **Push** to main or develop: every job; on main the image is pushed to ghcr.io and
  the web build is uploaded for the Pi's deploy agent.
- **Weekly schedule** (Monday 05:00 UTC): every job, plus the API performance tests,
  which assert wall-clock limits and so stay off the pull-request path.
- **Manual** (`workflow_dispatch`): the same as the schedule.

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

**Note**: Runs only on the weekly schedule and on manual runs. Its hard
wall-clock limits would flake on a shared runner, so it stays off pull requests.

#### Contract Tests

Runs all tests marked with `@pytest.mark.contract`:

- API response schema validation
- Request schema validation
- OpenAPI compliance checks

**Note**: These run as part of the main parallel test step, not a separate one,
and fail the job like any other test.

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

No workflow builds this image at present: the `build-rpi-image` job was removed
from `main.yml` (commit `696c468`), and no other workflow replaced it. What follows
describes the image that job produced.

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
   ./scripts/manage.sh status
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

- **Uploaded**: only when the Playwright job fails
- **Contents**: `web/playwright-report/` and `web/test-results/`
- **Retention**: 14 days
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

A Playwright failure blocks the Docker build and fails the summary. To investigate:

1. Download the `playwright-report` artifact and open `playwright-report/index.html`.
2. **A screenshot mismatch** shows the expected, actual and diff images. If the
   change was intended, run `make test-visual-update`, look at the re-rendered PNGs,
   and commit them. Never regenerate baselines outside the container: they will not
   match CI.
3. **"API calls with no mock"** means a page called an endpoint that
   `web/tests/e2e/mock-api.js` doesn't answer. Add the endpoint there, with a
   response shaped like the real API's.
4. **"@playwright/test is X, the image is Y"**: the dependency was bumped without the
   image. Update the tag in `.github/workflows/main.yml` and the `Makefile` together,
   then re-render the baselines.
5. Reproduce locally with `make test-visual`.

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
5. **Multi-architecture**: ARM64 and x86_64 supported (no 32-bit ARM: Temurin 25 has no arm/v7 image)
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
