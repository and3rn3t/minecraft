import { useCallback, useState } from 'react';
import { Alert, ErrorState } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

const formatCountdown = seconds => {
  if (seconds === null || seconds === undefined) return null;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}H ${minutes}M`;
  if (minutes > 0) return `${minutes}M`;
  return 'NOW';
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

const Bedtime = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async signal => {
    try {
      setStatus(await api.getBedtime(signal));
      setError(null);
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') {
        return;
      }
      console.error('Failed to load bedtime status:', err);
      setError('Could not load bedtime status.');
    } finally {
      setLoading(false);
    }
  }, []);

  // usePolling fetches on mount as well as on its interval, so this covers the
  // initial load too. A separate effect here would just fire a second request.
  // The countdown moves on its own, so it needs refreshing regardless.
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
      // A 500 or 503 also carries an `error` field, and showing that as a
      // friendly notice would dress a server failure up as a normal refusal.
      const status = err?.response?.status;
      const detail = err?.response?.data?.error;

      if (status === 409 && detail) {
        setNotice(detail);
        setError(null);
      } else {
        console.error(`Bedtime ${label} failed:`, err);
        setNotice(null);
        setError(detail || `Could not ${label.toLowerCase()}.`);
      }
    } finally {
      setBusy(false);
    }
  };

  const countdown = formatCountdown(status?.seconds_until_bedtime);
  const extensionsLeft = status ? status.extensions_allowed - status.extensions_used : 0;

  return (
    <div>
      <PageHeader title="BEDTIME" subtitle="A WARNED AND ORDERLY END TO THE EVENING" />

      {error && <ErrorState message={error} />}

      {notice && <Alert tone="success">{notice}</Alert>}

      {loading ? (
        <Card padding="lg" className="text-center text-[10px] font-minecraft text-minecraft-text-light">
          CHECKING THE CLOCK...
        </Card>
      ) : !status ? (
        <Card padding="lg" className="text-center text-[10px] font-minecraft text-minecraft-text-dark">
          BEDTIME STATUS UNAVAILABLE
        </Card>
      ) : !status.enabled ? (
        <Card padding="lg">
          <p className="text-[10px] font-minecraft text-minecraft-text-light leading-relaxed mb-3">
            BEDTIME IS OFF
          </p>
          <p className="text-[8px] font-minecraft text-minecraft-text-dark leading-relaxed">
            SET ENABLED=TRUE IN CONFIG/BEDTIME.CONF TO TURN IT ON
          </p>
        </Card>
      ) : (
        <>
          <Card padding="lg" className="mb-6">
            {status.closed ? (
              <>
                <p className="text-[8px] font-minecraft text-minecraft-text-dark mb-3">
                  THE SERVER IS CLOSED
                </p>
                <p className="text-2xl font-minecraft text-minecraft-text-light leading-tight mb-3">
                  GOODNIGHT
                </p>
                <p className="text-[10px] font-minecraft text-minecraft-text-dark leading-relaxed">
                  OPENS AT {status.wake_time}
                </p>
              </>
            ) : (
              <>
                <p className="text-[8px] font-minecraft text-minecraft-text-dark mb-3">
                  {status.skipped_tonight ? 'NO BEDTIME TONIGHT' : 'BEDTIME IN'}
                </p>
                <p className="text-3xl font-minecraft text-minecraft-grass-light leading-tight mb-3">
                  {status.skipped_tonight ? 'SKIPPED' : countdown}
                </p>
                <p className="text-[10px] font-minecraft text-minecraft-text-dark leading-relaxed">
                  {formatWhen(status.next_bedtime)}
                </p>
              </>
            )}
          </Card>

          <Card padding="lg" className="mb-6">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 leading-tight">
              CONTROLS
            </h2>
            <div className="flex flex-wrap gap-3">
              <Button
                variant="primary"
                size="sm"
                onClick={() => act(() => api.extendBedtime(), 'Extend')}
                disabled={busy || extensionsLeft <= 0 || status.closed}
              >
                +{status.extend_minutes} MINUTES ({extensionsLeft} LEFT)
              </Button>
              <Button
                size="sm"
                onClick={() => act(() => api.skipBedtime(), 'Skip')}
                disabled={busy || status.closed || status.skipped_tonight}
              >
                SKIP TONIGHT
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => act(() => api.startBedtimeNow(), 'Start bedtime')}
                disabled={busy || status.closed}
              >
                BEDTIME NOW
              </Button>
            </div>
          </Card>

          <Card padding="lg">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 leading-tight">
              SCHEDULE
            </h2>
            <dl className="space-y-3">
              <div className="flex justify-between gap-4">
                <dt className="text-[8px] font-minecraft text-minecraft-text-dark">SCHOOL NIGHTS</dt>
                <dd className="text-[10px] font-minecraft text-minecraft-text-light">
                  {status.weeknight_bedtime}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[8px] font-minecraft text-minecraft-text-dark">
                  FRIDAY & SATURDAY
                </dt>
                <dd className="text-[10px] font-minecraft text-minecraft-text-light">
                  {status.weekend_bedtime}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[8px] font-minecraft text-minecraft-text-dark">OPENS AGAIN</dt>
                <dd className="text-[10px] font-minecraft text-minecraft-text-light">
                  {status.wake_time}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[8px] font-minecraft text-minecraft-text-dark">AT BEDTIME</dt>
                <dd className="text-[10px] font-minecraft text-minecraft-text-light">
                  {status.action.toUpperCase()}
                </dd>
              </div>
            </dl>
          </Card>
        </>
      )}
    </div>
  );
};

export default Bedtime;
