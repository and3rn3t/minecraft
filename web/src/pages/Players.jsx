import { useState, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import { usePolling } from '../hooks/usePolling';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { useToast } from '../components/ToastContainer';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/Alert';
import { PageHeader } from '../components/ui/PageHeader';

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
    useCallback(async signal => {
      const [playersData, opsData] = await Promise.all([
        api.getPlayers(signal),
        api.getOps(signal),
      ]);
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
      <PageHeader title="PLAYER MANAGEMENT" />

      {pollingError && <ErrorState message="Failed to load players" onRetry={refetch} />}

      <Card padding="lg">
        <h2 className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
          Online Players ({players.length})
        </h2>
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING...
          </div>
        ) : players.length === 0 ? (
          <EmptyState icon="💤" title="No players online" />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {players.map((player, index) => {
              const isOp = opNames.has(player);
              const isToggling = opPlayerName === player;
              let opButtonLabel = isOp ? 'DEOP' : 'OP';
              if (isToggling) {
                opButtonLabel = '...';
              }
              return (
                <Card key={`${player}-${index}`} padding="md" className="flex flex-col gap-2 bg-minecraft-dirt">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-minecraft text-minecraft-text-light">
                      {player}
                    </span>
                    {isOp && <Badge status="success">OP</Badge>}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleToggleOp(player, isOp)}
                      disabled={isToggling}
                    >
                      {opButtonLabel}
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleKick(player)}
                      disabled={kickingPlayer === player}
                    >
                      {kickingPlayer === player ? 'KICKING...' : 'KICK'}
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
};

export default Players;
