import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Activity,
  ArrowLeft,
  ArrowUpRight,
  ChevronRight,
  CircleAlert,
  FlaskConical,
  Info,
  Minus,
  Pencil,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  UploadCloud,
  X,
} from 'lucide-react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuth } from '../auth.jsx'
import { getTrendDetail, getTrendSummary, updateTrendPoint } from '../services/reports.js'

const DISCLAIMER = 'This is not a diagnosis. Please discuss these results with your doctor.'

const TONES = {
  neutral: {
    background: 'var(--surface-2)',
    color: 'var(--text-muted)',
    borderColor: 'var(--border)',
  },
  success: {
    background: 'var(--success-bg)',
    color: 'var(--success-fg)',
    borderColor: 'var(--success-border)',
  },
  warning: {
    background: 'var(--warning-bg)',
    color: 'var(--warning-fg)',
    borderColor: 'var(--warning-border)',
  },
  danger: {
    background: 'var(--danger-bg)',
    color: 'var(--danger-fg)',
    borderColor: 'var(--danger-border)',
  },
  info: {
    background: 'var(--info-bg)',
    color: 'var(--info-fg)',
    borderColor: 'var(--info-border)',
  },
}

const DIRECTIONS = {
  rising: { label: 'Rising', Icon: TrendingUp, tone: 'warning' },
  falling: { label: 'Falling', Icon: TrendingDown, tone: 'info' },
  stable: { label: 'Stable', Icon: Minus, tone: 'neutral' },
  insufficient_data: { label: 'Not enough data', Icon: Minus, tone: 'neutral' },
}

const RANGE_STATUS = {
  within: { label: 'In range', tone: 'success' },
  below: { label: 'Below range', tone: 'info' },
  above: { label: 'Above range', tone: 'danger' },
  normal: { label: 'Normal', tone: 'success' },
  low: { label: 'Low', tone: 'info' },
  high: { label: 'High', tone: 'danger' },
  unknown: { label: 'Range unknown', tone: 'neutral' },
}

const DATE_SOURCES = {
  collected: 'Collection date',
  reported: 'Report date',
  upload: 'Upload date',
}

const EVENT_LABELS = {
  newly_out_of_range: 'Moved outside the reference range',
  returned_to_range: 'Returned to the reference range',
  still_out_of_range: 'Remained outside the reference range',
  crossed_range_between_reports: 'Crossed the reference range between reports',
}

function formatEvent(event) {
  if (EVENT_LABELS[event]) return EVENT_LABELS[event]
  const text = String(event || '').replace(/_/g, ' ')
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text
}

function toneStyle(tone = 'neutral') {
  return TONES[tone] || TONES.neutral
}

function Pill({ tone = 'neutral', children }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold"
      style={toneStyle(tone)}
    >
      {children}
    </span>
  )
}

function DirectionPill({ direction }) {
  const meta = DIRECTIONS[direction] || DIRECTIONS.insufficient_data
  const Icon = meta.Icon
  return (
    <Pill tone={meta.tone}>
      <Icon size={12} />
      {meta.label}
    </Pill>
  )
}

function RangePill({ status }) {
  const meta = RANGE_STATUS[status] || RANGE_STATUS.unknown
  return <Pill tone={meta.tone}>{meta.label}</Pill>
}

function formatNumber(value, maximumFractionDigits = 2) {
  if (value == null || value === '') return '—'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  return numeric.toLocaleString(undefined, { maximumFractionDigits })
}

function formatValue(value, unit = '') {
  const rendered = formatNumber(value)
  return unit ? `${rendered} ${unit}` : rendered
}

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value))
  if (!match) return String(value)
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function formatChange(changePct, changeAbs, unit) {
  if (changePct == null && changeAbs == null) return 'No previous comparison'
  const parts = []
  if (changePct != null) {
    parts.push(`${changePct > 0 ? '+' : ''}${formatNumber(changePct)}%`)
  }
  if (changeAbs != null) {
    parts.push(`${changeAbs > 0 ? '+' : ''}${formatNumber(changeAbs)} ${unit}`)
  }
  return parts.join(' · ')
}

