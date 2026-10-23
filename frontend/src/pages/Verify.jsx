import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { verifyPrescriptionToken, verifyEmergencyToken } from '../services/prescriptions'
import { ShieldCheck, AlertTriangle, XCircle, ArrowLeft } from 'lucide-react'

export function VerifyPrescription() {
  const { token } = useParams()
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    verifyPrescriptionToken(token)
      .then(setResult)
      .catch(() => setError('This verification code was not found. Check the QR link and try again.'))
      .finally(() => setLoading(false))
  }, [token])

  const statusColor = result?.status === 'valid' ? '#166534' : result?.status === 'revoked' ? '#b91c1c' : '#92400e'

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, background: 'var(--slate-50)' }}>
      <div className="card" style={{ maxWidth: 480, width: '100%', textAlign: 'center' }}>
        <ShieldCheck size={40} style={{ margin: '0 auto 12px', color: statusColor }} />
        <h2>Prescription Verification</h2>
        {loading && <p style={{ color: 'var(--slate-500)' }}>Checking authenticity...</p>}
        {error && (
          <>
            <div className="alert-banner alert-banner-danger" style={{ margin: '16px 0' }}>
              <XCircle size={18} /> <span>{error}</span>
            </div>
          </>
        )}
        {result && (
          <div style={{ margin: '16px 0', display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.92rem' }}>
            <div>
              Status:{' '}
              <strong style={{ color: statusColor, textTransform: 'uppercase' }}>
                {result.status === 'valid' ? 'Valid' : result.status === 'revoked' ? 'Revoked by doctor' : 'Modified — content changed'}
              </strong>
            </div>
            <div>Issued by: <strong>{result.doctor_name}</strong></div>
            <div>Issue date: <strong>{result.issue_date ? new Date(result.issue_date).toLocaleDateString() : '—'}</strong></div>
            <div>Reference: <strong>#{result.prescription_ref}</strong></div>
            <p style={{ color: 'var(--slate-500)', fontSize: '0.8rem', marginTop: 8 }}>{result.disclaimer}</p>
          </div>
        )}
        <Link to="/login" className="btn btn-secondary btn-sm" style={{ marginTop: 8 }}>
          <ArrowLeft size={14} /> Back to sign in
        </Link>
      </div>
    </div>
  )
}

export function VerifyEmergency() {
  const { token } = useParams()
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    verifyEmergencyToken(token)
      .then(setResult)
      .catch(() => setError('This emergency link is invalid or has been revoked.'))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, background: '#fef2f2' }}>
      <div className="card" style={{ maxWidth: 480, width: '100%', border: '2px solid #fecaca' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <AlertTriangle size={24} color="#b91c1c" />
          <h2 style={{ color: '#b91c1c', margin: 0 }}>Emergency Information</h2>
        </div>
        {loading && <p style={{ color: 'var(--slate-500)' }}>Loading...</p>}
        {error && <div className="alert-banner alert-banner-danger">{error}</div>}
        {result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: '0.95rem' }}>
            <div><strong>Blood group:</strong> {result.blood_group || 'Not recorded'}</div>
            <div><strong>Allergies:</strong> {(result.allergies || []).join(', ') || 'None recorded'}</div>
            <div><strong>Emergency contact:</strong> {result.emergency_contact_name || 'Not recorded'}</div>
            <div><strong>Contact phone:</strong> {result.emergency_contact_phone || 'Not recorded'}</div>
            <p style={{ color: 'var(--slate-500)', fontSize: '0.8rem' }}>{result.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  )
}
