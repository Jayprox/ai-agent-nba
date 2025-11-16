const BASE_URL = "http://127.0.0.1:8000";

export async function fetchNarrative(mode = "ai") {
  try {
    const res = await fetch(`${BASE_URL}/nba/narrative/markdown?mode=${mode}`);
    if (!res.ok) throw new Error(`Failed to fetch narrative: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchNarrative error:", err);
    return { ok: false, markdown: `Error: ${err.message}` };
  }
}
