import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileImage,
  FileText,
  Loader2,
  Plus,
  ScanLine,
  ShieldAlert,
  Trash2,
} from 'lucide-react'
import { FileDropzone } from '../components/ui/FileDropzone.jsx'
import { Stepper } from '../components/ui/Stepper.jsx'
import { Input } from '../components/ui/Input.jsx'
import { FormField } from '../components/ui/FormField.jsx'
import { Button } from '../components/ui/Button.jsx'
import { Badge } from '../components/ui/Badge.jsx'
import {
  confirmPaperPrescription,
  scanPaperPrescription,
} from '../services/prescriptions.js'

const EMPTY_ROW = {
  medicine_name: '',
  dosage: '',
  frequency: '',
  duration: '',
  instructions: '',
  confidence: 0.45,
  needs_review: true,
}

const STEPS = ['Upload paper', 'Review rows', 'Confirm & save']

function isLowConfidence(row) {
  return row.needs_review || Number(row.confidence) < 0.6
}

function HandwritingWarning({ compact = false }) {
  return (
    <div
      className={`flex items-start gap-2 rounded-item border border-status-warning-border bg-status-warning-bg text-status-warning ${
        compact ? 'px-3 py-2 text-xs' : 'px-4 py-3 text-sm'
      }`}
      role="note"
    >
      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
      <div>
        <span className="font-semibold">Handwriting accuracy warning.</span>{' '}
        OCR can misread medicine names, doses and frequencies. Compare every row with
        the paper prescription before saving. Digitized paper entries are not verified
        by a doctor.
      </div>
    </div>
  )
}

