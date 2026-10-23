import * as React from 'react'
import { Check, ArrowDown, ArrowUp, HelpCircle } from 'lucide-react'
import { cn } from '../../utils/cn'

export function LabBadge({ flag, className }) {
  const f = String(flag || '').toLowerCase()

  const config = {
    normal: {
      label: 'Normal',
      icon: Check,
      classes: 'bg-status-success-bg text-status-success border-status-success-border',
    },
    low: {
      label: 'Low',
      icon: ArrowDown,
      classes: 'bg-status-info-bg text-status-info border-status-info-border',
    },
    high: {
      label: 'High',
      icon: ArrowUp,
      classes: 'bg-status-danger-bg text-status-danger border-status-danger-border',
    },
    unknown: {
      label: 'Unknown',
      icon: HelpCircle,
      classes: 'bg-surface-2 text-foreground-muted border-border',
    },
  }[f] || {
    label: 'Normal',
    icon: Check,
    classes: 'bg-status-success-bg text-status-success border-status-success-border',
  }

  const Icon = config.icon

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border tabular-nums',
        config.classes,
        className
      )}
    >
      <Icon className="w-3 h-3 stroke-[2.5]" />
      <span>{config.label}</span>
    </span>
  )
}
