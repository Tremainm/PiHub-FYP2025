import request from '../api/client'

// -- request -------------------------------------------------------------------

describe('request', () => {
  let mockFetch

  beforeEach(() => {
    mockFetch = vi.fn()
    vi.stubGlobal('fetch', mockFetch)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls fetch with the correct full URL', async () => {
    mockFetch.mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({}),
    })
    await request('/health')
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/health',
      expect.any(Object)
    )
  })

  it('includes Content-Type application/json header by default', async () => {
    mockFetch.mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({}),
    })
    await request('/health')
    const options = mockFetch.mock.calls[0][1]
    expect(options.headers['Content-Type']).toBe('application/json')
  })

  it('returns parsed JSON for a 200 response', async () => {
    const data = [{ id: 1, name: 'Lamp' }]
    mockFetch.mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue(data),
    })
    const result = await request('/api/devices')
    expect(result).toEqual(data)
  })

  it('returns null for a 204 No Content response', async () => {
    mockFetch.mockResolvedValue({
      ok: true, status: 204,
      json: vi.fn(),
    })
    const result = await request('/api/devices/1', { method: 'DELETE' })
    expect(result).toBeNull()
  })

  it('merges method and body options into the fetch call', async () => {
    mockFetch.mockResolvedValue({
      ok: true, status: 201,
      json: vi.fn().mockResolvedValue({ id: 1 }),
    })
    const body = JSON.stringify({ node_id: 1, name: 'Lamp' })
    await request('/api/devices', { method: 'POST', body })
    const options = mockFetch.mock.calls[0][1]
    expect(options.method).toBe('POST')
    expect(options.body).toBe(body)
  })

  it('throws with the detail message from the response body on non-ok', async () => {
    mockFetch.mockResolvedValue({
      ok: false, status: 409,
      json: vi.fn().mockResolvedValue({ detail: 'Node 1 is already registered.' }),
    })
    await expect(request('/api/devices')).rejects.toThrow('Node 1 is already registered.')
  })

  it('throws a fallback message when non-ok response has no detail field', async () => {
    mockFetch.mockResolvedValue({
      ok: false, status: 500,
      json: vi.fn().mockResolvedValue({}),
    })
    await expect(request('/api/devices')).rejects.toThrow('Request failed: 500')
  })

  it('throws a fallback message when non-ok response body is not valid JSON', async () => {
    mockFetch.mockResolvedValue({
      ok: false, status: 503,
      json: vi.fn().mockRejectedValue(new Error('invalid json')),
    })
    await expect(request('/api/devices')).rejects.toThrow('Request failed: 503')
  })

  it('uses the correct node_id in a parameterised URL', async () => {
    mockFetch.mockResolvedValue({
      ok: true, status: 200,
      json: vi.fn().mockResolvedValue({}),
    })
    await request('/api/matter/nodes/42/sensors/live')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/42/'),
      expect.any(Object)
    )
  })
})
