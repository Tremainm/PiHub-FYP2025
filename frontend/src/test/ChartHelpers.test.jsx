import { render, screen } from '@testing-library/react'
import { formatTimestamp, ChartTooltip } from '../components/ChartHelpers'

// -- formatTimestamp -----------------------------------------------------------

describe('formatTimestamp', () => {
  beforeEach(() => {
    // Fix "now" to a known point: Monday 15 Jan 2024, 12:00 UTC
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns a time string (contains colons) for a timestamp from today', () => {
    const result = formatTimestamp('2024-01-15T10:30:00Z')
    expect(result).toMatch(/:/)
    expect(result).not.toContain('Yesterday')
  })

  it('does not include a date prefix for today', () => {
    const result = formatTimestamp('2024-01-15T08:00:00Z')
    // Today format is time-only - no "Yesterday", no month name, no day name prefix
    expect(result).not.toMatch(/^Yesterday/)
    expect(result).not.toMatch(/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)/)
  })

  it('starts with "Yesterday" for a timestamp from yesterday', () => {
    const result = formatTimestamp('2024-01-14T10:30:00Z')
    expect(result).toMatch(/^Yesterday/)
  })

  it('includes a time component after "Yesterday"', () => {
    const result = formatTimestamp('2024-01-14T10:30:00Z')
    expect(result).toMatch(/^Yesterday .+:/)
  })

  it('returns a short day name for a date within the past week', () => {
    // 2024-01-10 is 5 days before 2024-01-15 - within the 7-day window
    const result = formatTimestamp('2024-01-10T10:30:00Z')
    expect(result).not.toMatch(/^Yesterday/)
    // Should start with a 3-letter weekday abbreviation followed by a space
    expect(result).toMatch(/^\w{3} /)
  })

  it('returns a date string for timestamps older than a week', () => {
    // 2024-01-01 is 14 days before 2024-01-15 - outside the 7-day window
    const result = formatTimestamp('2024-01-01T10:30:00Z')
    expect(result).not.toMatch(/^Yesterday/)
    expect(result).not.toMatch(/^\w{3} \d{2}:/)  // not the "this week" format
    expect(result).toBeTruthy()
  })

  it('handles timestamps far in the past', () => {
    const result = formatTimestamp('2020-06-15T09:00:00Z')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})

// -- ChartTooltip --------------------------------------------------------------

describe('ChartTooltip', () => {
  it('renders nothing when active is false', () => {
    const { container } = render(
      <ChartTooltip active={false} payload={[{ dataKey: 'temp', value: 21.5, color: 'red' }]} label="10:00" unit="°C" />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when payload is empty', () => {
    const { container } = render(
      <ChartTooltip active={true} payload={[]} label="10:00" unit="°C" />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when payload is undefined', () => {
    const { container } = render(
      <ChartTooltip active={true} payload={undefined} label="10:00" unit="°C" />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders the label when active with payload', () => {
    render(
      <ChartTooltip
        active={true}
        payload={[{ dataKey: 'temp', value: 21.5, color: '#ff0000' }]}
        label="10:30:00"
        unit="°C"
      />
    )
    expect(screen.getByText('10:30:00')).toBeInTheDocument()
  })

  it('renders the value rounded to 2 decimal places', () => {
    render(
      <ChartTooltip
        active={true}
        payload={[{ dataKey: 'temp', value: 21.5678, color: '#ff0000' }]}
        label="10:30:00"
        unit="°C"
      />
    )
    expect(screen.getByText(/21\.57/)).toBeInTheDocument()
  })

  it('renders the unit alongside the value', () => {
    render(
      <ChartTooltip
        active={true}
        payload={[{ dataKey: 'humidity', value: 55.0, color: '#0000ff' }]}
        label="10:30:00"
        unit="%RH"
      />
    )
    expect(screen.getByText(/55\.00.*%RH/)).toBeInTheDocument()
  })

  it('renders one row per payload entry', () => {
    render(
      <ChartTooltip
        active={true}
        payload={[
          { dataKey: 'temp', value: 21.5, color: '#ff0000' },
          { dataKey: 'humidity', value: 55.0, color: '#0000ff' },
        ]}
        label="10:30:00"
        unit="°C"
      />
    )
    expect(screen.getByText(/21\.50/)).toBeInTheDocument()
    expect(screen.getByText(/55\.00/)).toBeInTheDocument()
  })
})
