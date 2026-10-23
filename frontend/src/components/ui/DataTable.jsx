import * as React from 'react'
import { cn } from '../../utils/cn'

export function DataTable({
  columns = [],
  data = [],
  keyExtractor = (item, idx) => item.id || idx,
  emptyMessage = 'No records found.',
  className,
  onRowClick,
}) {
  if (!data || data.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-foreground-muted border border-border rounded-card bg-surface">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className={cn('w-full', className)}>
      {/* Desktop Table */}
      <div className="hidden md:block overflow-x-auto border border-border rounded-card bg-surface shadow-card">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="border-b border-border bg-surface-2/60 text-xs font-semibold uppercase tracking-wider text-foreground-muted">
              {columns.map((col, idx) => (
                <th
                  key={col.key || idx}
                  className={cn('px-4 py-3.5', col.className)}
                  style={{ width: col.width }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {data.map((row, rowIdx) => {
              const rowKey = keyExtractor(row, rowIdx)
              return (
                <tr
                  key={rowKey}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    'transition-colors hover:bg-surface-2/40',
                    onRowClick && 'cursor-pointer'
                  )}
                >
                  {columns.map((col, colIdx) => (
                    <td key={col.key || colIdx} className={cn('px-4 py-3.5 text-foreground', col.cellClassName)}>
                      {col.render ? col.render(row, rowIdx) : row[col.accessor || col.key]}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Stacked Cards */}
      <div className="md:hidden flex flex-col gap-3">
        {data.map((row, rowIdx) => {
          const rowKey = keyExtractor(row, rowIdx)
          return (
            <div
              key={rowKey}
              onClick={() => onRowClick?.(row)}
              className={cn(
                'border border-border rounded-item bg-surface p-4 shadow-subtle flex flex-col gap-2.5',
                onRowClick && 'cursor-pointer active:bg-surface-2'
              )}
            >
              {columns.map((col, colIdx) => (
                <div key={col.key || colIdx} className="flex justify-between items-center text-sm">
                  <span className="text-xs font-medium text-foreground-muted">
                    {col.header}
                  </span>
                  <div className="text-foreground text-right font-medium">
                    {col.render ? col.render(row, rowIdx) : row[col.accessor || col.key]}
                  </div>
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
