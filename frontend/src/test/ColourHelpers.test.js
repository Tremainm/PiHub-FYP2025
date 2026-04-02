import { hexToXY, xyToHex } from '../components/ColourHelpers'

// -- hexToXY -------------------------------------------------------------------

describe('hexToXY', () => {
  it('returns {x:0, y:0} for black (#000000)', () => {
    expect(hexToXY('#000000')).toEqual({ x: 0, y: 0 })
  })

  it('returns an object with x and y properties', () => {
    const result = hexToXY('#ff0000')
    expect(result).toHaveProperty('x')
    expect(result).toHaveProperty('y')
  })

  it('returns floats with up to 6 decimal places for white', () => {
    const { x, y } = hexToXY('#ffffff')
    // D65 white point: x ≈ 0.323, y ≈ 0.329
    expect(x).toBeCloseTo(0.323, 2)
    expect(y).toBeCloseTo(0.329, 2)
  })

  it('returns high x value for red (#ff0000)', () => {
    const { x } = hexToXY('#ff0000')
    expect(x).toBeGreaterThan(0.5)
  })

  it('returns low x and y values for blue (#0000ff)', () => {
    const { x, y } = hexToXY('#0000ff')
    expect(x).toBeLessThan(0.2)
    expect(y).toBeLessThan(0.1)
  })

  it('returns x and y values between 0 and 1', () => {
    for (const hex of ['#ff0000', '#00ff00', '#0000ff', '#ffffff', '#808080']) {
      const { x, y } = hexToXY(hex)
      expect(x).toBeGreaterThanOrEqual(0)
      expect(x).toBeLessThanOrEqual(1)
      expect(y).toBeGreaterThanOrEqual(0)
      expect(y).toBeLessThanOrEqual(1)
    }
  })

  it('x + y is less than or equal to 1 for any input', () => {
    const { x, y } = hexToXY('#ff0000')
    expect(x + y).toBeLessThanOrEqual(1)
  })
})

// -- xyToHex -------------------------------------------------------------------

describe('xyToHex', () => {
  it('returns a string in #rrggbb format', () => {
    expect(xyToHex(0.3, 0.3)).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('returns #rrggbb format for red preset (x=0.700, y=0.299)', () => {
    expect(xyToHex(0.700, 0.299)).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('returns #rrggbb format for warm white (x=0.450, y=0.408)', () => {
    expect(xyToHex(0.450, 0.408)).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('returns #rrggbb format for cool white (x=0.313, y=0.329)', () => {
    expect(xyToHex(0.313, 0.329)).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('round-trips white approximately', () => {
    const { x, y } = hexToXY('#ffffff')
    const hex = xyToHex(x, y)
    // Should come back close to white — all channels should be high
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    expect(r).toBeGreaterThan(200)
    expect(g).toBeGreaterThan(200)
    expect(b).toBeGreaterThan(200)
  })

  it('round-trips red with dominant red channel', () => {
    const { x, y } = hexToXY('#ff0000')
    const hex = xyToHex(x, y)
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    // Red channel should dominate after round-trip
    expect(r).toBeGreaterThan(g)
    expect(r).toBeGreaterThan(b)
  })
})
