import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { listReports } from '../services/reports.js'
import { listPatientPrescriptions, generatePrescriptionPdf, downloadPrescriptionPdf } from '../services/prescriptions.js'
import { getPatientHistory } from '../services/history.js'
import {
  FileText,
  Pill,
  Clock,
  Sparkles,
  UploadCloud,
  ChevronRight,
  Activity,
  CheckCircle2,
  FileCheck,
  ArrowUpRight,
  Download,
  HeartPulse,
  ShieldCheck,
  Bell,
  AlertTriangle,
} from 'lucide-react'

export default function PatientDashboard() {
  const { user } = useAuth()

  const [loading, setLoading] = useState(true)
  const [reports, setReports] = useState([])
  const [prescriptions, setPrescriptions] = useState([])
  const [historyCount, setHistoryCount] = useState(0)
  const [aiStatus, setAiStatus] = useState(null)
  const [pdfBusyId, setPdfBusyId] = useState(null)
  const [pdfError, setPdfError] = useState('')

  const COUNT_LIMIT = 100

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true)
      try {
        const health = await fetch('/health').then((r) => (r.ok ? r.json() : null)).catch(() => null)
        if (health) setAiStatus(health)
        const [reportsData, rxData, histData] = await Promise.allSettled([
          listReports(0, COUNT_LIMIT),
          listPatientPrescriptions(0, COUNT_LIMIT),
          getPatientHistory('desc', 100)
        ])
        if (reportsData.status === 'fulfilled') setReports(reportsData.value || [])
        if (rxData.status === 'fulfilled') setPrescriptions(rxData.value || [])
        if (histData.status === 'fulfilled') setHistoryCount(histData.value?.length || 0)
      } finally {
        setLoading(false)
      }
    }
    loadDashboardData()
  }, [])

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

  const latestReport = reports[0]
  const latestPrescription = prescriptions[0]

  return (
    <div>
      {/* Welcome Page Header */}
      <div className="page-header">
        <div className="page-header-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className="badge badge-teal">
              <Activity size={12} />
              Patient Health Portal
            </span>
          </div>
          <h1>Welcome, {user?.full_name || user?.email}</h1>
          <p>Upload and understand your medical lab reports with AI-powered plain-language explanations.</p>
        </div>

        <div className="page-header-actions">
          <Link to="/patient/reports" className="btn btn-teal">
            <UploadCloud size={16} />
            <span>Upload Medical Report</span>
          </Link>
        </div>
      </div>

      {/* Alert Banner */}
      {pdfError && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div>{pdfError}</div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper stat-icon-teal">
            <FileCheck size={24} />
          </div>
          <div className="stat-info">
            <div className="stat-label">Uploaded Reports</div>
            <div className="stat-value">{loading ? '...' : reports.length}</div>
            <div className="stat-helper">Lab, MRI, Blood & Scan tests</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper stat-icon-emerald">
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
      </div>

      {/* Main Grid: Latest Report, Latest Prescription, Notifications */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
        {/* Latest Report */}
        <div className="card">
          <div className="card-header">
            <h3>
              <FileText size={18} color="var(--teal-600)" />
              <span>Latest Report</span>
            </h3>
            <Link to="/patient/reports" className="btn btn-ghost btn-sm">
              <span>View All</span>
              <ChevronRight size={14} />
            </Link>
          </div>

          {loading && <p style={{ color: 'var(--slate-500)', padding: 12 }}>Loading latest report...</p>}

          {!loading && !latestReport && (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--slate-400)' }}>
              <FileCheck size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>No medical reports uploaded yet</p>
              <p style={{ fontSize: '0.85rem' }}>Upload your first lab report to get an AI interpretation</p>
              <Link to="/patient/reports" className="btn btn-teal btn-sm" style={{ marginTop: 14 }}>
                <UploadCloud size={14} /> Upload Report
              </Link>
            </div>
          )}

          {latestReport && (
            <div style={{ padding: 16 }}>
              <div style={{ fontWeight: 600, color: 'var(--slate-900)', fontSize: '0.92rem', marginBottom: 4 }}>
                {latestReport.title}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                <span className="badge badge-info">{latestReport.category}</span>
                {latestReport.ocr_used && <span className="badge badge-teal">OCR Active</span>}
                {latestReport.ai_status === 'success' && <span className="badge badge-success"><Sparkles size={10} /> AI Ready</span>}
                {latestReport.ai_status === 'pending' && <span className="badge badge-warning">Processing...</span>}
                {latestReport.ai_status === 'error' && <span className="badge badge-danger">AI Failed</span>}
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--slate-500)', marginBottom: 16 }}>
                Uploaded: {new Date(latestReport.created_at).toLocaleDateString()}
              </p>
              <Link to={`/patient/reports/${latestReport.id}`} className="btn btn-teal btn-sm">
                <ArrowUpRight size={14} /> View Details
              </Link>
            </div>
          )}
        </div>

        {/* Latest Prescription */}
        <div className="card">
          <div className="card-header">
            <h3>
              <Pill size={18} color="var(--teal-600)" />
              <span>Latest Prescription</span>
            </h3>
            <Link to="/patient/prescriptions" className="btn btn-ghost btn-sm">
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

          {!loading && !latestPrescription && (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--slate-400)' }}>
              <Pill size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>No prescriptions found</p>
              <p style={{ fontSize: '0.85rem' }}>Prescriptions prescribed by your doctor will appear here</p>
            </div>
          )}

          {latestPrescription && (
            <div style={{ padding: 16 }}>
              <div style={{ fontWeight: 600, color: 'var(--slate-900)', fontSize: '0.92rem', marginBottom: 4 }}>
                Prescription #{latestPrescription.id.slice(-6).toUpperCase()}
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--slate-500)', marginBottom: 12 }}>
                {latestPrescription.prescription_date ? new Date(latestPrescription.prescription_date).toLocaleDateString() : 'Recent'} &bull; {latestPrescription.items?.length || 0} medicine(s)
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
                {latestPrescription.items?.map((m, idx) => (
                  <span key={idx} style={{ background: '#f1f5f9', color: '#334155', padding: '3px 8px', borderRadius: 6, fontSize: '0.78rem', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <Pill size={11} color="#0ea5e9" />
                    <strong>{m.medicine_name}</strong> {m.dosage && `(${m.dosage})`}
                  </span>
                ))}
              </div>
              <button
                className="btn btn-teal btn-sm"
                onClick={() => handleDownloadPdf(latestPrescription.id)}
                disabled={pdfBusyId === latestPrescription.id}
                title="Download Official PDF"
              >
                <Download size={14} />
                <span>{pdfBusyId === latestPrescription.id ? 'Working...' : 'Download PDF'}</span>
              </button>
            </div>
          )}
        </div>

        {/* Health Reminders */}
        <div className="card">
          <div className="card-header">
            <h3>
              <Bell size={18} color="var(--amber-600)" />
              <span>Health Reminders</span>
            </h3>
          </div>

          <div style={{ padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 16 }}>
              <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <ShieldCheck size={20} className="text-amber-600" />
              </div>
              <div className="flex-1">
                <h4 style={{ fontWeight: 600, color: 'var(--slate-900)', marginBottom: 4 }}>Prescription Access Control</h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--slate-600)' }}>
                  You can control which doctors can write prescriptions for you in Access & Privacy.
                  By default, any verified doctor can prescribe. Toggle off to require explicit approval.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <div className="w-10 h-10 rounded-xl bg-teal-100 dark:bg-teal-900/30 flex items-center justify-center">
                <HeartPulse size={20} className="text-teal-600" />
              </div>
              <div className="flex-1">
                <h4 style={{ fontWeight: 600, color: 'var(--slate-900)', marginBottom: 4 }}>Emergency Card</h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--slate-600)', marginBottom: 8 }}>
                  Create a printable emergency card with blood group, allergies, and emergency contacts.
                </p>
                <Link to="/patient/profile" className="btn btn-teal btn-sm">
                  Set up Emergency Card
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}