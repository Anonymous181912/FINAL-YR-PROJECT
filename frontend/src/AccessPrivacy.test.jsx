import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AccessPrivacy from './pages/AccessPrivacy.jsx'
import * as accessApi from './services/access'

vi.mock('./services/access', () => ({
  incomingRequests: vi.fn(),
  approveRequest: vi.fn(),
  denyRequest: vi.fn(),
  myGrants: vi.fn(),
  revokeGrant: vi.fn(),
  myAuditTrail: vi.fn(),
}))

const PENDING = [
  { id: 'req1', doctor_id: 'doctor-user-123456', scope: ['reports', 'history'], message: 'Follow-up review', status: 'pending' },
]
const GRANTS = [
  { id: 'g1', doctor_id: 'doctor-user-999', scope: ['reports'], status: 'active', expires_at: null },
]
const AUDIT = [
  { id: 'a1', actor_id: 'doctor-user-123456', actor_role: 'doctor', action: 'read',
    resource_type: 'report', resource_id: 'report-abc123', patient_id: 'patient-1',
    timestamp: new Date().toISOString() },
]

describe('Access & Privacy flow', () => {
  beforeEach(() => {
    accessApi.incomingRequests.mockResolvedValue(PENDING)
    accessApi.myGrants.mockResolvedValue(GRANTS)
    accessApi.myAuditTrail.mockResolvedValue(AUDIT)
    accessApi.approveRequest.mockResolvedValue({ id: 'g2', status: 'active' })
  })

  it('lists pending requests, grants and the audit trail', async () => {
    render(<AccessPrivacy />)
    await waitFor(() => expect(screen.getByText(/Pending Requests \(1\)/)).toBeInTheDocument())
    expect(screen.getByText(/Doctors With Access \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/Who Accessed Your Data \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/Follow-up review/)).toBeInTheDocument()
  })

  it('approves a request with the chosen expiry', async () => {
    render(<AccessPrivacy />)
    await waitFor(() => expect(screen.getByText(/Pending Requests \(1\)/)).toBeInTheDocument())
    fireEvent.click(screen.getByText('Approve'))
    await waitFor(() => expect(accessApi.approveRequest).toHaveBeenCalledWith('req1', 30))
  })
})
