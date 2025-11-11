import request from "./client";

export function getSensors() {
  return request("/api/sensors");
}
