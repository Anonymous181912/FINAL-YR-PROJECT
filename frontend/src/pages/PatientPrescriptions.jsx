import { useState, useEffect } from 'react'
import { useAuth } from '../auth.jsx'
import { listPatientPrescriptions, generatePrescriptionPdf, downloadPrescriptionPdf } from '../services/prescriptions.js'
import {
  Pill,
  FileDown,
  Calendar,
  User,
  Clock,
  QrCode,
  ShieldCheck as ShieldCheckIcon,
  AlertTriangle,
  HeartPulse,
} from 'lucide-react'

export default function PatientPrescriptions() {
  const { user } = useAuth()

  const [loading, setLoading] = useState(false)
  const [pdfLoadingId, setPdfLoadingId] = useState(null)
  const [error, setError] = useState('')
  const [prescriptions, setPrescriptions] = useState([])

  const fetchPrescriptions = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listPatientPrescriptions()
      setPrescriptions(data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load prescriptions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPrescriptions()
  }, [])

  const handlePdf = async (rx) => {
    setPdfLoadingId(rx.id)
    setError('')
    try {
      const blob = await generatePrescriptionPdf(rx.id)
      downloadPrescriptionPdf(blob, `Prescription_${rx.id.slice(-6)}.pdf`)
      await fetchPrescriptions()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate PDF')
    } finally {
      setPdfLoadingId(null)
    }
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', fontSize: '0.75rem', fontWeight: 600, marginBottom: 8 }}>
            <HeartPulse size={12} />
            <span>My Prescriptions</span>
          </div>
          <h1>My Prescriptions</h1>
          <p>Review your active and past prescribed medical regimens. Only issued prescriptions are shown.</p>
        </div>
      </div>

      {error && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 20 }}>
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {/* Prescription Directory Card */}
      <div className="card" style={{ padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18, flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Pill size={18} color="#0ea5e9" />
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>My Prescriptions</h3>
          </div>
          <span className="badge badge-teal">
            {prescriptions.length} {prescriptions.length === 1 ? 'Prescription' : 'Prescriptions'}
          </span>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#64748b', fontSize: '0.9rem' }}>Loading prescriptions...</p>
          </div>
        )}

        {!loading && prescriptions.length === 0 && (
          <div className="empty-state">
            <Pill size={36} />
            <h4 style={{ margin: '8px 0 4px', color: '#0f172a' }}>No prescriptions found</h4>
            <p style={{ margin: 0, fontSize: '0.85rem' }}>
              Prescriptions issued by your doctor will appear here.
            </p>
          </div>
        )}

        {!loading && prescriptions.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {prescriptions.map((rx) => {
              const dateStr = rx.prescription_date ? new Date(rx.prescription_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : 'Date not set'
              const status = rx.status || 'issued'
              const isPdfBusy = pdfLoadingId === rx.id
              const isRevoked = rx.verification_status === 'revoked'

              return (
                <div
                  key={rx.id}
                  className="card card-hover"
                  style={{
                    padding: '20px',
                    marginBottom: 0,
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
                    
                    {/* Left Details */}
                    <div style={{ display: 'flex', gap: 14, flex: 1, minWidth: 280 }}>
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 10,
                          background: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
                          color: 'white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontFamily: 'serif',
                          fontSize: '1.2rem',
                          flexShrink: 0,
                        }}
                      >
                        ℞
                      </div>

                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                          <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
                            Prescription #{rx.id.slice(-6).toUpperCase()}
                          </h4>
                          <span
                            className="badge"
                            style={{
                              textTransform: 'capitalize',
                              background: isRevoked ? '#fef2f2' : '#f0fdf4',
                              color: isRevoked ? '#b91c1c' : '#166534',
                              border: `1px solid ${isRevoked ? '#fecaca' : '#bbf7d0'}`,
                            }}
                          >
                            {isRevoked ? 'Revoked' : status}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 4, flexWrap: 'wrap', fontSize: '0.82rem', color: '#64748b' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <Calendar size={13} />
                            {dateStr}
                          </span>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <User size={13} />
                            Dr. {rx.doctor_name || 'Doctor'}
                          </span>
                          {rx.follow_up_date && (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#0d9488' }}>
                              <Clock size={13} />
                              Follow-up: {new Date(rx.follow_up_date).toLocaleDateString()}
                            </span>
                          )}
                        </div>

                        {/* Medicine Pills preview */}
                        {rx.items && rx.items.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
                            {rx.items.map((m, idx) => (
                              <span
                                key={idx}
                                style={{
                                  background: '#f1f5f9',
                                  color: '#334155',
                                  padding: '3px 8px',
                                  borderRadius: 6,
                                  fontSize: '0.78rem',
                                  fontWeight: 500,
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                }}
                              >
                                <Pill size={11} color="#0ea5e9" />
                                <strong>{m.medicine_name}</strong> {m.dosage && `(${m.dosage})`}
                              </span>
                            ))}
                          </div>
                        )}

                        {rx.diagnosis_notes && (
                          <p style={{ margin: '8px 0 0', fontSize: '0.82rem', color: '#475569', fontStyle: 'italic' }}>
                            "{rx.diagnosis_notes}"
                          </p>
                        )}

                        {rx.safety_warnings && rx.safety_warnings.length > 0 && (
                          <div style={{ marginTop: 10 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', fontWeight: 700, color: '#92400e', marginBottom: 8 }}>
                              <ShieldCheckIcon size={14} />
                              <span>Medication safety flags (educational — confirm with a pharmacist)</span>
                            </div>
                            {rx.safety_warnings.map((w, idx) => (
                              <div key={idx} style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8, padding: '8px 12px', fontSize: '0.82rem', color: '#78350f', marginTop: 6 }}>
                                <span className={`badge ${w.severity === 'severe' ? 'badge-danger' : w.severity === 'moderate' ? 'badge-warning' : 'badge-neutral'}`} style={{ marginRight: 8, textTransform: 'capitalize' }}>
                                  {w.severity}: {w.type}
                                </span>
                                <strong>{(w.drugs || []).join(' + ')}</strong>
                                {w.note ? ` — ${w.note}` : ''}
                              </div>
                            ))}
                          </div>
                        )}

                        <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                          {isRevoked ? (
                            <span className="badge badge-danger">Verification revoked</span>
                          ) : (
                            <span className="badge badge-success">Verified prescription</span>
                          )}
                          {rx.verification_token && (
                            <a
                              href={`${window.location.origin}/verify/${rx.verification_token}`}
                              target="_blank"
                              rel="noreferrer"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.8rem', color: '#0284c7' }}
                            >
                              <QrCode size={13} /> Public verification page
                            </a>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right Actions */}
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handlePdf(rx)}
                        disabled={isPdfBusy}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                      >
                        <FileDown size={14} />
                        <span>{isPdfBusy ? 'Generating...' : rx.file_path ? 'Download PDF' : 'Generate PDF'}</span>
                      </button>
                    </div>

                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}