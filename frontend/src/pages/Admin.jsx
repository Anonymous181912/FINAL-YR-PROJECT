import { useState, useEffect } from 'react'
import api from '../services/api'
import { adminAuditSearch } from '../services/access'
import { ShieldCheck, CheckCircle2, XCircle, RefreshCw, Eye, Search } from 'lucide-react'

export default function Admin() {
  const [pending, setPending] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const fetchPending = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/admin/pending-doctors')
      setPending(res.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load pending doctors')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPending() }, [])

  const [audit, setAudit] = useState([])
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditError, setAuditError] = useState('')
  const [filterAction, setFilterAction] = useState('')
  const [filterPatient, setFilterPatient] = useState('')
  const [filterActor, setFilterActor] = useState('')

  const fetchAudit = async () => {
    setAuditLoading(true)
    setAuditError('')
    try {
      const filters = {}
      if (filterAction) filters.action = filterAction
      if (filterPatient) filters.patient_id = filterPatient
      if (filterActor) filters.actor_id = filterActor
      setAudit((await adminAuditSearch(filters)) || [])
    } catch (err) {
      setAuditError(err.response?.data?.detail || 'Failed to load audit log')
    } finally {
      setAuditLoading(false)
    }
  }

  useEffect(() => { fetchAudit() }, [])

  const handleDecision = async (id, action) => {
    setBusyId(id + action)
    setError('')
    try {
      await api.post(`/admin/doctors/${id}/${action}`)
      await fetchPending()
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to ${action} doctor`)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 900, margin: '0 auto' }}>
      <div className="page-header">
        <div className="page-header-title">
          <span className="badge badge-info"><ShieldCheck size={12} /> Admin Console</span>
          <h1>Doctor Verification</h1>
          <p>Approve or reject doctor registrations before they can access patient data.</p>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-secondary btn-sm" onClick={fetchPending} disabled={loading}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>{error}</div>}

      <div className="card">
        {loading ? (
          <div style={{ textAlign: 'center', padding: 32 }}>
            <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--slate-500)' }}>Loading pending doctors...</p>
          </div>
        ) : pending.length === 0 ? (
          <div className="empty-state">
            <CheckCircle2 size={36} />
            <h4>No pending verifications</h4>
            <p>All doctor accounts have been reviewed.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {pending.map((d) => (
              <div key={d.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '12px 14px', border: '1px solid var(--slate-200)', borderRadius: 'var(--radius-md)', background: 'var(--slate-50)', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontWeight: 700 }}>{d.full_name}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--slate-500)' }}>
                    License: {d.license_number || 'not provided'} &bull; {d.specialization || 'no specialization'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-teal btn-sm" disabled={!!busyId} onClick={() => handleDecision(d.id, 'approve')}>
                    <CheckCircle2 size={14} /> Approve
                  </button>
                  <button className="btn btn-secondary btn-sm" disabled={!!busyId} onClick={() => handleDecision(d.id, 'reject')}>
                    <XCircle size={14} /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <h3>
            <Eye size={18} color="var(--primary-600)" />
            <span>Audit Log</span>
          </h3>
          <button className="btn btn-secondary btn-sm" onClick={fetchAudit} disabled={auditLoading}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
        <form
          onSubmit={(e) => { e.preventDefault(); fetchAudit() }}
          style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}
        >
          <input
            type="text" value={filterAction} onChange={(e) => setFilterAction(e.target.value)}
            placeholder="Filter: action (e.g. read)" className="form-control" style={{ maxWidth: 200 }}
            aria-label="Filter by action"
          />
          <input
            type="text" value={filterPatient} onChange={(e) => setFilterPatient(e.target.value)}
            placeholder="Filter: patient ID" className="form-control" style={{ maxWidth: 200 }}
            aria-label="Filter by patient"
          />
          <input
            type="text" value={filterActor} onChange={(e) => setFilterActor(e.target.value)}
            placeholder="Filter: actor ID" className="form-control" style={{ maxWidth: 200 }}
            aria-label="Filter by actor"
          />
          <button type="submit" className="btn btn-secondary btn-sm" disabled={auditLoading}>
            <Search size={14} /> Apply
          </button>
        </form>
        {auditError && <div className="alert-banner alert-banner-danger" style={{ marginBottom: 12 }}>{auditError}</div>}
        {auditLoading ? (
          <p style={{ color: 'var(--slate-500)' }}>Loading audit log...</p>
        ) : audit.length === 0 ? (
          <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>No audit entries yet.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }} aria-label="Admin audit log">
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--slate-500)', borderBottom: '1px solid var(--slate-200)' }}>
                  <th style={{ padding: '6px 8px' }}>Time</th>
                  <th style={{ padding: '6px 8px' }}>Actor</th>
                  <th style={{ padding: '6px 8px' }}>Action</th>
                  <th style={{ padding: '6px 8px' }}>Resource</th>
                  <th style={{ padding: '6px 8px' }}>Patient</th>
                </tr>
              </thead>
              <tbody>
                {audit.slice(0, 100).map((e) => (
                  <tr key={e.id} style={{ borderBottom: '1px solid var(--slate-100)' }}>
                    <td style={{ padding: '6px 8px' }}>{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</td>
                    <td style={{ padding: '6px 8px' }}>{e.actor_role} ({String(e.actor_id || '').slice(0, 8)}…)</td>
                    <td style={{ padding: '6px 8px' }}>{e.action}</td>
                    <td style={{ padding: '6px 8px' }}>{e.resource_type}{e.resource_id ? ` #${String(e.resource_id).slice(-6)}` : ''}</td>
                    <td style={{ padding: '6px 8px' }}>{e.patient_id ? `${String(e.patient_id).slice(0, 8)}…` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
