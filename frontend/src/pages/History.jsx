import { useState, useEffect } from 'react'
import { useAuth } from '../auth.jsx'
import { getPatientHistory, getDoctorPatientHistory } from '../services/history'
import { listPatients } from '../services/patients'
import { deleteReport } from '../services/reports'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Clock,
  FileText,
  Pill,
  Sparkles,
  AlertTriangle,
  ShieldAlert,
  ChevronRight,
  Calendar,
  RefreshCw,
  UserCheck,
  Stethoscope,
  ArrowUpRight,
  Trash2
} from 'lucide-react'

export default function History() {
  const { user } = useAuth()
  const isDoctor = user?.role === 'doctor'
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [events, setEvents] = useState([])
  const [order, setOrder] = useState('desc')
  const [patients, setPatients] = useState([])
  const [selectedPatientId, setSelectedPatientId] = useState(searchParams.get('patient') || '')
  const [loadingPatients, setLoadingPatients] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [deletingId, setDeletingId] = useState(null)

  const incomingPatientId = searchParams.get('patient') || ''

  useEffect(() => {
    if (incomingPatientId) setSelectedPatientId(incomingPatientId)
  }, [incomingPatientId])

  const handleConfirmDelete = async () => {
    if (!confirmDelete || deletingId) return
    setDeletingId(confirmDelete.source_id)
    setError('')
    try {
      await deleteReport(confirmDelete.source_id)
      setConfirmDelete(null)
      if (isDoctor && selectedPatientId) {
        await fetchHistory(selectedPatientId, order)
      } else if (!isDoctor) {
        await fetchHistory(null, order)
      }
    } catch (err) {
      setError(err.response?.data?.detail || "We couldn't delete this report. Please try again.")
    } finally {
      setDeletingId(null)
    }
  }

  const fetchHistory = async (patientId = null, sortOrder = order) => {
    setLoading(true)
    setError('')
    try {
      const data = isDoctor && patientId
        ? await getDoctorPatientHistory(patientId, sortOrder)
        : await getPatientHistory(sortOrder)
      setEvents(data || [])
    } catch (err) {
      setError(err.response?.data?.detail || "We couldn't load the medical timeline. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isDoctor) {
      setLoadingPatients(true)
      listPatients('', 0, 50)
        .then((data) => setPatients(data || []))
        .catch(() => setError('Failed to load patient directory. Please try again.'))
        .finally(() => setLoadingPatients(false))
    } else {
      fetchHistory()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDoctor])

  useEffect(() => {
    if (isDoctor && selectedPatientId) {
      fetchHistory(selectedPatientId, order)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [order, selectedPatientId])

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Date not recorded'
    const date = new Date(dateStr)
    if (Number.isNaN(date.getTime())) return 'Date not recorded'
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  }

  const groupEventsByDate = () => {
    const groups = {}
    events.forEach((event) => {
      const dateKey = event.event_date ? new Date(event.event_date).toDateString() : 'Unknown Date'
      if (!groups[dateKey]) groups[dateKey] = []
      groups[dateKey].push(event)
    })
    return groups
  }

  const grouped = groupEventsByDate()
  const reportCount = events.filter((e) => e.event_type === 'REPORT').length
  const rxCount = events.filter((e) => e.event_type === 'PRESCRIPTION').length

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div className="page-header-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className={`badge ${isDoctor ? 'badge-info' : 'badge-teal'}`}>
              {isDoctor ? <Stethoscope size={12} /> : <Clock size={12} />}
              {isDoctor ? 'Doctor Workspace' : 'Patient Health Portal'}
            </span>
          </div>
          <h1>Medical Timeline</h1>
          <p>
            {isDoctor
              ? 'Chronological view of a patient\u2019s reports and prescriptions.'
              : 'Your reports and prescriptions in chronological order.'}
          </p>
        </div>
        <div className="page-header-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => (isDoctor && selectedPatientId ? fetchHistory(selectedPatientId, order) : !isDoctor && fetchHistory(null, order))}
            disabled={loading || (isDoctor && !selectedPatientId)}
          >
            <RefreshCw size={14} className={loading ? 'spin' : undefined} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper stat-icon-blue">
            <Clock size={22} />
          </div>
          <div className="stat-info">
            <div className="stat-label">Timeline Events</div>
            <div className="stat-value">{loading ? '...' : events.length}</div>
            <div className="stat-helper">Reports + prescriptions</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon-wrapper stat-icon-teal">
            <FileText size={22} />
          </div>
          <div className="stat-info">
            <div className="stat-label">Reports</div>
            <div className="stat-value">{loading ? '...' : reportCount}</div>
            <div className="stat-helper">Uploaded clinical documents</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon-wrapper stat-icon-purple">
            <Pill size={22} />
          </div>
          <div className="stat-info">
            <div className="stat-label">Prescriptions</div>
            <div className="stat-value">{loading ? '...' : rxCount}</div>
            <div className="stat-helper">Issued digital Rx orders</div>
          </div>
        </div>
      </div>

      {isDoctor && (
        <div className="card">
          <div className="card-header">
            <h3>
              <UserCheck size={18} color="var(--primary-600)" />
              <span>Select Patient</span>
            </h3>
            {loadingPatients && <span className="badge badge-info">Loading directory...</span>}
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              className="form-control"
              style={{ maxWidth: 360 }}
              disabled={loadingPatients}
            >
              <option value="">-- Choose a patient --</option>
              {patients.map((p) => (
                <option key={p.id} value={p.patient_id || p.id}>
                  {p.full_name} {p.patient_id ? `(${String(p.patient_id).slice(0, 10)})` : ''}
                </option>
              ))}
            </select>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <label style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--slate-600)' }}>Sort:</label>
              <select value={order} onChange={(e) => setOrder(e.target.value)} className="form-control" style={{ width: 'auto' }}>
                <option value="desc">Newest first</option>
                <option value="asc">Oldest first</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {!isDoctor && (
        <div className="card" style={{ padding: '14px 18px', marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <Calendar size={16} color="var(--slate-500)" />
            <label style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--slate-600)' }}>Sort order:</label>
            <select value={order} onChange={(e) => { setOrder(e.target.value); fetchHistory(null, e.target.value) }} className="form-control" style={{ width: 'auto' }}>
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>
          </div>
        </div>
      )}

      {error && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      <div className="safety-note-banner">
        <ShieldAlert size={18} style={{ flexShrink: 0, marginTop: 1 }} />
        <div>
          <div style={{ fontWeight: 700, marginBottom: 2 }}>Assistive summaries only</div>
          <div>Timeline entries explain supplied records and are not diagnoses. Consult a licensed clinician for medical decisions.</div>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 20px' }}>
          <div className="loading-spinner" style={{ margin: '0 auto 14px' }} />
          <p style={{ fontWeight: 600, color: 'var(--slate-700)' }}>Loading your medical timeline...</p>
          <p style={{ fontSize: '0.85rem', color: 'var(--slate-500)' }}>Fetching reports and prescriptions</p>
        </div>
      )}

      {!loading && isDoctor && !selectedPatientId && (
        <div className="card">
          <div className="empty-state">
            <UserCheck size={36} />
            <h4 style={{ margin: '8px 0 4px', color: 'var(--slate-900)' }}>Select a patient to view history</h4>
            <p style={{ margin: 0, fontSize: '0.88rem' }}>Choose a patient from the directory above to load their timeline.</p>
          </div>
        </div>
      )}

      {!loading && (selectedPatientId || !isDoctor) && events.length === 0 && !error && (
        <div className="card">
          <div className="empty-state">
            <Clock size={36} />
            <h4 style={{ margin: '8px 0 4px', color: 'var(--slate-900)' }}>No medical records available yet</h4>
            <p style={{ margin: 0, fontSize: '0.88rem' }}>Uploaded reports and digital prescriptions will appear here.</p>
            {!isDoctor && (
              <Link to="/patient/reports" className="btn btn-primary btn-sm" style={{ marginTop: 14 }}>
                <span>Upload your first report</span>
                <ChevronRight size={14} />
              </Link>
            )}
          </div>
        </div>
      )}

      {!loading && events.length > 0 && (
        <div className="timeline-container">
          {Object.entries(grouped).map(([dateKey, dayEvents]) => (
            <div key={dateKey} className="timeline-node">
              <div className="timeline-bullet">
                <Calendar size={12} color="var(--primary-600)" />
              </div>
              <div className="timeline-date-label">{formatDate(dayEvents[0]?.event_date)}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {dayEvents.map((event) => {
                  const isReport = event.event_type === 'REPORT'
                  return (
                    <div key={event.event_id} className="card card-hover" style={{ marginBottom: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap' }}>
                        <div style={{ flex: 1, minWidth: 240 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                            <span className={`badge ${isReport ? 'badge-info' : 'badge-teal'}`}>
                              {isReport ? <FileText size={11} /> : <Pill size={11} />}
                              {isReport ? 'Report' : 'Prescription'}
                            </span>
                            {event.source_reference && (
                              <span className="badge badge-success">
                                <Sparkles size={11} /> AI Ready
                              </span>
                            )}
                          </div>
                          <h3 style={{ margin: '0 0 4px', fontSize: '1.02rem' }}>{event.title}</h3>
                          {event.summary && (
                            <p style={{ margin: 0, color: 'var(--slate-600)', fontSize: '0.9rem', lineHeight: 1.5 }}>{event.summary}</p>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                          {isReport ? (
                            <Link to={`${isDoctor ? '/doctor' : '/patient'}/reports/${event.source_id}`} className="btn btn-secondary btn-sm">
                              <span>View Report</span>
                              <ArrowUpRight size={14} />
                            </Link>
                          ) : (
                            <Link to={isDoctor ? '/doctor/prescriptions' : '/patient/prescriptions'} className="btn btn-secondary btn-sm">
                              <span>View Prescription</span>
                              <ArrowUpRight size={14} />
                            </Link>
                          )}
                          {isReport && !isDoctor && (
                            <button
                              className="btn btn-secondary btn-sm"
                              style={{ color: 'var(--danger-text)', borderColor: 'var(--danger-border)' }}
                              onClick={() => setConfirmDelete(event)}
                              disabled={deletingId === event.source_id}
                              title="Delete this report"
                            >
                              <Trash2 size={14} />
                              <span>{deletingId === event.source_id ? 'Deleting...' : 'Delete'}</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Delete this report?"
          message="This will permanently remove the report and its stored analysis. This action cannot be undone."
          confirmLabel="Delete"
          cancelLabel="Cancel"
          loading={deletingId === confirmDelete.source_id}
          onConfirm={handleConfirmDelete}
          onCancel={() => { if (!deletingId) setConfirmDelete(null) }}
        />
      )}
    </div>
  )
}
