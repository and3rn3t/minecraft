import { useCallback, useRef, useState } from 'react';
import { Alert, ErrorState } from '../components/ui/Alert';
import { Badge, StatusPill } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/FormField';
import { PageHeader } from '../components/ui/PageHeader';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

const OUTCOME_BADGE = {
  banter: 'success',
  quest_request: 'info',
  no_reply: 'neutral',
  rate_limited: 'warning',
  error: 'danger',
};

const formatWhen = isoString => {
  if (!isoString) return '';
  const when = new Date(isoString);
  if (Number.isNaN(when.getTime())) return isoString;
  return when.toLocaleString(undefined, {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const Oracle = () => {
  const [status, setStatus] = useState(null);
  const [exchanges, setExchanges] = useState([]);
  const [quests, setQuests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const [allowlistInput, setAllowlistInput] = useState('');
  const [rateLimitInput, setRateLimitInput] = useState('4');
  const formInitialized = useRef(false);

  const load = useCallback(async signal => {
    try {
      const [statusResult, exchangesResult, questsResult] = await Promise.all([
        api.getOracleStatus(signal),
        api.getOracleExchanges(50, signal),
        api.getOracleQuests(50, signal),
      ]);
      setStatus(statusResult);
      setExchanges(exchangesResult || []);
      setQuests(questsResult || []);
      setError(null);

      // Only seed the settings form from the server once: re-syncing on
      // every 15s poll would overwrite whatever the user is mid-typing.
      if (!formInitialized.current) {
        formInitialized.current = true;
        setAllowlistInput((statusResult.allowlist || []).join(', '));
        setRateLimitInput(String(statusResult.rate_limit_per_minute ?? 4));
      }
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') {
        return;
      }
      console.error('Failed to load Oracle status:', err);
      setError('Could not load the Oracle.');
    } finally {
      setLoading(false);
    }
  }, []);

  // usePolling fetches on mount as well as on its interval, covering the
  // initial load too -- a separate effect here would just fire a second
  // request. See Bedtime.jsx for the same pattern.
  usePolling(load, 15000);

  const act = async (action, label) => {
    setBusy(true);
    setNotice(null);
    try {
      const result = await action();
      setStatus(result.status || null);
      setNotice(result.message || `${label} done.`);
      setError(null);
    } catch (err) {
      // Only 409 means "the request was fine, the server will not do it".
      const responseStatus = err?.response?.status;
      const detail = err?.response?.data?.error;

      if (responseStatus === 409 && detail) {
        setNotice(detail);
        setError(null);
      } else {
        console.error(`Oracle ${label} failed:`, err);
        setNotice(null);
        setError(detail || `Could not ${label.toLowerCase()}.`);
      }
    } finally {
      setBusy(false);
    }
  };

  const handleSaveSettings = () => {
    const allowlist = allowlistInput
      .split(',')
      .map(name => name.trim())
      .filter(Boolean);
    const rateLimit = parseInt(rateLimitInput, 10);
    if (Number.isNaN(rateLimit)) {
      setNotice(null);
      setError('Rate limit must be a number.');
      return;
    }
    return act(
      () => api.updateOracleSettings({ allowlist, rate_limit_per_minute: rateLimit }),
      'Save settings'
    );
  };

  return (
    <div>
      <PageHeader title="THE ORACLE" subtitle="A CLAUDE-POWERED COMPANION IN CHAT" />

      {error && <ErrorState message={error} />}

      {notice && <Alert tone="success">{notice}</Alert>}

      {loading ? (
        <Card
          padding="lg"
          className="text-center text-[10px] font-minecraft text-minecraft-text-light"
        >
          CONSULTING THE ORACLE...
        </Card>
      ) : !status ? (
        <Card
          padding="lg"
          className="text-center text-[10px] font-minecraft text-minecraft-text-dark"
        >
          ORACLE STATUS UNAVAILABLE
        </Card>
      ) : (
        <>
          <Card padding="lg" className="mb-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <StatusPill status={status.enabled ? 'success' : 'danger'}>
                {status.enabled ? 'ENABLED' : 'DISABLED'}
              </StatusPill>
              <Button
                variant={status.enabled ? 'danger' : 'primary'}
                size="sm"
                disabled={busy}
                onClick={() =>
                  act(
                    () => (status.enabled ? api.disableOracle() : api.enableOracle()),
                    status.enabled ? 'Disable' : 'Enable'
                  )
                }
              >
                {status.enabled ? 'DISABLE' : 'ENABLE'}
              </Button>
            </div>

            {status.enabled && !status.has_api_key && (
              <p className="mt-4 text-[8px] font-minecraft text-minecraft-danger-light leading-relaxed">
                NO ANTHROPIC_API_KEY IS SET. THE ORACLE IS ENABLED BUT WILL NOT RESPOND TO ANYONE
                UNTIL ONE IS CONFIGURED AS A REAL ENVIRONMENT VARIABLE -- SEE DOCS/ORACLE.MD.
              </p>
            )}

            {!status.enabled && (
              <p className="mt-4 text-[8px] font-minecraft text-minecraft-text-dark leading-relaxed">
                OFF BY DEFAULT. TURNING IT ON ALSO NEEDS ANTHROPIC_API_KEY SET AS A REAL ENVIRONMENT
                VARIABLE -- IT IS NEVER STORED IN CONFIG/ORACLE.CONF.
              </p>
            )}
          </Card>

          <Card padding="lg" className="mb-6">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 leading-tight">
              SETTINGS
            </h2>
            <div className="grid gap-4 sm:grid-cols-[2fr_1fr]">
              <Input
                label="ALLOWLIST"
                hint="COMMA-SEPARATED EXACT MINECRAFT USERNAMES"
                value={allowlistInput}
                onChange={e => setAllowlistInput(e.target.value)}
              />
              <Input
                label="RATE LIMIT / MIN"
                type="number"
                min={1}
                max={60}
                hint="PER PLAYER"
                value={rateLimitInput}
                onChange={e => setRateLimitInput(e.target.value)}
              />
            </div>
            <div className="mt-4">
              <Button variant="primary" size="sm" disabled={busy} onClick={handleSaveSettings}>
                SAVE SETTINGS
              </Button>
            </div>
          </Card>

          <Card padding="lg" className="mb-6">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 leading-tight">
              RECENT EXCHANGES
            </h2>
            {exchanges.length === 0 ? (
              <p className="text-[10px] font-minecraft text-minecraft-text-dark">NOTHING YET</p>
            ) : (
              <ul className="space-y-3">
                {exchanges.map((exchange, index) => (
                  <li
                    key={`${exchange.timestamp}-${index}`}
                    className="border-b-2 border-minecraft-dirt-dark/30 pb-3 last:border-0 last:pb-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                      <span className="text-[10px] font-minecraft text-minecraft-text-light">
                        {exchange.player}
                      </span>
                      <div className="flex items-center gap-2">
                        <Badge status={OUTCOME_BADGE[exchange.outcome] || 'neutral'}>
                          {exchange.outcome.replace('_', ' ')}
                        </Badge>
                        <span className="text-[8px] font-minecraft text-minecraft-text-dark">
                          {formatWhen(exchange.timestamp)}
                        </span>
                      </div>
                    </div>
                    <p className="text-[8px] font-minecraft text-minecraft-text-dark">
                      &quot;{exchange.message}&quot;
                    </p>
                    {exchange.summary && (
                      <p className="text-[8px] font-minecraft text-minecraft-grass-light mt-1">
                        &rarr; {exchange.summary}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card padding="lg">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 leading-tight">
              RECENT QUESTS
            </h2>
            {quests.length === 0 ? (
              <p className="text-[10px] font-minecraft text-minecraft-text-dark">
                NONE YET -- ASK THE ORACLE FOR ONE IN CHAT
              </p>
            ) : (
              <ul className="space-y-3">
                {quests.map(quest => (
                  <li
                    key={quest.id}
                    className="border-b-2 border-minecraft-dirt-dark/30 pb-3 last:border-0 last:pb-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                      <span className="text-[10px] font-minecraft text-minecraft-text-light">
                        {quest.title}
                      </span>
                      <div className="flex items-center gap-2">
                        <Badge status={quest.delivered ? 'success' : 'danger'}>
                          {quest.delivered ? 'DELIVERED' : 'NOT DELIVERED'}
                        </Badge>
                        {quest.claimed && <Badge status="info">CLAIMED</Badge>}
                      </div>
                    </div>
                    <p className="text-[8px] font-minecraft text-minecraft-text-dark">
                      {quest.description}
                    </p>
                    <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-1">
                      FOR {quest.player} &middot; {quest.difficulty.toUpperCase()}
                      {quest.quantity
                        ? ` ×${quest.quantity} ${quest.target}`
                        : ` — ${quest.target}`}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

export default Oracle;
