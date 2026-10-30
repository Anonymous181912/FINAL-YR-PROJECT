import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, FileText, ScanLine, ShieldAlert } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/Dialog.jsx'
import { FileDropzone } from './ui/FileDropzone.jsx'
import { FormField } from './ui/FormField.jsx'
import { Input, Textarea } from './ui/Input.jsx'
import { Button } from './ui/Button.jsx'
import { createPaperPrescription } from '../services/prescriptions.js'

const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'pdf']
const MAX_SIZE_MB = 10

function todayIso() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 10)
}

function fileExtension(name) {
  return (name || '').split('.').pop().toLowerCase()
}

function isPdfFile(file) {
  return (file?.type || '').includes('pdf') || fileExtension(file?.name) === 'pdf'
}

export default function PaperPrescriptionModal({ open, onClose, onSaved }) {
  const previewUrlRef = useRef(null)

  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [doctorName, setDoctorName] = useState('')
  const [prescriptionDate, setPrescriptionDate] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const maxDate = todayIso()
  const dateIsFuture = !!prescriptionDate && prescriptionDate > maxDate

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    }
  }, [])

  const resetPreview = () => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
    setPreviewUrl('')
  }

  const handleFile = (selected) => {
    if (!selected) return
    setError('')

    if (!ALLOWED_EXTENSIONS.includes(fileExtension(selected.name))) {
      setFile(null)
      resetPreview()
      setError('Unsupported file type. Upload a JPG, PNG, WEBP or PDF.')
      return
    }

    if (selected.size > MAX_SIZE_MB * 1024 * 1024) {
      setFile(null)
      resetPreview()
      setError(`File is too large. Maximum size is ${MAX_SIZE_MB} MB.`)
      return
    }

    setFile(selected)
    resetPreview()
    if (!isPdfFile(selected) && typeof URL.createObjectURL === 'function') {
      const url = URL.createObjectURL(selected)
      previewUrlRef.current = url
      setPreviewUrl(url)
    }
  }

  const handleSave = async () => {
    if (saving) return
    setError('')

    if (!file) {
      setError('Choose a file to upload.')
      return
    }
    if (dateIsFuture) {
      return
    }

    setSaving(true)
    try {
      const record = await createPaperPrescription({
        file,
        doctorName: doctorName.trim() || undefined,
        prescriptionDate: prescriptionDate || undefined,
        note: note.trim() || undefined,
      })
      onSaved?.(record)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : 'Could not save this paper prescription. Please try again.'
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !saving) onClose?.()
      }}
    >
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ScanLine className="h-5 w-5 text-accent" />
            Add paper prescription
          </DialogTitle>
          <DialogDescription>
            Upload a photo or PDF of the paper prescription. The original file is
            stored with the record.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-start gap-2 rounded-item border border-status-warning-border bg-status-warning-bg px-3 py-2 text-xs text-status-warning">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Paper prescriptions are saved as{' '}
            <strong>Patient-uploaded - not verified by a doctor</strong>.
          </span>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-item border border-status-danger-border bg-status-danger-bg px-3 py-2 text-sm text-status-danger">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        <FormField label="Paper prescription file" required>
          <FileDropzone
            onFileSelect={handleFile}
            accept=".jpg,.jpeg,.png,.webp,.pdf"
            maxSizeMB={MAX_SIZE_MB}
            description={`Accepts JPG, PNG, WEBP or PDF (up to ${MAX_SIZE_MB} MB)`}
            disabled={saving}
          />
        </FormField>

        {file && (
          <div className="rounded-item border border-border bg-surface-2/50 overflow-hidden">
            {previewUrl && !isPdfFile(file) ? (
              <img
                src={previewUrl}
                alt="Uploaded paper prescription preview"
                className="max-h-64 w-full object-contain bg-surface"
              />
            ) : (
              <div className="flex items-center gap-3 p-4">
                <FileText className="h-8 w-8 text-accent shrink-0" />
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-foreground">
                    {file.name}
                  </div>
                  <div className="text-xs text-foreground-subtle">PDF selected</div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <FormField
            label="Prescription date"
            hint="Optional. Past dates only; blank uses today's date."
          >
            <Input
              aria-label="Prescription date"
              type="date"
              max={maxDate}
              value={prescriptionDate}
              onChange={(e) => setPrescriptionDate(e.target.value)}
              disabled={saving}
            />
          </FormField>
          <FormField label="Doctor name" hint="Optional. Type the name written on the paper.">
            <Input
              aria-label="Doctor name"
              value={doctorName}
              onChange={(e) => setDoctorName(e.target.value)}
              placeholder="e.g. Dr. Smith"
              disabled={saving}
            />
          </FormField>
        </div>

        {dateIsFuture && !saving && (
          <p className="text-xs font-medium text-status-danger">
            Prescription date must be in the past, not in the future.
          </p>
        )}

        <FormField label="Note" hint="Optional. Anything you want to remember about this paper.">
          <Textarea
            aria-label="Note"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Prescribed after a clinic visit"
            disabled={saving}
          />
        </FormField>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <div className="flex items-start gap-2 text-xs text-foreground-subtle">
            <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>The original file is stored but not QR verified.</span>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="button" onClick={handleSave} loading={saving}>
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
