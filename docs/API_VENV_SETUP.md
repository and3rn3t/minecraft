# API Server Virtual Environment Setup

This guide explains how to set up and use a Python virtual environment for the API server.

## Why Use a Virtual Environment?

- **Isolation**: Keeps API dependencies separate from system Python packages
- **Consistency**: Ensures the same Python version and packages across environments
- **Cleanliness**: Avoids conflicts with other Python projects
- **Best Practice**: Standard Python development practice

## Quick Setup

### Automatic Setup (Recommended)

```bash
cd ~/minecraft-server
chmod +x scripts/setup-api-venv.sh
./scripts/setup-api-venv.sh
```

This script will:

1. Create a virtual environment in `api/venv/`
2. Install all dependencies from `requirements.txt`
3. Verify the installation

### Manual Setup

```bash
cd ~/minecraft-server/api

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import flask; print('Flask installed successfully')"

# Deactivate (when done)
deactivate
```

## Systemd Service Configuration

The systemd service (`minecraft-api.service`) is already configured to use the virtual environment:

```ini
ExecStart=/home/pi/minecraft/api/venv/bin/python /home/pi/minecraft/api/server.py
Environment="PATH=/home/pi/minecraft/api/venv/bin:/usr/local/bin:/usr/bin:/bin"
```

**Important**: Make sure the path in the service file matches your project location:

- Default: `/home/pi/minecraft/api/venv`
- If different: Update the service file paths

## Updating Dependencies

### Method 1: Using Setup Script

```bash
cd ~/minecraft-server
./scripts/setup-api-venv.sh
```

### Method 2: Manual Update

```bash
cd ~/minecraft-server/api
source venv/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart minecraft-api.service
```

### Method 3: Add New Package

```bash
cd ~/minecraft-server/api
source venv/bin/activate
pip install <package-name>
pip freeze > requirements.txt  # Update requirements file
deactivate
```

## Verifying Virtual Environment

### Check if venv exists

```bash
ls -la ~/minecraft-server/api/venv/
```

### Check installed packages

```bash
cd ~/minecraft-server/api
source venv/bin/activate
pip list
deactivate
```

### Test API server manually

```bash
cd ~/minecraft-server/api
source venv/bin/activate
python server.py
# Press Ctrl+C to stop
deactivate
```

## Troubleshooting

### Service Won't Start

**Problem**: Service fails with "No such file or directory"

**Solution**: Check if venv exists and paths are correct:

```bash
# Check venv exists
ls -la ~/minecraft-server/api/venv/bin/python

# Check service file path
sudo cat /etc/systemd/system/minecraft-api.service | grep ExecStart

# Update service file if path is wrong
sudo nano /etc/systemd/system/minecraft-api.service
# Update paths to match your setup
sudo systemctl daemon-reload
sudo systemctl restart minecraft-api.service
```

### Dependencies Not Found

**Problem**: Import errors in logs

**Solution**: Reinstall dependencies:

```bash
cd ~/minecraft-server/api
source venv/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart minecraft-api.service
```

### Virtual Environment Corrupted

**Problem**: venv exists but doesn't work

**Solution**: Recreate it:

```bash
cd ~/minecraft-server/api
rm -rf venv
../scripts/setup-api-venv.sh
sudo systemctl restart minecraft-api.service
```

### Wrong Python Version

**Problem**: Service uses wrong Python version

**Solution**: Check and recreate venv:

```bash
# Check Python version
python3 --version

# Recreate venv with correct Python
cd ~/minecraft-server/api
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

## Path Configuration

If your project is in a different location, update these files:

1. **Systemd service file**: `/etc/systemd/system/minecraft-api.service`

   - Update `WorkingDirectory`
   - Update `ExecStart` path
   - Update `Environment` PATH

2. **Setup script**: `scripts/setup-api-venv.sh`
   - Script auto-detects project directory
   - No changes needed usually

## Best Practices

1. **Always use venv**: Don't install packages globally
2. **Keep requirements.txt updated**: Run `pip freeze > requirements.txt` after adding packages
3. **Version control venv**: Add `api/venv/` to `.gitignore` (don't commit it)
4. **Regular updates**: Update dependencies periodically for security
5. **Test before deploying**: Test API server manually before restarting service

## Quick Reference

```bash
# Setup venv
./scripts/setup-api-venv.sh

# Activate venv (for manual testing)
source ~/minecraft-server/api/venv/bin/activate

# Install package
pip install <package>

# Update requirements
pip freeze > requirements.txt

# Deactivate venv
deactivate

# Restart service
sudo systemctl restart minecraft-api.service

# Check service status
sudo systemctl status minecraft-api.service

# View logs
tail -f ~/minecraft-server/logs/api-server.log
```

## Summary

The API server now uses a Python virtual environment for better isolation and dependency management. The systemd service automatically uses the venv, so you don't need to activate it manually for the service to run.
