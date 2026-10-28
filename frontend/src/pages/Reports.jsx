import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { uploadReport, interpretReport, listReports, getReport, deleteReport, chatWithReport } from '../services/reports.js'
import { listPatients } from '../services/patients.js'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import {
  UploadCloud,
  FileText,
  Sparkles,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Check,
  ArrowLeft,
  Activity,
  FileSearch,
  BookOpen,
  Info,
   X,
   FileCheck2,
   RefreshCw,
   Search,
   Trash2,
   FlaskConical,
   MessageCircle,
   Volume2,
   Send,
   Quote,
   BadgeCheck,
   BadgeAlert
 } from 'lucide-react'

function flagBadgeClass(flag) {
  if (flag === 'low') return 'badge-warning'
  if (flag === 'high') return 'badge-danger'
  if (flag === 'unknown') return 'badge-neutral'
  return 'badge-success'
}

function flagLabel(flag) {
  if (flag === 'low') return 'Low'
  if (flag === 'high') return 'High'
  if (flag === 'unknown') return 'Unknown'
  return 'Normal'
}

export function LabResultsTable({ labs }) {
  if (!labs || labs.length === 0) {
    return (
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <h3>
            <FlaskConical size={18} color="var(--teal-600)" />
            <span>Laboratory Values</span>
          </h3>
        </div>
        <p style={{ color: 'var(--slate-400)', padding: '4px 4px 8px', fontSize: '0.9rem' }}>
          No laboratory values were detected in this report.
        </p>
      </div>
    )
  }
  return (
    <div className="card" style={{ marginTop: 24 }} data-testid="lab-results-table">
      <div className="card-header">
        <h3>
          <FlaskConical size={18} color="var(--teal-600)" />
          <span>Laboratory Values ({labs.length})</span>
        </h3>
        <span className="badge badge-teal">Reference ranges are educational, not clinical advice</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }} aria-label="Laboratory values">
          <thead>
            <tr style={{ textAlign: 'left', color: 'var(--slate-500)', borderBottom: '1px solid var(--slate-200)' }}>
              <th style={{ padding: '8px 10px' }}>Test</th>
              <th style={{ padding: '8px 10px' }}>Value</th>
              <th style={{ padding: '8px 10px' }}>Reference Range</th>
              <th style={{ padding: '8px 10px' }}>Flag</th>
              <th style={{ padding: '8px 10px' }}>Range Source</th>
            </tr>
          </thead>
          <tbody>
            {labs.map((lab, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid var(--slate-100)' }}>
                <td style={{ padding: '8px 10px', fontWeight: 600, color: 'var(--slate-800)' }}>{lab.name}</td>
                <td style={{ padding: '8px 10px' }}>{lab.value}{lab.unit ? ` ${lab.unit}` : ''}</td>
                <td style={{ padding: '8px 10px', color: 'var(--slate-600)' }}>
                  {lab.ref_low} – {lab.ref_high}{lab.unit ? ` ${lab.unit}` : ''}
                </td>
                <td style={{ padding: '8px 10px' }}>
                  <span className={`badge ${flagBadgeClass(lab.flag)}`}>{flagLabel(lab.flag)}</span>
                </td>
                <td style={{ padding: '8px 10px', color: 'var(--slate-500)', fontSize: '0.8rem' }}>
                  {lab.range_source === 'report' ? 'Printed on report' : lab.range_source === 'table' ? 'Standard table' : 'General adult'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ color: 'var(--slate-500)', fontSize: '0.8rem', marginTop: 10 }}>
        Flags only show whether a value is inside or outside the reference range.
        Discuss any result with your doctor — this is an explanation, not a diagnosis.
      </p>
    </div>
  )
}

export const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi' },
  { code: 'mr', label: 'Marathi' },
  { code: 'ta', label: 'Tamil' },
  { code: 'te', label: 'Telugu' },
  { code: 'bn', label: 'Bengali' },
  { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' },
]

export function speakText(text, lang = 'en') {
  try {
    if (!('speechSynthesis' in window) || !text) return false
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang
    window.speechSynthesis.speak(utterance)
    return true
  } catch {
    return false
  }
}

