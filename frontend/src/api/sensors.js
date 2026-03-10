import request from "./client";

// Live readings from subscription cache,call every few seconds for dashboard tile
export function getSensorLive(node_id) {
  return request(`/api/matter/nodes/${node_id}/sensors/live`);
}

// Historical readings, used by the SensorHistory chart page
// sensor_type: "temperature_c" | "humidity_rh" | omit for both
export function getSensorHistory(node_id, { sensor_type, limit = 100 } = {}) {
  const params = new URLSearchParams({ limit });
  if (sensor_type) params.set("sensor_type", sensor_type);
  return request(`/api/sensors/${node_id}/history?${params}`);
}