import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';

// Death categories, with an icon for each. Anything the backend classifies as
// 'unknown' falls through to the default.
const CATEGORY_ICONS = {
  combat: '⚔️',
  explosion: '💥',
  lava: '🌋',
  fire: '🔥',
  fall: '🪂',
  void: '🕳️',
  drowning: '🌊',
  starvation: '🍗',
  dehydration: '🏜️',
  freezing: '🧊',
  lightning: '⚡',
  crushing: '🧱',
  spikes: '🗿',
  prickly: '🌵',
  magic: '🔮',
  sonic: '📢',
  kinetic: '🚀',
  unknown: '❓',
};

const CATEGORY_LABELS = {
  combat: 'Slain',
  explosion: 'Exploded',
  lava: 'Lava',
  fire: 'Burned',
  fall: 'Fell',
  void: 'The Void',
  drowning: 'Drowned',
  starvation: 'Starved',
  dehydration: 'Dehydrated',
  freezing: 'Froze',
  lightning: 'Lightning',
  crushing: 'Crushed',
  spikes: 'Impaled',
  prickly: 'Prickled',
  magic: 'Magic',
  sonic: 'Sonic Boom',
  kinetic: 'Kinetic',
  unknown: 'Mysterious',
};

const iconFor = category => CATEGORY_ICONS[category] || CATEGORY_ICONS.unknown;
const labelFor = category => CATEGORY_LABELS[category] || CATEGORY_LABELS.unknown;

// A "favourite" way to die only means something once it has happened more than
// once. Somebody who died three times in three different ways has no mode, so
// showing their latest death is honest where "mostly" would not be.
const habitFor = entry => {
  if (entry.favourite_cause_count >= 2) {
    return { prefix: 'MOSTLY', category: entry.favourite_cause };
  }
  return { prefix: 'LATELY', category: entry.last_category || entry.favourite_cause };
};

const formatWhen = timestamp => {
  if (!timestamp) return '';
  const when = new Date(timestamp);
  if (Number.isNaN(when.getTime())) return '';
  return when.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const HallOfDeaths = () => {
  const [deaths, setDeaths] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [stats, setStats] = useState(null);
  const [playerFilter, setPlayerFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [recent, board] = await Promise.all([
        api.getDeaths({ limit: 50, player: playerFilter || null }),
        api.getDeathsLeaderboard(),
      ]);
      setDeaths(recent.deaths || []);
      setStats(recent.stats || null);
      setLeaderboard(board.leaderboard || []);
    } catch (err) {
      console.error('Failed to load the Hall of Deaths:', err);
      setError('Could not load the Hall of Deaths.');
    } finally {
      setLoading(false);
    }
  }, [playerFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const noDeathsYet = !loading && deaths.length === 0 && !playerFilter;

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-2 leading-tight">
        HALL OF DEATHS
      </h1>
      <p className="text-[10px] font-minecraft text-minecraft-text-dark mb-8 leading-relaxed">
        EVERY DEMISE, DULY RECORDED
      </p>

      {error && (
        <div className="card-minecraft p-4 mb-6 border-minecraft-redstone">
          <p className="text-[10px] font-minecraft text-red-400">{error}</p>
        </div>
      )}

      {stats && stats.total_deaths > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="card-minecraft p-4">
            <p className="text-[8px] font-minecraft text-minecraft-text-dark mb-2">TOTAL DEATHS</p>
            <p className="text-xl font-minecraft text-minecraft-text-light">{stats.total_deaths}</p>
          </div>
          <div className="card-minecraft p-4">
            <p className="text-[8px] font-minecraft text-minecraft-text-dark mb-2">THE FALLEN</p>
            <p className="text-xl font-minecraft text-minecraft-text-light">{stats.players}</p>
          </div>
          <div className="card-minecraft p-4">
            <p className="text-[8px] font-minecraft text-minecraft-text-dark mb-2">USUAL CAUSE</p>
            <p className="text-sm font-minecraft text-minecraft-text-light leading-tight">
              {iconFor(stats.most_common_cause)} {labelFor(stats.most_common_cause)}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="card-minecraft p-6">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
              <h2 className="text-sm font-minecraft text-minecraft-text-light leading-tight">
                RECENT OBITUARIES
              </h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={playerFilter}
                  onChange={event => setPlayerFilter(event.target.value)}
                  placeholder="FILTER BY PLAYER"
                  className="bg-minecraft-background-dark border-2 border-[#5D4037] px-3 py-2 text-[8px] font-minecraft text-minecraft-text-light placeholder:text-minecraft-text-dark"
                />
                <button onClick={load} className="btn-minecraft text-[8px]">
                  REFRESH
                </button>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
                CONSULTING THE RECORDS...
              </div>
            ) : noDeathsYet ? (
              <div className="text-center py-12">
                <p className="text-2xl mb-4">🕊️</p>
                <p className="text-[10px] font-minecraft text-minecraft-text-light leading-relaxed">
                  NOBODY HAS DIED YET
                </p>
                <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-3 leading-relaxed">
                  GIVE IT TIME
                </p>
              </div>
            ) : deaths.length === 0 ? (
              <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-dark">
                NO DEATHS FOR THAT PLAYER
              </div>
            ) : (
              <ul className="space-y-3">
                {deaths.map((death, index) => (
                  <li
                    key={`${death.timestamp}-${index}`}
                    className="bg-minecraft-dirt-DEFAULT border-2 border-[#5D4037] p-4"
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-xl leading-none" aria-hidden="true">
                        {iconFor(death.category)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-minecraft text-minecraft-text-light leading-relaxed">
                          {death.epitaph}
                        </p>
                        <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-2 leading-relaxed">
                          {labelFor(death.category)}
                          {death.culprit ? ` · ${death.culprit}` : ''}
                          {formatWhen(death.timestamp) ? ` · ${formatWhen(death.timestamp)}` : ''}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div>
          <div className="card-minecraft p-6">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-6 leading-tight">
              LEADERBOARD
            </h2>

            {leaderboard.length === 0 ? (
              <p className="text-[8px] font-minecraft text-minecraft-text-dark text-center py-4">
                NO ENTRIES YET
              </p>
            ) : (
              <ol className="space-y-3">
                {leaderboard.map((entry, index) => (
                  <li
                    key={entry.player}
                    className="bg-minecraft-background-dark border-2 border-[#5D4037] p-3"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-[10px] font-minecraft text-minecraft-text-light truncate">
                        {index + 1}. {entry.player}
                      </span>
                      <span className="text-[10px] font-minecraft text-minecraft-grass-light shrink-0">
                        {entry.deaths}
                      </span>
                    </div>
                    <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-2 leading-relaxed">
                      {habitFor(entry).prefix} {iconFor(habitFor(entry).category)}{' '}
                      {labelFor(habitFor(entry).category)}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HallOfDeaths;
