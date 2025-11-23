import { useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';
import { api } from '../services/api';

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('');
  const [connected, setConnected] = useState(false);
  const [useWebSocket, setUseWebSocket] = useState(true);
  const logEndRef = useRef(null);
  const socketRef = useRef(null);
  const pollIntervalRef = useRef(null);

  // WebSocket connection
  useEffect(() => {
    if (!useWebSocket) {
      // Fallback to polling
      loadLogs();
      pollIntervalRef.current = setInterval(loadLogs, 2000);
      return () => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
      };
    }

    // Get API key
    const apiKey = localStorage.getItem('api_key') || import.meta.env.VITE_API_KEY;
    if (!apiKey) {
      console.warn('No API key found, falling back to polling');
      setUseWebSocket(false);
      return;
    }

    // Get API URL
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080';
    const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');

    // Create socket connection
    const socket = io(wsUrl, {
      auth: {
        api_key: apiKey,
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    socketRef.current = socket;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
      setLoading(false);
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    });

    socket.on('connected', data => {
      console.log('Log stream connected:', data.message);
      setConnected(true);
      setLoading(false);
    });

    socket.on('error', data => {
      console.error('WebSocket error:', data.message);
      // Fallback to polling on error
      setUseWebSocket(false);
      setConnected(false);
    });

    // Log event handlers
    socket.on('logs', data => {
      if (data.type === 'initial') {
        // Replace all logs with initial batch
        setLogs(data.logs || []);
        setLoading(false);
      } else if (data.type === 'update') {
        // Append new logs
        setLogs(prevLogs => {
          const newLogs = [...prevLogs, ...(data.logs || [])];
          // Keep only last 1000 lines to prevent memory issues
          return newLogs.slice(-1000);
        });
      } else if (data.type === 'request') {
        // Replace logs with requested batch
        setLogs(data.logs || []);
      }
    });

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [useWebSocket]);

  // Auto-scroll effect
  useEffect(() => {
    if (autoScroll && logEndRef.current && logEndRef.current.scrollIntoView) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Fallback polling function
  const loadLogs = async () => {
    try {
      const data = await api.getLogs(200);
      setLogs(data.logs || []);
    } catch (error) {
      console.error('Failed to load logs:', error);
    } finally {
      setLoading(false);
    }
  };

  // Manual refresh function
  const refreshLogs = () => {
    if (socketRef.current && useWebSocket) {
      socketRef.current.emit('request_logs', { lines: 200 });
    } else {
      loadLogs();
    }
  };

  const filteredLogs = logs.filter(log => log.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Server Logs</h1>

      {/* Controls */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6 flex gap-4 items-center flex-wrap">
        <input
          type="text"
          placeholder="Filter logs..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="flex-1 min-w-[200px] bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:outline-none focus:border-primary-500"
        />
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={e => setAutoScroll(e.target.checked)}
            className="w-4 h-4"
          />
          <span>Auto-scroll</span>
        </label>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-gray-500'}`}
            title={connected ? 'WebSocket connected' : 'WebSocket disconnected'}
          />
          <span className="text-sm text-gray-400">
            {useWebSocket ? (connected ? 'Live' : 'Connecting...') : 'Polling'}
          </span>
        </div>
        <button
          onClick={refreshLogs}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Log Display */}
      <div className="bg-gray-800 rounded-lg p-4">
        {loading ? (
          <div className="text-center py-8">Loading logs...</div>
        ) : (
          <div className="font-mono text-sm overflow-auto max-h-[600px]">
            {filteredLogs.length === 0 ? (
              <div className="text-gray-400 text-center py-8">No logs found</div>
            ) : (
              filteredLogs.map((log, index) => (
                <div
                  key={index}
                  className={`py-1 px-2 hover:bg-gray-700 ${
                    log.includes('ERROR') || log.includes('WARN')
                      ? 'text-red-400'
                      : log.includes('INFO')
                        ? 'text-blue-400'
                        : 'text-gray-300'
                  }`}
                >
                  {log}
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default Logs;
