import { useCallback, useState } from 'react';
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

  const load = useCallback(async () => {
    try {
      setStatus(await api.getBedtime());
      setError(null);
    } catch (err) {
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
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-2 leading-tight">
        BEDTIME
      </h1>
      <p className="text-[10px] font-minecraft text-minecraft-text-dark mb-8 leading-relaxed">
        A WARNED AND ORDERLY END TO THE EVENING
      </p>

      {error && (
        <div className="card-minecraft p-4 mb-6">
          <p className="text-[10px] font-minecraft text-red-400 leading-relaxed">{error}</p>
        </div>
      )}

      {notice && (
        <div className="card-minecraft p-4 mb-6">
          <p className="text-[10px] font-minecraft text-minecraft-grass-light leading-relaxed">
            {notice}
          </p>
        </div>
      )}

      {loading ? (
        <div className="card-minecraft p-6 text-center text-[10px] font-minecraft text-minecraft-text-light">
          CHECKING THE CLOCK...
        </div>
      ) : !status ? (
        <div className="card-minecraft p-6 text-center text-[10px] font-minecraft text-minecraft-text-dark">
          BEDTIME STATUS UNAVAILABLE
        </div>
      ) : !status.enabled ? (
        <div className="card-minecraft p-6">
          <p className="text-[10px] font-minecraft text-minecraft-text-light leading-relaxed mb-3">
            BEDTIME IS OFF
          </p>
          <p className="text-[8px] font-minecraft text-minecraft-text-dark leading-relaxed">
            SET ENABLED=TRUE IN CONFIG/BEDTIME.CONF TO TURN IT ON
          </p>
        </div>
      ) : (
        <>
          <div className="card-minecraft p-6 mb-6">
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
          </div>

          <div className="card-minecraft p-6 mb-6">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 leading-tight">
              CONTROLS
            </h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => act(() => api.extendBedtime(), 'Extend')}
                disabled={busy || extensionsLeft <= 0 || status.closed}
                className="btn-minecraft-primary text-[8px] disabled:opacity-40"
              >
                +{status.extend_minutes} MINUTES ({extensionsLeft} LEFT)
              </button>
              <button
                onClick={() => act(() => api.skipBedtime(), 'Skip')}
                disabled={busy || status.closed || status.skipped_tonight}
                className="btn-minecraft text-[8px] disabled:opacity-40"
              >
                SKIP TONIGHT
              </button>
              <button
                onClick={() => act(() => api.startBedtimeNow(), 'Start bedtime')}
                disabled={busy || status.closed}
                className="btn-minecraft-danger text-[8px] disabled:opacity-40"
              >
                BEDTIME NOW
              </button>
            </div>
          </div>

          <div className="card-minecraft p-6">
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
          </div>
        </>
      )}
    </div>
  );
};

export default Bedtime;
