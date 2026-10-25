import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import {
  createPrescription,
  listDoctorPrescriptions,
  listPatientPrescriptions,
  updatePrescription,
  deletePrescription,
  generatePrescriptionPdf,
  downloadPrescriptionPdf,
  revokePrescription,
  issuePrescription,
  scanPrescription,
} from '../services/prescriptions'
import { listPatients, searchPatients } from '../services/patients'
import {
  Pill,
  Plus,
  Trash2,
  FileDown,
  Edit3,
  Calendar,
  User,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  Stethoscope,
  Sparkles,
  Search,
  ExternalLink,
  ChevronDown,
  ShieldCheck,
  QrCode,
  Ban,
  ScanLine,
  Send,
} from 'lucide-react'

const emptyItem = () => ({
  medicine_name: '',
  dosage: '',
  frequency: '',
  duration: '',
  route: 'Oral',
  instructions: '',
  quantity: '',
  timings: '',
})

export function SafetyWarnings({ warnings }) {
  if (!warnings || warnings.length === 0) return null
  const sevClass = (s) => s === 'severe' ? 'badge-danger' : s === 'moderate' ? 'badge-warning' : 'badge-neutral'
  return (
    <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="safety-warnings">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', fontWeight: 700, color: '#92400e' }}>
        <ShieldCheck size={14} />
        <span>Medication safety flags (educational — confirm with a pharmacist)</span>
      </div>
      {warnings.map((w, idx) => (
        <div key={idx} style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8, padding: '8px 12px', fontSize: '0.82rem', color: '#78350f' }}>
          <span className={`badge ${sevClass(w.severity)}`} style={{ marginRight: 8, textTransform: 'capitalize' }}>
            {w.severity}: {w.type}
          </span>
          <strong>{(w.drugs || []).join(' + ')}</strong>
          {w.note ? ` — ${w.note}` : ''}
        </div>
      ))}
    </div>
  )
}

