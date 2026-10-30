import { useState, useEffect, useRef } from 'react'
import { toast, Toaster } from 'react-hot-toast'
import {
  Pill,
  FileDown,
  Calendar,
  User,
  Clock,
  QrCode,
  ShieldCheck as ShieldCheckIcon,
  AlertTriangle,
  HeartPulse,
  ScanLine,
  Plus,
  Trash2,
  FileText,
  FileImage,
  Loader2,
  Eye,
} from 'lucide-react'
import {
  listPatientPrescriptions,
  generatePrescriptionPdf,
  downloadPrescriptionPdf,
  deletePaperPrescription,
  getPaperPrescriptionFile,
} from '../services/prescriptions.js'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/Tabs.jsx'
import { Badge } from '../components/ui/Badge.jsx'
import { Button } from '../components/ui/Button.jsx'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../components/ui/Dialog.jsx'
import PaperPrescriptionModal from '../components/PaperPrescriptionModal.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'

const PAPER_BADGE = 'Patient-uploaded - not verified by a doctor'

function isPdfRecord(rx) {
  const type = String(rx.file_type || '').toLowerCase()
  const name = String(rx.original_file_name || rx.file_path || '').toLowerCase()
  return type === 'pdf' || type.includes('pdf') || name.endsWith('.pdf')
}

