import { useState, useEffect } from 'react'
import { useAuth } from '../auth.jsx'
import { Link } from 'react-router-dom'
import { listReports } from '../services/reports.js'
import { listPatientPrescriptions, listDoctorPrescriptions, generatePrescriptionPdf, downloadPrescriptionPdf } from '../services/prescriptions.js'
import { listPatients } from '../services/patients.js'
import { getPatientHistory } from '../services/history.js'
import {
  FileText,
  Pill,
  Users,
  Clock,
  Sparkles,
  UploadCloud,
  ChevronRight,
  Activity,
  CheckCircle2,
  FileCheck,
  Stethoscope,
  ArrowUpRight,
  Download
} from 'lucide-react'

export default function Dashboard() {
  const { user } = useAuth()
  const isDoctor = user?.role === 'doctor'

  const [loading, setLoading] = useState(true)
  const [reports, setReports] = useState([])
  const [prescriptions, setPrescriptions] = useState([])
  const [patients, setPatients] = useState([])
  const [historyCount, setHistoryCount] = useState(0)
  const [aiStatus, setAiStatus] = useState(null)
  const [pdfBusyId, setPdfBusyId] = useState(null)
  const [pdfError, setPdfError] = useState('')

  // Backend caps list endpoints at 100 items; dashboard counts use the full
  // page so the numbers reflect the real database instead of a first page.
  const COUNT_LIMIT = 100

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true)
      try {
        const health = await fetch('/health').then((r) => (r.ok ? r.json() : null)).catch(() => null)
        if (health) setAiStatus(health)
        if (isDoctor) {
          const [patientsData, rxData] = await Promise.allSettled([
            listPatients('', 0, COUNT_LIMIT),
            listDoctorPrescriptions(0, COUNT_LIMIT)
          ])
          if (patientsData.status === 'fulfilled') setPatients(patientsData.value || [])
          if (rxData.status === 'fulfilled') setPrescriptions(rxData.value || [])
        } else {
          const [reportsData, rxData, histData] = await Promise.allSettled([
            listReports(0, COUNT_LIMIT),
            listPatientPrescriptions(0, COUNT_LIMIT),
            getPatientHistory('desc', 100)
          ])
          if (reportsData.status === 'fulfilled') setReports(reportsData.value || [])
          if (rxData.status === 'fulfilled') setPrescriptions(rxData.value || [])
          if (histData.status === 'fulfilled') setHistoryCount(histData.value?.length || 0)
        }
      } finally {
        setLoading(false)
      }
    }
    loadDashboardData()
  }, [isDoctor])

  const handleDownloadPdf = async (rxId) => {
    if (pdfBusyId) return
    setPdfBusyId(rxId)
    setPdfError('')
    try {
      const blob = await generatePrescriptionPdf(rxId)
      downloadPrescriptionPdf(blob, `prescription_${rxId}.pdf`)
    } catch (err) {
      setPdfError(err.response?.data?.detail || 'Failed to generate the PDF. Please try again.')
    } finally {
      setPdfBusyId(null)
    }
  }

  const interpretedReportsCount = reports.filter(r => r.ai_status === 'success' || r.ai_interpretation).length

  return (
    <div>
      {/* Welcome Page Header */}
      <div className="page-header">
        <div className="page-header-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className={`badge ${isDoctor ? 'badge-info' : 'badge-teal'}`}>
              {isDoctor ? <Stethoscope size={12} /> : <Activity size={12} />}
              {isDoctor ? 'Doctor Workspace' : 'Patient Health Portal'}
            </span>
          </div>
          <h1>Welcome, {user?.full_name || user?.email}</h1>
          <p>
            {isDoctor
              ? 'Review patient medical histories, analyze clinical reports, and create digital prescriptions.'
              : 'Upload and understand your medical lab reports with AI-powered plain-language explanations.'}
          </p>
        </div>

        <div className="page-header-actions">
          {isDoctor ? (
            <Link to="/prescriptions?new=1" className="btn btn-primary">
              <Pill size={16} />
              <span>New Prescription</span>
            </Link>
          ) : (
            <Link to="/reports" className="btn btn-primary">
              <UploadCloud size={16} />
              <span>Upload Medical Report</span>
            </Link>
          )}
        </div>
      </div>

      {/* Top Statistics Cards Grid */}
      <div className="stats-grid">
        {isDoctor ? (
          <>
            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-blue">
                <Users size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">Total Patients</div>
                <div className="stat-value">{loading ? '...' : patients.length}</div>
                <div className="stat-helper">Registered in directory</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-teal">
                <Pill size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">Prescriptions Issued</div>
                <div className="stat-value">{loading ? '...' : prescriptions.length}</div>
                <div className="stat-helper">Authored digital Rx</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-purple">
                <FileText size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">Report Access</div>
                <div className="stat-value">Per-patient</div>
                <div className="stat-helper">Open a patient dossier to review</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-amber">
                <Sparkles size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">AI Engine</div>
                <div className="stat-value">
                  {aiStatus === null && loading ? '...' : aiStatus?.ai_configured ? 'Active' : 'Offline'}
                </div>
                <div className="stat-helper">{aiStatus?.ai_model || 'Checking engine status...'}</div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-blue">
                <FileText size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">Uploaded Reports</div>
                <div className="stat-value">{loading ? '...' : reports.length}</div>
                <div className="stat-helper">Lab, MRI, Blood & Scan tests</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-teal">
                <Sparkles size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">AI Interpreted</div>
                <div className="stat-value">{loading ? '...' : interpretedReportsCount}</div>
                <div className="stat-helper">Simplified patient summaries</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-purple">
                <Pill size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">Prescriptions</div>
                <div className="stat-value">{loading ? '...' : prescriptions.length}</div>
                <div className="stat-helper">Active medications & advice</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper stat-icon-amber">
                <Clock size={24} />
              </div>
              <div className="stat-info">
                <div className="stat-label">Timeline Events</div>
                <div className="stat-value">{loading ? '...' : historyCount}</div>
                <div className="stat-helper">Chronological health logs</div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Action Banner / AI Highlights */}
      {!isDoctor && (
        <div className="ai-summary-card">
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
            <div style={{ maxWidth: 680 }}>
              <div className="ai-summary-header">
                <div className="ai-sparkle-icon">
                  <Sparkles size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.15rem', color: 'var(--teal-700)' }}>Have a new medical lab report?</h3>
                  <span style={{ fontSize: '0.84rem', color: 'var(--slate-500)' }}>PDF, PNG, JPG, or TXT documents supported</span>
                </div>
              </div>
              <p style={{ color: 'var(--slate-700)', fontSize: '0.94rem', lineHeight: 1.5, marginBottom: 16 }}>
                Upload your blood test, MRI, ECG, or scan. Our OCR & Clinical NLP system will extract metrics, and the AI interpreter will generate a patient-friendly summary without confusing medical jargon.
              </p>
              <Link to="/reports" className="btn btn-teal">
                <UploadCloud size={16} />
                <span>Upload & Interpret Report</span>
              </Link>
            </div>

            <div style={{
              background: 'rgba(255, 255, 255, 0.7)',
              backdropFilter: 'blur(8px)',
              border: '1px solid var(--teal-200)',
              borderRadius: 'var(--radius-lg)',
              padding: 16,
              minWidth: 240
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--slate-600)', textTransform: 'uppercase', marginBottom: 8 }}>
                AI Processing Pipeline:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.82rem', color: 'var(--slate-700)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} color="#10b981" /> 1. Text & OCR Extraction
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} color="#10b981" /> 2. Rule-Based Medical NLP
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} color="#10b981" /> 3. Measurement & Entity Recognition
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} color="#10b981" /> 4. Plain-Language Summary
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Recent Reports & Recent Prescriptions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 24 }}>
        {/* Left Column */}
        <div className="card">
          <div className="card-header">
            <h3>
              {isDoctor ? <Users size={18} color="var(--primary-600)" /> : <FileText size={18} color="var(--primary-600)" />}
              <span>{isDoctor ? 'Recent Patients' : 'Your Recent Reports'}</span>
            </h3>
            <Link to={isDoctor ? '/patients' : '/reports'} className="btn btn-ghost btn-sm">
              <span>View All</span>
              <ChevronRight size={14} />
            </Link>
          </div>

          {loading && <p style={{ color: 'var(--slate-500)', padding: 12 }}>{isDoctor ? 'Loading patients...' : 'Loading recent reports...'}</p>}

          {isDoctor && !loading && patients.length === 0 && (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--slate-400)' }}>
              <Users size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>No patients registered yet</p>
              <p style={{ fontSize: '0.85rem' }}>Patient records will appear here once registered</p>
            </div>
          )}

          {isDoctor && !loading && patients.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {patients.slice(0, 5).map((p) => (
                <div
                  key={p.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    border: '1px solid var(--slate-200)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--slate-50)',
                    transition: 'all 0.15s'
                  }}
                  className="card-hover"
                >
                  <div style={{ minWidth: 0, flex: 1, paddingRight: 10 }}>
                    <div style={{ fontWeight: 600, color: 'var(--slate-900)', fontSize: '0.92rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {p.full_name}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                      {p.blood_group && <span className="badge badge-danger">{p.blood_group}</span>}
                      {p.gender && <span className="badge badge-info" style={{ textTransform: 'capitalize' }}>{p.gender}</span>}
                    </div>
                  </div>

                  <Link to="/patients" className="btn btn-secondary btn-sm">
                    <span>Dossier</span>
                    <ArrowUpRight size={14} />
                  </Link>
                </div>
              ))}
            </div>
          )}

          {!isDoctor && !loading && reports.length === 0 && (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--slate-400)' }}>
              <FileCheck size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>No medical reports uploaded yet</p>
              <p style={{ fontSize: '0.85rem' }}>Upload your first lab report to get an AI interpretation</p>
              <Link to="/reports" className="btn btn-primary btn-sm" style={{ marginTop: 14 }}>
                <UploadCloud size={14} /> Upload Report
              </Link>
            </div>
          )}

          {!loading && reports.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {reports.slice(0, 5).map((r) => (
                <div
                  key={r.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    border: '1px solid var(--slate-200)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--slate-50)',
                    transition: 'all 0.15s'
                  }}
                  className="card-hover"
                >
                  <div style={{ minWidth: 0, flex: 1, paddingRight: 10 }}>
                    <div style={{ fontWeight: 600, color: 'var(--slate-900)', fontSize: '0.92rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {r.title}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                      <span className="badge badge-info">{r.category}</span>
                      {r.ocr_used && <span className="badge badge-teal">OCR Active</span>}
                      {r.ai_status === 'success' && <span className="badge badge-success"><Sparkles size={10} /> AI Ready</span>}
                    </div>
                  </div>

                  <Link to={`/reports/${r.id}`} className="btn btn-secondary btn-sm">
                    <span>View</span>
                    <ArrowUpRight size={14} />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Prescriptions */}
        <div className="card">
          <div className="card-header">
            <h3>
              <Pill size={18} color="var(--teal-600)" />
              <span>{isDoctor ? 'Issued Prescriptions' : 'Your Digital Prescriptions'}</span>
            </h3>
            <Link to="/prescriptions" className="btn btn-ghost btn-sm">
              <span>View All</span>
              <ChevronRight size={14} />
            </Link>
          </div>

          {loading && <p style={{ color: 'var(--slate-500)', padding: 12 }}>Loading prescriptions...</p>}

          {pdfError && (
            <div className="alert-banner alert-banner-danger" style={{ marginBottom: 12 }}>
              <span>{pdfError}</span>
            </div>
          )}

          {!loading && prescriptions.length === 0 && (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--slate-400)' }}>
              <Pill size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>No prescriptions found</p>
              <p style={{ fontSize: '0.85rem' }}>
                {isDoctor ? 'Create your first digital prescription for a patient' : 'Prescriptions prescribed by your doctor will appear here'}
              </p>
              {isDoctor && (
                <Link to="/prescriptions?new=1" className="btn btn-primary btn-sm" style={{ marginTop: 14 }}>
                  <Pill size={14} /> Create Prescription
                </Link>
              )}
            </div>
          )}

          {!loading && prescriptions.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {prescriptions.slice(0, 5).map((rx) => (
                <div
                  key={rx.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    border: '1px solid var(--slate-200)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--slate-50)',
                    transition: 'all 0.15s'
                  }}
                  className="card-hover"
                >
                  <div style={{ minWidth: 0, flex: 1, paddingRight: 10 }}>
                    <div style={{ fontWeight: 600, color: 'var(--slate-900)', fontSize: '0.92rem' }}>
                      Prescription #{rx.id.slice(-6).toUpperCase()}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--slate-500)', marginTop: 2 }}>
                      {rx.prescription_date ? new Date(rx.prescription_date).toLocaleDateString() : 'Recent'} &bull; {rx.items?.length || 0} medicine(s)
                    </div>
                  </div>

                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleDownloadPdf(rx.id)}
                    disabled={pdfBusyId === rx.id}
                    title="Download Official PDF"
                  >
                    <Download size={14} />
                    <span>{pdfBusyId === rx.id ? 'Working...' : 'PDF'}</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
