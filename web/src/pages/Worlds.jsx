import { useEffect, useState } from 'react';
import { ErrorState } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { PageHeader } from '../components/ui/PageHeader';
import { api } from '../services/api';

const Worlds = () => {
  const [worlds, setWorlds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadWorlds();
  }, []);

  const loadWorlds = async () => {
    try {
      const data = await api.listWorlds();
      setWorlds(data.worlds || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load worlds:', err);
      setError('Could not load worlds.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader title="WORLD MANAGEMENT" />

      {error && <ErrorState message={error} onRetry={loadWorlds} />}

      <Card padding="lg">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING WORLDS...
          </div>
        ) : error ? null : worlds.length === 0 ? (
          <EmptyState icon="🗺️" title="NO WORLDS FOUND" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {worlds.map(world => (
              <Card key={world.name} padding="md">
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
                  <Button variant="primary" size="sm" className="flex-1" disabled={world.active}>
                    SWITCH
                  </Button>
                  <Button size="sm" className="flex-1">
                    BACKUP
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default Worlds;
