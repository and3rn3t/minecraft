import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const MetricsChart = ({ metrics }) => {
  const cpuPercent = parseFloat(metrics.metrics?.cpu_percent?.replace('%', '') || 0);
  const memoryPercent = parseFloat(metrics.metrics?.memory_percent?.replace('%', '') || 0);

  const data = [
    {
      name: 'CPU',
      value: cpuPercent,
    },
    {
      name: 'Memory',
      value: memoryPercent,
    },
  ];

  const getStatusColor = value => {
    if (value >= 80) return '#C62828'; // Red
    if (value >= 60) return '#F57C00'; // Orange
    return '#7CB342'; // Green
  };

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
              className="w-4 h-4"
              style={{ backgroundColor: getStatusColor(cpuPercent), imageRendering: 'pixelated' }}
            />
            <p className="text-2xl font-minecraft text-minecraft-text-light">
              {metrics.metrics?.cpu_percent || 'N/A'}
            </p>
          </div>
          <div className="mt-4 bg-minecraft-dirt-DEFAULT h-3 border-2 border-[#5D4037] overflow-hidden">
            <div
              className="h-full transition-all duration-500 ease-out"
              style={{
                width: `${cpuPercent}%`,
                backgroundColor: getStatusColor(cpuPercent),
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
              className="w-4 h-4"
              style={{
                backgroundColor: getStatusColor(memoryPercent),
                imageRendering: 'pixelated',
              }}
            />
            <p className="text-2xl font-minecraft text-minecraft-text-light">
              {metrics.metrics?.memory_usage || 'N/A'}
            </p>
          </div>
          <div className="mt-4 bg-minecraft-dirt-DEFAULT h-3 border-2 border-[#5D4037] overflow-hidden">
            <div
              className="h-full transition-all duration-500 ease-out"
              style={{
                width: `${memoryPercent}%`,
                backgroundColor: getStatusColor(memoryPercent),
              }}
            />
          </div>
        </div>
      </div>

      {/* Chart */}
      {data.length > 0 && (
        <div className="card-minecraft p-4">
          <div className="bg-minecraft-dirt-DEFAULT p-4">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#5D4037" />
                <XAxis
                  dataKey="name"
                  tick={{
                    fill: '#E0E0E0',
                    fontSize: 10,
                    fontFamily: '"Press Start 2P", monospace',
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{
                    fill: '#E0E0E0',
                    fontSize: 10,
                    fontFamily: '"Press Start 2P", monospace',
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#6D4C41',
                    border: '2px solid #5D4037',
                    borderRadius: 0,
                    color: '#E0E0E0',
                    fontFamily: '"Press Start 2P", monospace',
                    fontSize: '10px',
                  }}
                />
                <Bar dataKey="value" fill="#7CB342" stroke="#558B2F" strokeWidth={2} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default MetricsChart;
