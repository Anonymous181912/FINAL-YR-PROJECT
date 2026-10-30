import { describe, it, expect, beforeEach, vi } from 'vitest'

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('./services/api', () => ({ default: api }))

import {
  confirmPaperPrescription,
  createPaperPrescription,
  deletePaperPrescription,
  getPaperPrescriptionFile,
  scanPaperPrescription,
} from './services/prescriptions.js'

describe('paper prescription service calls', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates a paper prescription directly with multipart fields', async () => {
    const file = new File(['paper'], 'paper.jpg', { type: 'image/jpeg' })
    api.post.mockResolvedValue({ data: { id: 'rx-paper' } })

    const result = await createPaperPrescription({
      file,
      doctorName: 'Dr. Smith',
      prescriptionDate: '2026-10-15',
      note: 'After a clinic visit',
    })

    expect(result).toEqual({ id: 'rx-paper' })
    expect(api.post).toHaveBeenCalledTimes(1)
    const [url, formData, config] = api.post.mock.calls[0]
    expect(url).toBe('/prescriptions/paper')
    expect(formData.get('file')).toBe(file)
    expect(formData.get('prescriber_name')).toBe('Dr. Smith')
    expect(formData.get('prescription_date')).toBe('2026-10-15')
    expect(formData.get('note')).toBe('After a clinic visit')
    expect(config).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } })
  })

  it('omits blank optional paper fields', async () => {
    const file = new File(['paper'], 'paper.jpg', { type: 'image/jpeg' })
    api.post.mockResolvedValue({ data: { id: 'rx-paper' } })

    await createPaperPrescription({ file })

    const [, formData] = api.post.mock.calls[0]
    expect(formData.get('prescriber_name')).toBeNull()
    expect(formData.get('prescription_date')).toBeNull()
    expect(formData.get('note')).toBeNull()
  })

  it('fetches the original paper file as a blob', async () => {
    const blob = new Blob(['paper'], { type: 'image/jpeg' })
    api.get.mockResolvedValue({ data: blob })

    const result = await getPaperPrescriptionFile('rx-paper')

    expect(result).toBe(blob)
    expect(api.get).toHaveBeenCalledWith('/prescriptions/paper/rx-paper/file', {
      responseType: 'blob',
    })
  })

  it('uploads the paper file to the patient scan endpoint', async () => {
    const file = new File(['paper'], 'paper.png', { type: 'image/png' })
    api.post.mockResolvedValue({ data: { temp_upload_id: 'temp-1' } })

    const result = await scanPaperPrescription(file)

    expect(result).toEqual({ temp_upload_id: 'temp-1' })
    expect(api.post).toHaveBeenCalledTimes(1)
    const [url, formData, config] = api.post.mock.calls[0]
    expect(url).toBe('/prescriptions/paper/scan')
    expect(formData.get('file')).toBe(file)
    expect(config).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } })
  })

  it('posts patient-reviewed rows to confirm', async () => {
    const payload = {
      temp_upload_id: 'temp-1',
      prescriber_name: 'Dr. Smith',
      prescription_date: '2026-10-28',
      items: [
        {
          medicine_name: 'Aspirin',
          dosage: '100mg',
          frequency: 'OD',
          duration: '3 days',
        },
      ],
      confirmed_by_patient: true,
    }
    api.post.mockResolvedValue({ data: { id: 'rx-paper' } })

    const result = await confirmPaperPrescription(payload)

    expect(result).toEqual({ id: 'rx-paper' })
    expect(api.post).toHaveBeenCalledWith('/prescriptions/paper/confirm', payload)
  })

  it('deletes only through the paper endpoint', async () => {
    api.delete.mockResolvedValue({ data: null })

    await deletePaperPrescription('rx-paper')

    expect(api.delete).toHaveBeenCalledWith('/prescriptions/paper/rx-paper')
  })
})
