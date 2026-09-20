import { cn } from '../../utils/cn';
import { useAutoDismiss } from '../../hooks/useAutoDismiss';
import { Button } from './Button';

const TONE_CLASS = {
  danger: 'bg-minecraft-danger border-minecraft-danger-dark',
  success: 'bg-minecraft-success border-minecraft-success-dark',
  warning: 'bg-minecraft-warning border-minecraft-warning-dark',
  info: 'bg-minecraft-info border-minecraft-info-dark',
};

/**
 * A page-level banner. Replaces 7 different error-banner recipes and 2
 * different success-banner recipes found across the app — only 3 of the 7
 * error variants offered a retry action, and the rest were dead ends.
 *
 * Pass `autoDismiss` (ms) + `onDismiss` for the transient case. This
 * replaces `useAutoDismiss`'s 7 separate inline reimplementations, which
 * had drifted to different delays (5000ms in three pages, 3000ms in one,
 * never in six others) instead of using the hook that already existed for
 * exactly this and was imported by nothing. Omit them for a banner that
 * stays until the user acts (a page-level error with a retry button).
 */
export function Alert({ tone = 'info', children, onDismiss, autoDismiss, action, className }) {
  useAutoDismiss(autoDismiss ? children : null, onDismiss ?? (() => {}), autoDismiss || 0);

  return (
    <div
      role="alert"
      className={cn(
        'card-minecraft mb-6 flex items-center justify-between gap-4 p-4 text-white',
        TONE_CLASS[tone],
        className
      )}
    >
      <p className="text-[10px] font-minecraft leading-relaxed">{children}</p>
      <div className="flex shrink-0 items-center gap-2">
        {action}
        {onDismiss && !autoDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss"
            className="font-minecraft text-lg text-white/80 hover:text-white"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * A page-level failure state: message + retry, matching the RETRY buttons
 * that already exist on Dashboard/Players/Backups/Analytics. Also the fix
 * for Worlds/Plugins/Logs silently swallowing fetch errors into an empty
 * state ("NO WORLDS FOUND" when the real answer is "could not reach the
 * server") — render this instead of the empty state whenever there's an
 * error, not just when there's no data.
 */
export function ErrorState({ message, onRetry, className }) {
  return (
    <Alert
      tone="danger"
      className={className}
      action={
        onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            RETRY
          </Button>
        )
      }
    >
      {message}
    </Alert>
  );
}
