import { useState, useEffect } from 'react'
import { useAuth } from '../auth.jsx'
import api from '../services/api'
import { downloadEmergencyCard, rotateEmergencyToken, revokeEmergencyToken } from '../services/notifications'
import {
  User as UserIcon,
  Stethoscope,
  Mail,
  ShieldCheck,
  AlertTriangle,
  HeartPulse,
  Download,
  RefreshCw,
  Ban
} from 'lucide-react'

export default function Profile({ verificationStatus }) {
  const { user } = useAuth()
  const isDoctor = user?.role === 'doctor'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [profile, setProfile] = useState(null)
  const [verifyStatus, setVerifyStatus] = useState(verificationStatus || null)
  const [cardBusy, setCardBusy] = useState(false)
  const [cardMsg, setCardMsg] = useState('')

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const endpoint = isDoctor ? '/doctors/me' : '/patients/me'
        const res = await api.get(endpoint)
        setProfile(res.data || null)
        if (isDoctor && res.data?.verification_status) setVerifyStatus(res.data.verification_status)
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load your profile. Please try again.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [isDoctor])

  const getInitials = (name) => {
    if (!name) return 'U'
    return name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
  }

  const rows = []
  if (profile) {
    if (profile.specialization) rows.push(['Specialization', profile.specialization])
    if (profile.license_number) rows.push(['License Number', profile.license_number])
    if (profile.verification_status) rows.push(['Verification', profile.verification_status])
    else if (verifyStatus) rows.push(['Verification', verifyStatus])
    if (profile.gender) rows.push(['Gender', String(profile.gender).replace(/_/g, ' ')])
    if (profile.date_of_birth) {
      const d = new Date(profile.date_of_birth)
      rows.push(['Date of Birth', Number.isNaN(d.getTime()) ? profile.date_of_birth : d.toLocaleDateString()])
    }
    if (profile.blood_group) rows.push(['Blood Group', profile.blood_group])
    if (profile.contact_phone) rows.push(['Phone', profile.contact_phone])
    if (profile.contact_email) rows.push(['Contact Email', profile.contact_email])
    if (profile.address) rows.push(['Address', profile.address])
    if (profile.allergies && profile.allergies.length > 0) rows.push(['Allergies', profile.allergies.join(', ')])
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="page-header">
        <div className="page-header-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className={`badge ${isDoctor ? 'badge-info' : 'badge-teal'}`}>
              {isDoctor ? <Stethoscope size={12} /> : <UserIcon size={12} />}
              {isDoctor ? 'Doctor Workspace' : 'Patient Health Portal'}
            </span>
          </div>
          <h1>Profile</h1>
          <p>Your account identity and {isDoctor ? 'practitioner' : 'patient'} record.</p>
        </div>
      </div>

      {error && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      <div className="card">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px 16px' }}>
            <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>Loading your profile...</p>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
              <div className="user-avatar" style={{ width: 56, height: 56, fontSize: '1.2rem' }}>
                {getInitials(user?.full_name || user?.email)}
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.25rem' }}>{user?.full_name || 'Unknown user'}</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                  <span className={`user-role-badge ${isDoctor ? 'role-doctor' : 'role-patient'}`}>
                    {isDoctor ? <Stethoscope size={10} /> : <UserIcon size={10} />}
                    {user?.role}
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.82rem', color: 'var(--slate-500)' }}>
                    <Mail size={13} /> {user?.email}
                  </span>
                </div>
              </div>
            </div>

            {rows.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
                {rows.map(([label, value]) => (
                  <div key={label} style={{ background: 'var(--slate-50)', padding: '10px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--slate-200)' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--slate-500)', display: 'block' }}>
                      {label}
                    </span>
                    <strong style={{ fontSize: '0.9rem', color: 'var(--slate-900)', textTransform: 'capitalize' }}>
                      {value}
                    </strong>
                  </div>
                ))}
              </div>
            ) : (
              !error && (
                <p style={{ color: 'var(--slate-500)', fontSize: '0.88rem', margin: 0 }}>
                  No additional {isDoctor ? 'practitioner' : 'clinical'} details recorded yet.
                </p>
              )
            )}

            <div className="safety-note-banner" style={{ marginTop: 20, marginBottom: 0 }}>
              <ShieldCheck size={18} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <div style={{ fontWeight: 700, marginBottom: 2 }}>Account identity</div>
                <div>Name, email, and role come from your verified sign-in and cannot be edited here.</div>
              </div>
            </div>

            {!isDoctor && !loading && (
              <div className="card" style={{ marginTop: 20, marginBottom: 0, border: '1px solid #fecaca' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <HeartPulse size={18} color="#b91c1c" />
                  <h3 style={{ margin: 0, fontSize: '1rem' }}>Emergency Card</h3>
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--slate-600)', marginBottom: 12 }}>
                  Printable PDF with your blood group, allergies and emergency contact, plus a
                  QR link to a revocable online page showing only those fields.
                </p>
                {cardMsg && <p style={{ fontSize: '0.85rem', color: 'var(--slate-600)' }}>{cardMsg}</p>}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={cardBusy}
                    onClick={async () => {
                      setCardBusy(true)
                      setCardMsg('')
                      try {
                        const blob = await downloadEmergencyCard()
                        const url = window.URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = 'emergency_card.pdf'
                        document.body.appendChild(a)
                        a.click()
                        window.URL.revokeObjectURL(url)
                        document.body.removeChild(a)
                      } catch {
                        setCardMsg('Could not generate the card. Please try again.')
                      } finally {
                        setCardBusy(false)
                      }
                    }}
                  >
                    <Download size={14} /> {cardBusy ? 'Working...' : 'Download card (PDF)'}
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={async () => {
                      try {
                        await rotateEmergencyToken()
                        setCardMsg('Emergency link renewed. Download the card again to get the new QR code.')
                      } catch {
                        setCardMsg('Could not renew the link.')
                      }
                    }}
                    title="Invalidate the old QR link and issue a new one"
                  >
                    <RefreshCw size={14} /> Renew link
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={async () => {
                      if (!window.confirm('Revoke the online emergency page? The QR code on printed cards will stop working.')) return
                      try {
                        await revokeEmergencyToken()
                        setCardMsg('Online emergency page revoked.')
                      } catch {
                        setCardMsg('Could not revoke the link.')
                      }
                    }}
                    title="Disable the online emergency page"
                  >
                    <Ban size={14} /> Revoke link
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
