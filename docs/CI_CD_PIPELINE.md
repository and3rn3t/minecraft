# CI/CD Pipeline Documentation

## Overview

The unified CI/CD pipeline (`main.yml`) combines all testing, building, and deployment workflows into a single comprehensive pipeline.

## Pipeline Structure

### Jobs Overview

1. **Lint** - Syntax and validation checks (blocking)
2. **Python Tests** - API tests (blocking)
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

## Non-Blocking Tests

### Frontend Tests

- **Status**: Non-blocking (`continue-on-error: true`)
- **Purpose**: Unit tests for React components
- **Failure Impact**: Pipeline continues, failure is reported in summary

### Playwright Tests

- **Status**: Non-blocking (`continue-on-error: true`)
- **Purpose**: End-to-end browser automation tests
- **Timeout**: 60 minutes
- **Failure Impact**: Pipeline continues, test report uploaded as artifact
- **Artifacts**: Playwright HTML report (retained for 30 days)

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

## Pipeline Triggers

### Automatic Triggers

- **Push to main/develop**: Runs all tests and builds
- **Pull Request**: Runs all tests (no image build)
- **Push to main**: Builds Raspberry Pi image

### Manual Triggers

Use GitHub Actions UI to manually trigger:

- Run all tests
- Build image (set `build_image: true`)

## Critical vs Non-Critical Jobs

### Critical (Must Pass)

- ✅ Lint
- ✅ Python Tests
- ✅ Bash Tests
- ✅ Docker Build

### Non-Critical (Can Fail)

- ⚠️ Frontend Tests
- ⚠️ Playwright Tests

## Artifacts

### Playwright Report

- **Location**: `web/playwright-report/`
- **Retention**: 30 days
- **Access**: Download from workflow run

### Raspberry Pi Image

- **Location**: Root directory
- **Format**: `.img.xz` (compressed)
- **Retention**: 90 days
- **Access**:
  - Artifacts (main branch)
  - GitHub Releases (tags)

## Troubleshooting

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

### Pipeline Summary

The summary job provides an overview of all job results. Check the workflow run summary for:

- Job status (✅ success, ❌ failure, ⚠️ skipped)
- Critical job failures
- Non-critical job warnings

## Migration from Separate Workflows

The old separate workflows are still present but can be disabled:

- `ci.yml` → Merged into `main.yml` (lint job)
- `tests.yml` → Merged into `main.yml` (python-tests, bash-tests)
- `playwright.yml` → Merged into `main.yml` (playwright-tests, non-blocking)
- `coverage.yml` → Can be kept separate or merged
- `release.yml` → Image building replaces Docker image push

To disable old workflows, add this to each:

```yaml
on:
  workflow_dispatch: # Only manual trigger
```

## Future Enhancements

Potential improvements:

1. **Matrix builds**: Test on multiple Python/Node versions
2. **Docker registry push**: Push images to GHCR
3. **Image signing**: Sign images for security
4. **Automated testing**: Test the built image in QEMU
5. **Multi-architecture**: Support Raspberry Pi 4 (ARM32)
