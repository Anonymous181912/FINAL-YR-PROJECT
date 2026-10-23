import * as React from 'react'
import { cn } from '../../utils/cn'

export function Avatar({ src, name, size = 'md', className }) {
  const [imgError, setImgError] = React.useState(false)

  const sizeClasses = {
    sm: 'w-7 h-7 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-14 h-14 text-base font-bold',
    xl: 'w-20 h-20 text-xl font-bold',
  }[size] || 'w-10 h-10 text-sm'

  const initials = (name || 'User')
    .split(' ')
    .map(n => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div
      className={cn(
        'relative rounded-full flex items-center justify-center font-semibold overflow-hidden shrink-0 border border-border/80 shadow-subtle',
        sizeClasses,
        className
      )}
      style={{
        background: 'linear-gradient(135deg, var(--accent), var(--accent-hover))',
        color: 'var(--on-accent)',
      }}
    >
      {src && !imgError ? (
        <img
          src={src}
          alt={name || 'Avatar'}
          onError={() => setImgError(true)}
          className="w-full h-full object-cover"
        />
      ) : (
        <span>{initials}</span>
      )}
    </div>
  )
}

export function ProgressMeter({
  value = 0,
  max = 100,
  label,
  showPercentage = true,
  className,
}) {
  const percentage = Math.min(100, Math.max(0, Math.round((value / max) * 100)))

  return (
    <div className={cn('w-full flex flex-col space-y-1.5', className)}>
      {(label || showPercentage) && (
        <div className="flex justify-between items-center text-xs font-semibold text-foreground-muted">
          {label && <span>{label}</span>}
          {showPercentage && <span className="tabular-nums">{percentage}%</span>}
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2 border border-border/60">
        <div
          className="h-full bg-accent transition-all duration-300 rounded-full"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
