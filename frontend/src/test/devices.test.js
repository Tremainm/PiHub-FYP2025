import { getDevices, registerDevice, unregisterDevice } from '../api/devices'
import request from '../api/client'

vi.mock('../api/client', () => ({ default: vi.fn() }))

beforeEach(() => { request.mockResolvedValue({}) })
afterEach(() => { vi.clearAllMocks() })

// -- getDevices ----------------------------------------------------------------

describe('getDevices', () => {
  it('calls the devices endpoint', async () => {
    await getDevices()
    expect(request).toHaveBeenCalledWith('/api/devices')
  })
})

// -- registerDevice ------------------------------------------------------------

describe('registerDevice', () => {
  it('calls the devices endpoint with POST', async () => {
    await registerDevice(1, 'Living Room')
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/devices')
    expect(options.method).toBe('POST')
  })

  it('sends node_id and name in the request body', async () => {
    await registerDevice(1, 'Living Room')
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.node_id).toBe(1)
    expect(body.name).toBe('Living Room')
  })

  it('uses the correct node_id in the body', async () => {
    await registerDevice(42, 'Bedroom')
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.node_id).toBe(42)
  })
})

// -- unregisterDevice ----------------------------------------------------------

describe('unregisterDevice', () => {
  it('calls the correct URL with the node_id', async () => {
    await unregisterDevice(3)
    expect(request).toHaveBeenCalledWith('/api/devices/3', expect.any(Object))
  })

  it('uses DELETE method', async () => {
    await unregisterDevice(3)
    expect(request.mock.calls[0][1].method).toBe('DELETE')
  })

  it('uses the correct node_id in the URL', async () => {
    await unregisterDevice(99)
    expect(request).toHaveBeenCalledWith('/api/devices/99', expect.any(Object))
  })
})
