import { useEffect, useState } from 'react';
import { api } from '../services/api';

const Players = () => {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPlayers();
    const interval = setInterval(loadPlayers, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadPlayers = async () => {
    try {
      const data = await api.getPlayers();
      setPlayers(data.players || []);
    } catch (error) {
      console.error('Failed to load players:', error);
    } finally {
      setLoading(false);
    }
  };

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
                key={index}
                className="bg-minecraft-dirt-DEFAULT border-2 border-[#5D4037] p-4 flex items-center justify-between"
              >
                <span className="text-sm font-minecraft text-minecraft-text-light">{player}</span>
                <button className="btn-minecraft-danger text-[8px]">KICK</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Players;
