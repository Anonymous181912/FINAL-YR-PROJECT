import { useEffect, useState } from 'react'
import { requestAccess, outgoingRequests, doctorGrants } from '../services/access'
import { searchPatients } from '../services/patients'
import {
  ShieldCheck,
  Send,
  RefreshCw,
  Search,
  CheckCircle2,
  Clock,
  XCircle,
  KeyRound,
  UserPlus,
} from 'lucide-react'

const SCOPE_OPTIONS = [
  { value: 'reports', label: 'Reports' },
  { value: 'prescriptions', label: 'Prescriptions' },
  { value: 'history', label: 'History' },
]

const statusBadge = (status) => {
  if (status === 'approved') return 'badge-success'
  if (status === 'denied' || status === 'revoked' || status === 'expired') return 'badge-danger'
  return 'badge-warning'
}

export default function DoctorAccess() {
  const [outgoing, setOutgoing] = useState([])
  const [grants, setGrants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')

  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState(null)
  const [scope, setScope] = useState(SCOPE_OPTIONS.map((o) => o.value))
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)

  const refresh = async () => {
    setLoading(true)
    setError('')
    try {
      const [out, gr] = await Promise.all([outgoingRequests(), doctorGrants()])
      setOutgoing(out || [])
      setGrants(gr || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load access requests')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const handleSearch = async () => {
    const q = query.trim()
    if (!q) return
    setSearching(true)
    setError('')
    try {
      const found = await searchPatients(q, 10)
      setResults(found || [])
      if (!found || found.length === 0) setError('No patient matched that name or patient code.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Patient lookup failed')
    } finally {
      setSearching(false)
    }
  }

  const toggleScope = (value) => {
    setScope((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    )
  }

  const handleRequest = async (e) => {
    e.preventDefault()
    const patientId = selected?.patient_id || selected?.id
    if (!patientId) {
      setError('Search and select a patient first.')
      return
    }
    if (scope.length === 0) {
      setError('Choose at least one data scope.')
      return
    }
    setSending(true)
    setError('')
    setMsg('')
    try {
      await requestAccess(patientId, scope, message.trim())
      setMsg('Access request sent. The patient must approve it before you can view their data.')
      setSelected(null)
      setQuery('')
      setResults([])
      setMessage('')
      await refresh()
      setTimeout(() => setMsg(''), 4000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send access request')
    } finally {
      setSending(false)
    }
  }

  const pendingCount = outgoing.filter((r) => r.status === 'pending').length
  const activeGrants = grants.filter((g) => g.status === 'active')

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1000, margin: '0 auto' }}>
      <div className="page-header">
        <div className="page-header-title">
          <span className="badge badge-primary"><ShieldCheck size={12} /> Consent Required</span>
          <h1>Access Requests</h1>
          <p>Request patient consent for reports and history. Writing prescriptions does not require a grant unless the patient has turned it off.</p>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-secondary btn-sm" onClick={refresh} disabled={loading}>
            <RefreshCw size={14} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>{error}</div>}
      {msg && <div className="alert-banner alert-banner-success" style={{ marginBottom: 20 }}>{msg}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
        <div className="card">
          <div className="card-header">
            <h3><UserPlus size={18} color="var(--primary-600)" /><span>Request New Access</span></h3>
          </div>

          <form onSubmit={handleRequest}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: '0.88rem', marginBottom: 8 }}>
              <Search size={14} color="var(--primary-600)" />
              <span>Find patient by name or patient code</span>
            </label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSearch() } }}
                placeholder="e.g. PAT-7X9K2 or Jane Doe"
                className="form-control"
                style={{ flex: 1, minWidth: 200 }}
                aria-label="Search patient by name or patient code"
              />
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleSearch} disabled={searching || !query.trim()}>
                <Search size={14} />
                <span>{searching ? 'Searching...' : 'Search'}</span>
              </button>
            </div>

            {selected && (
              <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#166534', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '8px 12px' }}>
                Selected: <strong>{selected.full_name}</strong>
                {selected.patient_code ? ` (${selected.patient_code})` : ''}
              </div>
            )}

            {results.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 10 }}>
                {results.map((p) => (
                  <button
                    type="button"
                    key={p.id}
                    onClick={() => { setSelected(p); setResults([]); setQuery('') }}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
                      textAlign: 'left', background: 'var(--slate-50)', border: '1px solid var(--slate-200)',
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

            <div style={{ marginTop: 16 }}>
              <label style={{ fontWeight: 600, fontSize: '0.88rem', display: 'block', marginBottom: 8 }}>Data scope</label>
              <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
                {SCOPE_OPTIONS.map((o) => (
                  <label key={o.value} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.86rem', cursor: 'pointer' }}>
                    <input type="checkbox" checked={scope.includes(o.value)} onChange={() => toggleScope(o.value)} />
                    <span>{o.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 16 }}>
              <label style={{ fontWeight: 600, fontSize: '0.88rem', display: 'block', marginBottom: 8 }}>Message to patient (optional)</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={3}
                maxLength={500}
                placeholder="Why do you need access to this patient's data?"
                className="form-control"
              />
            </div>

            <button type="submit" className="btn btn-primary" style={{ marginTop: 16, width: '100%' }} disabled={sending || !selected}>
              <Send size={15} />
              <span>{sending ? 'Sending...' : 'Send Access Request'}</span>
            </button>
          </form>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="card">
            <div className="card-header">
              <h3><Clock size={18} color="var(--amber-600)" /><span>Outgoing Requests ({outgoing.length})</span></h3>
              {pendingCount > 0 && <span className="badge badge-warning">{pendingCount} pending</span>}
            </div>
            {loading ? (
              <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>Loading requests...</p>
            ) : outgoing.length === 0 ? (
              <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>You have not requested access to any patient yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {outgoing.map((r) => (
                  <div key={r.id} style={{ border: '1px solid var(--slate-200)', borderRadius: 10, padding: '10px 14px', background: 'var(--slate-50)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>Patient {String(r.patient_id || '').slice(0, 10)}…</span>
                      <span className={`badge ${statusBadge(r.status)}`} style={{ textTransform: 'capitalize' }}>{r.status}</span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--slate-500)', marginTop: 4 }}>
                      Scope: {(r.scope || []).join(', ') || '—'}
                      {r.created_at ? ` • ${new Date(r.created_at).toLocaleDateString()}` : ''}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <h3><CheckCircle2 size={18} color="var(--teal-600)" /><span>Active Grants ({activeGrants.length})</span></h3>
            </div>
            {loading ? (
              <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>Loading grants...</p>
            ) : grants.length === 0 ? (
              <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>No patients have granted you access yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {grants.map((g) => (
                  <div key={g.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, border: '1px solid var(--slate-200)', borderRadius: 10, padding: '10px 14px', flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>Patient {String(g.patient_id || '').slice(0, 10)}…</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
                        {(g.scope || []).join(', ')} • {g.status}
                        {g.expires_at ? ` • expires ${new Date(g.expires_at).toLocaleDateString()}` : ''}
                      </div>
                    </div>
                    <span className={`badge ${g.status === 'active' ? 'badge-success' : 'badge-neutral'}`} style={{ textTransform: 'capitalize' }}>
                      {g.status === 'active' ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
                      {g.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card" style={{ background: 'var(--slate-50)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <KeyRound size={18} color="var(--primary-600)" style={{ flexShrink: 0, marginTop: 2 }} />
              <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--slate-600)' }}>
                Patients control consent from their Access &amp; Privacy page. Prescribing permission is separate:
                it is on by default, and patients can disable it.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}