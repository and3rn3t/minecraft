import { useEffect, useState } from 'react';
import { ErrorState } from '../components/ui/Alert';
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
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        PLUGIN MANAGEMENT
      </h1>

      {error && <ErrorState message={error} onRetry={loadPlugins} />}

      <div className="card-minecraft p-6">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING PLUGINS...
          </div>
        ) : error ? null : plugins.length === 0 ? (
          <div className="text-minecraft-text-dark text-center py-8 text-[10px] font-minecraft">
            NO PLUGINS INSTALLED
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plugins.map(plugin => (
              <div
                key={plugin.filename}
                className="bg-minecraft-dirt border-2 border-[#5D4037] p-4"
              >
                <h3 className="text-sm font-minecraft text-minecraft-text-light mb-1 leading-tight">
                  {plugin.name}
                </h3>
                <p className="text-[10px] font-minecraft text-minecraft-text-dark mb-2">
                  v{plugin.version} · {plugin.enabled ? 'ENABLED' : 'DISABLED'}
                </p>
                <div className="flex gap-2 mt-4">
                  <button
                    className="flex-1 btn-minecraft-primary text-[8px]"
                    disabled={plugin.enabled}
                  >
                    ENABLE
                  </button>
                  <button
                    className="flex-1 btn-minecraft-danger text-[8px]"
                    disabled={!plugin.enabled}
                  >
                    DISABLE
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Plugins;
