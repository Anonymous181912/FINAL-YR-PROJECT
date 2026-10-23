import * as React from 'react'
import { ShieldCheck, Info } from 'lucide-react'
import { cn } from '../../utils/cn'

export function DisclaimerChip({
  type = 'educational', // 'educational' | 'reference-range' | 'drug-safety'
  text,
  className,
}) {
  const defaultText = {
    educational: 'Educational explanation, not a diagnosis',
    'reference-range': 'Reference ranges are educational, not clinical advice',
    'drug-safety': 'Safety flags are educational, not clinical advice',
  }[type] || 'Educational explanation, not a diagnosis'

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors bg-status-info-bg text-status-info border-status-info-border',
        className
      )}
    >
      <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
      <span>{text || defaultText}</span>
    </div>
  )
}