export function highlightVerifiedQuotes(text, quotes) {
  // Returns React nodes with verified quotes wrapped in <mark>.
  if (!text) return text
  const valid = (quotes || []).filter((q) => q && q.length >= 4)
  if (valid.length === 0) return text
  const lower = text.toLowerCase()
  const ranges = []
  valid.forEach((q) => {
    const idx = lower.indexOf(q.toLowerCase())
    if (idx >= 0) ranges.push([idx, idx + q.length])
  })
  if (ranges.length === 0) return text
  ranges.sort((a, b) => a[0] - b[0])
  const merged = []
  ranges.forEach((r) => {
    const last = merged[merged.length - 1]
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1])
    else merged.push([...r])
  })
  const nodes = []
  let pos = 0
  merged.forEach(([s, e], i) => {
    if (s > pos) nodes.push(text.slice(pos, s))
    nodes.push(<mark key={i} style={{ background: '#fef08a', borderRadius: 2 }}>{text.slice(s, e)}</mark>)
    pos = e
  })
  if (pos < text.length) nodes.push(text.slice(pos))
  return nodes
}

export function ChatPanel({ reportId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const send = async (e) => {
    e.preventDefault()
    const question = input.trim()
    if (!question || busy) return
    setError('')
    const history = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }))
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setInput('')
    setBusy(true)
    try {
      const res = await chatWithReport(reportId, question, history)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.answer, refused: res.refused }])
    } catch (err) {
      setError(err.response?.data?.detail || 'Chat failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card" style={{ marginTop: 24 }} data-testid="chat-panel">
      <div className="card-header">
        <h3>
          <MessageCircle size={18} color="var(--primary-600)" />
          <span>Chat With Your Report</span>
        </h3>
        <span className="badge badge-teal">Answers only from this report</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 320, overflowY: 'auto', marginBottom: 12 }} aria-live="polite">
        {messages.length === 0 && (
          <p style={{ color: 'var(--slate-400)', fontSize: '0.88rem' }}>
            Ask about values and findings written in this report — e.g. "What was my hemoglobin?".
            Diagnosis and treatment questions will be declined.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? 'var(--primary-600)' : 'var(--slate-100)',
              color: m.role === 'user' ? 'white' : 'var(--slate-800)',
              borderRadius: 12,
              padding: '8px 12px',
              maxWidth: '85%',
              fontSize: '0.88rem',
              lineHeight: 1.5,
            }}
          >
            {m.content}
          </div>
        ))}
        {busy && <p style={{ color: 'var(--slate-400)', fontSize: '0.85rem' }}>Thinking...</p>}
      </div>
      {error && <div className="alert-banner alert-banner-danger" style={{ marginBottom: 10 }}>{error}</div>}
      <form onSubmit={send} style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this report..."
          aria-label="Ask about this report"
          className="form-control"
          style={{ flex: 1 }}
          maxLength={1000}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !input.trim()} aria-label="Send question">
          <Send size={14} /> Send
        </button>
      </form>
      <p style={{ color: 'var(--slate-500)', fontSize: '0.78rem', marginTop: 8 }}>
        Educational explanation only — not a diagnosis. Never share treatment decisions without your doctor.
      </p>
    </div>
  )
}

