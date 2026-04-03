import { renderHook, act } from '@testing-library/react'
import { useLedState } from '../hooks/useLedState'
import { getLightState, toggleLight, setBrightness, setColorXY } from '../api/matter'

vi.mock('../api/matter', () => ({
  getLightState: vi.fn(),
  toggleLight:   vi.fn(),
  setBrightness: vi.fn(),
  setColorXY:    vi.fn(),
}))

beforeEach(() => {
  getLightState.mockResolvedValue(null)
  toggleLight.mockResolvedValue({})
  setBrightness.mockResolvedValue({})
  setColorXY.mockResolvedValue({})
  vi.useFakeTimers()
})

afterEach(() => {
  vi.clearAllMocks()
  vi.useRealTimers()
})

// -- Initial state -------------------------------------------------------------

describe('initial state', () => {
  it('defaults isOn to false', () => {
    const { result } = renderHook(() => useLedState(1))
    expect(result.current.isOn).toBe(false)
  })

  it('defaults brightness to 128', () => {
    const { result } = renderHook(() => useLedState(1))
    expect(result.current.brightness).toBe(128)
  })

  it('defaults colorHex to #ffaa44', () => {
    const { result } = renderHook(() => useLedState(1))
    expect(result.current.colorHex).toBe('#ffaa44')
  })
})

// -- syncFromCache (mount) -----------------------------------------------------

describe('syncFromCache', () => {
  it('calls getLightState with the nodeId on mount', async () => {
    renderHook(() => useLedState(5))
    await act(async () => { await Promise.resolve() })
    expect(getLightState).toHaveBeenCalledWith(5)
  })

  it('updates isOn from the API response', async () => {
    getLightState.mockResolvedValue({ on: true, brightness: null })
    const { result } = renderHook(() => useLedState(1))
    await act(async () => { await Promise.resolve() })
    expect(result.current.isOn).toBe(true)
  })

  it('updates brightness from the API response', async () => {
    getLightState.mockResolvedValue({ on: null, brightness: 200 })
    const { result } = renderHook(() => useLedState(1))
    await act(async () => { await Promise.resolve() })
    expect(result.current.brightness).toBe(200)
  })

  it('updates colorHex from color_xy when user has not set a color', async () => {
    getLightState.mockResolvedValue({ on: null, brightness: null, color_xy: { x: 0.3127, y: 0.3290 } })
    const { result } = renderHook(() => useLedState(1))
    await act(async () => { await Promise.resolve() })
    // xyToHex round-trip will produce some hex string - just verify it changed
    expect(result.current.colorHex).not.toBe('#ffaa44')
  })

  it('does not crash when getLightState rejects', async () => {
    getLightState.mockRejectedValue(new Error('network error'))
    const { result } = renderHook(() => useLedState(1))
    await act(async () => { await Promise.resolve() })
    // state should stay at defaults
    expect(result.current.isOn).toBe(false)
  })

  it('polls getLightState again after POLL_INTERVAL', async () => {
    renderHook(() => useLedState(1))
    await act(async () => { await Promise.resolve() })
    const callsAfterMount = getLightState.mock.calls.length

    await act(async () => {
      vi.advanceTimersByTime(4000)
      await Promise.resolve()
    })

    expect(getLightState.mock.calls.length).toBeGreaterThan(callsAfterMount)
  })
})

// -- toggle -------------------------------------------------------------------

describe('toggle', () => {
  it('optimistically flips isOn from false to true', async () => {
    const { result } = renderHook(() => useLedState(1))
    await act(async () => { result.current.toggle() })
    expect(result.current.isOn).toBe(true)
  })

  it('calls toggleLight with the nodeId', async () => {
    const { result } = renderHook(() => useLedState(1))
    await act(async () => { result.current.toggle() })
    expect(toggleLight).toHaveBeenCalledWith(1)
  })

  it('reverts isOn when toggleLight rejects', async () => {
    toggleLight.mockRejectedValue(new Error('toggle failed'))
    const { result } = renderHook(() => useLedState(1))
    await act(async () => { result.current.toggle() })
    expect(result.current.isOn).toBe(false)
  })
})

// -- changeBrightness ---------------------------------------------------------

describe('changeBrightness', () => {
  it('immediately updates brightness state', async () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => { result.current.changeBrightness(200) })
    expect(result.current.brightness).toBe(200)
  })

  it('does not call setBrightness API before the 300ms debounce', async () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => { result.current.changeBrightness(200) })
    await act(async () => { vi.advanceTimersByTime(299) })
    expect(setBrightness).not.toHaveBeenCalled()
  })

  it('calls setBrightness API after the 300ms debounce', async () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => { result.current.changeBrightness(200) })
    await act(async () => {
      vi.advanceTimersByTime(300)
      await Promise.resolve()
    })
    expect(setBrightness).toHaveBeenCalledWith(1, 200)
  })

  it('debounces multiple rapid calls into one API call', async () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => {
      result.current.changeBrightness(100)
      result.current.changeBrightness(150)
      result.current.changeBrightness(200)
    })
    await act(async () => {
      vi.advanceTimersByTime(300)
      await Promise.resolve()
    })
    expect(setBrightness).toHaveBeenCalledTimes(1)
    expect(setBrightness).toHaveBeenCalledWith(1, 200)
  })
})

// -- changeColor --------------------------------------------------------------

describe('changeColor', () => {
  it('immediately updates colorHex state', () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => { result.current.changeColor('#ff0000') })
    expect(result.current.colorHex).toBe('#ff0000')
  })

  it('does not call setColorXY API before the 300ms debounce', async () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => { result.current.changeColor('#ff0000') })
    await act(async () => { vi.advanceTimersByTime(299) })
    expect(setColorXY).not.toHaveBeenCalled()
  })

  it('calls setColorXY API after the 300ms debounce', async () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => { result.current.changeColor('#ff0000') })
    await act(async () => {
      vi.advanceTimersByTime(300)
      await Promise.resolve()
    })
    expect(setColorXY).toHaveBeenCalledWith(1, expect.any(Number), expect.any(Number))
  })

  it('debounces multiple rapid calls into one API call', async () => {
    const { result } = renderHook(() => useLedState(1))
    act(() => {
      result.current.changeColor('#ff0000')
      result.current.changeColor('#00ff00')
      result.current.changeColor('#0000ff')
    })
    await act(async () => {
      vi.advanceTimersByTime(300)
      await Promise.resolve()
    })
    expect(setColorXY).toHaveBeenCalledTimes(1)
  })

  it('prevents syncFromCache from overwriting a user-set color', async () => {
    getLightState.mockResolvedValue({
      on: null, brightness: null,
      color_xy: { x: 0.3127, y: 0.3290 },
    })
    const { result } = renderHook(() => useLedState(1))

    // User sets a colour
    act(() => { result.current.changeColor('#ff0000') })
    await act(async () => {
      vi.advanceTimersByTime(300)
      await Promise.resolve()
    })

    // Trigger a poll
    await act(async () => {
      vi.advanceTimersByTime(4000)
      await Promise.resolve()
    })

    // colorHex must still be the user-chosen value
    expect(result.current.colorHex).toBe('#ff0000')
  })
})
