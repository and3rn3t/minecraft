import { useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Input } from '../components/ui/FormField';
import { StatusPill } from '../components/ui/Badge';
import { PageHeader } from '../components/ui/PageHeader';
import { api } from '../services/api';

const Console = () => {
  const [commandHistory, setCommandHistory] = useState([]);
  const [commandInput, setCommandInput] = useState('');
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [connected, setConnected] = useState(false);
  const [output, setOutput] = useState([]);
  const [loading, setLoading] = useState(true);
  const socketRef = useRef(null);
  const outputEndRef = useRef(null);
  const inputRef = useRef(null);
  const commandHistoryRef = useRef([]);

  // Load command history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('console_history');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        commandHistoryRef.current = parsed;
        setCommandHistory(parsed);
      } catch (e) {
        console.error('Failed to load command history:', e);
      }
    }
  }, []);

  // Save command history to localStorage
  const saveHistory = newHistory => {
    const limited = newHistory.slice(-100); // Keep last 100 commands
    commandHistoryRef.current = limited;
    localStorage.setItem('console_history', JSON.stringify(limited));
    setCommandHistory(limited);
  };

  // WebSocket connection
  useEffect(() => {
    const apiKey = localStorage.getItem('api_key') || import.meta.env.VITE_API_KEY;
    const token = localStorage.getItem('auth_token');

    if (!apiKey && !token) {
      console.warn('No API key or token found for console');
      setLoading(false);
      return;
    }

    // Connect to the current origin at Socket.IO's default path (/socket.io),
    // which nginx (prod) and vite's dev server proxy through to the API.
    // Deriving this from VITE_API_URL (an axios baseURL like "/api") doesn't
    // work: passed to io() as a bare path, it's parsed as a namespace rather
    // than a server address, so the connection never reaches the backend.
    const socket = io(window.location.origin, {
      auth: {
        api_key: apiKey,
        token,
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Console WebSocket connected');
      setConnected(true);
      setLoading(false);
      addOutput('Connected to server console', 'system');
    });

    socket.on('disconnect', () => {
      console.log('Console WebSocket disconnected');
      setConnected(false);
      addOutput('Disconnected from server console', 'system');
    });

    socket.on('connected', data => {
      setConnected(true);
      setLoading(false);
      addOutput(data.message || 'Connected to server console', 'system');
    });

    socket.on('error', data => {
      console.error('Console WebSocket error:', data.message);
      addOutput(`Error: ${data.message}`, 'error');
    });

    socket.on('command_response', data => {
      if (data.success) {
        addOutput(`> ${data.command}`, 'command');
        if (data.response) {
          addOutput(data.response, 'response');
        }
      } else {
        addOutput(`> ${data.command}`, 'command');
        addOutput(`Error: ${data.response}`, 'error');
      }
    });

    socket.on('command_error', data => {
      addOutput(`> ${data.command || 'command'}`, 'command');
      addOutput(`Error: ${data.message}`, 'error');
    });

    // Also listen to logs for server output
    socket.on('logs', data => {
      if (data.type === 'update' && data.logs) {
        // One state update for the whole batch rather than one per line —
        // each setOutput call copies the (up to 1000-entry) array, so an
        // N-line batch was N copies instead of one.
        const lines = data.logs.filter(log => log.trim()).map(text => ({ text, type: 'log' }));
        addOutputBatch(lines);
      }
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, []);

  // Auto-scroll output
  useEffect(() => {
    if (outputEndRef.current) {
      outputEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [output]);

  const addOutput = (text, type = 'log') => {
    const timestamp = new Date().toLocaleTimeString();
    setOutput(prev => [...prev, { text, type, timestamp }].slice(-1000)); // Keep last 1000 lines
  };

  // Same as addOutput, but for a batch of lines in a single state update.
  const addOutputBatch = entries => {
    if (entries.length === 0) return;
    const timestamp = new Date().toLocaleTimeString();
    setOutput(prev => [...prev, ...entries.map(e => ({ ...e, timestamp }))].slice(-1000));
  };

  const executeCommand = async cmd => {
    if (!cmd.trim()) return;

    const trimmedCmd = cmd.trim();

    // Add to history
    const newHistory = [...commandHistoryRef.current];
    if (newHistory[newHistory.length - 1] !== trimmedCmd) {
      newHistory.push(trimmedCmd);
      saveHistory(newHistory);
    }
    setHistoryIndex(-1);

    // Execute via WebSocket if connected, otherwise fallback to HTTP
    if (socketRef.current && connected) {
      socketRef.current.emit('execute_command', { command: trimmedCmd });
    } else {
      // Fallback to HTTP API
      try {
        addOutput(`> ${trimmedCmd}`, 'command');
        const result = await api.sendCommand(trimmedCmd);
        if (result.success) {
          if (result.response) {
            addOutput(result.response, 'response');
          }
        } else {
          addOutput(`Error: ${result.error || 'Command failed'}`, 'error');
        }
      } catch (error) {
        addOutput(`Error: ${error.message || 'Failed to execute command'}`, 'error');
      }
    }

    setCommandInput('');
  };

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      executeCommand(commandInput);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistoryRef.current.length > 0) {
        const newIndex =
          historyIndex === -1
            ? commandHistoryRef.current.length - 1
            : Math.max(0, historyIndex - 1);
        setHistoryIndex(newIndex);
        setCommandInput(commandHistoryRef.current[newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex >= 0) {
        const newIndex = historyIndex + 1;
        if (newIndex >= commandHistoryRef.current.length) {
          setHistoryIndex(-1);
          setCommandInput('');
        } else {
          setHistoryIndex(newIndex);
          setCommandInput(commandHistoryRef.current[newIndex]);
        }
      }
    } else if (e.key === 'Tab') {
      e.preventDefault();
      // Basic autocomplete for common commands
      const input = commandInput.toLowerCase();
      const commonCommands = [
        'help',
        'list',
        'say',
        'tell',
        'give',
        'tp',
        'gamemode',
        'time',
        'weather',
        'difficulty',
        'whitelist',
        'ban',
        'kick',
        'op',
        'deop',
        'save-all',
        'stop',
        'restart',
      ];
      const matches = commonCommands.filter(cmd => cmd.startsWith(input));
      if (matches.length === 1) {
        setCommandInput(matches[0] + ' ');
      } else if (matches.length > 1) {
        // Show possible completions
        addOutput(`Possible completions: ${matches.join(', ')}`, 'system');
      }
    }
  };

  const clearOutput = () => {
    setOutput([]);
  };

  const getOutputClass = type => {
    switch (type) {
      case 'command':
        return 'text-minecraft-water-light font-bold';
      case 'response':
        return 'text-minecraft-grass-light';
      case 'error':
        return 'text-minecraft-danger';
      case 'system':
        return 'text-minecraft-text-dark italic';
      default:
        return 'text-minecraft-text-light';
    }
  };

  return (
    <div>
      <PageHeader title="SERVER CONSOLE" />

      {/* Connection Status */}
      <Card padding="md" className="mb-6 flex items-center gap-4">
        <StatusPill
          status={connected ? 'success' : 'neutral'}
          title={connected ? 'Connected' : 'Disconnected'}
        >
          {loading ? 'CONNECTING...' : connected ? 'CONNECTED' : 'DISCONNECTED'}
        </StatusPill>
        <Button onClick={clearOutput}>CLEAR</Button>
        <span className="ml-auto text-[10px] font-minecraft text-minecraft-text-dark">
          {commandHistory.length} COMMANDS IN HISTORY
        </span>
      </Card>

      {/* Output Area */}
      <Card padding="md" className="mb-4">
        <div className="max-h-[500px] overflow-auto bg-minecraft-dirt p-2 font-minecraft text-[10px]">
          {output.length === 0 ? (
            <EmptyState icon="💻" title="No output yet" hint="Type a command below" />
          ) : (
            output.map((item, index) => (
              <div key={index} className={`py-1 px-2 ${getOutputClass(item.type)}`}>
                <span className="mr-2 text-minecraft-text-dark">[{item.timestamp}]</span>
                {item.text}
              </div>
            ))
          )}
          <div ref={outputEndRef} />
        </div>
      </Card>

      {/* Command Input */}
      <Card padding="md">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-minecraft text-minecraft-text-light">$</span>
          <Input
            ref={inputRef}
            type="text"
            aria-label="Console command"
            value={commandInput}
            onChange={e => setCommandInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="TYPE COMMAND HERE... (UP/DOWN FOR HISTORY, TAB FOR AUTOCOMPLETE)"
            className="flex-1 font-minecraft text-[10px]"
            disabled={!connected && loading}
          />
          <Button onClick={() => executeCommand(commandInput)} disabled={!connected || !commandInput.trim()}>
            EXECUTE
          </Button>
        </div>
        <div className="mt-2 text-[8px] font-minecraft text-minecraft-text-dark">
          TIP: Use ↑/↓ to navigate command history, TAB for autocomplete
        </div>
      </Card>
    </div>
  );
};

export default Console;
