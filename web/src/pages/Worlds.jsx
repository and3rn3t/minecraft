import { useEffect, useState } from 'react';
import { api } from '../services/api';

const Worlds = () => {
  const [worlds, setWorlds] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorlds();
  }, []);

  const loadWorlds = async () => {
    try {
      const data = await api.listWorlds();
      setWorlds(data.worlds || []);
    } catch (error) {
      console.error('Failed to load worlds:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        WORLD MANAGEMENT
      </h1>

      <div className="card-minecraft p-6">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING WORLDS...
          </div>
        ) : worlds.length === 0 ? (
          <div className="text-minecraft-text-dark text-center py-8 text-[10px] font-minecraft">
            NO WORLDS FOUND
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {worlds.map(world => (
              <div
                key={world.name}
                className="bg-minecraft-dirt border-2 border-[#5D4037] p-4"
              >
                <h3 className="text-sm font-minecraft text-minecraft-text-light mb-1 leading-tight">
                  {world.name}
                  {world.active && (
                    <span className="ml-2 text-[8px] text-minecraft-grass-light">[ACTIVE]</span>
                  )}
                </h3>
                <p className="text-[10px] font-minecraft text-minecraft-text-dark mb-2">
                  {world.type} · {world.size}
                </p>
                <div className="flex gap-2 mt-4">
                  <button className="flex-1 btn-minecraft-primary text-[8px]" disabled={world.active}>
                    SWITCH
                  </button>
                  <button className="flex-1 btn-minecraft text-[8px]">BACKUP</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Worlds;
