import { useEffect, useId, useRef } from 'react';
import { cn } from '../../utils/cn';

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

/**
 * A real modal: role="dialog", aria-modal, a focus trap, focus restored to
 * whatever opened it on close, Escape to close, and click-outside to close.
 * Replaces the app's only modal (Users.jsx), which had none of these, and
 * the two places in ApiKeys.jsx commented "Modal" that were actually
 * inline cards in document flow rather than overlays. Destructive actions
 * elsewhere in the app go through the OS's native confirm() instead of any
 * of this — routing those through Modal too is a Phase 3 conversion item.
 */
export function Modal({ open, onClose, title, children, className }) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    previouslyFocusedRef.current = document.activeElement;
    const dialog = dialogRef.current;
    const focusable = dialog?.querySelectorAll(FOCUSABLE_SELECTOR);
    (focusable?.[0] || dialog)?.focus();

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = e => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !focusable || focusable.length === 0) {
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = originalOverflow;
      previouslyFocusedRef.current?.focus?.();
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onMouseDown={e => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
        className={cn('card-minecraft w-full max-w-md p-6', className)}
      >
        {title && (
          <h2 id={titleId} className="mb-4 text-sm font-minecraft uppercase text-minecraft-text-light">
            {title}
          </h2>
        )}
        {children}
      </div>
    </div>
  );
}
