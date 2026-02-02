// frontend/src/services/narrativeAPI.js
import { API_BASE_URL } from "../config/api.js";

/**
 * Fetch narrative markdown from the backend.
 *
 * Backend response shape (expected):
 * {
 *   ok: boolean,
 *   markdown: string,
 *   error?: string,
 *   raw?: { meta?: object, ... },
 *   summary?: { metadata?: object, ... }
 * }
 */
export async function fetchNarrativeMarkdown({
  mode = "ai",
  compact = false,
  cacheTtl = 0,
  trends = null, // null => omit param, true => trends=1, false => trends=0
  signal,
} = {}) {
  const params = new URLSearchParams();
  params.set("mode", mode);

  if (compact) params.set("compact", "true");

  // Always send cache_ttl explicitly (matches your dashboard behavior)
  params.set("cache_ttl", String(Number(cacheTtl) || 0));

  if (trends === true) params.set("trends", "1");
  if (trends === false) params.set("trends", "0");

  const url = `${API_BASE_URL}/nba/narrative/markdown?${params.toString()}`;

  // Optional safety timeout (15s)
  const controller = !signal ? new AbortController() : null;
  const timeoutId = !signal
    ? setTimeout(() => controller.abort(), 15000)
    : null;

  try {
    const res = await fetch(url, { signal: signal || controller.signal });

    // Try to parse JSON either way for best error messages
    let data = null;
    try {
      data = await res.json();
    } catch {
      // If backend ever returns non-JSON, keep it graceful
      const txt = await res.text().catch(() => "");
      if (!res.ok) {
        throw new Error(
          `Request failed: ${res.status} ${res.statusText}${
            txt ? ` — ${txt.slice(0, 200)}` : ""
          }`
        );
      }
      // If it's OK but not JSON, treat as "markdown text"
      return { ok: true, markdown: txt };
    }

    if (!res.ok) {
      throw new Error(
        data?.error ||
          `Request failed: ${res.status} ${res.statusText}`
      );
    }

    if (data?.ok === false) {
      throw new Error(data?.error || "Backend returned ok:false");
    }

    if (typeof data?.markdown !== "string" || !data.markdown.trim()) {
      throw new Error("No markdown returned by backend");
    }

    return data; // return the full payload (markdown + meta) for flexibility
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}
