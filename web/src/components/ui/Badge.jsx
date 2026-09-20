import { cn } from '../../utils/cn';

const BADGE_CLASS = {
  success: 'bg-minecraft-success text-white',
  danger: 'bg-minecraft-danger text-white',
  warning: 'bg-minecraft-warning text-white',
  info: 'bg-minecraft-info text-white',
  neutral: 'bg-minecraft-stone text-white',
};

/**
 * Replaces the app's 4 different recipes for an enabled/disabled-style
 * badge (Users.jsx and ApiKeys.jsx had byte-identical duplicated code for
 * it; Plugins.jsx rendered the same concept as plain unstyled text).
 */
export function Badge({ status = 'neutral', className, children, ...props }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-1 text-[8px] font-minecraft uppercase',
        BADGE_CLASS[status],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

const DOT_CLASS = {
  success: 'bg-minecraft-success-light',
  danger: 'bg-minecraft-danger',
  warning: 'bg-minecraft-warning',
  info: 'bg-minecraft-info',
  neutral: 'bg-minecraft-stone',
};

/**
 * A connected/online-style status dot + label. Replaces 3 different
 * recipes for the same indicator: Dashboard used red-with-pulse for
 * offline, Logs and Console used gray-with-no-pulse — so "disconnected"
 * looked different depending which page you were on.
 */
export function StatusPill({ status = 'neutral', pulse = false, children, className }) {
  return (
    <span className={cn('inline-flex items-center gap-2 text-[10px] font-minecraft', className)}>
      <span
        className={cn('h-2.5 w-2.5 shrink-0', DOT_CLASS[status], pulse && 'animate-pulse')}
        aria-hidden="true"
      />
      {children}
    </span>
  );
}
