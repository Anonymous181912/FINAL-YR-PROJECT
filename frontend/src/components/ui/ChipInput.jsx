import * as React from 'react'
import { X, Plus } from 'lucide-react'
import { cn } from '../../utils/cn'

export function ChipInput({
  value = [],
  onChange,
  placeholder = 'Add an item and press Enter...',
  disabled = false,
  className,
}) {
  const [inputValue, setInputValue] = React.useState('')

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const trimmed = inputValue.trim()
      if (trimmed && !value.includes(trimmed)) {
        onChange?.([...value, trimmed])
        setInputValue('')
      }
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      onChange?.(value.slice(0, -1))
    }
  }

  const handleRemove = (indexToRemove) => {
    onChange?.(value.filter((_, idx) => idx !== indexToRemove))
  }

  const handleAddButton = () => {
    const trimmed = inputValue.trim()
    if (trimmed && !value.includes(trimmed)) {
      onChange?.([...value, trimmed])
      setInputValue('')
    }
  }

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-1.5 min-h-[42px] p-1.5 rounded-item border border-border bg-surface text-sm transition-colors focus-within:ring-2 focus-within:ring-accent focus-within:border-transparent',
        disabled && 'opacity-50 pointer-events-none',
        className
      )}
    >
      {value.map((chip, idx) => (
        <span
          key={idx}
          className="inline-flex items-center gap-1 bg-accent-soft text-accent border border-accent/20 px-2.5 py-1 rounded-full text-xs font-medium"
        >
          <span>{chip}</span>
          {!disabled && (
            <button
              type="button"
              onClick={() => handleRemove(idx)}
              className="hover:text-status-danger focus:outline-none ml-0.5"
              aria-label={`Remove ${chip}`}
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </span>
      ))}

      {!disabled && (
        <div className="flex-1 flex items-center min-w-[140px]">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={value.length === 0 ? placeholder : 'Add more...'}
            className="w-full bg-transparent border-none p-1 text-sm text-foreground placeholder:text-foreground-subtle focus:outline-none"
          />
          {inputValue.trim() && (
            <button
              type="button"
              onClick={handleAddButton}
              className="p-1 rounded-md text-accent hover:bg-accent-soft"
              title="Add"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
        </div>
      )}
    </div>
  )
}
