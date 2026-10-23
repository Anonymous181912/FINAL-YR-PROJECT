import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LabResultsTable } from './pages/Reports.jsx'

const SAMPLE = [
  { name: 'Hemoglobin', canonical_name: 'hemoglobin', value: 9.5, unit: 'g/dL',
    ref_low: 12.0, ref_high: 16.0, flag: 'low', range_source: 'report',
    source_text: 'Hemoglobin 9.5 g/dL', start: 0, end: 20 },
  { name: 'WBC (White Blood Cells)', canonical_name: 'wbc', value: 7.0, unit: 'x10^3/uL',
    ref_low: 4.0, ref_high: 11.0, flag: 'normal', range_source: 'table',
    source_text: 'WBC 7.0', start: 21, end: 28 },
]

describe('LabResultsTable', () => {
  it('renders values with colored Low/Normal badges and range source', () => {
    render(<LabResultsTable labs={SAMPLE} />)
    expect(screen.getByText('Hemoglobin')).toBeInTheDocument()
    expect(screen.getByText('Low')).toBeInTheDocument()
    expect(screen.getByText('Normal')).toBeInTheDocument()
    expect(screen.getByText('Printed on report')).toBeInTheDocument()
    expect(screen.getByText('Standard table')).toBeInTheDocument()
    expect(screen.getByText(/educational, not clinical advice/i)).toBeInTheDocument()
  })

  it('shows an empty state when no labs were detected', () => {
    render(<LabResultsTable labs={[]} />)
    expect(screen.getByText(/No laboratory values were detected/)).toBeInTheDocument()
  })
})
