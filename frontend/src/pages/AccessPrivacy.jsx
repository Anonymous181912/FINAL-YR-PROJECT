import { useState, useEffect } from 'react'
import { incomingRequests, approveRequest, denyRequest, myGrants, revokeGrant, myAuditTrail } from '../services/access'
import { getMyPatientProfile, updateMyPatientProfile } from '../services/patients'
import { ShieldCheck, CheckCircle2, XCircle, Clock, Eye, Pill, AlertTriangle } from 'lucide-react'

export default function AccessPrivacy() {
  const [pending, setPending] = useState([])
  const [grants, setGrants] = useState([])
  const [audit, setAudit] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [expiry, setExpiry] = useState({})
  const [allowPrescriptions, setAllowPrescriptions] = useState(true)
  const [savingPermission, setSavingPermission] = useState(false)

  const refresh = async () => {
    setLoading(true)
    setError('')
    try {
      const [p, g, a, profile] = await Promise.all([
        incomingRequests('pending'),
        myGrants(),
        myAuditTrail(50),
        getMyPatientProfile(),
      ])
      setPending(p || [])
      setGrants(g || [])
      setAudit(a || [])
      if (profile) setAllowPrescriptions(profile.allow_prescriptions !== false)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load access data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  const handlePermissionChange = async (nextValue) => {
    setSavingPermission(true)
    setError('')
    setMsg('')
    try {
      const updated = await updateMyPatientProfile({ allow_prescriptions: nextValue })
      setAllowPrescriptions(updated?.allow_prescriptions !== false)
      setMsg(nextValue ? 'Prescription writing enabled.' : 'Prescription writing disabled. Doctors cannot create prescriptions for you.')
      setTimeout(() => setMsg(''), 4000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update prescription permission')
    } finally {
      setSavingPermission(false)
    }
  }

  const handleApprove = async (id) => {
    const days = Math.min(365, Math.max(1, parseInt(expiry[id] || '30', 10) || 30))
    try {
      await approveRequest(id, days)
      setMsg('Access approved')
      await refresh()
      setTimeout(() => setMsg(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Approval failed')
    }
  }

  const handleDeny = async (id) => {
    try {
      await denyRequest(id)
      setMsg('Request denied')
      await refresh()
      setTimeout(() => setMsg(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Deny failed')
    }
  }

  const handleRevoke = async (id) => {
    if (!window.confirm('Revoke this doctor\'s access? They will immediately lose access to your data.')) return
    try {
      await revokeGrant(id)
      setMsg('Access revoked')
      await refresh()
      setTimeout(() => setMsg(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Revoke failed')
    }
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 960, margin: '0 auto' }}>
      <div className="page-header">
        <div className="page-header-title">
          <span className="badge badge-teal"><ShieldCheck size={12} /> Privacy First</span>
          <h1>Access &amp; Privacy</h1>
          <p>Doctors can only see your data after you approve them here. Revoke anytime.</p>
        </div>
      </div>

      {error && <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>{error}</div>}
      {msg && <div className="alert-banner alert-banner-success" style={{ marginBottom: 20 }}>{msg}</div>}

      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: 32 }}>
          <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
          <p style={{ color: 'var(--slate-500)' }}>Loading access data...</p>
        </div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <h3><Pill size={18} color="var(--teal-600)" /><span>Prescription Writing Permission</span></h3>
              <span className={`badge ${allowPrescriptions ? 'badge-success' : 'badge-danger'}`}>
                {allowPrescriptions ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <p style={{ margin: '0 0 10px', fontSize: '0.88rem', color: 'var(--slate-600)' }}>
                  When enabled, any verified doctor can write a prescription for you without requesting
                  additional access. Disable this if you want to control who prescribes.
                </p>
                <button
                  type="button"
                  className={`btn ${allowPrescriptions ? 'btn-secondary' : 'btn-teal'} btn-sm`}
                  disabled={savingPermission}
                  onClick={() => handlePermissionChange(!allowPrescriptions)}
                >
                  {savingPermission
                    ? 'Saving...'
                    : allowPrescriptions
                      ? 'Disable prescription writing'
                      : 'Enable prescription writing'}
                </button>
              </div>
              <AlertTriangle size={18} color={allowPrescriptions ? 'var(--slate-400)' : 'var(--danger-fg)'} style={{ flexShrink: 0 }} />
            </div>
          </div>

          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <h3><Clock size={18} color="var(--primary-600)" /><span>Pending Requests ({pending.length})</span></h3>
            </div>
            {pending.length === 0 ? (
              <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>No pending doctor requests.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {pending.map((r) => (
                  <div key={r.id} style={{ border: '1px solid var(--slate-200)', borderRadius: 10, padding: '12px 14px', background: 'var(--slate-50)' }}>
                    <div style={{ fontWeight: 700 }}>Doctor ID: {r.doctor_id.slice(0, 10)}…</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--slate-500)' }}>
                      Scope: {(r.scope || []).join(', ')}{r.message ? ` • "${r.message}"` : ''}
                    </div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                      <label style={{ fontSize: '0.8rem', color: 'var(--slate-600)' }}>
                        Approve for{' '}
                        <input
                          type="number"
                          min={1}
                          max={365}
                          value={expiry[r.id] || 30}
                          onChange={(e) => setExpiry({ ...expiry, [r.id]: e.target.value })}
                          style={{ width: 70, padding: '4px 8px', borderRadius: 6, border: '1px solid var(--slate-200)' }}
                          aria-label="Approval duration in days"
                        />{' '}
                        days
                      </label>
                      <button className="btn btn-teal btn-sm" onClick={() => handleApprove(r.id)}>
                        <CheckCircle2 size={14} /> Approve
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleDeny(r.id)}>
                        <XCircle size={14} /> Deny
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <h3><ShieldCheck size={18} color="var(--teal-600)" /><span>Doctors With Access ({grants.filter((g) => g.status === 'active').length})</span></h3>
            </div>
            {grants.length === 0 ? (
              <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>Nobody has access to your data right now.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {grants.map((g) => (
                  <div key={g.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, border: '1px solid var(--slate-200)', borderRadius: 10, padding: '10px 14px', flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Doctor ID: {g.doctor_id.slice(0, 10)}…</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
                        {(g.scope || []).join(', ')} • {g.status}
                        {g.expires_at ? ` • expires ${new Date(g.expires_at).toLocaleDateString()}` : ''}
                      </div>
                    </div>
                    {g.status === 'active' && (
                      <button className="btn btn-secondary btn-sm" style={{ color: '#b91c1c', borderColor: '#fecaca' }} onClick={() => handleRevoke(g.id)}>
                        Revoke
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <h3><Eye size={18} color="var(--primary-600)" /><span>Who Accessed Your Data ({audit.length})</span></h3>
            </div>
            {audit.length === 0 ? (
              <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>No recorded access yet.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }} aria-label="Access audit trail">
                  <thead>
                    <tr style={{ textAlign: 'left', color: 'var(--slate-500)', borderBottom: '1px solid var(--slate-200)' }}>
                      <th style={{ padding: '6px 8px' }}>When</th>
                      <th style={{ padding: '6px 8px' }}>Who</th>
                      <th style={{ padding: '6px 8px' }}>Action</th>
                      <th style={{ padding: '6px 8px' }}>What</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit.map((e) => (
                      <tr key={e.id} style={{ borderBottom: '1px solid var(--slate-100)' }}>
                        <td style={{ padding: '6px 8px' }}>{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</td>
                        <td style={{ padding: '6px 8px' }}>{e.actor_role} ({String(e.actor_id || '').slice(0, 8)}…)</td>
                        <td style={{ padding: '6px 8px' }}>{e.action}</td>
                        <td style={{ padding: '6px 8px' }}>{e.resource_type}{e.resource_id ? ` #${String(e.resource_id).slice(-6)}` : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
