import * as React from 'react'
import { Check, Loader2 } from 'lucide-react'
import { cn } from '../../utils/cn'

export function Stepper({ steps = [], currentStep = 0, className }) {
  return (
    <div className={cn('w-full py-4', className)}>
      <div className="flex items-center justify-between relative">
        {/* Connecting bar */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 -translate-y-1/2 bg-border z-0" />
        
        {steps.map((step, idx) => {
          const isDone = idx < currentStep
          const isCurrent = idx === currentStep
          const isPending = idx > currentStep

          return (
            <div key={idx} className="relative z-10 flex flex-col items-center group">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-200 border-2',
                  isDone && 'bg-status-success text-white border-status-success',
                  isCurrent && 'bg-accent text-accent-foreground border-accent ring-4 ring-accent/20 animate-pulse',
                  isPending && 'bg-surface text-foreground-muted border-border'
                )}
              >
                {isDone ? (
                  <Check className="w-4 h-4 stroke-[3]" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  idx + 1
                )}
              </div>
              <span
                className={cn(
                  'text-xs font-medium mt-2 max-w-[80px] text-center truncate',
                  isCurrent && 'text-accent font-bold',
                  isDone && 'text-foreground font-semibold',
                  isPending && 'text-foreground-subtle'
                )}
              >
                {step.label || step}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
