import request from "./client";

// -- Live light state ----------------------------------------------------------

export function getLightState(node_id) {
  return request(`/api/matter/nodes/${node_id}/state/live`);
}

// -- OnOff ---------------------------------------------------------------------

export function turnOn(node_id) {
  return request(`/api/matter/nodes/${node_id}/on`, { method: "POST" });
}

export function turnOff(node_id) {
  return request(`/api/matter/nodes/${node_id}/off`, { method: "POST" });
}

export function toggleLight(node_id) {
  return request(`/api/matter/nodes/${node_id}/toggle`, { method: "POST" });
}

// -- Brightness ----------------------------------------------------------------

// level: 0-254, transition_time: tenths of a second
export function setBrightness(node_id, level, transition_time = 0) {
  return request(`/api/matter/nodes/${node_id}/brightness`, {
    method: "POST",
    body: JSON.stringify({ level, transition_time }),
  });
}

// -- Colour --------------------------------------------------------------------

// x, y: CIE XY floats 0.0-1.0
export function setColorXY(node_id, x, y, transition_time = 0) {
  return request(`/api/matter/nodes/${node_id}/color/xy`, {
    method: "POST",
    body: JSON.stringify({ x, y, transition_time }),
  });
}

// -- Node management -----------------------------------------------------------

export function getMatterNodes() {
  return request("/api/matter/nodes");
}

export function removeNode(node_id) {
  return request(`/api/matter/nodes/${node_id}`, { method: "DELETE" });
}

// -- Commissioning -------------------------------------------------------------

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