import {
  getLightState,
  turnOn, turnOff, toggleLight,
  setBrightness, setColorXY,
  getMatterNodes, removeNode,
  setWifiCredentials, commissionDevice,
} from '../api/matter'
import request from '../api/client'

vi.mock('../api/client', () => ({ default: vi.fn() }))

beforeEach(() => { request.mockResolvedValue({}) })
afterEach(() => { vi.clearAllMocks() })

// -- getLightState -------------------------------------------------------------

describe('getLightState', () => {
  it('calls the live state endpoint for the given node_id', async () => {
    await getLightState(1)
    expect(request).toHaveBeenCalledWith('/api/matter/nodes/1/state/live')
  })
})

// -- turnOn / turnOff / toggleLight --------------------------------------------

describe('turnOn', () => {
  it('calls the on endpoint with POST', async () => {
    await turnOn(1)
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/nodes/1/on')
    expect(options.method).toBe('POST')
  })
})

describe('turnOff', () => {
  it('calls the off endpoint with POST', async () => {
    await turnOff(1)
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/nodes/1/off')
    expect(options.method).toBe('POST')
  })
})

describe('toggleLight', () => {
  it('calls the toggle endpoint with POST', async () => {
    await toggleLight(1)
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/nodes/1/toggle')
    expect(options.method).toBe('POST')
  })
})

// -- setBrightness -------------------------------------------------------------

describe('setBrightness', () => {
  it('calls the brightness endpoint with POST', async () => {
    await setBrightness(1, 128)
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/nodes/1/brightness')
    expect(options.method).toBe('POST')
  })

  it('sends level in the request body', async () => {
    await setBrightness(1, 200)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.level).toBe(200)
  })

  it('defaults transition_time to 0', async () => {
    await setBrightness(1, 128)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.transition_time).toBe(0)
  })

  it('sends a custom transition_time when provided', async () => {
    await setBrightness(1, 128, 10)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.transition_time).toBe(10)
  })
})

// -- setColorXY ----------------------------------------------------------------

describe('setColorXY', () => {
  it('calls the color endpoint with POST', async () => {
    await setColorXY(1, 0.7, 0.3)
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/nodes/1/color/xy')
    expect(options.method).toBe('POST')
  })

  it('sends x and y in the request body', async () => {
    await setColorXY(1, 0.7, 0.3)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.x).toBe(0.7)
    expect(body.y).toBe(0.3)
  })

  it('defaults transition_time to 0', async () => {
    await setColorXY(1, 0.5, 0.4)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.transition_time).toBe(0)
  })

  it('sends a custom transition_time when provided', async () => {
    await setColorXY(1, 0.5, 0.4, 5)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.transition_time).toBe(5)
  })
})

// -- getMatterNodes / removeNode -----------------------------------------------

describe('getMatterNodes', () => {
  it('calls the nodes endpoint', async () => {
    await getMatterNodes()
    expect(request).toHaveBeenCalledWith('/api/matter/nodes')
  })
})

describe('removeNode', () => {
  it('calls the correct node endpoint with DELETE', async () => {
    await removeNode(3)
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/nodes/3')
    expect(options.method).toBe('DELETE')
  })

  it('uses the correct node_id in the URL', async () => {
    await removeNode(99)
    expect(request).toHaveBeenCalledWith('/api/matter/nodes/99', expect.any(Object))
  })
})

// -- setWifiCredentials --------------------------------------------------------

describe('setWifiCredentials', () => {
  it('calls the wifi endpoint with POST', async () => {
    await setWifiCredentials('MyNet', 'pass123')
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/wifi')
    expect(options.method).toBe('POST')
  })

  it('sends ssid and password in the request body', async () => {
    await setWifiCredentials('MyNet', 'pass123')
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.ssid).toBe('MyNet')
    expect(body.password).toBe('pass123')
  })
})

// -- commissionDevice ----------------------------------------------------------

describe('commissionDevice', () => {
  it('calls the commission endpoint with POST', async () => {
    await commissionDevice('MT:Y.ABC1')
    const [url, options] = request.mock.calls[0]
    expect(url).toBe('/api/matter/commission')
    expect(options.method).toBe('POST')
  })

  it('sends the pairing code in the request body', async () => {
    await commissionDevice('MT:Y.ABC1')
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.code).toBe('MT:Y.ABC1')
  })

  it('defaults node_id to null and network_only to false', async () => {
    await commissionDevice('MT:Y.ABC1')
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.node_id).toBeNull()
    expect(body.network_only).toBe(false)
  })

  it('sends a custom node_id when provided', async () => {
    await commissionDevice('MT:Y.ABC1', 5)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.node_id).toBe(5)
  })

  it('sends network_only when provided', async () => {
    await commissionDevice('MT:Y.ABC1', null, true)
    const body = JSON.parse(request.mock.calls[0][1].body)
    expect(body.network_only).toBe(true)
  })
})
