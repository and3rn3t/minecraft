import { memo } from 'react';

const StatusCard = ({ title, value, status, icon, subtitle, onClick, index = 0 }) => {
  const statusColors = {
    success: {
      bg: 'bg-minecraft-grass',
      light: 'bg-minecraft-grass-light',
      border: 'border-minecraft-grass-light',
      glow: 'shadow-glow-success',
    },
    error: {
      bg: 'bg-minecraft-danger',
      light: 'bg-minecraft-danger-light',
      border: 'border-minecraft-danger-light',
      glow: 'shadow-glow-danger',
    },
    warning: {
      bg: 'bg-minecraft-warning',
      light: 'bg-minecraft-warning-light',
      border: 'border-minecraft-warning-light',
      glow: 'shadow-glow-warning',
    },
    info: {
      bg: 'bg-minecraft-water',
      light: 'bg-minecraft-water-light',
      border: 'border-minecraft-water-light',
      glow: 'shadow-glow-info',
    },
  };

  const colors = statusColors[status] || statusColors.info;

  return (
    <div
      className={`card-minecraft p-6 relative overflow-hidden hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-200 ${
        onClick ? 'cursor-pointer' : ''
      } ${colors.glow}`}
      style={{ animationDelay: `${index * 80}ms` }}
      onClick={onClick}
      onKeyDown={onClick ? e => e.key === 'Enter' && onClick() : undefined}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Animated background gradient */}
      <div
        className={`absolute top-0 right-0 w-32 h-32 ${colors.bg} opacity-10 rounded-full blur-2xl transform translate-x-8 -translate-y-8`}
      />
      {/* Status accent bar */}
      <div className={`absolute bottom-0 left-0 right-0 h-1 ${colors.bg}`} />

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          {/* h2: these sit directly under the page's h1 (axe heading-order) */}
          <h2 className="text-[10px] font-minecraft text-minecraft-text-dark uppercase tracking-wide">
            {title}
          </h2>
          <span
            className="w-9 h-9 flex items-center justify-center text-lg bg-minecraft-dirt-dark border-2 border-t-minecraft-dirt-light border-l-minecraft-dirt-light border-r-minecraft-background border-b-minecraft-background transition-transform duration-200 hover:scale-110 shrink-0"
            style={{ imageRendering: 'pixelated' }}
          >
            {icon}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div
            className={`w-4 h-4 ${colors.bg} ${colors.border} border-2 animate-pulse shrink-0`}
            style={{ imageRendering: 'pixelated' }}
          />
          <div className="min-w-0">
            <p className="text-xl font-minecraft text-minecraft-text-light leading-tight truncate">
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

export default memo(StatusCard);
