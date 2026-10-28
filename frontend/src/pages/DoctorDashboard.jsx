import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { listDoctorPrescriptions, generatePrescriptionPdf, downloadPrescriptionPdf } from '../services/prescriptions.js'
import { listPatients } from '../services/patients.js'
import { outgoingRequests } from '../services/access.js'
import {
  FileText,
  Pill,
  Users,
  Clock,
  Sparkles,
  ChevronRight,
  Activity,
  Stethoscope,
  ArrowUpRight,
  Download,
  Calendar,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react'

export default function DoctorDashboard() {
  const { user } = useAuth()

  const [loading, setLoading] = useState(true)
  const [reports, setReports] = useState([])
  const [prescriptions, setPrescriptions] = useState([])
  const [patients, setPatients] = useState([])
  const [pendingRequests, setPendingRequests] = useState([])
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
        const [patientsData, rxData, requestData] = await Promise.allSettled([
          listPatients('', 0, COUNT_LIMIT),
          listDoctorPrescriptions(0, COUNT_LIMIT),
          outgoingRequests()
        ])
        if (patientsData.status === 'fulfilled') setPatients(patientsData.value || [])
        if (rxData.status === 'fulfilled') setPrescriptions(rxData.value || [])
        if (requestData.status === 'fulfilled') {
          setPendingRequests((requestData.value || []).filter((r) => r.status === 'pending'))
        }
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

  // Calculate prescriptions issued today
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const prescriptionsToday = prescriptions.filter(rx => {
    const rxDate = new Date(rx.prescription_date || rx.created_at)
    return rxDate >= today && rx.status === 'issued'
  }).length

  // Calculate follow-ups due in next 7 days
  const nextWeek = new Date()
  nextWeek.setDate(nextWeek.getDate() + 7)
  const followUpsDue = prescriptions.filter(rx => {
    if (!rx.follow_up_date) return false
    const followUp = new Date(rx.follow_up_date)
    return followUp >= today && followUp <= nextWeek
  }).length

  return (
    <div>
      {/* Welcome Page Header */}
      <div className="page-header">
        <div className="page-header-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className="badge badge-primary">
              <Stethoscope size={12} />
              Doctor Workspace
            </span>
          </div>
          <h1>Welcome, {user?.full_name || user?.email}</h1>
          <p>Review patient medical histories, analyze clinical reports, and create digital prescriptions.</p>
        </div>

        <div className="page-header-actions">
          <Link to="/doctor/prescriptions?new=1" className="btn btn-primary">
            <Pill size={16} />
            <span>New Prescription</span>
          </Link>
        </div>
      </div>

      {pdfError && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div>{pdfError}</div>
        </div>
      )}

      {/* Top Statistics Cards Grid */}
      <div className="stats-grid">
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
            <div className="stat-label">Prescriptions Today</div>
            <div className="stat-value">{loading ? '...' : prescriptionsToday}</div>
            <div className="stat-helper">Issued today</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper stat-icon-purple">
            <FileText size={24} />
          </div>
          <div className="stat-info">
            <div className="stat-label">Follow-ups Due (7 days)</div>
            <div className="stat-value">{loading ? '...' : followUpsDue}</div>
            <div className="stat-helper">Patients needing follow-up</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper stat-icon-blue">
            <ShieldCheck size={24} />
          </div>
          <div className="stat-info">
            <div className="stat-label">Pending Access Requests</div>
            <div className="stat-value">{loading ? '...' : pendingRequests.length}</div>
            <div className="stat-helper">Awaiting patient approval</div>
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
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 24 }}>
        {/* Left Column: Recent Patients */}
        <div className="card">
          <div className="card-header">
            <h3>
              <Users size={18} color="var(--primary-600)" />
              <span>Recent Patients</span>
            </h3>
            <Link to="/doctor/patients" className="btn btn-ghost btn-sm">
              <span>View All</span>
              <ChevronRight size={14} />
            </Link>
          </div>

          {loading && <p style={{ color: 'var(--slate-500)', padding: 12 }}>Loading patients...</p>}

          {!loading && patients.length === 0 && (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--slate-500)' }}>
              <Users size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>No patients registered yet</p>
              <p style={{ fontSize: '0.85rem' }}>Patient records will appear here once registered</p>
            </div>
          )}

          {!loading && patients.length > 0 && (
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
                      {p.patient_code && <span className="badge badge-primary">{p.patient_code}</span>}
                      {p.blood_group && <span className="badge badge-danger">{p.blood_group}</span>}
                      {p.gender && <span className="badge badge-info" style={{ textTransform: 'capitalize' }}>{p.gender}</span>}
                    </div>
                  </div>

                  <Link to="/doctor/patients" className="btn btn-secondary btn-sm">
                    <span>View Dossier</span>
                    <ArrowUpRight size={14} />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Recent Prescriptions & Quick Actions */}
        <div className="card">
          <div className="card-header">
            <h3>
              <Pill size={18} color="var(--teal-600)" />
              <span>Recent Prescriptions</span>
            </h3>
            <Link to="/doctor/prescriptions" className="btn btn-ghost btn-sm">
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
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--slate-500)' }}>
              <Pill size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>No prescriptions found</p>
              <p style={{ fontSize: '0.85rem' }}>Create your first digital prescription for a patient</p>
              <Link to="/doctor/prescriptions?new=1" className="btn btn-primary btn-sm" style={{ marginTop: 14 }}>
                <Pill size={14} /> Create Prescription
              </Link>
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
                      {rx.prescription_date ? new Date(rx.prescription_date).toLocaleDateString() : 'Recent'} &bull; {rx.items?.length || 0} medicine(s) &bull; {rx.status}
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

          {/* Quick Actions */}
          <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--slate-200)' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--slate-700)', marginBottom: 12 }}>Quick Actions</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
              <Link to="/doctor/prescriptions?new=1" className="btn btn-primary btn-sm" style={{ justifyContent: 'center' }}>
                <Pill size={14} /> New Prescription
              </Link>
              <Link to="/doctor/patients" className="btn btn-secondary btn-sm" style={{ justifyContent: 'center' }}>
                <Users size={14} /> View Patients
              </Link>
              <Link to="/doctor/reports" className="btn btn-secondary btn-sm" style={{ justifyContent: 'center' }}>
                <FileText size={14} /> Review Reports
              </Link>
              <Link to="/doctor/access" className="btn btn-ghost btn-sm" style={{ justifyContent: 'center' }}>
                <ShieldCheck size={14} /> Access Requests
              </Link>
              <Link to="/doctor/profile" className="btn btn-ghost btn-sm" style={{ justifyContent: 'center' }}>
                <Stethoscope size={14} /> My Profile
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}