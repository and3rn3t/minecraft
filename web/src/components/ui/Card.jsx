import { cn } from '../../utils/cn';

const PADDING_CLASS = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

/**
 * The themed card, wrapping .card-minecraft. Existing usage split across
 * p-2/p-3/p-4/p-6/p-8 with no rule for which container gets which — `padding`
 * gives that a name. `animateIn` opts into the fade-in the class used to
 * apply unconditionally on every mount (65 uses), which read as flicker
 * under a 5s poll; it's off by default now.
 */
export function Card({
  as: Tag = 'div',
  padding = 'md',
  animateIn = false,
  accent,
  className,
  children,
  ...props
}) {
  return (
    <Tag
      className={cn(
        'card-minecraft relative',
        PADDING_CLASS[padding],
        animateIn && 'animate-fadeIn',
        className
      )}
      {...props}
    >
      {accent && (
        <div className={cn('absolute inset-x-0 top-0 h-1', accent)} aria-hidden="true" />
      )}
      {children}
    </Tag>
  );
}