function PrescriptionCard({
  rx,
  onPdf,
  pdfBusy,
  onDelete,
  deleting,
  paperPreview,
  onViewPaper,
}) {
  const isPaper = rx.source === 'patient_uploaded'
  const paperIsPdf = isPaper && isPdfRecord(rx)
  const dateStr = rx.prescription_date
    ? new Date(rx.prescription_date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'Date not set'
  const status = rx.status || 'issued'
  const isRevoked = rx.verification_status === 'revoked'

  return (
    <div className="rounded-card border border-border bg-surface p-5 transition-colors">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-1 gap-4 min-w-[260px]">
          {isPaper ? (
            <button
              type="button"
              onClick={() => onViewPaper?.(rx)}
              className="group flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-item border border-border bg-surface-2 text-foreground-muted transition-colors hover:border-accent hover:text-accent"
              aria-label={`View paper prescription ${rx.id.slice(-6).toUpperCase()}`}
            >
              {paperIsPdf ? (
                <FileText className="h-7 w-7" />
              ) : paperPreview?.url ? (
                <img
                  src={paperPreview.url}
                  alt={`Paper prescription ${rx.id.slice(-6).toUpperCase()} thumbnail`}
                  className="h-full w-full object-cover"
                />
              ) : paperPreview?.loading ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                <FileImage className="h-7 w-7" />
              )}
            </button>
          ) : (
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-item bg-accent text-accent-foreground font-bold">
              <Pill className="h-5 w-5" />
            </div>
          )}

          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-base font-semibold text-foreground">
                {isPaper ? 'Paper Prescription' : 'Prescription'} #
                {rx.id.slice(-6).toUpperCase()}
              </h4>
              {isPaper ? (
                <Badge variant="warning">{PAPER_BADGE}</Badge>
              ) : (
                <Badge variant={isRevoked ? 'danger' : 'success'}>
                  {isRevoked ? 'Revoked' : status}
                </Badge>
              )}
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-4 text-xs text-foreground-muted">
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {dateStr}
              </span>
              <span className="inline-flex items-center gap-1">
                <User className="h-3.5 w-3.5" />
                {isPaper
                  ? rx.prescriber_name || 'Prescriber not recorded'
                  : `Dr. ${rx.doctor_name || 'Doctor'}`}
              </span>
              {rx.follow_up_date && (
                <span className="inline-flex items-center gap-1 text-accent">
                  <Clock className="h-3.5 w-3.5" />
                  Follow-up: {new Date(rx.follow_up_date).toLocaleDateString()}
                </span>
              )}
            </div>

            {rx.items && rx.items.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {rx.items.map((m, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 rounded-item border border-border bg-surface-2 px-2 py-1 text-xs font-medium text-foreground"
                  >
                    <Pill className="h-3 w-3 text-accent" />
                    <strong>{m.medicine_name}</strong>
                    {m.dosage && ` (${m.dosage})`}
                  </span>
                ))}
              </div>
            )}

            {rx.diagnosis_notes && (
              <p className="mt-2 text-xs italic text-foreground-muted">
                &quot;{rx.diagnosis_notes}&quot;
              </p>
            )}

            {rx.safety_warnings && rx.safety_warnings.length > 0 && (
              <div className="mt-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-status-warning">
                  <ShieldCheckIcon className="h-3.5 w-3.5" />
                  <span>
                    Medication safety flags (educational)
                    {isPaper ? ' - based on unverified data' : ''}
                  </span>
                </div>
                {rx.safety_warnings.map((w, idx) => (
                  <div
                    key={idx}
                    className="rounded-item border border-status-warning-border bg-status-warning-bg px-3 py-2 text-xs text-status-warning"
                  >
                    <span className="font-semibold capitalize">
                      {w.severity}: {w.type}
                    </span>{' '}
                    <strong>{(w.drugs || []).join(' + ')}</strong>
                    {w.note ? ` - ${w.note}` : ''}
                  </div>
                ))}
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {isPaper ? (
                <Badge variant="warning">
                  <FileText className="h-3 w-3" />
                  Original file stored - not QR verified
                </Badge>
              ) : isRevoked ? (
                <Badge variant="danger">Verification revoked</Badge>
              ) : (
                <Badge variant="success">Verified prescription</Badge>
              )}
              {!isPaper && rx.verification_token && (
                <a
                  href={`${window.location.origin}/verify/${rx.verification_token}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                >
                  <QrCode className="h-3.5 w-3.5" />
                  Public verification page
                </a>
              )}
            </div>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {!isPaper && (
            <button
              className="btn btn-secondary btn-sm inline-flex items-center gap-1.5"
              onClick={() => onPdf(rx)}
              disabled={pdfBusy}
            >
              <FileDown className="h-3.5 w-3.5" />
              <span>{pdfBusy ? 'Generating...' : rx.file_path ? 'Download PDF' : 'Generate PDF'}</span>
            </button>
          )}
          {isPaper && (
            <>
              <button
                className="btn btn-secondary btn-sm inline-flex items-center gap-1.5"
                onClick={() => onViewPaper?.(rx)}
              >
                <Eye className="h-3.5 w-3.5" />
                View
              </button>
              <button
                className="inline-flex items-center gap-1.5 rounded-item border border-status-danger-border bg-status-danger-bg px-3 py-1.5 text-xs font-semibold text-status-danger hover:opacity-90 disabled:opacity-50"
                onClick={() => onDelete(rx)}
                disabled={deleting}
              >
                <Trash2 className="h-3.5 w-3.5" />
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PatientPrescriptions() {
  const [loading, setLoading] = useState(false)
  const [pdfLoadingId, setPdfLoadingId] = useState(null)
  const [error, setError] = useState('')
  const [prescriptions, setPrescriptions] = useState([])
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [addOpen, setAddOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('doctor')
  const [paperPreviews, setPaperPreviews] = useState({})
  const [lightbox, setLightbox] = useState(null)
  const paperUrlsRef = useRef({})

  const fetchPrescriptions = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listPatientPrescriptions()
      setPrescriptions(data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load prescriptions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPrescriptions()
  }, [])

  useEffect(() => {
    const papers = prescriptions.filter((rx) => rx.source === 'patient_uploaded')
    const activeIds = new Set(papers.map((rx) => rx.id))

    for (const [id, url] of Object.entries(paperUrlsRef.current)) {
      if (!activeIds.has(id)) {
        if (typeof URL.revokeObjectURL === 'function') URL.revokeObjectURL(url)
        delete paperUrlsRef.current[id]
        setPaperPreviews((prev) => {
          if (!(id in prev)) return prev
          const next = { ...prev }
          delete next[id]
          return next
        })
      }
    }

    let cancelled = false
    papers.forEach((rx) => {
      if (isPdfRecord(rx) || paperUrlsRef.current[rx.id]) return

      setPaperPreviews((prev) => ({
        ...prev,
        [rx.id]: { url: '', loading: true, error: '' },
      }))

      getPaperPrescriptionFile(rx.id)
        .then((blob) => {
          const url = URL.createObjectURL(blob)
          if (cancelled) {
            if (typeof URL.revokeObjectURL === 'function') URL.revokeObjectURL(url)
            return
          }
          paperUrlsRef.current[rx.id] = url
          setPaperPreviews((prev) => ({
            ...prev,
            [rx.id]: { url, loading: false, error: '' },
          }))
        })
        .catch((err) => {
          if (cancelled) return
          setPaperPreviews((prev) => ({
            ...prev,
            [rx.id]: {
              url: '',
              loading: false,
              error: err.response?.data?.detail || 'Preview unavailable',
            },
          }))
        })
    })

    return () => {
      cancelled = true
    }
  }, [prescriptions])

  useEffect(() => {
    return () => {
      if (typeof URL.revokeObjectURL !== 'function') return
      Object.values(paperUrlsRef.current).forEach((url) => URL.revokeObjectURL(url))
      paperUrlsRef.current = {}
    }
  }, [])

  const handleViewPaper = async (rx) => {
    setError('')
    const paperIsPdf = isPdfRecord(rx)

    if (!paperIsPdf) {
      const existing = paperUrlsRef.current[rx.id]
      if (existing) {
        setLightbox({ url: existing, rx })
        return
      }
    }

    const newTab = paperIsPdf ? window.open('', '_blank') : null
    try {
      const blob = await getPaperPrescriptionFile(rx.id)
      const url = URL.createObjectURL(blob)
      if (paperIsPdf) {
        if (newTab) {
          newTab.location.href = url
        } else {
          const link = document.createElement('a')
          link.href = url
          link.target = '_blank'
          link.rel = 'noreferrer'
          link.click()
        }
        setTimeout(() => URL.revokeObjectURL(url), 120000)
      } else {
        paperUrlsRef.current[rx.id] = url
        setPaperPreviews((prev) => ({
          ...prev,
          [rx.id]: { url, loading: false, error: '' },
        }))
        setLightbox({ url, rx })
      }
    } catch (err) {
      newTab?.close()
      setError(err.response?.data?.detail || 'Could not open the original file')
    }
  }

  const handlePdf = async (rx) => {
    setPdfLoadingId(rx.id)
    setError('')
    try {
      const blob = await generatePrescriptionPdf(rx.id)
      downloadPrescriptionPdf(blob, `Prescription_${rx.id.slice(-6)}.pdf`)
      await fetchPrescriptions()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate PDF')
    } finally {
      setPdfLoadingId(null)
    }
  }

  const handleDelete = async () => {
    if (!confirmDelete || deletingId) return
    setDeletingId(confirmDelete.id)
    setError('')
    try {
      await deletePaperPrescription(confirmDelete.id)
      setConfirmDelete(null)
      await fetchPrescriptions()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete paper prescription')
    } finally {
      setDeletingId(null)
    }
  }

  const handlePaperSaved = async () => {
    setAddOpen(false)
    setActiveTab('paper')
    toast.success('Paper prescription saved')
    await fetchPrescriptions()
  }

  const doctorIssued = prescriptions.filter((rx) => rx.source !== 'patient_uploaded')
  const paperPrescriptions = prescriptions.filter((rx) => rx.source === 'patient_uploaded')

  const renderList = (items, emptyTitle, emptyText, paper = false, emptyAction = null) => {
    if (loading) {
      return (
        <div className="py-10 text-center">
          <div className="loading-spinner mx-auto mb-3" />
          <p className="text-sm text-foreground-muted">Loading prescriptions...</p>
        </div>
      )
    }
    if (items.length === 0) {
      return (
        <div className="empty-state">
          {paper ? <ScanLine size={36} /> : <Pill size={36} />}
          <h4 className="mt-2 text-base font-semibold text-foreground">{emptyTitle}</h4>
          <p className="mt-1 text-sm text-foreground-muted">{emptyText}</p>
          {emptyAction && <div className="mt-4">{emptyAction}</div>}
        </div>
      )
    }
    return (
      <div className="flex flex-col gap-3.5">
        {items.map((rx) => (
          <PrescriptionCard
            key={rx.id}
            rx={rx}
            onPdf={handlePdf}
            pdfBusy={pdfLoadingId === rx.id}
            onDelete={setConfirmDelete}
            deleting={deletingId === rx.id}
            paperPreview={paperPreviews[rx.id]}
            onViewPaper={handleViewPaper}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="animate-fade-in mx-auto max-w-5xl">
      <div className="page-header flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-accent/20 bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent">
            <HeartPulse size={12} />
            <span>My Prescriptions</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground">My Prescriptions</h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Doctor-issued prescriptions and paper prescriptions you digitized yourself.
          </p>
        </div>
        <Button type="button" size="sm" onClick={() => setAddOpen(true)}>
          <ScanLine className="h-4 w-4" />
          Digitize paper prescription
        </Button>
      </div>

      {error && (
        <div className="mb-5 flex items-start gap-2 rounded-item border border-status-danger-border bg-status-danger-bg px-4 py-3 text-sm text-status-danger">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <div>{error}</div>
        </div>
      )}

      <div className="rounded-card border border-border bg-surface p-5">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="doctor">
              Doctor-issued ({doctorIssued.length})
            </TabsTrigger>
            <TabsTrigger value="paper">
              Paper prescriptions ({paperPrescriptions.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="doctor">
            {renderList(
              doctorIssued,
              'No doctor-issued prescriptions found',
              'Prescriptions issued by your doctor will appear here.'
            )}
          </TabsContent>

          <TabsContent value="paper">
            <div className="mb-3 flex justify-end">
              <Button type="button" size="sm" onClick={() => setAddOpen(true)}>
                <Plus className="h-4 w-4" />
                Add paper prescription
              </Button>
            </div>
            <div className="mb-3 rounded-item border border-status-warning-border bg-status-warning-bg px-3 py-2 text-xs text-status-warning">
              <strong>{PAPER_BADGE}.</strong> These entries are your own uploads of a
              paper prescription and are not clinically verified.
            </div>
            {renderList(
              paperPrescriptions,
              'No paper prescriptions yet',
              'Add one from a photo or PDF. The original file is saved as-is.',
              true
            )}
          </TabsContent>
        </Tabs>
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title="Delete this paper prescription?"
          message="This permanently removes the record and the original stored file. This action cannot be undone."
          confirmLabel="Delete"
          cancelLabel="Cancel"
          loading={deletingId === confirmDelete.id}
          onConfirm={handleDelete}
          onCancel={() => {
            if (!deletingId) setConfirmDelete(null)
          }}
        />
      )}

      {addOpen && (
        <PaperPrescriptionModal
          open={addOpen}
          onClose={() => setAddOpen(false)}
          onSaved={handlePaperSaved}
        />
      )}

      <Dialog
        open={!!lightbox}
        onOpenChange={(next) => {
          if (!next) setLightbox(null)
        }}
      >
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle>Paper prescription</DialogTitle>
            <DialogDescription>
              {lightbox?.rx?.prescription_date
                ? new Date(lightbox.rx.prescription_date).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })
                : 'Date not set'}
              {lightbox?.rx?.prescriber_name
                ? ` - ${lightbox.rx.prescriber_name}`
                : ''}
            </DialogDescription>
          </DialogHeader>
          {lightbox?.url && (
            <img
              src={lightbox.url}
              alt="Paper prescription full view"
              className="max-h-[75vh] w-full rounded-item bg-surface-2 object-contain"
            />
          )}
        </DialogContent>
      </Dialog>

      <Toaster position="top-right" />
    </div>
  )
}
