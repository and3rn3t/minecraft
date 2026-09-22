import { cn } from '../../utils/cn';

/**
 * Replaces 7 different <h1> treatments found across the app's 21 pages
 * (different margins, sizes, some with drop-shadow-lg, and one — Analytics
 * — that dropped the pixel font and uppercase convention entirely).
 */
export function PageHeader({ title, subtitle, actions, lastUpdated, className }) {
  return (
    <div className={cn('mb-8 flex flex-wrap items-start justify-between gap-4', className)}>
      <div>
        <h1 className="text-2xl font-minecraft text-minecraft-grass-light leading-tight">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-2 text-[10px] font-minecraft text-minecraft-text-dark">{subtitle}</p>
        )}
        {lastUpdated && (
          <p className="mt-1 text-[8px] font-minecraft text-minecraft-text-dark">
            LAST UPDATED {lastUpdated}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
