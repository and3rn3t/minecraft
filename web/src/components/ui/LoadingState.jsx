import { cn } from '../../utils/cn';

/**
 * Replaces the identical centered "LOADING..." div copy-pasted across every
 * page's loading branch, so the label is the only thing that varies.
 */
export function LoadingState({ children = 'LOADING...', className }) {
  return (
    <div className={cn('text-center py-8 text-[10px] font-minecraft text-minecraft-text-light', className)}>
      {children}
    </div>
  );
}
