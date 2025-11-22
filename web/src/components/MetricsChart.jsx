import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const MetricsChart = ({ metrics }) => {
  // For now, display simple metrics
  // In the future, this could show historical data
  const data = [
    {
      name: 'CPU',
      value: parseFloat(metrics.metrics?.cpu_percent?.replace('%', '') || 0),
    },
    {
      name: 'Memory',
      value: parseFloat(metrics.metrics?.memory_percent?.replace('%', '') || 0),
    },
  ]

  return (
    <div className="mt-4">
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-700 rounded p-4">
          <p className="text-sm text-gray-400">CPU Usage</p>
          <p className="text-2xl font-bold">{metrics.metrics?.cpu_percent || 'N/A'}</p>
        </div>
        <div className="bg-gray-700 rounded p-4">
          <p className="text-sm text-gray-400">Memory Usage</p>
          <p className="text-2xl font-bold">{metrics.metrics?.memory_usage || 'N/A'}</p>
        </div>
      </div>
      {data.length > 0 && (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#0ea5e9" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

export default MetricsChart

