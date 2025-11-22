#!/usr/bin/env python3
"""
Minecraft Server REST API
Provides HTTP API for remote server management
"""

import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify
from functools import wraps

# Optional CORS support
try:
    from flask_cors import CORS  # noqa: F401
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    CORS = None  # Placeholder for type checking

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = Flask(__name__)

# Enable CORS if available
if CORS_AVAILABLE:
    CORS(app)  # Enable CORS for web interfaces
else:
    # Fallback: Add CORS headers manually if needed
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add(
            'Access-Control-Allow-Headers',
            'Content-Type,Authorization,X-API-Key'
        )
        response.headers.add(
            'Access-Control-Allow-Methods',
            'GET,POST,PUT,DELETE,OPTIONS'
        )
        return response

# Configuration
API_CONFIG_FILE = PROJECT_ROOT / "config" / "api.conf"
API_KEYS_FILE = PROJECT_ROOT / "config" / "api-keys.json"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Default configuration
API_PORT = 8080
API_HOST = "127.0.0.1"  # Only listen on localhost by default
API_ENABLED = True

# Load configuration
if API_CONFIG_FILE.exists():
    with open(API_CONFIG_FILE, 'r') as f:
        config = {}
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
        API_PORT = int(config.get('API_PORT', API_PORT))
        API_HOST = config.get('API_HOST', API_HOST)
        API_ENABLED = config.get('API_ENABLED', 'true').lower() == 'true'

# Load API keys
API_KEYS = {}
if API_KEYS_FILE.exists():
    try:
        with open(API_KEYS_FILE, 'r') as f:
            API_KEYS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        API_KEYS = {}


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = (request.headers.get('X-API-Key') or
                   request.args.get('api_key'))

        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        # Check if API key is valid
        if api_key not in API_KEYS:
            return jsonify({'error': 'Invalid API key'}), 401

        # Check if key is enabled
        key_info = API_KEYS.get(api_key, {})
        if not key_info.get('enabled', True):
            return jsonify({'error': 'API key disabled'}), 401

        # Store key info in request context
        request.api_key_info = key_info
        return f(*args, **kwargs)

    return decorated_function