function sameOriginal(point) {
  return (
    point.edited_by_patient &&
    point.original_value != null &&
    Number(point.original_value) !== Number(point.value)
  )
}

function MetricCard({ label, value, detail }) {
  return (
    <div className="rounded-card border border-border bg-surface-2 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-foreground-subtle">{label}</p>
      <p className="mt-1.5 font-heading text-xl font-bold tabular-nums text-foreground">{value}</p>
      {detail && <p className="mt-0.5 text-xs text-foreground-muted">{detail}</p>}
    </div>
  )
}

function LoadingCards() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Loading health trends">
      {[0, 1, 2].map((item) => (
        <div key={item} className="h-48 animate-pulse rounded-card border border-border bg-surface-2" />
      ))}
    </div>
  )
}

function SummaryCard({ test, onOpen }) {
  const latestDate = formatDate(test.latest_date)
  const firstDate = formatDate(test.first_date)
  const eventCount = test.events?.length || 0
  return (
    <button
      type="button"
      onClick={() => onOpen(test.canonical_test)}
      className="group flex h-full flex-col rounded-card border border-border bg-surface p-5 text-left shadow-card transition hover:-translate-y-0.5 hover:border-foreground-subtle hover:shadow-dropdown"
      aria-label={`View ${test.display_name} trend`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate font-heading text-base font-bold text-foreground">{test.display_name}</h3>
          <p className="mt-0.5 text-xs text-foreground-muted">
            {test.point_count} report{test.point_count === 1 ? '' : 's'} · latest {latestDate}
          </p>
        </div>
        <DirectionPill direction={test.direction} />
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-2">
        <span className="font-heading text-3xl font-bold tabular-nums text-foreground">
          {formatNumber(test.latest_value)}
        </span>
        <span className="pb-1 text-sm font-medium text-foreground-muted">{test.unit}</span>
        <span className="pb-1">
          <RangePill status={test.range_status_latest} />
        </span>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-foreground-muted">
        {formatNumber(test.first_value)} on {firstDate}
        <span className="px-1.5 text-foreground-subtle">→</span>
        {formatNumber(test.latest_value)} on {latestDate}
      </p>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-border pt-3 text-xs">
        <span className="font-medium text-foreground-muted">
          {formatChange(test.change_pct, test.change_abs, test.unit)}
        </span>
        <span className="inline-flex items-center gap-1 font-semibold text-accent">
          {eventCount > 0 ? `${eventCount} event${eventCount === 1 ? '' : 's'}` : 'View details'}
          <ChevronRight size={14} className="transition group-hover:translate-x-0.5" />
        </span>
      </div>
    </button>
  )
}

function DataQuality({ detail }) {
  const notComparable = detail?.not_comparable || []
  const duplicateNotes = detail?.duplicate_notes || []
  if (notComparable.length === 0 && duplicateNotes.length === 0) return null

  return (
    <div className="mt-5 rounded-card border border-border bg-surface-2 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <Info size={16} className="text-foreground-muted" />
        Data quality notes
      </div>
      {duplicateNotes.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs leading-relaxed text-foreground-muted">
          {duplicateNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
      {notComparable.length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs font-semibold text-foreground-muted">
            {notComparable.length} value{notComparable.length === 1 ? '' : 's'} could not be compared
          </summary>
          <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-foreground-muted">
            {notComparable.map((item, index) => (
              <li key={`${item.report_id}-${index}`}>
                {formatDate(item.collected_on)}: {item.reason}
                {item.unit ? ` (${item.unit})` : ''}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

export default function HealthTrends() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const params = useParams()
  const isDoctor = user?.role === 'doctor'
  const canEdit = user?.role === 'patient'
  const patientId = isDoctor ? params.patientId : null
  const selectedTest = params.canonicalTest || null

  const [summary, setSummary] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [summaryError, setSummaryError] = useState('')

  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

  const [editingReportId, setEditingReportId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [savingId, setSavingId] = useState(null)
  const [actionError, setActionError] = useState('')

  const basePath = isDoctor
    ? `/doctor/trends/${encodeURIComponent(patientId || '')}`
    : '/patient/trends'

  const loadSummary = useCallback(async () => {
    if (isDoctor && !patientId) return
    setSummaryLoading(true)
    setSummaryError('')
    try {
      const data = await getTrendSummary(isDoctor ? patientId : null)
      setSummary(data)
    } catch (err) {
      setSummaryError(err.response?.data?.detail || 'Failed to load health trends')
    } finally {
      setSummaryLoading(false)
    }
  }, [isDoctor, patientId])

  useEffect(() => {
    loadSummary()
  }, [loadSummary])

  useEffect(() => {
    if (!selectedTest) {
      setDetail(null)
      setDetailError('')
      setDetailLoading(false)
      return undefined
    }

    let cancelled = false
    setDetailLoading(true)
    setDetailError('')
    setActionError('')
    setEditingReportId(null)

    getTrendDetail(selectedTest, isDoctor ? patientId : null)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        if (!cancelled) {
          setDetail(null)
          setDetailError(err.response?.data?.detail || 'Failed to load this trend')
        }
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [selectedTest, isDoctor, patientId])

  const selectOptions = useMemo(() => {
    const byCanonical = new Map()
    for (const item of summary?.tests || []) byCanonical.set(item.canonical_test, item)
    for (const item of summary?.insufficient_tests || []) byCanonical.set(item.canonical_test, item)
    if (detail && !byCanonical.has(detail.canonical_test)) {
      byCanonical.set(detail.canonical_test, detail)
    }
    return [...byCanonical.values()].sort((a, b) =>
      String(a.display_name || '').localeCompare(String(b.display_name || '')),
    )
  }, [summary, detail])

  const chartData = useMemo(
    () =>
      (detail?.points || []).map((point) => ({
        date: formatDate(point.collected_on),
        value: Number(point.value),
        source: point.date_source,
      })),
    [detail],
  )

  const openTest = (canonicalTest) => {
    navigate(`${basePath}/${encodeURIComponent(canonicalTest)}`)
  }

  const backToOverview = () => {
    navigate(basePath)
  }

  const handleSelectTest = (event) => {
    if (event.target.value) openTest(event.target.value)
    else backToOverview()
  }

  const beginEdit = (point) => {
    setActionError('')
    setEditingReportId(point.report_id)
    setEditValue(String(point.value))
  }

  const cancelEdit = () => {
    setEditingReportId(null)
    setEditValue('')
    setActionError('')
  }

  const applyUpdate = async (reportId, payload) => {
    setSavingId(reportId)
    setActionError('')
    try {
      const result = await updateTrendPoint(selectedTest, reportId, payload)
      setDetail(result.series)
      setEditingReportId(null)
      setEditValue('')
      loadSummary()
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Could not update this trend point')
    } finally {
      setSavingId(null)
    }
  }

  const saveCorrection = (point) => {
    const parsed = Number(editValue)
    if (editValue.trim() === '' || !Number.isFinite(parsed) || parsed < 0) {
      setActionError('Enter a valid non-negative number.')
      return
    }
    applyUpdate(point.report_id, { corrected_value: parsed })
  }

  const setExcluded = (point, excluded) => {
    applyUpdate(point.report_id, { excluded_by_patient: excluded })
  }

  const chartValues = chartData.map((point) => point.value).filter(Number.isFinite)
  const bounds = [detail?.ref_low, detail?.ref_high, ...chartValues].filter(
    (value) => typeof value === 'number' && Number.isFinite(value),
  )
  const yMin = bounds.length ? Math.min(...bounds) : 0
  const yMax = bounds.length ? Math.max(...bounds) : 1
  const yPad = (yMax - yMin) * 0.15 || Math.abs(yMax || 1) * 0.15
  const yDomain = [Math.max(0, yMin - yPad), yMax + yPad]
  const hasReferenceBand =
    typeof detail?.ref_low === 'number' && typeof detail?.ref_high === 'number'

  return (
    <div className="animate-fade-in mx-auto max-w-container">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-2.5 py-1 text-xs font-semibold text-accent">
            <Activity size={13} />
            Longitudinal analysis
          </div>
          <h1 className="font-heading text-2xl font-bold text-foreground md:text-3xl">Health Trends</h1>
          <p className="mt-1.5 max-w-2xl text-sm text-foreground-muted">
            Compare laboratory results across reports. Values are standardized and explanations are
            generated from the stored numbers only.
          </p>
        </div>
        {selectedTest ? (
          <button type="button" onClick={backToOverview} className="btn btn-secondary btn-sm">
            <ArrowLeft size={14} />
            All trends
          </button>
        ) : (
          <Link
            to={isDoctor ? '/doctor/patients' : '/patient/reports?upload=1'}
            className="btn btn-secondary btn-sm"
          >
            {isDoctor ? <ArrowLeft size={14} /> : <UploadCloud size={14} />}
            {isDoctor ? 'Patient directory' : 'Upload report'}
          </Link>
        )}
      </div>

      {isDoctor && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-2 px-4 py-3">
          <div className="flex items-center gap-2 text-sm text-foreground-muted">
            <ShieldCheck size={17} className="text-accent" />
            <span>
              Read-only clinical view for patient{' '}
              <span className="font-mono text-xs text-foreground">{patientId}</span>
            </span>
          </div>
          <Link to="/doctor/patients" className="text-xs font-semibold text-accent hover:underline">
            Back to patient directory
          </Link>
        </div>
      )}

      {summaryError && (
        <div className="alert-banner alert-banner-danger mb-5">
          <CircleAlert size={18} className="shrink-0" />
          <div>
            <strong>Could not load trends:</strong> {summaryError}
          </div>
        </div>
      )}

      {!selectedTest && (
        <div>
          {summaryLoading && <LoadingCards />}

          {!summaryLoading && !summaryError && summary && (
            <>
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 className="font-heading text-lg font-bold text-foreground">Tests with trends</h2>
                  <p className="text-xs text-foreground-muted">
                    At least two comparable reports are needed to describe a trend.
                  </p>
                </div>
                <span className="badge badge-neutral">
                  {summary.test_count} test{summary.test_count === 1 ? '' : 's'}
                </span>
              </div>

              {(summary.tests || []).length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {summary.tests.map((test) => (
                    <SummaryCard key={test.canonical_test} test={test} onOpen={openTest} />
                  ))}
                </div>
              ) : (
                <div className="rounded-card border border-dashed border-border bg-surface p-10 text-center">
                  <FlaskConical size={34} className="mx-auto text-foreground-subtle" />
                  <h3 className="mt-3 font-heading text-base font-bold text-foreground">
                    No comparable lab trends yet
                  </h3>
                  <p className="mx-auto mt-1 max-w-md text-sm text-foreground-muted">
                    Upload at least two reports containing the same lab test to see a trend.
                  </p>
                  {!isDoctor && (
                    <Link to="/patient/reports?upload=1" className="btn btn-primary btn-sm mt-4">
                      <UploadCloud size={14} />
                      Upload a report
                    </Link>
                  )}
                </div>
              )}

              {(summary.insufficient_tests || []).length > 0 && (
                <div className="mt-6 rounded-card border border-border bg-surface p-5 shadow-card">
                  <div className="flex items-center gap-2">
                    <Sparkles size={17} className="text-accent" />
                    <h3 className="font-heading text-base font-bold text-foreground">
                      Not enough history yet
                    </h3>
                  </div>
                  <p className="mt-1 text-xs text-foreground-muted">
                    These tests have only one comparable result.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(summary.insufficient_tests || []).map((test) => (
                      <button
                        key={test.canonical_test}
                        type="button"
                        onClick={() => openTest(test.canonical_test)}
                        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1 text-xs font-medium text-foreground-muted transition hover:border-foreground-subtle hover:text-foreground"
                      >
                        {test.display_name}
                        <span className="tabular-nums text-foreground-subtle">
                          {formatValue(test.latest_value, test.unit)}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {((summary.not_comparable || []).length > 0 ||
                (summary.duplicate_notes || []).length > 0) && (
                <div className="mt-6 rounded-card border border-border bg-surface-2 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <Info size={16} className="text-foreground-muted" />
                    Data quality notes
                  </div>
                  {(summary.duplicate_notes || []).map((note) => (
                    <p key={note} className="mt-1.5 text-xs text-foreground-muted">
                      {note}
                    </p>
                  ))}
                  {(summary.not_comparable || []).length > 0 && (
                    <p className="mt-1.5 text-xs text-foreground-muted">
                      {(summary.not_comparable || []).length} stored value
                      {(summary.not_comparable || []).length === 1 ? '' : 's'} could not be compared
                      because the unit was missing or unsupported.
                    </p>
                  )}
                </div>
              )}

              <p className="mt-6 text-xs leading-relaxed text-foreground-subtle">{DISCLAIMER}</p>
            </>
          )}
        </div>
      )}

      {selectedTest && (
        <div>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-heading text-lg font-bold text-foreground">
                {detail?.display_name || selectedTest.replace(/_/g, ' ')}
              </h2>
              <p className="text-xs text-foreground-muted">
                {detail?.point_count
                  ? `${detail.point_count} comparable report${detail.point_count === 1 ? '' : 's'}`
                  : 'No comparable values yet'}
                {detail?.days_between != null ? ` · ${detail.days_between} days between reports` : ''}
              </p>
            </div>
            <label className="flex items-center gap-2 text-xs font-semibold text-foreground-muted">
              Test
              <select
                value={selectedTest}
                onChange={handleSelectTest}
                className="rounded-item border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground"
                aria-label="Select lab test"
              >
                <option value="">All trends</option>
                {selectOptions.map((option) => (
                  <option key={option.canonical_test} value={option.canonical_test}>
                    {option.display_name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {detailLoading && (
            <div className="rounded-card border border-border bg-surface p-8 text-center">
              <div className="loading-spinner mx-auto" />
              <p className="mt-3 text-sm text-foreground-muted">Loading trend...</p>
            </div>
          )}

          {detailError && (
            <div className="alert-banner alert-banner-danger">
              <CircleAlert size={18} className="shrink-0" />
              <div>
                <strong>Could not load this trend:</strong> {detailError}
              </div>
            </div>
          )}

          {actionError && (
            <div className="alert-banner alert-banner-danger mb-4">
              <CircleAlert size={18} className="shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          {!detailLoading && !detailError && detail && (
            <div className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  label="Latest"
                  value={formatValue(detail.latest?.value, detail.unit)}
                  detail={formatDate(detail.latest?.collected_on)}
                />
                <MetricCard
                  label="Previous"
                  value={
                    detail.previous ? formatValue(detail.previous.value, detail.unit) : 'No previous value'
                  }
                  detail={detail.previous ? formatDate(detail.previous.collected_on) : undefined}
                />
                <MetricCard
                  label="Change vs previous"
                  value={formatChange(detail.change_pct, detail.change_abs, detail.unit)}
                />
                <MetricCard
                  label="Latest range status"
                  value={
                    (RANGE_STATUS[detail.range_status_latest] || RANGE_STATUS.unknown).label
                  }
                  detail={
                    hasReferenceBand
                      ? `${formatNumber(detail.ref_low)} – ${formatNumber(detail.ref_high)} ${detail.unit}`
                      : 'Reference range unavailable'
                  }
                />
              </div>

              <div className="rounded-card border border-border bg-surface p-5 shadow-card">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">Trend chart</h3>
                    <p className="text-xs text-foreground-muted">
                      Shaded band shows the latest available reference range.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <DirectionPill direction={detail.direction} />
                    <RangePill status={detail.range_status_latest} />
                  </div>
                </div>

                {chartData.length >= 2 ? (
                  <>
                    <div className="h-80 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                          <XAxis
                            dataKey="date"
                            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                            stroke="var(--border)"
                            tickMargin={8}
                          />
                          <YAxis
                            domain={yDomain}
                            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                            stroke="var(--border)"
                            width={58}
                          />
                          <Tooltip
                            contentStyle={{
                              background: 'var(--surface)',
                              border: '1px solid var(--border)',
                              borderRadius: 12,
                              color: 'var(--text)',
                              boxShadow: 'var(--shadow-dropdown)',
                            }}
                            labelStyle={{ color: 'var(--text-muted)' }}
                            itemStyle={{ color: 'var(--text)' }}
                            formatter={(value) => [
                              `${formatNumber(value)} ${detail.unit}`,
                              detail.display_name,
                            ]}
                          />
                          {hasReferenceBand && (
                            <ReferenceArea
                              y1={detail.ref_low}
                              y2={detail.ref_high}
                              fill="var(--success-border)"
                              fillOpacity={0.22}
                            />
                          )}
                          <Line
                            type="monotone"
                            dataKey="value"
                            stroke="var(--accent)"
                            strokeWidth={2.5}
                            dot={{ r: 4, strokeWidth: 2, fill: 'var(--surface)' }}
                            activeDot={{ r: 6 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="mt-3 text-xs text-foreground-subtle">
                      Dates use the collection date printed on the report. When that is missing, the
                      reported or upload date is used.
                    </p>
                  </>
                ) : (
                  <div className="rounded-card border border-dashed border-border bg-surface-2 p-8 text-center">
                    <TrendingUp size={30} className="mx-auto text-foreground-subtle" />
                    <p className="mt-2 text-sm font-semibold text-foreground">Not enough data for a chart</p>
                    <p className="mt-1 text-xs text-foreground-muted">
                      {detail.point_count === 1
                        ? 'One comparable result is available. At least two are needed to draw a trend.'
                        : 'No comparable results are available yet.'}
                    </p>
                  </div>
                )}
              </div>

              <div className="rounded-card border border-border bg-surface p-5 shadow-card">
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles size={17} className="text-accent" />
                  <h3 className="font-heading text-base font-bold text-foreground">
                    Plain-language summary
                  </h3>
                </div>
                <p className="text-sm leading-relaxed text-foreground-muted">{detail.explanation}</p>

                {(detail.events || []).length > 0 && (
                  <div className="mt-4 border-t border-border pt-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-foreground-subtle">
                      Range events
                    </h4>
                    <ul className="mt-2 space-y-1.5">
                      {(detail.events || []).map((event) => (
                        <li
                          key={formatEvent(event)}
                          className="flex items-start gap-2 text-sm leading-relaxed text-foreground-muted"
                        >
                          <ArrowUpRight size={14} className="mt-1 shrink-0 text-accent" />
                          <span>{formatEvent(event)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="rounded-card border border-border bg-surface p-5 shadow-card">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="font-heading text-base font-bold text-foreground">Report values</h3>
                    <p className="text-xs text-foreground-muted">
                      {canEdit
                        ? 'You can exclude a value or correct a transcription error. Corrections affect this trend only.'
                        : 'Values shown in the standardized unit for this test.'}
                    </p>
                  </div>
                  <span className="badge badge-neutral">{detail.point_count} point{detail.point_count === 1 ? '' : 's'}</span>
                </div>

                {(detail.points || []).length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm" aria-label={`${detail.display_name} trend values`}>
                      <thead>
                        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-foreground-subtle">
                          <th className="px-2 py-2 font-semibold">Date</th>
                          <th className="px-2 py-2 font-semibold">Value</th>
                          <th className="px-2 py-2 font-semibold">Reference range</th>
                          <th className="px-2 py-2 font-semibold">Status</th>
                          {canEdit && <th className="px-2 py-2 text-right font-semibold">Actions</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {(detail.points || []).map((point) => (
                          <Fragment key={point.report_id}>
                            <tr className="border-b border-border last:border-0">
                              <td className="px-2 py-3">
                                <div className="font-medium text-foreground">
                                  {formatDate(point.collected_on)}
                                </div>
                                <div className="text-xs text-foreground-subtle">
                                  {DATE_SOURCES[point.date_source] || 'Report date'}
                                </div>
                              </td>
                              <td className="px-2 py-3">
                                <div className="font-semibold tabular-nums text-foreground">
                                  {formatValue(point.value, detail.unit)}
                                </div>
                                {sameOriginal(point) && (
                                  <div className="text-xs text-foreground-subtle">
                                    Original: {formatValue(point.original_value, point.original_unit)}
                                  </div>
                                )}
                                {point.edited_by_patient && (
                                  <div className="mt-0.5 inline-flex items-center gap-1 text-xs font-medium text-accent">
                                    <Pencil size={11} /> Corrected by you
                                  </div>
                                )}
                              </td>
                              <td className="px-2 py-3 tabular-nums text-foreground-muted">
                                {point.ref_low != null && point.ref_high != null
                                  ? `${formatNumber(point.ref_low)} – ${formatNumber(point.ref_high)} ${detail.unit}`
                                  : 'Not available'}
                              </td>
                              <td className="px-2 py-3">
                                <RangePill status={point.flag} />
                              </td>
                              {canEdit && (
                                <td className="px-2 py-3">
                                  <div className="flex justify-end gap-1.5">
                                    <button
                                      type="button"
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => beginEdit(point)}
                                      disabled={savingId === point.report_id}
                                    >
                                      <Pencil size={12} />
                                      Correct
                                    </button>
                                    <button
                                      type="button"
                                      className="btn btn-ghost btn-sm"
                                      onClick={() => setExcluded(point, true)}
                                      disabled={savingId === point.report_id}
                                      title="Exclude this value from your trend"
                                    >
                                      <X size={13} />
                                      Exclude
                                    </button>
                                  </div>
                                </td>
                              )}
                            </tr>
                            {canEdit && editingReportId === point.report_id && (
                              <tr className="border-b border-border bg-surface-2">
                                <td colSpan={5} className="px-2 py-3">
                                  <form
                                    className="flex flex-wrap items-end gap-2"
                                    onSubmit={(event) => {
                                      event.preventDefault()
                                      saveCorrection(point)
                                    }}
                                  >
                                    <label className="text-xs font-semibold text-foreground-muted">
                                      Corrected value ({detail.unit})
                                      <input
                                        type="number"
                                        step="any"
                                        min="0"
                                        value={editValue}
                                        onChange={(event) => setEditValue(event.target.value)}
                                        className="mt-1 block w-40 rounded-item border border-border bg-surface px-3 py-2 text-sm text-foreground"
                                        autoFocus
                                      />
                                    </label>
                                    <button
                                      type="submit"
                                      className="btn btn-primary btn-sm"
                                      disabled={savingId === point.report_id}
                                    >
                                      {savingId === point.report_id ? 'Saving...' : 'Save correction'}
                                    </button>
                                    <button
                                      type="button"
                                      className="btn btn-ghost btn-sm"
                                      onClick={cancelEdit}
                                      disabled={savingId === point.report_id}
                                    >
                                      Cancel
                                    </button>
                                  </form>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-state">
                    <FlaskConical size={30} />
                    <p className="font-semibold text-foreground">No comparable values</p>
                    <p className="text-xs text-foreground-muted">
                      Missing or unsupported units are listed in the data quality notes.
                    </p>
                  </div>
                )}

                {(detail.excluded_points || []).length > 0 && (
                  <div className="mt-4 border-t border-border pt-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-foreground-subtle">
                      Excluded by you
                    </h4>
                    <div className="mt-2 space-y-2">
                      {(detail.excluded_points || []).map((point) => (
                        <div
                          key={point.report_id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-item border border-border bg-surface-2 px-3 py-2"
                        >
                          <span className="text-sm text-foreground-muted">
                            {formatDate(point.collected_on)} ·{' '}
                            <span className="font-semibold tabular-nums text-foreground">
                              {formatValue(point.value, detail.unit)}
                            </span>
                          </span>
                          {canEdit && (
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => setExcluded(point, false)}
                              disabled={savingId === point.report_id}
                            >
                              <RotateCcw size={12} />
                              Restore
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <DataQuality detail={detail} />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-foreground-subtle">{DISCLAIMER}</p>
                <button
                  type="button"
                  onClick={() => {
                    loadSummary()
                    if (selectedTest) {
                      getTrendDetail(selectedTest, isDoctor ? patientId : null)
                        .then(setDetail)
                        .catch(() => {})
                    }
                  }}
                  className="btn btn-ghost btn-sm"
                >
                  <RefreshCw size={13} />
                  Refresh
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
