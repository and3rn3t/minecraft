import { useState, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import { usePolling } from '../hooks/usePolling';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { useToast } from '../components/ToastContainer';

const Players = () => {
  const [kickingPlayer, setKickingPlayer] = useState(null);
  const [opPlayerName, setOpPlayerName] = useState(null);
  const { success } = useToast();
  const handleError = useErrorHandler();

  const {
    data,
    loading,
    error: pollingError,
    refetch,
  } = usePolling(
    useCallback(async () => {
      const [playersData, opsData] = await Promise.all([api.getPlayers(), api.getOps()]);
      return {
        players: playersData.players || [],
        opNames: new Set((opsData.operators || []).map(op => op.name)),
      };
    }, []),
    5000
  );

  useEffect(() => {
    if (pollingError) {
      handleError(pollingError, 'Failed to load players');
    }
  }, [pollingError, handleError]);

  const players = data?.players || [];
  const opNames = data?.opNames || new Set();

  const handleKick = useCallback(
    async (playerName) => {
      if (!confirm(`Are you sure you want to kick ${playerName}?`)) {
        return;
      }

      setKickingPlayer(playerName);
      try {
        await api.sendCommand(`kick ${playerName} Kicked by server administrator`);
        success(`Successfully kicked ${playerName}`);
        refetch();
      } catch (err) {
        handleError(err, `Failed to kick ${playerName}`);
      } finally {
        setKickingPlayer(null);
      }
    },
    [success, handleError, refetch]
  );

  const handleToggleOp = useCallback(
    async (playerName, isOp) => {
      const verb = isOp ? 'revoke operator status from' : 'grant operator status to';
      if (!confirm(`Are you sure you want to ${verb} ${playerName}?`)) {
        return;
      }

      setOpPlayerName(playerName);
      try {
        if (isOp) {
          await api.deopPlayer(playerName);
          success(`Revoked operator status from ${playerName}`);
        } else {
          await api.opPlayer(playerName, 4);
          success(`Granted operator status to ${playerName}`);
        }
        refetch();
      } catch (err) {
        handleError(err, `Failed to update operator status for ${playerName}`);
      } finally {
        setOpPlayerName(null);
      }
    },
    [success, handleError, refetch]
  );

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        PLAYER MANAGEMENT
      </h1>

      {pollingError && (
        <div className="card-minecraft p-4 mb-6 flex items-center justify-between gap-4">
          <p className="text-[10px] font-minecraft text-red-400 leading-relaxed">
            FAILED TO LOAD PLAYERS
          </p>
          <button onClick={refetch} className="btn-minecraft-danger text-[8px] shrink-0">
            RETRY
          </button>
        </div>
      )}

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
            {players.map((player, index) => {
              const isOp = opNames.has(player);
              const isToggling = opPlayerName === player;
              let opButtonLabel = isOp ? 'DEOP' : 'OP';
              if (isToggling) {
                opButtonLabel = '...';
              }
              return (
                <div
                  key={`${player}-${index}`}
                  className="bg-minecraft-dirt-DEFAULT border-2 border-[#5D4037] p-4 flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-minecraft text-minecraft-text-light">
                      {player}
                    </span>
                    {isOp && (
                      <span className="text-[8px] font-minecraft text-minecraft-grass-light">
                        OP
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleToggleOp(player, isOp)}
                      disabled={isToggling}
                      className="flex-1 btn-minecraft-primary text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {opButtonLabel}
                    </button>
                    <button
                      onClick={() => handleKick(player)}
                      disabled={kickingPlayer === player}
                      className="flex-1 btn-minecraft-danger text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {kickingPlayer === player ? 'KICKING...' : 'KICK'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default Players;
