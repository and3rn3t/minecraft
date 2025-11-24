import { useEffect, useMemo, useRef, useState } from 'react';
import { io } from 'socket.io-client';
import { VirtualList } from '../components/VirtualList';
import { useDebounce } from '../hooks/useDebounce';
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

  // Debounce filter input to reduce unnecessary filtering
  const debouncedFilter = useDebounce(filter, 300);

  const filteredLogs = useMemo(
    () => logs.filter(log => log.toLowerCase().includes(debouncedFilter.toLowerCase())),
    [logs, debouncedFilter]
  );

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        SERVER LOGS
      </h1>

      {/* Controls */}
      <div className="card-minecraft p-4 mb-6 flex gap-4 items-center flex-wrap">
        <input
          type="text"
          placeholder="FILTER LOGS..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="input-minecraft flex-1 min-w-[200px]"
        />
        <label className="flex items-center gap-2 cursor-pointer text-[10px] font-minecraft text-minecraft-text-light">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={e => setAutoScroll(e.target.checked)}
            className="w-4 h-4"
          />
          <span>AUTO-SCROLL</span>
        </label>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 ${connected ? 'bg-minecraft-grass-DEFAULT' : 'bg-minecraft-stone-DEFAULT'}`}
            title={connected ? 'WebSocket connected' : 'WebSocket disconnected'}
            style={{ imageRendering: 'pixelated' }}
          />
          <span className="text-[10px] font-minecraft text-minecraft-text-dark">
            {useWebSocket ? (connected ? 'LIVE' : 'CONNECTING...') : 'POLLING'}
          </span>
        </div>
        <button onClick={refreshLogs} className="btn-minecraft text-[10px]">
          REFRESH
        </button>
      </div>

      {/* Log Display */}
      <div className="card-minecraft p-4">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING LOGS...
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-minecraft-text-dark text-center py-8">NO LOGS FOUND</div>
        ) : filteredLogs.length > 100 ? (
          // Use virtual scrolling for large lists
          <VirtualList
            items={filteredLogs}
            renderItem={(log, index) => (
              <div
                key={`log-${index}-${log.substring(0, 50)}`}
                className={`py-1 px-2 hover:bg-minecraft-dirt-DEFAULT font-minecraft text-[10px] ${
                  log.includes('ERROR') || log.includes('WARN')
                    ? 'text-[#C62828]'
                    : log.includes('INFO')
                      ? 'text-minecraft-water-light'
                      : 'text-minecraft-text-light'
                }`}
              >
                {log}
              </div>
            )}
            itemHeight={24}
            containerHeight={600}
            overscan={10}
            className="font-minecraft text-[10px]"
          />
        ) : (
          // Regular list for smaller datasets
          <div className="font-minecraft text-[10px] overflow-auto max-h-[600px]">
            {filteredLogs.map((log, index) => (
              <div
                key={`log-${index}-${log.substring(0, 50)}`}
                className={`py-1 px-2 hover:bg-minecraft-dirt-DEFAULT ${
                  log.includes('ERROR') || log.includes('WARN')
                    ? 'text-[#C62828]'
                    : log.includes('INFO')
                      ? 'text-minecraft-water-light'
                      : 'text-minecraft-text-light'
                }`}
              >
                {log}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default Logs;
