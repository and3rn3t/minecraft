import { cn } from '../../utils/cn';

/**
 * Composable table primitives, replacing the 4 hand-rolled <table>s in the
 * app (Users, AuditLogs, ApiKeys, Backups) that had drifted to 2 different
 * header treatments and, in every case, no <caption>, no <th scope> and no
 * `overflow-x-auto` wrapper for narrow viewports.
 *
 * Deliberately not a rows/columns data-grid — the 4 real tables this
 * replaces have genuinely different columns and per-row actions, so
 * composing <TableRow>/<TableCell> yourself fits them better than a rigid
 * generic API would.
 */
export function Table({ caption, className, children, ...props }) {
  return (
    <div className="overflow-x-auto">
      <table className={cn('w-full text-left', className)} {...props}>
        {caption && <caption className="sr-only">{caption}</caption>}
        {children}
      </table>
    </div>
  );
}

export function TableHead({ children }) {
  return <thead>{children}</thead>;
}

export function TableBody({ children }) {
  return <tbody>{children}</tbody>;
}

export function TableRow({ className, children, ...props }) {
  return (
    <tr className={cn('border-b-2 border-minecraft-stone', className)} {...props}>
      {children}
    </tr>
  );
}

export function TableHeaderCell({ className, children, ...props }) {
  return (
    <th
      scope="col"
      className={cn(
        'px-4 py-3 text-[10px] font-minecraft uppercase text-minecraft-text-light',
        className
      )}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableCell({ className, children, ...props }) {
  return (
    <td className={cn('px-4 py-3 text-[10px] font-minecraft text-minecraft-text-light', className)} {...props}>
      {children}
    </td>
  );
}
