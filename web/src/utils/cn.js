import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combine class names, with later Tailwind utilities winning over earlier
 * ones that target the same CSS property (e.g. cn('p-4', condition && 'p-6')
 * resolves to just 'p-6', not both). Non-Tailwind classes (card-minecraft,
 * btn-minecraft, ...) pass through unaffected.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
