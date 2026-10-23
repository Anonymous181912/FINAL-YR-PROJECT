import * as React from 'react'
import { cn } from '../../utils/cn'
import { Button } from './Button'

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
  children,
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 md:p-12 text-center rounded-card border border-dashed border-border bg-surface-2/30',
        className
      )}
    >
      {Icon && (
        <div className="w-12 h-12 rounded-full bg-accent-soft text-accent flex items-center justify-center mb-4">
          <Icon className="w-6 h-6" />
        </div>
      )}
      {title && <h4 className="text-base font-bold text-foreground mb-1 font-heading">{title}</h4>}
      {description && <p className="text-sm text-foreground-muted max-w-sm mb-6">{description}</p>}
      {actionLabel && onAction && (
        <Button onClick={onAction} size="sm">
          {actionLabel}
        </Button>
      )}
      {children}
    </div>
  )
}
