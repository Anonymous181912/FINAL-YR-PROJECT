import * as React from 'react'
import { cn } from '../../utils/cn'

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  className,
}) {
  return (
    <div
      className={cn(
        'rounded-card border border-border bg-surface p-5 shadow-card flex items-start justify-between transition-all hover:border-border/80',
        className
      )}
    >
      <div className="flex flex-col space-y-1">
        <span className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
          {title}
        </span>
        <span className="text-2xl font-bold font-heading text-foreground tabular-nums">
          {value}
        </span>
        {subtitle && (
          <span className="text-xs text-foreground-subtle flex items-center gap-1">
            {subtitle}
          </span>
        )}
      </div>
      {Icon && (
        <div className="w-10 h-10 rounded-item bg-accent-soft text-accent flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5" />
        </div>
      )}
    </div>
  )
}

export function PageHeader({
  title,
  description,
  action,
  breadcrumbs = [],
  className,
}) {
  return (
    <div className={cn('flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6', className)}>
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-foreground-subtle mb-1.5">
            {breadcrumbs.map((b, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <span>/</span>}
                {b.href ? (
                  <a href={b.href} className="hover:text-accent transition-colors">
                    {b.label}
                  </a>
                ) : (
                  <span>{b.label}</span>
                )}
              </React.Fragment>
            ))}
          </div>
        )}
        <h1 className="text-2xl md:text-3xl font-bold font-heading tracking-tight text-foreground">
          {title}
        </h1>
        {description && (
          <p className="text-sm text-foreground-muted mt-1">
            {description}
          </p>
        )}
      </div>
      {action && <div className="flex items-center gap-2 shrink-0">{action}</div>}
    </div>
  )
}
