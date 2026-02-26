import request from "./client";

export function getSensors() {
  return request("/api/sensors");
}

export function createSensor(data) {
  return request("/api/sensors", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
