// frontend/src/config/api.js

// IMPORTANT:
// - In Azure Static Web Apps, set VITE_API_BASE_URL to your Container Apps URL (https://...azurecontainerapps.io)
// - Locally, it will fall back to localhost
const raw = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

// Normalize: remove trailing slashes so `${API_BASE_URL}/path` is clean
export const API_BASE_URL = String(raw).replace(/\/+$/, "");