export default function Prescriptions() {
  const { user } = useAuth()
  const isDoctor = user?.role === 'doctor'

  const [loading, setLoading] = useState(false)
  const [pdfLoadingId, setPdfLoadingId] = useState(null)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [prescriptions, setPrescriptions] = useState([])
  const [formVisible, setFormVisible] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const [patientId, setPatientId] = useState('')
  const [prescriptionDate, setPrescriptionDate] = useState(new Date().toISOString().slice(0, 10))
  const [diagnosisNotes, setDiagnosisNotes] = useState('')
  const [advice, setAdvice] = useState('')
  const [followUpDate, setFollowUpDate] = useState('')
  const [items, setItems] = useState([emptyItem()])
  const [status, setStatus] = useState('draft')
  const [directory, setDirectory] = useState([])
  const [ackWarnings, setAckWarnings] = useState(false)
  const [ackReason, setAckReason] = useState('')
  const [needsAck, setNeedsAck] = useState(false)
  const [lastWarnings, setLastWarnings] = useState([])
  const [scanFile, setScanFile] = useState(null)
  const [scanLoading, setScanLoading] = useState(false)
  const [scanDraft, setScanDraft] = useState(null)
  const [patientQuery, setPatientQuery] = useState('')
  const [patientResults, setPatientResults] = useState([])
  const [searchingPatient, setSearchingPatient] = useState(false)
  const [selectedPatient, setSelectedPatient] = useState(null)

  const fetchPrescriptions = async () => {
    setLoading(true)
    setError('')
    try {
      const data = isDoctor
        ? await listDoctorPrescriptions()
        : await listPatientPrescriptions()
      setPrescriptions(data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load prescriptions')
    } finally {
      setLoading(false)
    }
  }

  const [searchParams] = useSearchParams()

  useEffect(() => {
    fetchPrescriptions()
    if (isDoctor) {
      listPatients('', 0, 50).then((data) => setDirectory(data || [])).catch(() => {})
      // Deep-link handoff: dossier "Prescribe" and nav "Create Prescription"
      // arrive as /prescriptions?patient=<id>&new=1 — prefill and open the form.
      const incomingPatient = searchParams.get('patient')
      if (incomingPatient) setPatientId(incomingPatient)
      if (searchParams.get('new') === '1') {
        resetForm()
        if (incomingPatient) setPatientId(incomingPatient)
        setFormVisible(true)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDoctor])

  const resetForm = () => {
    setPatientId('')
    setPrescriptionDate(new Date().toISOString().slice(0, 10))
    setDiagnosisNotes('')
    setAdvice('')
    setFollowUpDate('')
    setItems([emptyItem()])
    setStatus('draft')
    setEditingId(null)
    setAckWarnings(false)
    setAckReason('')
    setNeedsAck(false)
    setLastWarnings([])
    setScanDraft(null)
    setScanFile(null)
    setPatientQuery('')
    setPatientResults([])
    setSelectedPatient(null)
  }

  const handleEdit = (rx) => {
    setEditingId(rx.id)
    setPatientId(rx.patient_id)
    setPrescriptionDate(rx.prescription_date ? new Date(rx.prescription_date).toISOString().slice(0, 10) : '')
    setDiagnosisNotes(rx.diagnosis_notes || '')
    setAdvice(rx.advice || '')
    setFollowUpDate(rx.follow_up_date ? new Date(rx.follow_up_date).toISOString().slice(0, 10) : '')
    setItems(rx.items && rx.items.length > 0 ? rx.items : [emptyItem()])
    setStatus(rx.status || 'draft')
    setAckWarnings(!!rx.acknowledged_warnings)
    setAckReason('')
    setNeedsAck(false)
    setLastWarnings(rx.safety_warnings || [])
    setScanDraft(null)
    setFormVisible(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleAddItem = () => {
    setItems([...items, emptyItem()])
  }

  const handleRemoveItem = (index) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const handleItemChange = (index, field, value) => {
    const updated = [...items]
    updated[index] = { ...updated[index], [field]: value }
    setItems(updated)
  }

  const handlePatientSearch = async () => {
    const q = patientQuery.trim()
    if (!q) return
    setSearchingPatient(true)
    setError('')
    try {
      const results = await searchPatients(q, 10)
      setPatientResults(results || [])
      if (!results || results.length === 0) {
        setError('No patient matched that name or patient code.')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Patient lookup failed')
    } finally {
      setSearchingPatient(false)
    }
  }

  const handleSelectPatient = (patient) => {
    setSelectedPatient(patient)
    setPatientId(patient.patient_id || patient.id)
    setPatientResults([])
    setPatientQuery('')
  }

  const handleIssue = async (rx) => {
    if (!window.confirm(`Issue prescription #${rx.id.slice(-6)} to the patient? This notifies them and cannot be undone.`)) return
    setError('')
    setSuccessMsg('')
    try {
      await issuePrescription(rx.id)
      setSuccessMsg('Prescription issued — the patient has been notified.')
      await fetchPrescriptions()
      setTimeout(() => setSuccessMsg(''), 4000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to issue prescription')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccessMsg('')

    if (!items.length || items.some((it) => !it.medicine_name.trim())) {
      setError('Each medicine row must have a valid medication name')
      return
    }

    const payload = {
      patient_id: patientId,
      prescription_date: prescriptionDate || undefined,
      diagnosis_notes: diagnosisNotes || undefined,
      advice: advice || undefined,
      follow_up_date: followUpDate || undefined,
      items: items.map(({ quantity, timings, ...rest }) => rest),
      status,
      acknowledge_warnings: ackWarnings,
      ack_reason: ackReason || undefined,
    }

    setLoading(true)
    try {
      let saved
      if (editingId) {
        saved = await updatePrescription(editingId, payload)
        setSuccessMsg('Prescription updated successfully')
      } else {
        saved = await createPrescription(payload)
        setSuccessMsg('Draft saved — it stays hidden from the patient until you click "Issue to Patient".')
      }
      setLastWarnings(saved?.safety_warnings || [])
      resetForm()
      setFormVisible(false)
      await fetchPrescriptions()
      setTimeout(() => setSuccessMsg(''), 4000)
    } catch (err) {
      // FastAPI validation errors arrive as an array of {msg,...} objects;
      // flatten them to text (rendering the raw array would crash React).
      const raw = err.response?.data?.detail
      const detailText = Array.isArray(raw)
        ? raw.map((d) => d?.msg || JSON.stringify(d)).join('; ')
        : raw
      if (detailText && detailText.toLowerCase().includes('acknowledged')) {
        setNeedsAck(true)
      }
      const statusHint = err.response ? ` (HTTP ${err.response.status})` : ' (network error)'
      setError(detailText ? `${detailText}${err.response ? ` (HTTP ${err.response.status})` : ''}` : `Failed to save prescription${statusHint}`)
    } finally {
      setLoading(false)
    }
  }

  const handleRevoke = async (rx) => {
    if (!window.confirm(`Revoke verification for prescription #${rx.id.slice(-6)}? The public verification page will show "revoked".`)) return
    setError('')
    try {
      await revokePrescription(rx.id)
      setSuccessMsg('Prescription verification revoked')
      await fetchPrescriptions()
      setTimeout(() => setSuccessMsg(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke prescription')
    }
  }

  const handleScan = async () => {
    if (!scanFile) {
      setError('Choose a photo/scan of the handwritten prescription first')
      return
    }
    setScanLoading(true)
    setError('')
    setScanDraft(null)
    try {
      const draft = await scanPrescription(scanFile)
      setScanDraft(draft)
      if (!draft.items || draft.items.length === 0) {
        setError('No medicines could be read from the scan. Try a clearer photo.')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed. Try a clearer photo.')
    } finally {
      setScanLoading(false)
    }
  }

  const handleLoadDraft = () => {
    if (!scanDraft?.items?.length) return
    setItems(scanDraft.items.map(({ needs_review, ...rest }) => ({
      route: 'Oral', instructions: '', quantity: '', timings: '', ...rest,
    })))
    setScanDraft(null)
    setScanFile(null)
    setSuccessMsg('Draft loaded — review every row before saving')
    setTimeout(() => setSuccessMsg(''), 4000)
  }

  const handleDelete = async (rx) => {
    if (!window.confirm(`Delete prescription #${rx.id.slice(-6)}? This action cannot be undone.`)) return
    setLoading(true)
    try {
      await deletePrescription(rx.id)
      setSuccessMsg('Prescription deleted')
      await fetchPrescriptions()
      setTimeout(() => setSuccessMsg(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete prescription')
    } finally {
      setLoading(false)
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

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', fontSize: '0.75rem', fontWeight: 600, marginBottom: 8 }}>
            <Stethoscope size={12} />
            <span>Digital Clinical Rx Management</span>
          </div>
          <h1>Digital Prescriptions</h1>
          <p>{isDoctor ? 'Author, edit, and issue verified digital prescriptions with PDF export.' : 'Review your active and past prescribed medical regimens.'}</p>
        </div>

        {isDoctor && !formVisible && (
          <button
            className="btn btn-primary"
            onClick={() => { resetForm(); setFormVisible(true) }}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, boxShadow: '0 4px 12px rgba(14,165,233,0.25)' }}
          >
            <Plus size={16} />
            <span>New Prescription (Rx)</span>
          </button>
        )}
      </div>

      {error && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {successMsg && (
        <div className="alert-banner alert-banner-success" style={{ marginBottom: 20 }}>
          <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
          <div>{successMsg}</div>
        </div>
      )}

      {/* Prescription Form (Doctor Mode) */}
      {isDoctor && formVisible && (
        <div className="card prescription-header-banner" style={{ marginBottom: 28, padding: 28 }}>
          
          {/* Rx Header Badge */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #e2e8f0', paddingBottom: 16, marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #0d9488, #0ea5e9)',
                  color: 'white',
                  fontWeight: 900,
                  fontSize: '1.4rem',
                  fontFamily: 'serif',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 2px 8px rgba(13,148,136,0.3)',
                }}
              >
                ℞
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                  {editingId ? 'Edit Medical Prescription' : 'New Clinical Prescription'}
                </h3>
                <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Issued by Dr. {user?.full_name || 'Practitioner'} • Verified Electronic Order
                </span>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => { resetForm(); setFormVisible(false) }}
            >
              Cancel
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Patient lookup by name or patient_code (A1) */}
            {!editingId && (
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '14px 16px', marginBottom: 20 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: '0.9rem', color: '#0f172a', marginBottom: 8 }}>
                  <Search size={14} color="#0ea5e9" />
                  <span>Find patient by name or patient code</span>
                </label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    value={patientQuery}
                    onChange={(e) => setPatientQuery(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handlePatientSearch() } }}
                    placeholder="e.g. PAT-7X9K2 or Jane Doe"
                    className="form-control"
                    style={{ flex: 1, minWidth: 220, background: 'white' }}
                    aria-label="Search patient by name or patient code"
                  />
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handlePatientSearch}
                    disabled={searchingPatient || !patientQuery.trim()}
                  >
                    <Search size={14} />
                    <span>{searchingPatient ? 'Searching...' : 'Search'}</span>
                  </button>
                </div>

                {selectedPatient && (
                  <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#166534', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '8px 12px' }}>
                    Selected: <strong>{selectedPatient.full_name}</strong>
                    {selectedPatient.patient_code ? ` (${selectedPatient.patient_code})` : ''}
                  </div>
                )}

                {patientResults.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 10 }}>
                    {patientResults.map((p) => (
                      <button
                        type="button"
                        key={p.id}
                        onClick={() => handleSelectPatient(p)}
                        style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
                          textAlign: 'left', background: 'white', border: '1px solid #e2e8f0',
                          borderRadius: 8, padding: '8px 12px', cursor: 'pointer', fontSize: '0.86rem',
                        }}
                      >
                        <span>
                          <strong>{p.full_name}</strong>
                          {p.age != null ? ` · ${p.age} yrs` : ''}
                        </span>
                        {p.patient_code && <span className="badge badge-primary">{p.patient_code}</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Top Patient & Date Row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 20 }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <User size={14} color="#0ea5e9" />
                  <span>Patient ID / Reference *</span>
                </label>
                <input
                  type="text"
                  placeholder="Select from directory or paste patient ID"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  required
                  disabled={!!editingId}
                  className="form-control"
                  list="rx-patient-directory"
                />
                <datalist id="rx-patient-directory">
                  {directory.map((p) => (
                    <option key={p.id} value={p.patient_id || p.user_id || p.id}>
                      {p.full_name}
                    </option>
                  ))}
                </datalist>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Calendar size={14} color="#0ea5e9" />
                  <span>Prescription Date</span>
                </label>
                <input
                  type="date"
                  value={prescriptionDate}
                  onChange={(e) => setPrescriptionDate(e.target.value)}
                  className="form-control"
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Clock size={14} color="#0ea5e9" />
                  <span>Follow-Up Date</span>
                </label>
                <input
                  type="date"
                  value={followUpDate}
                  onChange={(e) => setFollowUpDate(e.target.value)}
                  className="form-control"
                />
              </div>

              {/* Status is only editable on existing prescriptions: the backend
                  stores every newly created prescription as draft. */}
              {editingId && (
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Status</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="form-control"
                  >
                    <option value="draft">Draft</option>
                    <option value="issued">Issued (severe safety flags need acknowledgement)</option>
                    <option value="finalized">Finalized</option>
                    <option value="active">Active</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              )}
            </div>

            {/* Diagnosis & Clinical Notes */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Diagnosis & Clinical Impressions</label>
                <textarea
                  value={diagnosisNotes}
                  onChange={(e) => setDiagnosisNotes(e.target.value)}
                  rows={3}
                  maxLength={2000}
                  placeholder="e.g. Acute upper respiratory tract infection, mild wheezing..."
                  className="form-control"
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Dietary & General Advice</label>
                <textarea
                  value={advice}
                  onChange={(e) => setAdvice(e.target.value)}
                  rows={3}
                  maxLength={2000}
                  placeholder="e.g. Drink warm fluids, avoid cold exposure, rest for 3 days..."
                  className="form-control"
                />
              </div>
            </div>

            {/* Handwritten scan -> draft (doctor reviews before saving) */}
            <div style={{ background: '#f8fafc', border: '1px dashed #94a3b8', borderRadius: 10, padding: '14px 16px', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <ScanLine size={16} color="#0ea5e9" />
                <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>Scan handwritten prescription (draft only)</strong>
              </div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.pdf,.txt"
                  onChange={(e) => setScanFile(e.target.files?.[0] || null)}
                  aria-label="Handwritten prescription scan"
                />
                <button type="button" className="btn btn-secondary btn-sm" onClick={handleScan} disabled={scanLoading || !scanFile}>
                  {scanLoading ? 'Reading...' : 'Read scan'}
                </button>
              </div>
              {scanDraft && (
                <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#334155' }}>
                  <div>Detected {scanDraft.items?.length || 0} medicine row(s) via {scanDraft.extraction_method}. {scanDraft.note}</div>
                  {(scanDraft.items || []).map((d, i) => (
                    <div key={i} style={{ padding: '4px 0' }}>
                      • <strong>{d.medicine_name}</strong> {d.dosage} — {d.frequency} — {d.duration}
                    </div>
                  ))}
                  {(scanDraft.items?.length || 0) > 0 && (
                    <button type="button" className="btn btn-teal btn-sm" style={{ marginTop: 8 }} onClick={handleLoadDraft}>
                      Load draft into form for review
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Medicines List Builder */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Pill size={16} color="#0d9488" />
                  <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f172a' }}>
                    Prescribed Medications ({items.length})
                  </span>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleAddItem}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  <Plus size={14} />
                  <span>Add Medicine</span>
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {items.map((item, index) => (
                  <div
                    key={index}
                    style={{
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: 10,
                      padding: '16px',
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.75rem' }}>Medicine Name *</label>
                        <input
                          type="text"
                          placeholder="e.g. Amoxicillin / Clavulanate"
                          value={item.medicine_name}
                          onChange={(e) => handleItemChange(index, 'medicine_name', e.target.value)}
                          required
                          className="form-control"
                          style={{ background: 'white' }}
                        />
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.75rem' }}>Dosage *</label>
                        <input
                          type="text"
                          placeholder="e.g. 625 mg"
                          value={item.dosage}
                          onChange={(e) => handleItemChange(index, 'dosage', e.target.value)}
                          required
                          className="form-control"
                          style={{ background: 'white' }}
                        />
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.75rem' }}>Frequency *</label>
                        <input
                          type="text"
                          placeholder="e.g. 1-0-1 (Twice daily)"
                          value={item.frequency}
                          onChange={(e) => handleItemChange(index, 'frequency', e.target.value)}
                          required
                          className="form-control"
                          style={{ background: 'white' }}
                        />
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.75rem' }}>Duration *</label>
                        <input
                          type="text"
                          placeholder="e.g. 5 days"
                          value={item.duration}
                          onChange={(e) => handleItemChange(index, 'duration', e.target.value)}
                          required
                          className="form-control"
                          style={{ background: 'white' }}
                        />
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.75rem' }}>Route</label>
                        <select
                          value={item.route}
                          onChange={(e) => handleItemChange(index, 'route', e.target.value)}
                          className="form-control"
                          style={{ background: 'white' }}
                        >
                          <option value="Oral">Oral (PO)</option>
                          <option value="Topical">Topical</option>
                          <option value="Inhalation">Inhalation</option>
                          <option value="Intramuscular">Intramuscular (IM)</option>
                          <option value="Intravenous">Intravenous (IV)</option>
                          <option value="Sublingual">Sublingual</option>
                          <option value="Ophthalmic">Ophthalmic (Eye drops)</option>
                        </select>
                      </div>

                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.75rem' }}>Instructions</label>
                        <input
                          type="text"
                          placeholder="e.g. After meals with water"
                          value={item.instructions}
                          onChange={(e) => handleItemChange(index, 'instructions', e.target.value)}
                          className="form-control"
                          style={{ background: 'white' }}
                        />
                      </div>
                    </div>

                    {items.length > 1 && (
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ color: '#b91c1c', borderColor: '#fecaca', background: '#fff' }}
                          onClick={() => handleRemoveItem(index)}
                        >
                          <Trash2 size={13} style={{ marginRight: 4 }} />
                          <span>Remove Item</span>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Safety acknowledgement (required when severe flags exist) */}
            <div style={{ background: needsAck ? '#fef2f2' : '#f8fafc', border: `1px solid ${needsAck ? '#fecaca' : '#e2e8f0'}`, borderRadius: 10, padding: '14px 16px', marginBottom: 20 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.88rem', fontWeight: 600, color: '#0f172a', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={ackWarnings}
                  onChange={(e) => setAckWarnings(e.target.checked)}
                />
                <span>I have reviewed the medication safety flags and take clinical responsibility</span>
              </label>
              {ackWarnings && (
                <input
                  type="text"
                  value={ackReason}
                  onChange={(e) => setAckReason(e.target.value)}
                  placeholder="Reason for overriding severe flags (required)"
                  className="form-control"
                  style={{ marginTop: 10, background: 'white' }}
                  aria-label="Acknowledgement reason"
                />
              )}
              <SafetyWarnings warnings={lastWarnings} />
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', borderTop: '1px solid #f1f5f9', paddingTop: 18 }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => { resetForm(); setFormVisible(false) }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
                style={{ minWidth: 160 }}
              >
                {loading ? 'Saving...' : editingId ? 'Update Prescription' : 'Save as Draft'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Prescription Directory Card */}
      <div className="card" style={{ padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18, flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={18} color="#0ea5e9" />
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>
              {isDoctor ? 'Prescriptions (drafts & issued)' : 'My Prescriptions'}
            </h3>
          </div>
          <span className="badge badge-neutral">
            {prescriptions.length} {prescriptions.length === 1 ? 'Record' : 'Records'}
          </span>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#64748b', fontSize: '0.9rem' }}>Loading prescriptions...</p>
          </div>
        )}

        {!loading && prescriptions.length === 0 && (
          <div className="empty-state">
            <Pill size={36} />
            <h4 style={{ margin: '8px 0 4px', color: '#0f172a' }}>No prescriptions found</h4>
            <p style={{ margin: 0, fontSize: '0.85rem' }}>
              {isDoctor
                ? 'Create a new prescription to issue medical orders to your patients.'
                : 'Prescriptions issued by your doctor will appear here.'}
            </p>
          </div>
        )}

        {!loading && prescriptions.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {prescriptions.map((rx) => {
              const dateStr = rx.prescription_date ? new Date(rx.prescription_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : 'Date not set'
              const status = rx.status || 'draft'
              const statusLabel = status === 'issued'
                ? 'Issued'
                : status === 'draft'
                  ? 'Draft'
                  : status.charAt(0).toUpperCase() + status.slice(1)
              const statusClass = status === 'issued'
                ? 'badge-success'
                : status === 'draft'
                  ? 'badge-warning'
                  : status === 'revoked'
                    ? 'badge-danger'
                    : 'badge-neutral'
              const isPdfBusy = pdfLoadingId === rx.id

              return (
                <div
                  key={rx.id}
                  className="card card-hover"
                  style={{
                    padding: '20px',
                    marginBottom: 0,
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
                    
                    {/* Left Details */}
                    <div style={{ display: 'flex', gap: 14, flex: 1, minWidth: 280 }}>
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 10,
                          background: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
                          color: 'white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontFamily: 'serif',
                          fontSize: '1.2rem',
                          flexShrink: 0,
                        }}
                      >
                        ℞
                      </div>

                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                          <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
                            Prescription #{rx.id.slice(-6).toUpperCase()}
                          </h4>
                          <span className={`badge ${statusClass}`}>
                            {statusLabel}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 4, flexWrap: 'wrap', fontSize: '0.82rem', color: '#64748b' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <Calendar size={13} />
                            {dateStr}
                          </span>
                          {rx.patient_id && (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                              <User size={13} />
                              Patient: {rx.patient_id.slice(0, 10)}
                            </span>
                          )}
                          {rx.follow_up_date && (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#0d9488' }}>
                              <Clock size={13} />
                              Follow-up: {new Date(rx.follow_up_date).toLocaleDateString()}
                            </span>
                          )}
                        </div>

                        {/* Medicine Pills preview */}
                        {rx.items && rx.items.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
                            {rx.items.map((m, idx) => (
                              <span
                                key={idx}
                                style={{
                                  background: '#f1f5f9',
                                  color: '#334155',
                                  padding: '3px 8px',
                                  borderRadius: 6,
                                  fontSize: '0.78rem',
                                  fontWeight: 500,
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                }}
                              >
                                <Pill size={11} color="#0ea5e9" />
                                <strong>{m.medicine_name}</strong> {m.dosage && `(${m.dosage})`}
                              </span>
                            ))}
                          </div>
                        )}

                        {rx.diagnosis_notes && (
                          <p style={{ margin: '8px 0 0', fontSize: '0.82rem', color: '#475569', fontStyle: 'italic' }}>
                            "{rx.diagnosis_notes}"
                          </p>
                        )}

                        <SafetyWarnings warnings={rx.safety_warnings} />

                        <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                          {rx.verification_status === 'revoked' ? (
                            <span className="badge badge-danger">Verification revoked</span>
                          ) : (
                            <span className="badge badge-success">Verified prescription</span>
                          )}
                          {rx.verification_token && (
                            <Link
                              to={`/verify/${rx.verification_token}`}
                              target="_blank"
                              rel="noreferrer"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.8rem', color: '#0284c7' }}
                            >
                              <QrCode size={13} /> Public verification page
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right Actions */}
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handlePdf(rx)}
                        disabled={isPdfBusy}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                      >
                        <FileDown size={14} />
                        <span>{isPdfBusy ? 'Generating...' : rx.file_path ? 'Download PDF' : 'Generate PDF'}</span>
                      </button>

                      {isDoctor && (
                        <>
                          {status === 'draft' && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => handleIssue(rx)}
                              style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                            >
                              <Send size={13} />
                              <span>Issue to Patient</span>
                            </button>
                          )}
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleEdit(rx)}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                          >
                            <Edit3 size={13} />
                            <span>Edit</span>
                          </button>
                          {rx.verification_status !== 'revoked' && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleRevoke(rx)}
                              title="Revoke public verification"
                              style={{ color: '#b45309', borderColor: '#fde68a' }}
                            >
                              <Ban size={13} />
                              <span>Revoke</span>
                            </button>
                          )}
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleDelete(rx)}
                            style={{ color: '#b91c1c', borderColor: '#fecaca' }}
                          >
                            <Trash2 size={13} />
                          </button>
                        </>
                      )}
                    </div>

                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
