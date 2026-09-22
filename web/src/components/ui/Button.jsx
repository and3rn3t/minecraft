import { forwardRef } from 'react';
import { cn } from '../../utils/cn';

const VARIANT_CLASS = {
  primary: 'btn-minecraft-primary',
  danger: 'btn-minecraft-danger',
  secondary: 'btn-minecraft',
};

const SIZE_CLASS = {
  sm: 'text-[8px] px-3 py-1.5',
  md: 'text-[10px] px-4 py-2',
};

/**
 * The themed button, wrapping the existing .btn-minecraft* classes so every
 * button in the app shares one API instead of the ~41 hand-rolled variants
 * this replaces. `ghost` isn't a CSS class — it's the bare bevel look with
 * no fill, for a lower-emphasis action next to a primary one.
 */
export const Button = forwardRef(
  (
    {
      variant = 'secondary',
      size = 'md',
      loading = false,
      disabled = false,
      icon,
      iconLabel,
      className,
      children,
      type = 'button',
      ...props
    },
    ref
  ) => {
    const isGhost = variant === 'ghost';
    const isIconOnly = icon && !children;

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-label={isIconOnly ? iconLabel : undefined}
        aria-busy={loading || undefined}
        className={cn(
          isGhost
            ? 'font-minecraft border-2 border-transparent bg-transparent text-white transition-colors duration-150 hover:border-minecraft-dirt-dark'
            : VARIANT_CLASS[variant],
          SIZE_CLASS[size],
          'inline-flex items-center justify-center gap-2',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
          className
        )}
        {...props}
      >
        {loading ? (
          <span className="inline-block h-3 w-3 animate-spin border-2 border-white border-t-transparent" />
        ) : (
          icon && <span aria-hidden="true">{icon}</span>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
