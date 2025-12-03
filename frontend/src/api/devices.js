import request from "./client";

// GET devices
export function getDevices() {
  return request("/api/devices");
}

// POST toggle device
export function toggleDevice(id) {
  return request(`/api/devices/${id}/toggle`, {
    method: "PUT",
  });
}
