import { describe, it, expect, beforeEach, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import PaperPrescriptionModal from './components/PaperPrescriptionModal.jsx'
import { createPaperPrescription } from './services/prescriptions.js'

vi.mock('./services/prescriptions.js', () => ({
  createPaperPrescription: vi.fn(),
}))

function renderModal(onSaved = vi.fn()) {
  return render(
    <PaperPrescriptionModal open onClose={vi.fn()} onSaved={onSaved} />
  )
}

function upload(name = 'paper.png', type = 'image/png', size = null) {
  const input = document.querySelector('input[type="file"]')
  const file = new File(['paper'], name, { type })
  if (size !== null) {
    Object.defineProperty(file, 'size', { value: size })
  }
  fireEvent.change(input, { target: { files: [file] } })
  return file
}

function tomorrowIso() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 10)
}

describe('PaperPrescriptionModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    createPaperPrescription.mockResolvedValue({ id: 'rx-paper' })
  })

  it('saves the file directly without an extraction step', async () => {
    const onSaved = vi.fn()
    renderModal(onSaved)

    expect(screen.queryByText(/Upload & Extract/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Detected medicines/i)).not.toBeInTheDocument()
    expect(
      screen.getByText("Optional. Past dates only; blank uses today's date.")
    ).toBeInTheDocument()

    const file = upload()
    fireEvent.click(screen.getByRole('button', { name: /^Save$/i }))

    await waitFor(() => expect(createPaperPrescription).toHaveBeenCalledTimes(1))
    expect(createPaperPrescription).toHaveBeenCalledWith({
      file,
      doctorName: undefined,
      prescriptionDate: undefined,
      note: undefined,
    })
    expect(onSaved).toHaveBeenCalledWith({ id: 'rx-paper' })
  })

  it('sends the optional date, doctor and note', async () => {
    renderModal()

    upload()
    fireEvent.change(screen.getByLabelText('Prescription date'), {
      target: { value: '2026-10-15' },
    })
    fireEvent.change(screen.getByLabelText('Doctor name'), {
      target: { value: ' Dr. Smith ' },
    })
    fireEvent.change(screen.getByLabelText('Note'), {
      target: { value: ' After a clinic visit ' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^Save$/i }))

    await waitFor(() => expect(createPaperPrescription).toHaveBeenCalledTimes(1))
    expect(createPaperPrescription).toHaveBeenCalledWith({
      file: expect.any(File),
      doctorName: 'Dr. Smith',
      prescriptionDate: '2026-10-15',
      note: 'After a clinic visit',
    })
  })

  it('rejects a wrong file type and requires a valid file to save', async () => {
    renderModal()

    upload('notes.txt', 'text/plain')

    expect(await screen.findByText(/Unsupported file type/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^Save$/i }))
    expect(await screen.findByText(/Choose a file to upload/i)).toBeInTheDocument()
    expect(createPaperPrescription).not.toHaveBeenCalled()
  })

  it('rejects an oversize file', async () => {
    renderModal()

    upload('paper.jpg', 'image/jpeg', 10 * 1024 * 1024 + 1)

    expect(await screen.findByText(/exceeds 10MB limit/i)).toBeInTheDocument()
    expect(createPaperPrescription).not.toHaveBeenCalled()
  })

  it('rejects a future prescription date', async () => {
    renderModal()

    upload()
    fireEvent.change(screen.getByLabelText('Prescription date'), {
      target: { value: tomorrowIso() },
    })
    fireEvent.click(screen.getByRole('button', { name: /^Save$/i }))

    expect(
      await screen.findByText(/must be in the past, not in the future/i)
    ).toBeInTheDocument()
    expect(createPaperPrescription).not.toHaveBeenCalled()
  })

  it('disables the form and shows Saving while the request is in flight', async () => {
    let resolveSave
    createPaperPrescription.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSave = resolve
        })
    )
    const onSaved = vi.fn()
    renderModal(onSaved)

    upload()
    fireEvent.click(screen.getByRole('button', { name: /^Save$/i }))

    expect(await screen.findByText('Saving...')).toBeInTheDocument()
    expect(screen.getByLabelText('Doctor name')).toBeDisabled()
    expect(screen.getByLabelText('Prescription date')).toBeDisabled()
    expect(screen.getByLabelText('Note')).toBeDisabled()
    expect(document.querySelector('input[type="file"]')).toBeDisabled()

    resolveSave({ id: 'rx-paper' })
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith({ id: 'rx-paper' }))
  })
})
