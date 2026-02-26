const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default async function request(endpoint, options = {}) {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }

  // 204 No Content responses have no body
  if (res.status === 204) return null;
  return res.json();
}