import { useState, useCallback } from 'react';
import { api } from '../services/api';
import { usePolling } from '../hooks/usePolling';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { useToast } from '../components/ToastContainer';

const Players = () => {
  const [kickingPlayer, setKickingPlayer] = useState(null);
  const { success, error } = useToast();
  const handleError = useErrorHandler();

  const { data: playersData, loading } = usePolling(
    useCallback(async () => {
      const data = await api.getPlayers();
      return data.players || [];
    }, []),
    5000
  );

  const players = playersData || [];

  const handleKick = useCallback(
    async (playerName) => {
      if (!confirm(`Are you sure you want to kick ${playerName}?`)) {
        return;
      }

      setKickingPlayer(playerName);
      try {
        await api.sendCommand(`kick ${playerName} Kicked by server administrator`);
        success(`Successfully kicked ${playerName}`);
        // Refresh players list immediately
        setTimeout(() => {
          // Trigger refetch will happen automatically via polling
        }, 1000);
      } catch (err) {
        handleError(err, `Failed to kick ${playerName}`);
      } finally {
        setKickingPlayer(null);
      }
    },
    [success, handleError]
  );

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        PLAYER MANAGEMENT
      </h1>

      <div className="card-minecraft p-6">
        <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
          ONLINE PLAYERS ({players.length})
        </h2>
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING...
          </div>
        ) : players.length === 0 ? (
          <div className="text-minecraft-text-dark text-center py-8 text-[10px] font-minecraft">
            NO PLAYERS ONLINE
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {players.map((player, index) => (
              <div
                key={`${player}-${index}`}
                className="bg-minecraft-dirt-DEFAULT border-2 border-[#5D4037] p-4 flex items-center justify-between"
              >
                <span className="text-sm font-minecraft text-minecraft-text-light">{player}</span>
                <button
                  onClick={() => handleKick(player)}
                  disabled={kickingPlayer === player}
                  className="btn-minecraft-danger text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {kickingPlayer === player ? 'KICKING...' : 'KICK'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Players;
