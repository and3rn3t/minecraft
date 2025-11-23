const StatusCard = ({ title, value, status, icon, subtitle, onClick }) => {
  const statusColors = {
    success: {
      bg: 'bg-minecraft-grass-DEFAULT',
      light: 'bg-minecraft-grass-light',
      border: 'border-minecraft-grass-light',
      glow: 'shadow-[0_0_15px_rgba(124,179,66,0.3)]',
    },
    error: {
      bg: 'bg-[#C62828]',
      light: 'bg-[#F44336]',
      border: 'border-[#F44336]',
      glow: 'shadow-[0_0_15px_rgba(198,40,40,0.3)]',
    },
    warning: {
      bg: 'bg-[#F57C00]',
      light: 'bg-[#FFB74D]',
      border: 'border-[#FFB74D]',
      glow: 'shadow-[0_0_15px_rgba(245,124,0,0.3)]',
    },
    info: {
      bg: 'bg-minecraft-water-DEFAULT',
      light: 'bg-minecraft-water-light',
      border: 'border-minecraft-water-light',
      glow: 'shadow-[0_0_15px_rgba(33,150,243,0.3)]',
    },
  };

  const colors = statusColors[status] || statusColors.info;

  return (
    <div
      className={`card-minecraft p-6 relative overflow-hidden hover:scale-[1.02] transition-transform duration-200 ${
        onClick ? 'cursor-pointer' : ''
      } ${colors.glow}`}
      onClick={onClick}
      onKeyDown={onClick ? e => e.key === 'Enter' && onClick() : undefined}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Animated background gradient */}
      <div
        className={`absolute top-0 right-0 w-32 h-32 ${colors.bg} opacity-10 rounded-full blur-2xl transform translate-x-8 -translate-y-8`}
      />

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[10px] font-minecraft text-minecraft-text-dark uppercase tracking-wide">
            {title}
          </h3>
          <span
            className="text-2xl transition-transform duration-200 hover:scale-110"
            style={{ imageRendering: 'pixelated' }}
          >
            {icon}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div
            className={`w-4 h-4 ${colors.bg} ${colors.border} border-2 animate-pulse`}
            style={{ imageRendering: 'pixelated' }}
          />
          <div>
            <p className="text-xl font-minecraft text-minecraft-text-light leading-tight">
              {value}
            </p>
            {subtitle && (
              <p className="text-[8px] font-minecraft text-minecraft-text-dark mt-1">{subtitle}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusCard;
