import * as React from 'react'
import { cva } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-surface-2 text-foreground border border-border',
        primary: 'bg-accent-soft text-accent border border-accent/20',
        success: 'bg-status-success-bg text-status-success border border-status-success-border',
        warning: 'bg-status-warning-bg text-status-warning border border-status-warning-border',
        danger: 'bg-status-danger-bg text-status-danger border border-status-danger-border',
        info: 'bg-status-info-bg text-status-info border border-status-info-border',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export function Badge({ className, variant, children, ...props }) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {children}
    </span>
  )
}

export function StatusPill({ status, label, className }) {
  const s = String(status || '').toLowerCase()
  let variant = 'default'
  if (['active', 'approved', 'verified', 'completed', 'valid', 'normal'].includes(s)) variant = 'success'
  else if (['pending', 'processing', 'draft', 'moderate', 'low'].includes(s)) variant = 'warning'
  else if (['rejected', 'revoked', 'failed', 'severe', 'high', 'danger'].includes(s)) variant = 'danger'
  else if (['info', 'not_started'].includes(s)) variant = 'info'

  return (
    <Badge variant={variant} className={cn('capitalize font-medium', className)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', {
        'bg-status-success': variant === 'success',
        'bg-status-warning': variant === 'warning',
        'bg-status-danger': variant === 'danger',
        'bg-status-info': variant === 'info',
        'bg-foreground-muted': variant === 'default',
      })} />
      {label || status}
    </Badge>
  )
}
