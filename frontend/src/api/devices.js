import request from "./client";

// GET all registered devices (node_id + name)
export function getDevices() {
  return request("/api/devices");
}

// POST register a new device name after commissioning
export function registerDevice(node_id, name) {
  return request("/api/devices", {
    method: "POST",
    body: JSON.stringify({ node_id, name }),
  });
}

// DELETE remove a device from the name registry
export function unregisterDevice(node_id) {
  return request(`/api/devices/${node_id}`, { method: "DELETE" });
}