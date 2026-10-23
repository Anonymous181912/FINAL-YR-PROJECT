import * as React from 'react'
import { cn } from '../../utils/cn'

export function FormField({
  id,
  label,
  hint,
  error,
  required,
  children,
  className,
}) {
  const generatedId = React.useId()
  const fieldId = id || generatedId
  const hintId = `${fieldId}-hint`
  const errorId = `${fieldId}-error`

  return (
    <div className={cn('flex flex-col space-y-1.5 mb-4', className)}>
      {label && (
        <label
          htmlFor={fieldId}
          className="text-sm font-semibold text-foreground flex items-center justify-between"
        >
          <span>
            {label}
            {required && <span className="text-status-danger ml-1" aria-hidden="true">*</span>}
          </span>
        </label>
      )}

      {/* Clone children to inject id and aria-describedby if needed */}
      {React.isValidElement(children)
        ? React.cloneElement(children, {
            id: fieldId,
            'aria-invalid': !!error,
            'aria-describedby': error ? errorId : hint ? hintId : undefined,
            required,
            className: cn(
              children.props.className,
              error && 'border-status-danger focus-visible:ring-status-danger'
            ),
          })
        : children}

      {hint && !error && (
        <p id={hintId} className="text-xs text-foreground-subtle">
          {hint}
        </p>
      )}

      {error && (
        <p id={errorId} className="text-xs font-medium text-status-danger animate-fadeIn">
          {error}
        </p>
      )}
    </div>
  )
}