export default function Reports() {
  const { id: paramId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()

  const [file, setFile] = useState(null)
  const [category, setCategory] = useState('Blood Test')
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [interpretation, setInterpretation] = useState(null)
  const [interpreting, setInterpreting] = useState(false)
  const [reports, setReports] = useState([])
  const [loadingReports, setLoadingReports] = useState(false)
  const [viewingReport, setViewingReport] = useState(null)
  const [copiedText, setCopiedText] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [filterCategory, setFilterCategory] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [doctorPatients, setDoctorPatients] = useState([])
  const [selectedPatientId, setSelectedPatientId] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [language, setLanguage] = useState('en')
  const fileInputRef = useRef(null)

  const isDoctor = user?.role === 'doctor'

  useEffect(() => {
    if (!isDoctor && searchParams.get('upload') === '1') {
      const target = document.getElementById('upload-report')
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [isDoctor, searchParams])

  const fetchReports = async (patientId = selectedPatientId) => {
    setLoadingReports(true)
    try {
      // Upload/interpret are patient-only actions; doctors review a selected
      // patient's reports in read-only mode.
      if (isDoctor && !patientId && !paramId) {
        setReports([])
        return
      }
      const data = await listReports(0, 50, isDoctor ? patientId : null)
      setReports(data || [])
    } catch (err) {
      // Silently fail
    } finally {
      setLoadingReports(false)
    }
  }

  useEffect(() => {
    if (isDoctor) {
      listPatients('', 0, 50).then((data) => setDoctorPatients(data || [])).catch(() => {})
    }
    fetchReports()
    if (paramId) {
      handleViewReport(paramId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramId])

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      setFile(droppedFile)
      if (!title) setTitle(droppedFile.name.replace(/\.[^/.]+$/, ''))
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      if (!title) setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setInterpretation(null)

    if (!file) {
      setError('Please select a file to upload')
      return
    }

    setLoading(true)
    try {
      const data = await uploadReport(file, category, title || file.name)
      setResult(data)
      setFile(null)
      setTitle('')
      await fetchReports()
      // Phase 4d: background mode returns status "processing" — poll with
      // backoff until it completes or fails.
      if (data && data.status === 'processing' && data.id) {
        pollReportUntilDone(data.id)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please check file format.')
    } finally {
      setLoading(false)
    }
  }

  const pollReportUntilDone = async (reportId) => {
    const delays = [2000, 4000, 8000, 8000, 15000]
    for (const wait of delays) {
      await new Promise((resolve) => setTimeout(resolve, wait))
      try {
        const data = await getReport(reportId)
        if (data.status !== 'processing') {
          setResult(data)
          await fetchReports()
          return
        }
      } catch {
        return
      }
    }
  }

  const handleInterpret = async (reportId = null) => {
    const targetId = reportId || result?.id || viewingReport?.id
    if (!targetId) return
    setInterpreting(true)
    setError('')
    try {
      const data = await interpretReport(targetId, language)
      setInterpretation(data)
      // Update viewing report if active
      if (viewingReport && viewingReport.id === targetId) {
        setViewingReport(prev => ({ ...prev, ai_status: 'success', ai_interpretation: data }))
      }
      await fetchReports()
    } catch (err) {
      const detail = err.response?.data?.detail
      if (detail && detail.includes('OMNIROUTE_API_KEY is not configured')) {
        setError('AI interpretation service is not configured. Please contact support.')
      } else {
        setError(detail || 'Interpretation request failed. Please try again.')
      }
    } finally {
      setInterpreting(false)
    }
  }

  const handleViewReport = async (reportId) => {
    setLoading(true)
    setError('')
    try {
      const data = await getReport(reportId)
      setViewingReport(data)
      if (data.ai_interpretation) {
        setInterpretation(data.ai_interpretation)
      } else {
        setInterpretation(null)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load report')
    } finally {
      setLoading(false)
    }
  }

  const handleBackToList = () => {
    setViewingReport(null)
    setResult(null)
    setInterpretation(null)
    setError('')
    if (paramId) {
      navigate('/reports')
    }
  }

  const handleConfirmDelete = async () => {
    if (!confirmDelete || deletingId) return
    setDeletingId(confirmDelete.id)
    setError('')
    try {
      await deleteReport(confirmDelete.id)
      setReports((prev) => prev.filter((r) => r.id !== confirmDelete.id))
      if (viewingReport && viewingReport.id === confirmDelete.id) {
        handleBackToList()
      } else {
        await fetchReports()
      }
      setConfirmDelete(null)
    } catch (err) {
      setError(err.response?.data?.detail || "We couldn't delete this report. Please try again.")
    } finally {
      setDeletingId(null)
    }
  }

  const handleCopyText = (text) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopiedText(true)
    setTimeout(() => setCopiedText(false), 2000)
  }

  const filteredReports = reports.filter(r => {
    const matchesCategory = filterCategory === 'ALL' || r.category === filterCategory
    const matchesSearch = !searchQuery || r.title?.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  // Render Interpretation Sections Component
  const renderInterpretationView = (data) => {
    if (!data) return null
    return (
      <div style={{ marginTop: 24 }}>
        {/* Safety Disclaimer Banner */}
        <div className="safety-note-banner">
          <ShieldAlert size={20} style={{ flexShrink: 0, marginTop: 1 }} />
          <div>
            <div style={{ fontWeight: 700, marginBottom: 2 }}>Educational Patient Information</div>
            <div>{data.safety_note || "This is an explanation of the supplied report findings and not a medical diagnosis. Consult a licensed healthcare provider for clinical decisions."}</div>
          </div>
        </div>

        {/* AI Patient Summary Card */}
        {data.summary && (
          <div className="ai-summary-card">
            <div className="ai-summary-header">
              <div className="ai-sparkle-icon">
                <Sparkles size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.2rem', color: 'var(--teal-700)' }}>Patient-Friendly Summary</h3>
                <span style={{ fontSize: '0.82rem', color: 'var(--slate-500)' }}>Generated by Clinical AI Engine</span>
              </div>
            </div>
            <p style={{ color: 'var(--slate-800)', fontSize: '1.02rem', lineHeight: 1.6 }}>
              {data.summary}
            </p>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ marginTop: 10 }}
              onClick={() => speakText(data.summary, data.language || 'en')}
              aria-label="Listen to summary"
              title="Listen using your browser's speech synthesis"
            >
              <Volume2 size={14} /> Listen
            </button>
          </div>
        )}

        {/* Key Findings Section */}
        {data.key_findings && data.key_findings.length > 0 && (
          <div className="card">
            <div className="card-header">
              <h3>
                <Activity size={18} color="var(--primary-600)" />
                <span>Key Medical Findings ({data.key_findings.length})</span>
              </h3>
            </div>
            <div className="findings-grid">
              {data.key_findings.map((kf, idx) => {
                const sev = kf.severity?.toLowerCase() || ''
                let findingClass = 'finding-normal'
                if (sev.includes('critical') || sev.includes('high') || sev.includes('severe')) {
                  findingClass = 'finding-critical'
                } else if (sev.includes('mod') || sev.includes('warn') || sev.includes('mild')) {
                  findingClass = 'finding-warning'
                }

                return (
                  <div key={idx} className={`finding-card ${findingClass}`}>
                    <div className="finding-header">
                      <span className="finding-title">{kf.finding}</span>
                      {kf.severity && (
                        <span className={`badge ${findingClass === 'finding-critical' ? 'badge-danger' : findingClass === 'finding-warning' ? 'badge-warning' : 'badge-success'}`}>
                          {kf.severity}
                        </span>
                      )}
                    </div>
                    <p className="finding-desc">{kf.explanation}</p>
                    {kf.source_quote && (
                      <div style={{ marginTop: 8, fontSize: '0.8rem', color: 'var(--slate-600)', background: 'var(--slate-50)', borderRadius: 6, padding: '6px 10px' }}>
                        <Quote size={12} style={{ marginRight: 4 }} />
                        <em>"{kf.source_quote}"</em>
                      </div>
                    )}
                    {kf.source_quote ? (
                      kf.verified ? (
                        <span className="badge badge-success" style={{ marginTop: 8 }}>
                          <BadgeCheck size={12} /> Verified in report
                        </span>
                      ) : (
                        <span className="badge badge-warning" style={{ marginTop: 8 }}>
                          <BadgeAlert size={12} /> Unverified — quote not found in report
                        </span>
                      )
                    ) : null}
                    {kf.negated && (
                      <span className="badge badge-warning" style={{ marginTop: 8 }}>
                        Negated Finding (Ruled Out)
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Measurements & Laboratory Values */}
        {data.measurements && data.measurements.length > 0 && (
          <div className="card">
            <div className="card-header">
              <h3>
                <FileSearch size={18} color="var(--teal-600)" />
                <span>Extracted Lab Measurements ({data.measurements.length})</span>
              </h3>
            </div>
            <div className="measurements-grid">
              {data.measurements.map((m, idx) => (
                <div key={idx} className="measurement-card">
                  <div>
                    <div className="measurement-title">{m.name}</div>
                    <div className="measurement-value-row">
                      <span className="measurement-value">{m.value}</span>
                      {m.unit && <span className="measurement-unit">{m.unit}</span>}
                    </div>
                  </div>
                  {m.explanation && (
                    <div className="measurement-explanation">{m.explanation}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Medical Terms Glossary */}
        {data.medical_terms && data.medical_terms.length > 0 && (
          <div className="card">
            <div className="card-header">
              <h3>
                <BookOpen size={18} color="var(--primary-600)" />
                <span>Medical Terms Glossary</span>
              </h3>
            </div>
            <div className="medical-terms-grid">
              {data.medical_terms.map((item, idx) => (
                <div key={idx} className="medical-term-pill">
                  <div className="medical-term-name">{item.term}</div>
                  <div className="medical-term-desc">{item.simple_explanation}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Limitations & Advice */}
        {data.limitations && data.limitations.length > 0 && (
          <div className="card" style={{ background: 'var(--slate-50)' }}>
            <div className="card-header">
              <h3 style={{ fontSize: '1rem', color: 'var(--slate-700)' }}>
                <Info size={16} />
                <span>Interpretation Limitations</span>
              </h3>
            </div>
            <ul style={{ paddingLeft: 20, color: 'var(--slate-600)', fontSize: '0.88rem', lineHeight: 1.6 }}>
              {data.limitations.map((limit, idx) => (
                <li key={idx} style={{ marginBottom: 4 }}>{limit}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  // If currently viewing a specific report details
  if (viewingReport) {
    const isInterpreted = viewingReport.ai_status === 'success' || !!interpretation || !!viewingReport.ai_interpretation
    const currentAiData = interpretation || viewingReport.ai_interpretation

    return (
      <div>
        {/* Detail Header */}
        <div className="page-header">
          <div className="page-header-title">
            <button
              onClick={handleBackToList}
              className="btn btn-ghost btn-sm"
              style={{ padding: 0, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--slate-500)' }}
            >
              <ArrowLeft size={16} /> Back to Reports Directory
            </button>
            <h1>{viewingReport.title}</h1>
            <p>Report ID: {viewingReport.id} &bull; Category: <strong>{viewingReport.category}</strong></p>
          </div>

          <div className="page-header-actions">
            {!isDoctor ? (
              <>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  aria-label="Interpretation language"
                  title="Language for the patient-friendly explanation"
                  className="form-control"
                  style={{ maxWidth: 150 }}
                >
                  {SUPPORTED_LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>{l.label}</option>
                  ))}
                </select>
                <button
                  className="btn btn-primary"
                  onClick={() => handleInterpret(viewingReport.id)}
                  disabled={interpreting || deletingId === viewingReport.id}
                >
                  {interpreting ? (
                    <>
                      <RefreshCw size={16} className="spin" />
                      <span>Interpreting Report...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      <span>{isInterpreted ? 'Re-interpret with AI' : 'Interpret Report'}</span>
                    </>
                  )}
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ color: 'var(--danger-text)', borderColor: 'var(--danger-border)' }}
                  onClick={() => setConfirmDelete(viewingReport)}
                  disabled={deletingId === viewingReport.id}
                  title="Delete this report"
                >
                  <Trash2 size={14} />
                  <span>{deletingId === viewingReport.id ? 'Deleting...' : 'Delete Report'}</span>
                </button>
              </>
            ) : (
              <span className="badge badge-info">Read-only review — interpretation is a patient action</span>
            )}
          </div>
        </div>

        {error && (
          <div className="safety-note-banner" style={{ background: 'var(--danger-bg)', borderColor: 'var(--danger-border)', color: 'var(--danger-text)' }}>
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        {/* Meta Stats & Pipeline Status */}
        <div className="stats-grid" style={{ marginBottom: 20 }}>
          <div className="stat-card">
            <div className="stat-icon-wrapper stat-icon-blue">
              <FileText size={20} />
            </div>
            <div className="stat-info">
              <div className="stat-label">Extraction Method</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--slate-800)', textTransform: 'uppercase' }}>
                {viewingReport.extraction_method || 'Text'}
              </div>
              <div className="stat-helper">{viewingReport.ocr_used ? 'Optical Character Recognition used' : 'Native text parser'}</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-wrapper stat-icon-teal">
              <Activity size={20} />
            </div>
            <div className="stat-info">
              <div className="stat-label">NLP Processing</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--slate-800)', textTransform: 'capitalize' }}>
                {viewingReport.nlp_status || 'Completed'}
              </div>
              <div className="stat-helper">{viewingReport.entities?.length || 0} entities identified</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-wrapper stat-icon-amber">
              <Sparkles size={20} />
            </div>
            <div className="stat-info">
              <div className="stat-label">AI Status</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem', color: isInterpreted ? 'var(--success-text)' : 'var(--slate-600)', textTransform: 'capitalize' }}>
                {isInterpreted ? 'Analyzed' : 'Ready to Interpret'}
              </div>
              <div className="stat-helper">{isInterpreted ? 'Summary available below' : 'Click Interpret above'}</div>
            </div>
          </div>
        </div>

        {/* AI Interpretation View */}
        {renderInterpretationView(currentAiData)}

        {/* Laboratory Values (deterministic parser output) */}
        <LabResultsTable labs={viewingReport.lab_results} />

        {/* Extracted Text & Entities Drawer */}
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-header">
            <h3>
              <FileSearch size={18} color="var(--slate-700)" />
              <span>Extracted Clinical Text & OCR Output</span>
            </h3>
            {viewingReport.extracted_text && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleCopyText(viewingReport.extracted_text)}
              >
                {copiedText ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                <span>{copiedText ? 'Copied' : 'Copy Text'}</span>
              </button>
            )}
          </div>

          {viewingReport.extracted_text ? (
            <div className="ocr-text-box">
              {highlightVerifiedQuotes(
                viewingReport.extracted_text,
                (currentAiData?.key_findings || []).filter((kf) => kf.verified).map((kf) => kf.source_quote)
              )}
            </div>
          ) : (
            <p style={{ color: 'var(--slate-400)', padding: 16 }}>No extracted text found in this report.</p>
          )}

          {/* Rule-Based NLP Entities Grouping */}
          {viewingReport.entities && viewingReport.entities.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ fontSize: '0.95rem', color: 'var(--slate-800)', marginBottom: 10 }}>
                Rule-Based NLP Entities Detected:
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {viewingReport.entities.map((ent, idx) => (
                  <span key={idx} className="badge badge-info" style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                    <strong>{ent.text}</strong> ({ent.type || 'entity'}{ent.value ? `: ${ent.value}${ent.unit ? ` ${ent.unit}` : ''}` : ''})
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Chat with this report */}
        <ChatPanel reportId={viewingReport.id} />

        {confirmDelete && (
          <ConfirmDialog
            title="Delete this report?"
            message="This will permanently remove the report and its stored analysis. This action cannot be undone."
            confirmLabel="Delete"
            cancelLabel="Cancel"
            loading={deletingId === confirmDelete.id}
            onConfirm={handleConfirmDelete}
            onCancel={() => { if (!deletingId) setConfirmDelete(null) }}
          />
        )}
      </div>
    )
  }

  // Default Reports Main Page (Upload & Directory)
  return (
    <div>
      <div className="page-header">
        <div className="page-header-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className="badge badge-teal">
              <Sparkles size={12} /> AI Medical Document Interpreter
            </span>
          </div>
          <h1>Medical Reports</h1>
          <p>Upload multi-format diagnostic reports for OCR extraction, clinical NLP analysis, and AI interpretation.</p>
        </div>
      </div>

      {error && (
        <div className="safety-note-banner" style={{ background: 'var(--danger-bg)', borderColor: 'var(--danger-border)', color: 'var(--danger-text)' }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Doctor patient picker (doctors review read-only; upload is patient-only) */}
      {isDoctor && (
        <div className="card">
          <div className="card-header">
            <h3>
              <FileSearch size={18} color="var(--primary-600)" />
              <span>Select Patient to Review</span>
            </h3>
            <span className="badge badge-info">Read-only review</span>
          </div>
          <select
            value={selectedPatientId}
            onChange={(e) => { setSelectedPatientId(e.target.value); fetchReports(e.target.value) }}
            className="form-control"
            style={{ maxWidth: 380 }}
          >
            <option value="">-- Choose a patient --</option>
            {doctorPatients.map((p) => (
              <option key={p.id} value={p.patient_id || p.user_id || p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
          {!selectedPatientId && (
            <p style={{ color: 'var(--slate-500)', fontSize: '0.88rem', marginTop: 10 }}>
              Choose a patient from the directory to list their reports. Uploading and AI
              interpretation are patient actions; doctors review the results.
            </p>
          )}
        </div>
      )}

      {/* Upload Box Card (patients only) */}
      {!isDoctor && (
      <div className="card" id="upload-report">
        <div className="card-header">
          <h3>
            <UploadCloud size={20} color="var(--primary-600)" />
            <span>Upload New Report</span>
          </h3>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, marginBottom: 18 }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Report Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Complete Blood Count (CBC) - March"
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="Blood Test">Blood Test / CBC</option>
                <option value="MRI">MRI Scan</option>
                <option value="CT">CT Scan</option>
                <option value="ECG">ECG / Cardiology</option>
                <option value="Ultrasound">Ultrasound / Sonography</option>
                <option value="X-ray">X-ray Diagnostic</option>
                <option value="Other">Other Clinical Document</option>
              </select>
            </div>
          </div>

          {/* Drag & Drop Upload Zone */}
          <div
            className={`upload-dropzone ${dragActive ? 'dragging' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.txt"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <div className="upload-icon-circle">
              <UploadCloud size={28} />
            </div>
            <h4>{file ? file.name : 'Click to browse or drag & drop medical report'}</h4>
            <p>Supported file types: PDF, PNG, JPG, JPEG, TXT &bull; Max 10MB</p>

            <div className="format-badges">
              <span className="format-pill">PDF Document</span>
              <span className="format-pill">Lab Image (PNG/JPG)</span>
              <span className="format-pill">Clinical TXT</span>
            </div>
          </div>

          {/* File Selected Notification Pill */}
          {file && (
            <div className="file-preview-pill">
              <div className="file-preview-info">
                <FileCheck2 size={20} color="var(--primary-600)" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--slate-900)' }}>{file.name}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--slate-500)' }}>{(file.size / 1024).toFixed(1)} KB</div>
                </div>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
              >
                <X size={16} />
              </button>
            </div>
          )}

          <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn btn-primary btn-lg" disabled={loading || !file}>
              {loading ? (
                <>
                  <RefreshCw size={18} className="spin" />
                  <span>Processing Upload & OCR...</span>
                </>
              ) : (
                <>
                  <UploadCloud size={18} />
                  <span>Upload & Analyze Report</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
      )}

      {/* Fresh Upload Result Card */}
      {result && (
        <div className="card" style={{ border: '2px solid var(--teal-500)', background: '#fafdfd' }}>
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <CheckCircle2 size={22} color="#10b981" />
              <h3 style={{ color: 'var(--teal-700)' }}>Upload & Extraction Completed</h3>
            </div>
            <span className="badge badge-success">Status: {result.status}</span>
          </div>

          {/* 4-Step Pipeline Visualizer */}
          <div className="pipeline-stepper">
            <div className="step-box completed">
              <div className="step-number"><Check size={14} /></div>
              <div className="step-text">1. Uploaded</div>
            </div>
            <div className="step-box completed">
              <div className="step-number"><Check size={14} /></div>
              <div className="step-text">2. OCR Extracted</div>
            </div>
            <div className="step-box completed">
              <div className="step-number"><Check size={14} /></div>
              <div className="step-text">3. NLP Entities</div>
            </div>
            <div className={`step-box ${interpretation ? 'completed' : 'active'}`}>
              <div className="step-number">{interpretation ? <Check size={14} /> : '4'}</div>
              <div className="step-text">4. AI Interpretation</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--slate-800)' }}>{result.title}</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--slate-500)', marginTop: 2 }}>
                Method: {result.extraction_method?.toUpperCase()} &bull; OCR Used: {result.ocr_used ? 'Yes' : 'No'} &bull; {result.entities?.length || 0} entities recognized
              </div>
            </div>

            <button
              type="button"
              className="btn btn-teal"
              onClick={() => handleInterpret(result.id)}
              disabled={interpreting}
            >
              {interpreting ? (
                <>
                  <RefreshCw size={16} className="spin" />
                  <span>Interpreting with AI...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Generate AI Interpretation</span>
                </>
              )}
            </button>
          </div>

          {/* Render Interpretation Result if already performed */}
          {interpretation && renderInterpretationView(interpretation)}

          {/* Laboratory values flagged at upload time */}
          {result.lab_results && <LabResultsTable labs={result.lab_results} />}
        </div>
      )}

      {/* Reports Directory & History List */}
      <div className="card" style={{ marginTop: 28 }}>
        <div className="card-header">
          <h3>
            <FileText size={20} color="var(--primary-600)" />
            <span>Reports Directory ({filteredReports.length})</span>
          </h3>

          {/* Search and Category Filter Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                placeholder="Search reports..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ padding: '6px 12px 6px 32px', fontSize: '0.85rem', width: 180, borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}
              />
              <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--slate-400)' }} />
            </div>

            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              style={{ padding: '6px 10px', fontSize: '0.85rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}
            >
              <option value="ALL">All Categories</option>
              <option value="Blood Test">Blood Test</option>
              <option value="MRI">MRI</option>
              <option value="CT">CT</option>
              <option value="ECG">ECG</option>
              <option value="Ultrasound">Ultrasound</option>
              <option value="X-ray">X-ray</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>

        {loadingReports && <p style={{ color: 'var(--slate-500)', padding: 16 }}>Loading reports directory...</p>}

        {!loadingReports && filteredReports.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--slate-400)' }}>
            <FileText size={40} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
            <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>
              {isDoctor && !selectedPatientId ? 'Select a patient above to list their reports' : 'No reports match your filters'}
            </p>
            <p style={{ fontSize: '0.85rem' }}>
              {isDoctor ? 'Reports uploaded by the selected patient will appear here' : 'Upload a report using the form above'}
            </p>
          </div>
        )}

        {!loadingReports && filteredReports.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {filteredReports.map((r) => {
              const hasAi = r.ai_status === 'success' || r.ai_interpretation
              return (
                <div
                  key={r.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '16px 20px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--slate-200)',
                    background: 'var(--white)',
                    gap: 16,
                    flexWrap: 'wrap'
                  }}
                  className="card-hover"
                >
                  <div style={{ minWidth: 240, flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--slate-900)' }}>{r.title}</span>
                      <span className="badge badge-info">{r.category}</span>
                      {r.ocr_used && <span className="badge badge-teal">OCR</span>}
                      {hasAi && (
                        <span className="badge badge-success">
                          <Sparkles size={11} /> AI Interpreted
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.84rem', color: 'var(--slate-500)' }}>
                      ID: #{r.id.slice(-6)} &bull; Method: {r.extraction_method?.toUpperCase()} &bull; File: {r.file_name}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleViewReport(r.id)}
                    >
                      <FileSearch size={14} />
                      <span>View Details</span>
                    </button>

                    {!isDoctor && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => {
                          handleViewReport(r.id)
                          handleInterpret(r.id)
                        }}
                        disabled={interpreting || deletingId === r.id}
                      >
                        <Sparkles size={14} />
                        <span>{hasAi ? 'Re-interpret' : 'Interpret'}</span>
                      </button>
                    )}
                    {!isDoctor && (
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ color: 'var(--danger-text)', borderColor: 'var(--danger-border)' }}
                        onClick={() => setConfirmDelete(r)}
                        disabled={deletingId === r.id}
                        title="Delete this report"
                      >
                        <Trash2 size={14} />
                        <span>{deletingId === r.id ? 'Deleting...' : 'Delete'}</span>
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title="Delete this report?"
          message="This will permanently remove the report and its stored analysis. This action cannot be undone."
          confirmLabel="Delete"
          cancelLabel="Cancel"
          loading={deletingId === confirmDelete.id}
          onConfirm={handleConfirmDelete}
          onCancel={() => { if (!deletingId) setConfirmDelete(null) }}
        />
      )}
    </div>
  )
}
