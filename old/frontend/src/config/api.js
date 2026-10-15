// frontend/src/config/api.js

// IMPORTANT:
// - In Azure Static Web Apps, set VITE_API_BASE_URL to your Container Apps URL (https://...azurecontainerapps.io)
// - Locally, default to the current browser host on port 8000 (works for localhost and LAN dev IPs)
function deriveDefaultApiBase() {
  if (typeof window === "undefined") return "http://127.0.0.1:8000";
  const host = window.location.hostname || "127.0.0.1";
  return `http://${host}:8000`;
}

const raw = import.meta.env.VITE_API_BASE_URL || deriveDefaultApiBase();

// Normalize: remove trailing slashes so `${API_BASE_URL}/path` is clean
export const API_BASE_URL = String(raw).replace(/\/+$/, "");
