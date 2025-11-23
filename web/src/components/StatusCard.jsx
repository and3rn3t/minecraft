const StatusCard = ({ title, value, status, icon }) => {
  const statusColors = {
    success: 'bg-minecraft-grass-DEFAULT',
    error: 'bg-[#C62828]',
    warning: 'bg-[#F57C00]',
    info: 'bg-minecraft-water-DEFAULT',
  }

  return (
    <div className="card-minecraft p-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] font-minecraft text-minecraft-text-dark uppercase">{title}</h3>
        <span className="text-xl">{icon}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 ${statusColors[status] || statusColors.info]}`} style={{ imageRendering: 'pixelated' }}></div>
        <p className="text-lg font-minecraft text-minecraft-text-light">{value}</p>
      </div>
    </div>
  )
}

export default StatusCard

