import request from "./client";

// ── Live light state ──────────────────────────────────────────────────────────

export function getLightState(node_id) {
  return request(`/api/matter/nodes/${node_id}/state/live`);
}

// ── OnOff ─────────────────────────────────────────────────────────────────────

export function turnOn(node_id) {
  return request(`/api/matter/nodes/${node_id}/on`, { method: "POST" });
}

export function turnOff(node_id) {
  return request(`/api/matter/nodes/${node_id}/off`, { method: "POST" });
}

export function toggleLight(node_id) {
  return request(`/api/matter/nodes/${node_id}/toggle`, { method: "POST" });
}

// ── Brightness ────────────────────────────────────────────────────────────────

// level: 0-254, transition_time: tenths of a second
export function setBrightness(node_id, level, transition_time = 0) {
  return request(`/api/matter/nodes/${node_id}/brightness`, {
    method: "POST",
    body: JSON.stringify({ level, transition_time }),
  });
}

// ── Colour ────────────────────────────────────────────────────────────────────

// x, y: CIE XY floats 0.0-1.0
export function setColorXY(node_id, x, y, transition_time = 0) {
  return request(`/api/matter/nodes/${node_id}/color/xy`, {
    method: "POST",
    body: JSON.stringify({ x, y, transition_time }),
  });
}

// ── Node management ───────────────────────────────────────────────────────────

export function getMatterNodes() {
  return request("/api/matter/nodes");
}

export function removeNode(node_id) {
  return request(`/api/matter/nodes/${node_id}`, { method: "DELETE" });
}

// ── Commissioning ─────────────────────────────────────────────────────────────

export function setWifiCredentials(ssid, password) {
  return request("/api/matter/wifi", {
    method: "POST",
    body: JSON.stringify({ ssid, password }),
  });
}

export function commissionDevice(code, node_id = null, network_only = false) {
  return request("/api/matter/commission", {
    method: "POST",
    body: JSON.stringify({ code, node_id, network_only }),
  });
}

// ── Colour conversion helpers ─────────────────────────────────────────────────

/**
 * Convert a hex colour string (#rrggbb) to CIE XY for the MoveToColor command.
 * Uses the sRGB → XYZ → xy conversion with the D65 white point.
 */
export function hexToXY(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;

  // Gamma correction (sRGB linearisation)
  const lr = r > 0.04045 ? Math.pow((r + 0.055) / 1.055, 2.4) : r / 12.92;
  const lg = g > 0.04045 ? Math.pow((g + 0.055) / 1.055, 2.4) : g / 12.92;
  const lb = b > 0.04045 ? Math.pow((b + 0.055) / 1.055, 2.4) : b / 12.92;

  // Wide RGB D65 conversion
  const X = lr * 0.664511 + lg * 0.154324 + lb * 0.162028;
  const Y = lr * 0.283881 + lg * 0.668433 + lb * 0.047685;
  const Z = lr * 0.000088 + lg * 0.072310 + lb * 0.986039;

  const sum = X + Y + Z;
  if (sum === 0) return { x: 0, y: 0 };
  return {
    x: parseFloat((X / sum).toFixed(6)),
    y: parseFloat((Y / sum).toFixed(6)),
  };
}

/**
 * Convert CIE XY (from the live cache) back to an approximate hex colour
 * for displaying the current colour in the UI colour picker.
 */
export function xyToHex(x, y) {
  const z = 1.0 - x - y;
  const Y = 1.0;
  const X = (Y / y) * x;
  const Z = (Y / y) * z;

  // Wide RGB D65 reverse
  let r =  X * 1.656492 - Y * 0.354851 - Z * 0.255038;
  let g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152;
  let b =  X * 0.051713 - Y * 0.121364 + Z * 1.011530;

  // Clamp and gamma encode
  const clamp = (v) => Math.max(0, Math.min(1, v));
  const gamma = (v) => v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055;

  r = gamma(clamp(r));
  g = gamma(clamp(g));
  b = gamma(clamp(b));

  const toHex = (v) => Math.round(v * 255).toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}