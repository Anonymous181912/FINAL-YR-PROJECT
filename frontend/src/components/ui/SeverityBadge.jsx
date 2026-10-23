import * as React from 'react'
import { AlertCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react'
import { cn } from '../../utils/cn'

export function SeverityBadge({ severity, className }) {
  const s = String(severity || '').toLowerCase()

  const config = {
    severe: {
      label: 'Attention Needed',
      icon: AlertCircle,
      classes: 'bg-status-danger-bg text-status-danger border-status-danger-border',
    },
    moderate: {
      label: 'Moderate',
      icon: AlertTriangle,
      classes: 'bg-status-warning-bg text-status-warning border-status-warning-border',
    },
    minor: {
      label: 'Minor',
      icon: Info,
      classes: 'bg-status-info-bg text-status-info border-status-info-border',
    },
    normal: {
      label: 'Normal',
      icon: CheckCircle,
      classes: 'bg-status-success-bg text-status-success border-status-success-border',
    },
  }[s] || {
    label: s ? s.charAt(0).toUpperCase() + s.slice(1) : 'Standard',
    icon: Info,
    classes: 'bg-surface-2 text-foreground-muted border-border',
  }

  const Icon = config.icon

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border',
        config.classes,
        className
      )}
    >
      <Icon className="w-3.5 h-3.5" />
      <span>{config.label}</span>
    </span>
  )
}
