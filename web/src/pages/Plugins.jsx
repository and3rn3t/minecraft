import { useEffect, useState } from 'react';
import { ErrorState } from '../components/ui/Alert';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { PageHeader } from '../components/ui/PageHeader';
import { api } from '../services/api';

const Plugins = () => {
  const [plugins, setPlugins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPlugins();
  }, []);

  const loadPlugins = async () => {
    try {
      const data = await api.listPlugins();
      setPlugins(data.plugins || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load plugins:', err);
      setError('Could not load plugins.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader title="PLUGIN MANAGEMENT" />

      {error && <ErrorState message={error} onRetry={loadPlugins} />}

      <Card padding="lg">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING PLUGINS...
          </div>
        ) : error ? null : plugins.length === 0 ? (
          <EmptyState icon="🧩" title="NO PLUGINS INSTALLED" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plugins.map(plugin => (
              <Card key={plugin.filename} padding="md">
                <h3 className="text-sm font-minecraft text-minecraft-text-light mb-1 leading-tight">
                  {plugin.name}
                </h3>
                <p className="text-[10px] font-minecraft text-minecraft-text-dark mb-2">
                  v{plugin.version}{' '}
                  <Badge status={plugin.enabled ? 'success' : 'neutral'}>
                    {plugin.enabled ? 'ENABLED' : 'DISABLED'}
                  </Badge>
                </p>
                <div className="flex gap-2 mt-4">
                  <Button variant="primary" size="sm" className="flex-1" disabled={plugin.enabled}>
                    ENABLE
                  </Button>
                  <Button variant="danger" size="sm" className="flex-1" disabled={!plugin.enabled}>
                    DISABLE
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

export default Plugins;
