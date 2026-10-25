import { useState, useEffect } from 'react'
import { useAuth } from '../auth.jsx'
import { listPatients, getPatient } from '../services/patients'
import { requestAccess, outgoingRequests } from '../services/access'
import { Link } from 'react-router-dom'
import {
  Users,
  Search,
  User,
  Phone,
  Mail,
  Calendar,
  HeartPulse,
  MapPin,
  Droplet,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  FileText,
  Pill,
  Sparkles,
  ChevronRight,
  X,
  UserCheck,
  KeyRound,
  CheckCircle2
} from 'lucide-react'

export default function Patients() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [patients, setPatients] = useState([])
  const [search, setSearch] = useState('')
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [copiedId, setCopiedId] = useState(false)
  const [requestId, setRequestId] = useState('')
  const [requestMsg, setRequestMsg] = useState('')
  const [outgoing, setOutgoing] = useState([])

  const handleCopyId = (id) => {
    if (!id) return
    navigator.clipboard.writeText(id).catch(() => {})
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 1500)
  }

  const fetchPatients = async (query = search) => {
    setLoading(true)
    setError('')
    try {
      const data = await listPatients(query, 0, 50)
      setPatients(data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load patient records')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPatients()
    outgoingRequests().then(setOutgoing).catch(() => {})
  }, [])

  const handleRequestAccess = async (e) => {
    e.preventDefault()
    setError('')
    setNotice('')
    if (!requestId.trim()) {
      setError('Enter a patient ID to request access')
      return
    }
    try {
      await requestAccess(requestId.trim(), ['reports', 'prescriptions', 'history'], requestMsg)
      setNotice('Access request sent. The patient must approve it before you can see their data.')
      setRequestId('')
      setRequestMsg('')
      setOutgoing(await outgoingRequests())
      setTimeout(() => setNotice(''), 4000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send access request')
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    fetchPatients(search)
  }

  const handleViewPatient = async (patientId) => {
    setLoadingDetail(true)
    setError('')
    try {
      const data = await getPatient(patientId)
      setSelectedPatient(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load patient profile')
    } finally {
      setLoadingDetail(false)
    }
  }

  // Calculate initials
  const getInitials = (name) => {
    if (!name) return 'PT'
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    return name.slice(0, 2).toUpperCase()
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* Page Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', fontSize: '0.75rem', fontWeight: 600, marginBottom: 8 }}>
            <UserCheck size={12} />
            <span>Clinical Patient Directory</span>
          </div>
          <h1>Patient Management</h1>
          <p>Search, review medical dossiers, and access longitudinal patient records.</p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div className="badge badge-neutral" style={{ padding: '8px 14px', fontSize: '0.85rem' }}>
            <Users size={14} style={{ marginRight: 6 }} />
            Total: <strong>{patients.length}</strong> Patients
          </div>
        </div>
      </div>

      {/* Request-access card: doctors only see granted patients below */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h3>
            <KeyRound size={18} color="var(--primary-600)" />
            <span>Request Patient Access</span>
          </h3>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--slate-500)', marginBottom: 12 }}>
          This directory lists only patients who approved you. To access a new patient,
          send a request with their patient ID — they approve it in Access &amp; Privacy.
        </p>
        <form onSubmit={handleRequestAccess} style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            type="text"
            value={requestId}
            onChange={(e) => setRequestId(e.target.value)}
            placeholder="Patient ID"
            className="form-control"
            style={{ maxWidth: 260 }}
            aria-label="Patient ID for access request"
          />
          <input
            type="text"
            value={requestMsg}
            onChange={(e) => setRequestMsg(e.target.value)}
            placeholder="Message for the patient (optional)"
            className="form-control"
            style={{ flex: 1, minWidth: 220 }}
            aria-label="Message for the patient"
          />
          <button type="submit" className="btn btn-primary btn-sm">
            <KeyRound size={14} /> Send request
          </button>
        </form>
        {notice && (
          <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#166534', display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle2 size={14} /> {notice}
          </div>
        )}
        {outgoing.length > 0 && (
          <div style={{ marginTop: 12, fontSize: '0.82rem', color: 'var(--slate-600)' }}>
            <strong>Your requests:</strong>{' '}
            {outgoing.slice(0, 8).map((r) => `${r.patient_id.slice(0, 8)}…(${r.status})`).join(' • ')}
            {outgoing.length > 8 ? ` • +${outgoing.length - 8} more` : ''}
          </div>
        )}
      </div>

      {error && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>
          <ShieldAlert size={18} style={{ flexShrink: 0 }} />
          <div>
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Search Bar Bar Card */}
      <div className="card" style={{ marginBottom: 24, padding: '16px 20px' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={18}
              style={{
                position: 'absolute',
                left: 14,
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#94a3b8',
              }}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search patients by full name, ID, or phone..."
              className="form-control"
              style={{ paddingLeft: 42, fontSize: '0.95rem' }}
            />
            {search && (
              <button
                type="button"
                onClick={() => { setSearch(''); fetchPatients('') }}
                style={{
                  position: 'absolute',
                  right: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#94a3b8',
                }}
              >
                <X size={16} />
              </button>
            )}
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ minWidth: 110 }}>
            {loading ? 'Searching...' : 'Search'}
          </button>
          {search && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => { setSearch(''); fetchPatients('') }}
            >
              Reset
            </button>
          )}
        </form>
      </div>

      {/* Main Layout: Patients List + Selected Dossier */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedPatient ? '1.1fr 1fr' : '1fr', gap: 24 }}>
        
        {/* Patient Grid / List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {loading && (
            <div className="card" style={{ textAlign: 'center', padding: '40px 20px' }}>
              <div className="loading-spinner" style={{ margin: '0 auto 16px' }} />
              <p style={{ color: '#64748b', fontSize: '0.9rem' }}>Fetching patient records...</p>
            </div>
          )}

          {!loading && patients.length === 0 && (
            <div className="empty-state">
              <Users size={36} />
              <h4 style={{ margin: '8px 0 4px', color: '#0f172a' }}>No patients found</h4>
              <p style={{ margin: 0, fontSize: '0.85rem' }}>
                {search ? `No matching records found for "${search}". Try another keyword.` : 'Patient records will appear once registered in the system.'}
              </p>
            </div>
          )}

          {!loading && patients.map((patient) => {
            const pId = patient.patient_id || patient.id
            const isSelected = selectedPatient && (selectedPatient.patient_id === pId || selectedPatient.id === pId)
            const initials = getInitials(patient.full_name)

            return (
              <div
                key={patient.id}
                className="card card-hover"
                style={{
                  padding: '18px 20px',
                  marginBottom: 0,
                  border: isSelected ? '2px solid #0ea5e9' : '1px solid var(--border-color)',
                  background: isSelected ? '#f8fafc' : 'white',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer',
                }}
                onClick={() => handleViewPatient(pId)}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div
                      style={{
                        width: 46,
                        height: 46,
                        borderRadius: 12,
                        background: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
                        color: 'white',
                        fontWeight: 700,
                        fontSize: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 2px 8px rgba(14,165,233,0.25)',
                        flexShrink: 0,
                      }}
                    >
                      {initials}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
                          {patient.full_name}
                        </h4>
                        <span className="badge badge-neutral" style={{ fontFamily: 'monospace', fontSize: '0.72rem' }} title={pId}>
                          ID: {pId.slice(0, 10)}
                        </span>
                        {patient.gender && (
                          <span className="badge badge-info" style={{ textTransform: 'capitalize' }}>
                            {patient.gender}
                          </span>
                        )}
                        {patient.blood_group && (
                          <span className="badge" style={{ background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca' }}>
                            🩸 {patient.blood_group}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 6, flexWrap: 'wrap', fontSize: '0.82rem', color: '#64748b' }}>
                        {patient.contact_phone && (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <Phone size={13} color="#94a3b8" />
                            {patient.contact_phone}
                          </span>
                        )}
                        {patient.contact_email && (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <Mail size={13} color="#94a3b8" />
                            {patient.contact_email}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleViewPatient(pId)
                      }}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                    >
                      <span>Dossier</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Selected Patient Detailed Dossier Card */}
        {selectedPatient && (
          <div style={{ position: 'sticky', top: 20, alignSelf: 'start' }}>
            <div className="card" style={{ padding: 24, border: '1px solid #cbd5e1', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.08)' }}>
              
              {/* Card Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #f1f5f9', paddingBottom: 16, marginBottom: 18 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: 14,
                      background: 'linear-gradient(135deg, #0d9488, #0ea5e9)',
                      color: 'white',
                      fontWeight: 700,
                      fontSize: '1.15rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 4px 12px rgba(13,148,136,0.25)',
                    }}
                  >
                    {getInitials(selectedPatient.full_name)}
                  </div>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#0f172a' }}>
                      {selectedPatient.full_name}
                    </h3>
                    <span style={{ fontSize: '0.8rem', color: '#64748b', fontFamily: 'monospace' }}>
                      Ref: {selectedPatient.patient_id || selectedPatient.id}
                    </span>
                    <div style={{ marginTop: 4 }}>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleCopyId(selectedPatient.patient_id || selectedPatient.user_id || selectedPatient.id)}
                        title="Copy full patient ID for prescriptions"
                      >
                        <span>{copiedId ? 'Copied!' : 'Copy patient ID'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => setSelectedPatient(null)}
                  style={{
                    background: '#f1f5f9',
                    border: 'none',
                    borderRadius: 8,
                    width: 32,
                    height: 32,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: '#64748b',
                  }}
                  title="Close dossier"
                >
                  <X size={16} />
                </button>
              </div>

              {loadingDetail ? (
                <div style={{ textAlign: 'center', padding: 24 }}>
                  <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
                  <p style={{ color: '#64748b', fontSize: '0.85rem' }}>Loading clinical details...</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                  
                  {/* Demographics Grid */}
                  <div>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8' }}>
                      Demographics & Clinical Profile
                    </span>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 8 }}>
                      <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                        <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Gender</span>
                        <strong style={{ fontSize: '0.9rem', color: '#0f172a', textTransform: 'capitalize' }}>
                          {selectedPatient.gender || 'Not recorded'}
                        </strong>
                      </div>
                      <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                        <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Blood Group</span>
                        <strong style={{ fontSize: '0.9rem', color: selectedPatient.blood_group ? '#b91c1c' : '#0f172a' }}>
                          {selectedPatient.blood_group ? `🩸 ${selectedPatient.blood_group}` : 'Not recorded'}
                        </strong>
                      </div>
                      <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                        <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Date of Birth</span>
                        <strong style={{ fontSize: '0.85rem', color: '#0f172a' }}>
                          {selectedPatient.date_of_birth ? new Date(selectedPatient.date_of_birth).toLocaleDateString() : 'Not recorded'}
                        </strong>
                      </div>
                      <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                        <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Contact Phone</span>
                        <strong style={{ fontSize: '0.85rem', color: '#0f172a' }}>
                          {selectedPatient.contact_phone || 'Not recorded'}
                        </strong>
                      </div>
                    </div>
                  </div>

                  {/* Contact & Address */}
                  <div>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8' }}>
                      Contact & Address
                    </span>
                    <div style={{ marginTop: 8, background: '#f8fafc', padding: '12px 14px', borderRadius: 8, border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: '#334155' }}>
                        <Mail size={14} color="#0ea5e9" />
                        <span>{selectedPatient.contact_email || 'No email provided'}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: '0.85rem', color: '#334155' }}>
                        <MapPin size={14} color="#0ea5e9" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span>{selectedPatient.address || 'No residential address recorded'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Allergies & Alerts */}
                  <div>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8' }}>
                      Allergies & Contraindications
                    </span>
                    <div style={{ marginTop: 8 }}>
                      {selectedPatient.allergies && selectedPatient.allergies.length > 0 ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {selectedPatient.allergies.map((allergy, idx) => (
                            <span
                              key={idx}
                              className="badge"
                              style={{
                                background: '#fef2f2',
                                color: '#b91c1c',
                                border: '1px solid #fecaca',
                                padding: '5px 10px',
                                fontSize: '0.8rem',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                              }}
                            >
                              <AlertTriangle size={12} />
                              {allergy}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <div style={{ background: '#f0fdf4', padding: '10px 12px', borderRadius: 8, border: '1px solid #bbf7d0', color: '#166534', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <HeartPulse size={15} />
                          <span>No known active allergies or contraindications recorded.</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Fast Action Shortcuts */}
                  <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8' }}>
                      Quick Actions
                    </span>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <Link
                        to={`/doctor/prescriptions?patient=${encodeURIComponent(selectedPatient.patient_id || selectedPatient.user_id || selectedPatient.id)}&new=1`}
                        className="btn btn-primary btn-sm"
                        style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                      >
                        <Pill size={14} />
                        <span>Prescribe</span>
                      </Link>
                      <Link
                        to={`/doctor/history?patient=${encodeURIComponent(selectedPatient.patient_id || selectedPatient.user_id || selectedPatient.id)}`}
                        className="btn btn-secondary btn-sm"
                        style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                      >
                        <FileText size={14} />
                        <span>Timeline</span>
                      </Link>
                    </div>
                  </div>

                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
