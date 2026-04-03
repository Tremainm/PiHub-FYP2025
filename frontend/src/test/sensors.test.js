import { getSensorLive, getSensorHistory } from '../api/sensors'
import request from '../api/client'

vi.mock('../api/client', () => ({ default: vi.fn() }))

// -- getSensorLive -------------------------------------------------------------

describe('getSensorLive', () => {
  beforeEach(() => { request.mockResolvedValue({}) })
  afterEach(() => { vi.clearAllMocks() })

  it('calls the live sensors endpoint for the given node_id', async () => {
    await getSensorLive(1)
    expect(request).toHaveBeenCalledWith('/api/matter/nodes/1/sensors/live')
  })

  it('uses the correct node_id in the URL', async () => {
    await getSensorLive(42)
    expect(request).toHaveBeenCalledWith('/api/matter/nodes/42/sensors/live')
  })
})

// -- getSensorHistory ----------------------------------------------------------

describe('getSensorHistory', () => {
  beforeEach(() => { request.mockResolvedValue([]) })
  afterEach(() => { vi.clearAllMocks() })

  it('calls the history endpoint for the given node_id', async () => {
    await getSensorHistory(1)
    expect(request).toHaveBeenCalledWith(expect.stringContaining('/api/sensors/1/history'))
  })

  it('includes a default limit of 100 when no options are given', async () => {
    await getSensorHistory(1)
    expect(request).toHaveBeenCalledWith(expect.stringContaining('limit=100'))
  })

  it('uses a custom limit when provided', async () => {
    await getSensorHistory(1, { limit: 50 })
    expect(request).toHaveBeenCalledWith(expect.stringContaining('limit=50'))
  })

  it('includes sensor_type in the URL when provided', async () => {
    await getSensorHistory(1, { sensor_type: 'temperature_c' })
    expect(request).toHaveBeenCalledWith(expect.stringContaining('sensor_type=temperature_c'))
  })

  it('omits sensor_type from the URL when not provided', async () => {
    await getSensorHistory(1)
    const url = request.mock.calls[0][0]
    expect(url).not.toContain('sensor_type')
  })

  it('includes both sensor_type and limit together', async () => {
    await getSensorHistory(1, { sensor_type: 'humidity_rh', limit: 200 })
    const url = request.mock.calls[0][0]
    expect(url).toContain('humidity_rh')
    expect(url).toContain('limit=200')
  })

  it('uses the correct node_id in the URL', async () => {
    await getSensorHistory(7)
    expect(request).toHaveBeenCalledWith(expect.stringContaining('/api/sensors/7/history'))
  })
})
