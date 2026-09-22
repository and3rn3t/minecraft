import { memo, useMemo } from 'react';

const getStatusColor = value => {
  if (value >= 80) return '#C62828'; // Red
  if (value >= 60) return '#F57C00'; // Orange
  return '#7CB342'; // Green
};

const MetricsChart = memo(({ metrics }) => {
  const { cpuPercent, memoryPercent } = useMemo(() => {
    const cpu = parseFloat(metrics?.metrics?.cpu_percent?.replace('%', '') || 0);
    const memory = parseFloat(metrics?.metrics?.memory_percent?.replace('%', '') || 0);
    return { cpuPercent: cpu, memoryPercent: memory };
  }, [metrics?.metrics?.cpu_percent, metrics?.metrics?.memory_percent]);

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card-minecraft p-6 hover:scale-[1.02] transition-transform duration-200">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-minecraft text-minecraft-text-dark uppercase">
              CPU Usage
            </p>
            <span className="text-xl">💻</span>
          </div>
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 shrink-0"
              style={{ backgroundColor: getStatusColor(cpuPercent), imageRendering: 'pixelated' }}
            />
            <p className="text-2xl font-minecraft text-minecraft-text-light">
              {metrics.metrics?.cpu_percent || 'N/A'}
            </p>
          </div>
          <div className="mt-4 bg-minecraft-dirt h-3 border-2 border-[#5D4037] overflow-hidden">
            <div
              className="h-full transition-all duration-500 ease-out"
              style={{
                width: `${Math.min(cpuPercent, 100)}%`,
                backgroundColor: getStatusColor(cpuPercent),
                boxShadow: `0 0 8px ${getStatusColor(cpuPercent)}`,
              }}
            />
          </div>
        </div>
        <div className="card-minecraft p-6 hover:scale-[1.02] transition-transform duration-200">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-minecraft text-minecraft-text-dark uppercase">
              Memory Usage
            </p>
            <span className="text-xl">💾</span>
          </div>
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 shrink-0"
              style={{
                backgroundColor: getStatusColor(memoryPercent),
                imageRendering: 'pixelated',
              }}
            />
            <p className="text-2xl font-minecraft text-minecraft-text-light">
              {metrics.metrics?.memory_usage || 'N/A'}
            </p>
            {metrics.metrics?.memory_percent && (
              <span className="text-[8px] font-minecraft text-minecraft-text-dark ml-auto">
                {memoryPercent}%
              </span>
            )}
          </div>
          <div className="mt-4 bg-minecraft-dirt h-3 border-2 border-[#5D4037] overflow-hidden">
            <div
              className="h-full transition-all duration-500 ease-out"
              style={{
                width: `${Math.min(memoryPercent, 100)}%`,
                backgroundColor: getStatusColor(memoryPercent),
                boxShadow: `0 0 8px ${getStatusColor(memoryPercent)}`,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
});

MetricsChart.displayName = 'MetricsChart';

export default MetricsChart;
