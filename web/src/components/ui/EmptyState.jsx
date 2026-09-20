import { cn } from '../../utils/cn';

/**
 * Replaces the app's 5 tiers of empty-state richness (a bare unstyled div,
 * a styled one-liner, a heading with no hint, a heading with a CTA hint,
 * and a fully illustrated 3-part state) with one shape every page uses the
 * same way, so the same kind of "nothing here yet" reads the same
 * everywhere.
 */
export function EmptyState({ icon = '💤', title, hint, action, className }) {
  return (
    <div className={cn('flex flex-col items-center gap-2 py-10 text-center', className)}>
      <span className="text-3xl opacity-50" aria-hidden="true">
        {icon}
      </span>
      <p className="text-[10px] font-minecraft text-minecraft-text-dark">{title}</p>
      {hint && (
        <p className="max-w-xs text-[8px] font-minecraft text-minecraft-text-dark opacity-75">
          {hint}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
