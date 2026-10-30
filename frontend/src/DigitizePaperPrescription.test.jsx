import { describe, it, expect, beforeEach, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DigitizePaperPrescription from './pages/DigitizePaperPrescription.jsx'
import {
  confirmPaperPrescription,
  scanPaperPrescription,
} from './services/prescriptions.js'

vi.mock('./services/prescriptions.js', () => ({
  scanPaperPrescription: vi.fn(),
  confirmPaperPrescription: vi.fn(),
}))

const SCAN_RESULT = {
  temp_upload_id: 'temp-1',
  original_filename: 'paper.png',
  ocr_used: true,
  raw_text: 'Dr. Smith 2026-10-28 Aspirin 100mg OD for 3 days',
  detected_doctor_name: 'Dr. Smith',
  detected_prescription_date: '2026-10-28',
  extraction_method: 'ocr+rule-based',
  items: [
    {
      medicine_name: 'Aspirin',
      dosage: '100mg',
      frequency: 'OD',
      duration: '3 days',
      instructions: '',
      confidence: 0.42,
      needs_review: true,
    },
  ],
}

const SAVED_RECORD = {
  id: 'rx-paper',
  prescriber_name: 'Dr. Smith',
  prescription_date: '2026-10-28',
  items: [{ medicine_name: 'Aspirin' }],
  source: 'patient_uploaded',
  verified: false,
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/patient/prescriptions/digitize']}>
      <DigitizePaperPrescription />
    </MemoryRouter>,
  )
}

async function uploadFile(container) {
  const input = container.querySelector('input[type="file"]')
  fireEvent.change(input, {
    target: {
      files: [new File(['paper'], 'paper.png', { type: 'image/png' })],
    },
  })
  await waitFor(() => expect(scanPaperPrescription).toHaveBeenCalledTimes(1))
}

describe('DigitizePaperPrescription', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    scanPaperPrescription.mockResolvedValue(SCAN_RESULT)
    confirmPaperPrescription.mockResolvedValue(SAVED_RECORD)
  })

  it('shows the handwriting warning and editable low-confidence rows', async () => {
    const { container } = renderPage()
    await uploadFile(container)

    expect(screen.getByText(/Handwriting accuracy warning/i)).toBeInTheDocument()
    expect(screen.getByText(/Low confidence - check against paper/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue('Aspirin')).toBeInTheDocument()
    expect(screen.getByDisplayValue('100mg')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Dr. Smith')).toBeInTheDocument()
    expect(screen.getByDisplayValue('2026-10-28')).toBeInTheDocument()
  })

  it('requires confirmation before saving and sends patient-reviewed rows', async () => {
    const { container } = renderPage()
    await uploadFile(container)

    const save = screen.getByRole('button', { name: /Save paper prescription/i })
    expect(save).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Prescriber name'), {
      target: { value: 'Dr. Smith' },
    })
    fireEvent.change(screen.getByLabelText('Prescription date'), {
      target: { value: '2026-10-28' },
    })
    expect(save).toBeDisabled()

    fireEvent.click(screen.getByLabelText(/I checked these details against the paper/i))
    expect(save).toBeEnabled()

    fireEvent.click(save)

    await waitFor(() => expect(confirmPaperPrescription).toHaveBeenCalledTimes(1))
    expect(confirmPaperPrescription).toHaveBeenCalledWith({
      temp_upload_id: 'temp-1',
      prescriber_name: 'Dr. Smith',
      prescription_date: '2026-10-28',
      items: [
        {
          medicine_name: 'Aspirin',
          dosage: '100mg',
          frequency: 'OD',
          duration: '3 days',
          instructions: undefined,
        },
      ],
      confirmed_by_patient: true,
    })

    expect(await screen.findByText(/Paper prescription saved/i)).toBeInTheDocument()
    expect(
      screen.getAllByText(/Patient-uploaded - not verified by a doctor/i).length,
    ).toBeGreaterThan(0)
  })

  it('requires a medicine name before enabling save', async () => {
    const { container } = renderPage()
    await uploadFile(container)

    fireEvent.change(screen.getByLabelText('Prescriber name'), {
      target: { value: 'Dr. Smith' },
    })
    fireEvent.change(screen.getByLabelText('Prescription date'), {
      target: { value: '2026-10-28' },
    })
    fireEvent.change(screen.getByLabelText('Medicine name row 1'), {
      target: { value: '   ' },
    })
    fireEvent.click(screen.getByLabelText(/I checked these details against the paper/i))

    expect(
      screen.getByRole('button', { name: /Save paper prescription/i }),
    ).toBeDisabled()
  })
})