def run_script(script_name, *args):
    """Run a management script and return output"""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        return None, f"Script not found: {script_name}", 404

    try:
        result = subprocess.run(
            [str(script_path)] + list(args),
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return None, "Script execution timeout", 504
    except Exception as e:
        return None, str(e), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/status', methods=['GET'])
@require_api_key
def get_status():
    """Get server status"""
    # Check if server is running
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=minecraft-server',
             '--format', '{{.Status}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_running = 'Up' in result.stdout if result.returncode == 0 else False
        status_text = result.stdout if result.returncode == 0 else 'Unknown'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        is_running = False
        status_text = 'Unable to check status'

    return jsonify({
        'running': is_running,
        'status': status_text,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route('/api/server/start', methods=['POST'])
@require_api_key
def start_server():
    """Start the server"""
    stdout, stderr, code = run_script('manage.sh', 'start')

    if code == 0:
        return jsonify({
            'success': True,
            'message': 'Server starting',
            'output': stdout
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': stderr or 'Failed to start server'
        }), 500


@app.route('/api/server/stop', methods=['POST'])
@require_api_key
def stop_server():
    """Stop the server"""
    stdout, stderr, code = run_script('manage.sh', 'stop')

    if code == 0:
        return jsonify({
            'success': True,
            'message': 'Server stopping',
            'output': stdout
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': stderr or 'Failed to stop server'
        }), 500


@app.route('/api/server/restart', methods=['POST'])
@require_api_key
def restart_server():
    """Restart the server"""
    stdout, stderr, code = run_script('manage.sh', 'restart')

    if code == 0:
        return jsonify({
            'success': True,
            'message': 'Server restarting',
            'output': stdout
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': stderr or 'Failed to restart server'
        }), 500


@app.route('/api/server/command', methods=['POST'])
@require_api_key
def send_command():
    """Send a command to the server via RCON"""
    data = request.get_json()
    command = data.get('command')

    if not command:
        return jsonify({'error': 'Command required'}), 400

    stdout, stderr, code = run_script('rcon-client.sh', 'command', command)

    if code == 0:
        return jsonify({
            'success': True,
            'response': stdout,
            'command': command
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': stderr or 'Command failed',
            'command': command
        }), 500


@app.route('/api/backup', methods=['POST'])
@require_api_key
def create_backup():
    """Create a server backup"""
    stdout, stderr, code = run_script('manage.sh', 'backup')

    if code == 0:
        return jsonify({
            'success': True,
            'message': 'Backup created',
            'output': stdout
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': stderr or 'Backup failed'
        }), 500


@app.route('/api/backups', methods=['GET'])
@require_api_key
def list_backups():
    """List available backups"""
    backups_dir = PROJECT_ROOT / "backups"
    backups = []

    if backups_dir.exists():
        for backup_file in backups_dir.glob("minecraft_backup_*.tar.gz"):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x['created'], reverse=True)

    return jsonify({
        'backups': backups,
        'count': len(backups)
    })


@app.route('/api/logs', methods=['GET'])
@require_api_key
def get_logs():
    """Get server logs"""
    lines = request.args.get('lines', 100, type=int)

    _, stderr, _ = run_script('manage.sh', 'logs')

    # Get last N lines from Docker logs
    try:
        result = subprocess.run(
            ['docker', 'logs', '--tail', str(lines),
             'minecraft-server'],
            capture_output=True,
            text=True,
            timeout=10
        )
        logs = result.stdout if result.returncode == 0 else stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logs = stderr or "Unable to retrieve logs"

    return jsonify({
        'logs': logs.split('\n'),
        'lines': len(logs.split('\n'))
    })


@app.route('/api/players', methods=['GET'])
@require_api_key
def get_players():
    """Get list of online players"""
    stdout, _, _ = run_script('rcon-client.sh', 'command', 'list')

    # Parse player list from RCON response
    players = []
    if stdout:
        # Extract player names from RCON response
        import re
        match = re.search(r'online:\s*(.+)', stdout)
        if match:
            player_list = match.group(1).strip()
            players = [p.strip() for p in player_list.split(',') if p.strip()]

    return jsonify({
        'players': players,
        'count': len(players)
    })


@app.route('/api/metrics', methods=['GET'])
@require_api_key
def get_metrics():
    """Get server metrics"""
    # Run monitor script
    _, _, _ = run_script('monitor.sh')

    metrics = {}

    # Try to get Docker stats
    try:
        result = subprocess.run(
            ['docker', 'stats', 'minecraft-server', '--no-stream',
             '--format', '{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout:
            parts = result.stdout.strip().split(',')
            if len(parts) >= 3:
                metrics['cpu_percent'] = parts[0].rstrip('%')
                metrics['memory_usage'] = parts[1]
                metrics['memory_percent'] = parts[2].rstrip('%')
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return jsonify({
        'metrics': metrics,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route('/api/worlds', methods=['GET'])
@require_api_key
def list_worlds():
    """List all worlds"""
    stdout, _, _ = run_script('world-manager.sh', 'list')

    # Parse world list (basic implementation)
    worlds = []
    if stdout:
        for line in stdout.split('\n'):
            if ('world' in line.lower() and
                    ('ACTIVE' in line or '○' in line or '✓' in line)):
                # Extract world name (simplified parsing)
                parts = line.split()
                for part in parts:
                    if part.startswith('world') or part.isalnum():
                        worlds.append(part)
                        break

    return jsonify({
        'worlds': worlds,
        'count': len(worlds)
    })


@app.route('/api/plugins', methods=['GET'])
@require_api_key
def list_plugins():
    """List installed plugins"""
    stdout, _, _ = run_script('plugin-manager.sh', 'list')

    plugins = []
    if stdout:
        # Parse plugin list (simplified)
        for line in stdout.split('\n'):
            if '✓' in line or 'plugin' in line.lower():
                # Extract plugin name
                parts = line.split()
                for part in parts:
                    if (part and not part.startswith('(') and
                            not part.startswith('v')):
                        plugins.append(part)
                        break

    return jsonify({
        'plugins': plugins,
        'count': len(plugins)
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    if not API_ENABLED:
        print("API is disabled in configuration")
        sys.exit(1)

    print(f"Starting Minecraft Server API on {API_HOST}:{API_PORT}")
    app.run(host=API_HOST, port=API_PORT, debug=False)

