import * as React from 'react'
import { UploadCloud, File, AlertCircle } from 'lucide-react'
import { cn } from '../../utils/cn'

export function FileDropzone({
  onFileSelect,
  accept = '.pdf,.png,.jpg,.jpeg,.txt',
  maxSizeMB = 10,
  description,
  className,
  disabled = false,
}) {
  const [dragActive, setDragActive] = React.useState(false)
  const [error, setError] = React.useState('')
  const [selectedFile, setSelectedFile] = React.useState(null)
  const inputRef = React.useRef(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (disabled) return
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const validateAndSelect = (file) => {
    if (disabled) return
    setError('')
    if (!file) return

    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File size exceeds ${maxSizeMB}MB limit.`)
      return
    }

    setSelectedFile(file)
    onFileSelect?.(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (disabled) return
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSelect(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSelect(e.target.files[0])
    }
  }

  return (
    <div className={cn('flex flex-col space-y-2', className)}>
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => {
          if (!disabled) inputRef.current?.click()
        }}
        className={cn(
          'relative flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-card transition-all text-center',
          disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
          dragActive
            ? 'border-accent bg-accent-soft/30 scale-[1.01]'
            : 'border-border bg-surface-2/40 hover:bg-surface-2/70 hover:border-foreground-subtle/50',
          selectedFile && 'border-accent/60 bg-accent-soft/10'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          className="hidden"
          disabled={disabled}
        />

        {selectedFile ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-12 h-12 rounded-full bg-accent-soft text-accent flex items-center justify-center">
              <File className="w-6 h-6" />
            </div>
            <div className="text-sm font-semibold text-foreground">{selectedFile.name}</div>
            <div className="text-xs text-foreground-muted tabular-nums">
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &bull; Click or drop another to replace
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="w-12 h-12 rounded-full bg-surface-2 text-foreground-muted flex items-center justify-center">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div className="text-sm font-semibold text-foreground">
              Drop your report file here, or <span className="text-accent underline">browse</span>
            </div>
            <div className="text-xs text-foreground-subtle">
              {description || `Accepts PDF, PNG, JPG, TXT (up to ${maxSizeMB}MB)`}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-1.5 text-xs text-status-danger mt-1">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
