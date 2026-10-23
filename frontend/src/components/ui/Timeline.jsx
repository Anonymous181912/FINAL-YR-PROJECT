import * as React from 'react'
import { FileText, Pill, Stethoscope, Calendar, ChevronRight } from 'lucide-react'
import { cn } from '../../utils/cn'

export function Timeline({ items = [], onItemClick, className }) {
  if (!items || items.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-foreground-muted border border-border rounded-card bg-surface">
        No events found in timeline.
      </div>
    )
  }

  const getEventIcon = (type) => {
    switch (type) {
      case 'report':
        return FileText
      case 'prescription':
        return Pill
      case 'consultation':
      case 'visit':
        return Stethoscope
      default:
        return Calendar
    }
  }

  return (
    <div className={cn('relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border', className)}>
      {items.map((item, idx) => {
        const Icon = getEventIcon(item.type)
        return (
          <div
            key={item.id || idx}
            onClick={() => onItemClick?.(item)}
            className={cn(
              'relative group flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-item border border-border bg-surface shadow-subtle transition-all',
              onItemClick && 'cursor-pointer hover:border-accent/60 hover:shadow-card active:scale-[0.99]'
            )}
          >
            {/* Timeline bullet icon */}
            <div className="absolute -left-[30px] top-4 w-4 h-4 rounded-full bg-surface border-2 border-accent flex items-center justify-center">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            </div>

            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-item bg-accent-soft text-accent flex items-center justify-center shrink-0 mt-0.5">
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold text-foreground font-heading">{item.title}</h4>
                  {item.badge && <span className="text-xs">{item.badge}</span>}
                </div>
                {item.description && (
                  <p className="text-xs text-foreground-muted mt-0.5 max-w-xl line-clamp-2">
                    {item.description}
                  </p>
                )}
                {item.subtitle && (
                  <span className="text-xs text-foreground-subtle mt-1">{item.subtitle}</span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 self-end sm:self-center shrink-0">
              <span className="text-xs text-foreground-subtle tabular-nums">
                {item.date ? new Date(item.date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : ''}
              </span>
              {onItemClick && (
                <ChevronRight className="w-4 h-4 text-foreground-subtle group-hover:text-accent transition-transform group-hover:translate-x-0.5" />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
