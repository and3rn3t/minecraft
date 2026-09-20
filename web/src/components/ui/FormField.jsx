import { useId } from 'react';
import { cn } from '../../utils/cn';

function FieldWrapper({ fieldId, label, error, hint, required, className, children }) {
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {label && (
        <label
          htmlFor={fieldId}
          className="text-[8px] font-minecraft text-minecraft-text-dark uppercase tracking-wide"
        >
          {label}
          {required && (
            <span className="ml-1 text-minecraft-danger-light" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      {children}
      {hint && !error && (
        <p id={hintId} className="text-[8px] font-minecraft text-minecraft-text-dark">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-[8px] font-minecraft text-minecraft-danger-light">
          {error}
        </p>
      )}
    </div>
  );
}

// Every form control below always renders a real <label htmlFor>, always
// wires aria-invalid/aria-describedby to its own error text, and always
// gets a stable id (generated via useId when the caller doesn't pass one).
// This is the fix for the 11 orphaned <label>s and the handful of controls
// with no label at all found across the app.

export function Input({ label, error, hint, required, id, className, ...props }) {
  const generatedId = useId();
  const fieldId = id || generatedId;
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;

  return (
    <FieldWrapper fieldId={fieldId} label={label} error={error} hint={hint} required={required}>
      <input
        id={fieldId}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          'input-minecraft w-full',
          error && 'border-t-minecraft-danger-light border-l-minecraft-danger-light border-r-minecraft-danger-dark border-b-minecraft-danger-dark',
          className
        )}
        {...props}
      />
    </FieldWrapper>
  );
}

export function Textarea({ label, error, hint, required, id, className, ...props }) {
  const generatedId = useId();
  const fieldId = id || generatedId;
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;

  return (
    <FieldWrapper fieldId={fieldId} label={label} error={error} hint={hint} required={required}>
      <textarea
        id={fieldId}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn('input-minecraft w-full', className)}
        {...props}
      />
    </FieldWrapper>
  );
}

export function Select({ label, error, hint, required, id, className, children, ...props }) {
  const generatedId = useId();
  const fieldId = id || generatedId;
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;

  return (
    <FieldWrapper fieldId={fieldId} label={label} error={error} hint={hint} required={required}>
      <select
        id={fieldId}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn('input-minecraft w-full', className)}
        {...props}
      >
        {children}
      </select>
    </FieldWrapper>
  );
}
