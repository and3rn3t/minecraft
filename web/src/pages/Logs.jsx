import { useEffect, useMemo, useRef, useState } from 'react';
import { io } from 'socket.io-client';
import { ErrorState } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Input } from '../components/ui/FormField';
import { StatusPill } from '../components/ui/Badge';
import { PageHeader } from '../components/ui/PageHeader';
import { VirtualList } from '../components/VirtualList';
import { useDebounce } from '../hooks/useDebounce';
import { api } from '../services/api';

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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

    // Get API key or JWT — either is accepted by the socket auth handler
    const apiKey = localStorage.getItem('api_key') || import.meta.env.VITE_API_KEY;
    const token = localStorage.getItem('auth_token');
    if (!apiKey && !token) {
      console.warn('No API key or token found, falling back to polling');
      setUseWebSocket(false);
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
      setError(null);
    } catch (err) {
      console.error('Failed to load logs:', err);
      setError('Could not load logs.');
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
      <PageHeader title="SERVER LOGS" />

      {error && <ErrorState message={error} onRetry={refreshLogs} />}

      {/* Controls */}
      <Card padding="md" className="mb-6 flex flex-wrap items-center gap-4">
        <Input
          type="text"
          placeholder="FILTER LOGS..."
          aria-label="Filter logs"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="min-w-[200px] flex-1"
        />
        <label className="flex items-center gap-2 cursor-pointer text-[10px] font-minecraft text-minecraft-text-light">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={e => setAutoScroll(e.target.checked)}
            className="h-4 w-4"
          />
          <span>AUTO-SCROLL</span>
        </label>
        <StatusPill
          status={connected ? 'success' : 'neutral'}
          title={connected ? 'WebSocket connected' : 'WebSocket disconnected'}
        >
          {useWebSocket ? (connected ? 'LIVE' : 'CONNECTING...') : 'POLLING'}
        </StatusPill>
        <Button onClick={refreshLogs}>REFRESH</Button>
      </Card>

      {/* Log Display */}
      <Card padding="md">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING LOGS...
          </div>
        ) : filteredLogs.length === 0 ? (
          <EmptyState icon="📜" title="No logs found" />
        ) : filteredLogs.length > 100 ? (
          // Use virtual scrolling for large lists
          <VirtualList
            items={filteredLogs}
            renderItem={(log, index) => (
              <div
                key={`log-${index}-${log.substring(0, 50)}`}
                className={`py-1 px-2 hover:bg-minecraft-dirt font-minecraft text-[10px] ${
                  log.includes('ERROR') || log.includes('WARN')
                    ? 'text-minecraft-danger'
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
                className={`py-1 px-2 hover:bg-minecraft-dirt ${
                  log.includes('ERROR') || log.includes('WARN')
                    ? 'text-minecraft-danger'
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
      </Card>
    </div>
  );
};

export default Logs;