export default function DigitizePaperPrescription() {
  const navigate = useNavigate()
  const previewUrlRef = useRef(null)

  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState('')
  const [draft, setDraft] = useState(null)
  const [rows, setRows] = useState([])
  const [prescriber, setPrescriber] = useState('')
  const [prescriptionDate, setPrescriptionDate] = useState('')
  const [checked, setChecked] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saved, setSaved] = useState(null)

  const currentStep = saved ? 2 : draft ? 1 : 0

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

  const handleFile = async (selected) => {
    if (!selected) return
    setFile(selected)
    setDraft(null)
    setRows([])
    setSaved(null)
    setChecked(false)
    setScanError('')
    setSaveError('')
    resetPreview()
    if (typeof URL.createObjectURL === 'function') {
      const url = URL.createObjectURL(selected)
      previewUrlRef.current = url
      setPreviewUrl(url)
    }

    setScanning(true)
    try {
      const result = await scanPaperPrescription(selected)
      setDraft(result)
      setRows(
        (result.items || []).map((item) => ({
          ...EMPTY_ROW,
          ...item,
          medicine_name: item.medicine_name || '',
          dosage: item.dosage || '',
          frequency: item.frequency || '',
          duration: item.duration || '',
          instructions: item.instructions || '',
        }))
      )
      setPrescriber(result.detected_doctor_name || '')
      setPrescriptionDate(result.detected_prescription_date || '')
    } catch (err) {
      setScanError(err.response?.data?.detail || 'Could not scan this file. Try a clearer photo.')
    } finally {
      setScanning(false)
    }
  }

  const updateRow = (index, field, value) => {
    setRows((prev) =>
      prev.map((row, idx) => (idx === index ? { ...row, [field]: value } : row))
    )
  }

  const addRow = () => setRows((prev) => [...prev, { ...EMPTY_ROW }])

  const removeRow = (index) => {
    setRows((prev) => (prev.length <= 1 ? prev : prev.filter((_, idx) => idx !== index)))
  }

  const canSave =
    !!draft &&
    checked &&
    prescriber.trim().length > 0 &&
    !!prescriptionDate &&
    rows.length > 0 &&
    rows.every((row) => row.medicine_name.trim())

  const handleSave = async () => {
    if (!canSave || saving) return
    setSaving(true)
    setSaveError('')
    try {
      const record = await confirmPaperPrescription({
        temp_upload_id: draft.temp_upload_id,
        prescriber_name: prescriber.trim(),
        prescription_date: prescriptionDate,
        items: rows.map((row) => ({
          medicine_name: row.medicine_name.trim(),
          dosage: row.dosage.trim() || 'As directed',
          frequency: row.frequency.trim() || 'As directed',
          duration: row.duration.trim() || 'As directed',
          instructions: row.instructions.trim() || undefined,
        })),
        confirmed_by_patient: true,
      })
      setSaved(record)
    } catch (err) {
      setSaveError(err.response?.data?.detail || 'Could not save this paper prescription.')
    } finally {
      setSaving(false)
    }
  }

  const fileIsPdf = (file?.type || '').includes('pdf') || /\.pdf$/i.test(file?.name || '')

  if (saved) {
    return (
      <div className="animate-fade-in max-w-3xl mx-auto space-y-5">
        <div className="rounded-card border border-status-success-border bg-status-success-bg p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-6 h-6 text-status-success shrink-0" />
            <div>
              <h1 className="text-xl font-bold text-foreground">Paper prescription saved</h1>
              <p className="text-sm text-foreground-muted mt-1">
                It is now in your Medical History and under the Paper prescriptions tab.
              </p>
              <div className="mt-3">
                <Badge variant="warning">Patient-uploaded - not verified by a doctor</Badge>
              </div>
            </div>
          </div>
        </div>

        <HandwritingWarning />

        <div className="rounded-card border border-border bg-surface p-5">
          <div className="text-sm text-foreground-muted">Saved record</div>
          <div className="font-semibold text-foreground mt-1">
            {saved.prescriber_name ? `Prescriber: ${saved.prescriber_name}` : 'Paper prescription'}
          </div>
          <div className="text-sm text-foreground-muted mt-1">
            {saved.items?.length || 0} medicine row(s) ·{' '}
            {saved.prescription_date
              ? new Date(saved.prescription_date).toLocaleDateString()
              : 'Date saved'}
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button onClick={() => navigate('/patient/prescriptions')}>
            View my prescriptions
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setSaved(null)
              setDraft(null)
              setRows([])
              setFile(null)
              setChecked(false)
              setPrescriber('')
              setPrescriptionDate('')
              resetPreview()
            }}
          >
            Digitize another
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-5">
      <div className="page-header">
        <div>
          <Link
            to="/patient/prescriptions"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-foreground-muted hover:text-accent mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to My Prescriptions
          </Link>
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent-soft px-3 py-1 text-xs font-semibold text-accent mb-2">
            <ScanLine className="w-3.5 h-3.5" />
            Patient portal
          </div>
          <h1 className="text-2xl font-bold text-foreground">Digitize paper prescription</h1>
          <p className="text-sm text-foreground-muted mt-1">
            Upload a photo or PDF, review the suggested rows, then confirm the details
            against the paper. Nothing is saved until you confirm.
          </p>
        </div>
      </div>

      <Stepper steps={STEPS} currentStep={currentStep} />

      <HandwritingWarning />

      {scanError && (
        <div className="flex items-start gap-2 rounded-item border border-status-danger-border bg-status-danger-bg px-4 py-3 text-sm text-status-danger">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>{scanError}</div>
        </div>
      )}

      {saveError && (
        <div className="flex items-start gap-2 rounded-item border border-status-danger-border bg-status-danger-bg px-4 py-3 text-sm text-status-danger">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>{saveError}</div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] items-start">
        {/* Left: upload + paper preview */}
        <div className="rounded-card border border-border bg-surface p-5 space-y-4 lg:sticky lg:top-20">
          <div className="flex items-center gap-2">
            <FileImage className="w-5 h-5 text-accent" />
            <h2 className="font-semibold text-foreground">1. Upload the paper prescription</h2>
          </div>

          <FileDropzone
            onFileSelect={handleFile}
            accept=".pdf,.png,.jpg,.jpeg"
            maxSizeMB={10}
          />

          {scanning && (
            <div className="flex items-center gap-2 text-sm text-foreground-muted">
              <Loader2 className="w-4 h-4 animate-spin" />
              Reading the prescription...
            </div>
          )}

          <div className="rounded-item border border-border bg-surface-2/50 overflow-hidden">
            {previewUrl && file && !fileIsPdf ? (
              <img
                src={previewUrl}
                alt="Uploaded paper prescription preview"
                className="w-full max-h-[520px] object-contain bg-surface"
              />
            ) : previewUrl && file && fileIsPdf ? (
              <div className="flex flex-col items-center justify-center gap-2 p-8 text-center">
                <FileText className="w-10 h-10 text-foreground-muted" />
                <div className="text-sm font-semibold text-foreground">{file.name}</div>
                <div className="text-xs text-foreground-subtle">PDF uploaded for scanning</div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center gap-2 p-8 text-center">
                <FileImage className="w-10 h-10 text-foreground-subtle" />
                <div className="text-sm font-medium text-foreground-muted">
                  Your uploaded photo will appear here
                </div>
                <div className="text-xs text-foreground-subtle">
                  Use a clear, well-lit photo of the whole prescription.
                </div>
              </div>
            )}
          </div>

          {draft?.raw_text && (
            <details className="rounded-item border border-border bg-surface-2/40 p-3">
              <summary className="cursor-pointer text-xs font-semibold text-foreground-muted">
                OCR text (for checking only)
              </summary>
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words text-xs text-foreground-muted">
                {draft.raw_text}
              </pre>
            </details>
          )}
        </div>

        {/* Right: editable rows */}
        <div className="rounded-card border border-border bg-surface p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-accent" />
              <h2 className="font-semibold text-foreground">2. Check and edit every row</h2>
            </div>
            {draft && (
              <Badge variant="info">
                {rows.length} {rows.length === 1 ? 'row' : 'rows'}
              </Badge>
            )}
          </div>

          {!draft && !scanning && (
            <div className="rounded-item border border-dashed border-border bg-surface-2/30 p-6 text-center text-sm text-foreground-muted">
              Upload a photo or PDF to see editable medicine rows.
            </div>
          )}

          {draft && rows.length === 0 && (
            <div className="rounded-item border border-status-warning-border bg-status-warning-bg p-4 text-sm text-status-warning">
              No medicine rows were detected. Add rows manually from the paper.
            </div>
          )}

          {rows.map((row, index) => {
            const low = isLowConfidence(row)
            return (
              <div
                key={index}
                className={`rounded-item border p-4 space-y-3 ${
                  low
                    ? 'border-status-warning-border bg-status-warning-bg/40'
                    : 'border-border bg-surface-2/30'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wide text-foreground-subtle">
                      Row {index + 1}
                    </span>
                    {low && (
                      <Badge variant="warning">
                        Low confidence - check against paper
                      </Badge>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeRow(index)}
                    disabled={rows.length <= 1}
                    aria-label={`Remove row ${index + 1}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Remove
                  </Button>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <FormField label={`Medicine ${index + 1}`} required>
                    <Input
                      aria-label={`Medicine name row ${index + 1}`}
                      value={row.medicine_name}
                      onChange={(e) => updateRow(index, 'medicine_name', e.target.value)}
                      placeholder="e.g. Amoxicillin"
                    />
                  </FormField>
                  <FormField label={`Dose ${index + 1}`}>
                    <Input
                      aria-label={`Dose row ${index + 1}`}
                      value={row.dosage}
                      onChange={(e) => updateRow(index, 'dosage', e.target.value)}
                      placeholder="e.g. 500 mg"
                    />
                  </FormField>
                  <FormField label={`Frequency ${index + 1}`}>
                    <Input
                      aria-label={`Frequency row ${index + 1}`}
                      value={row.frequency}
                      onChange={(e) => updateRow(index, 'frequency', e.target.value)}
                      placeholder="e.g. TDS / three times daily"
                    />
                  </FormField>
                  <FormField label={`Duration ${index + 1}`}>
                    <Input
                      aria-label={`Duration row ${index + 1}`}
                      value={row.duration}
                      onChange={(e) => updateRow(index, 'duration', e.target.value)}
                      placeholder="e.g. 5 days"
                    />
                  </FormField>
                </div>
                <FormField label={`Instructions ${index + 1}`}>
                  <Input
                    aria-label={`Instructions row ${index + 1}`}
                    value={row.instructions}
                    onChange={(e) => updateRow(index, 'instructions', e.target.value)}
                    placeholder="e.g. after food"
                  />
                </FormField>
              </div>
            )
          })}

          {draft && (
            <Button type="button" variant="secondary" onClick={addRow}>
              <Plus className="w-4 h-4" />
              Add medicine row
            </Button>
          )}

          <div className="border-t border-border pt-4 space-y-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-accent" />
              <h2 className="font-semibold text-foreground">3. Prescriber and date</h2>
            </div>
            <p className="text-xs text-foreground-muted">
              Type or confirm these details from the paper. They are never guessed for you.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <FormField label="Prescriber name" required>
                <Input
                  aria-label="Prescriber name"
                  value={prescriber}
                  onChange={(e) => setPrescriber(e.target.value)}
                  placeholder="Name written on the paper"
                />
              </FormField>
              <FormField label="Prescription date" required>
                <Input
                  aria-label="Prescription date"
                  type="date"
                  value={prescriptionDate}
                  onChange={(e) => setPrescriptionDate(e.target.value)}
                />
              </FormField>
            </div>

            <label className="flex items-start gap-3 rounded-item border border-border bg-surface-2/40 p-3 cursor-pointer">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-border text-accent focus:ring-accent"
                checked={checked}
                onChange={(e) => setChecked(e.target.checked)}
              />
              <span className="text-sm text-foreground">
                I checked these details against the paper prescription
              </span>
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                onClick={handleSave}
                disabled={!canSave}
                loading={saving}
              >
                Save paper prescription
              </Button>
              {!checked && draft && (
                <span className="text-xs text-foreground-subtle">
                  Tick the confirmation checkbox to enable Save.
                </span>
              )}
            </div>

            <div className="flex items-start gap-2 text-xs text-foreground-subtle">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>
                Saved as <strong>Patient-uploaded - not verified by a doctor</strong>.
                Any safety note based on this entry is based on unverified data.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
