import { describe, it, expect, beforeEach, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import HealthTrends from './pages/HealthTrends.jsx'
import { getTrendDetail, getTrendSummary, updateTrendPoint } from './services/reports.js'

vi.mock('./auth.jsx', () => ({
  useAuth: () => ({ user: { role: 'patient', user_id: 'p1', full_name: 'Test Patient' } }),
}))

vi.mock('./services/reports.js', () => ({
  getTrendSummary: vi.fn(),
  getTrendDetail: vi.fn(),
  updateTrendPoint: vi.fn(),
}))

const SUMMARY = {
  patient_id: 'p1',
  test_count: 1,
  tests: [
    {
      canonical_test: 'fasting_glucose',
      display_name: 'Fasting glucose',
      unit: 'mg/dL',
      point_count: 3,
      first_value: 95,
      first_date: '2026-01-12',
      latest_value: 128,
      latest_date: '2026-07-10',
      latest_flag: 'high',
      range_status_latest: 'above',
      direction: 'rising',
      change_abs: 16,
      change_pct: 14.29,
      events: ['Fasting glucose went above the reference range.'],
    },
  ],
  insufficient_tests: [],
  not_comparable: [],
  duplicate_notes: [],
}

const POINTS = [
  {
    canonical_test: 'fasting_glucose',
    report_id: 'r1',
    value: 95,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 100,
    flag: 'normal',
    collected_on: '2026-01-12',
    date_source: 'collected',
    original_value: 95,
    original_unit: 'mg/dL',
    excluded_by_patient: false,
    edited_by_patient: false,
  },
  {
    canonical_test: 'fasting_glucose',
    report_id: 'r2',
    value: 112,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 100,
    flag: 'high',
    collected_on: '2026-04-10',
    date_source: 'collected',
    original_value: 112,
    original_unit: 'mg/dL',
    excluded_by_patient: false,
    edited_by_patient: false,
  },
  {
    canonical_test: 'fasting_glucose',
    report_id: 'r3',
    value: 128,
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 100,
    flag: 'high',
    collected_on: '2026-07-10',
    date_source: 'collected',
    original_value: 128,
    original_unit: 'mg/dL',
    excluded_by_patient: false,
    edited_by_patient: false,
  },
]

const DETAIL = {
  canonical_test: 'fasting_glucose',
  display_name: 'Fasting glucose',
  unit: 'mg/dL',
  points: POINTS,
  excluded_points: [],
  not_comparable: [],
  duplicate_notes: [],
  point_count: 3,
  first: POINTS[0],
  previous: POINTS[1],
  latest: POINTS[2],
  change_abs: 16,
  change_pct: 14.29,
  days_between: 179,
  direction: 'rising',
  ref_low: 70,
  ref_high: 100,
  range_source: 'table',
  range_status_latest: 'above',
  events: ['Fasting glucose went above the reference range.'],
  explanation:
    'Fasting glucose rose from 95 mg/dL to 128 mg/dL, an increase of 34.74%. This is not a diagnosis. Please discuss these results with your doctor.',
}

function renderTrends(initialEntry = '/patient/trends') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/patient/trends" element={<HealthTrends />} />
        <Route path="/patient/trends/:canonicalTest" element={<HealthTrends />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('HealthTrends', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getTrendSummary.mockResolvedValue(SUMMARY)
    getTrendDetail.mockResolvedValue(DETAIL)
    updateTrendPoint.mockResolvedValue({
      report_id: 'r3',
      canonical_test: 'fasting_glucose',
      series: DETAIL,
    })
  })

  it('shows summary cards and opens a test detail', async () => {
    renderTrends()

    expect(await screen.findByRole('heading', { name: 'Health Trends' })).toBeInTheDocument()
    expect(await screen.findByText('Fasting glucose')).toBeInTheDocument()
    expect(screen.getByText('128')).toBeInTheDocument()
    expect(screen.getByText('Rising')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'View Fasting glucose trend' }))

    expect(await screen.findByText('Plain-language summary')).toBeInTheDocument()
    expect(screen.getByText(/rose from 95 mg\/dL to 128 mg\/dL/)).toBeInTheDocument()
    expect(getTrendDetail).toHaveBeenCalledWith('fasting_glucose', null)
  })

  it('lets a patient correct a stored value', async () => {
    renderTrends('/patient/trends/fasting_glucose')

    expect(await screen.findByRole('heading', { name: 'Report values' })).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Correct' })[2])

    const input = screen.getByLabelText(/Corrected value/)
    fireEvent.change(input, { target: { value: '126' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save correction' }))

    await waitFor(() =>
      expect(updateTrendPoint).toHaveBeenCalledWith('fasting_glucose', 'r3', {
        corrected_value: 126,
      }),
    )
  })
})
