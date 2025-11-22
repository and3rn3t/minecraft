const StatusCard = ({ title, value, status, icon }) => {
  const statusColors = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    warning: 'bg-yellow-600',
    info: 'bg-blue-600',
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${statusColors[status] || statusColors.info}`}></div>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  )
}

export default StatusCard

