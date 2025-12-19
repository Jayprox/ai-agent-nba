// frontend/src/components/NarrativeDashboard.jsx
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function safeToLocalString(iso) {
  try {
    return iso ? new Date(iso).toLocaleString() : "N/A";
  } catch {
    return "N/A";
  }
}

function extractTeamName(teamLike, fallback) {
  if (!teamLike) return fallback;
  if (typeof teamLike === "string") return teamLike;
  if (typeof teamLike === "object") {
    return (
      teamLike.name ||
      teamLike.full_name ||
      teamLike.abbreviation ||
      teamLike.team_name ||
      fallback
    );
  }
  return fallback;
}

function getAwayTeamName(g) {
  // Support multiple possible response shapes
  return (
    extractTeamName(g?.away_team, null) ||
    extractTeamName(g?.away, null) ||
    extractTeamName(g?.teams?.away, null) ||
    extractTeamName(g?.awayTeam, null) ||
    extractTeamName(g?.visitor_team, null) ||
    extractTeamName(g?.visitor, null) ||
    extractTeamName(g?.away_team_name, null) ||
    extractTeamName(g?.away_name, null) ||
    "Away"
  );
}

function getHomeTeamName(g) {
  // Support multiple possible response shapes
  return (
    extractTeamName(g?.home_team, null) ||
    extractTeamName(g?.home, null) ||
    extractTeamName(g?.teams?.home, null) ||
    extractTeamName(g?.homeTeam, null) ||
    extractTeamName(g?.home_team_name, null) ||
    extractTeamName(g?.home_name, null) ||
    "Home"
  );
}

function buildMatchups(games, limit = 5) {
  if (!Array.isArray(games) || games.length === 0) return [];
  return games.slice(0, limit).map((g) => {
    const away = getAwayTeamName(g);
    const home = getHomeTeamName(g);
    return `${away} @ ${home}`;
  });
}

function guessSlateDateLabel(games) {
  try {
    if (!Array.isArray(games) || games.length === 0) return null;
    const first = games[0];
    if (!first?.date) return null;
    const d = new Date(first.date);
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

function pickGamesArray(data) {
  // Prefer the "raw" payload, but fall back to top-level if needed
  const candidates = [
    data?.raw?.games_today,
    data?.raw?.gamesToday,
    data?.raw?.games,
    data?.games_today,
    data?.gamesToday,
    data?.games,
  ];

  for (const c of candidates) {
    if (Array.isArray(c)) return c;
  }
  return [];
}

function pickTimezone(games, metaTz) {
  return (
    games?.[0]?.timezone ||
    games?.[0]?.tz ||
    games?.[0]?.time_zone ||
    metaTz ||
    "—"
  );
}

function parseTrendsOverride(value) {
  // null => default/env behavior (no query param)
  // true => trends=1
  // false => trends=0
  if (value === "1" || value === 1 || value === true) return true;
  if (value === "0" || value === 0 || value === false) return false;
  return null;
}

const NarrativeDashboard = () => {
  const [markdown, setMarkdown] = useState("");
  const [meta, setMeta] = useState({});
  const [rawMeta, setRawMeta] = useState({});
  const [gamesToday, setGamesToday] = useState([]);
  const [gamesTodayCount, setGamesTodayCount] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // F4: frontend control for trends param:
  // null = default/env, true = force ON (trends=1), false = force OFF (trends=0)
  const [trendsOverride, setTrendsOverride] = useState(null);

  const trendsLabel = useMemo(() => {
    if (trendsOverride === true) return "ON (forced)";
    if (trendsOverride === false) return "OFF (forced)";
    return "DEFAULT (env)";
  }, [trendsOverride]);

  const fetchMarkdown = async (forceRefresh = false, override = trendsOverride) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.set("mode", "ai");

      // Respect force refresh
      if (forceRefresh) params.set("cache_ttl", "0");

      // Only include trends param if override is not null
      if (override === true) params.set("trends", "1");
      if (override === false) params.set("trends", "0");

      const url = `${API_BASE}/nba/narrative/markdown?${params.toString()}`;
      console.log("🔍 [NarrativeDashboard D2] Fetching from:", url);

      const res = await fetch(url);
      console.log("📡 [NarrativeDashboard D2] Response status:", res.status);

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

      const data = await res.json();

      if (!data.ok) throw new Error(data.error || "Backend returned ok: false");
      if (!data.markdown) throw new Error("No markdown field in response");

      setMarkdown(data.markdown);

      const md = data.summary?.metadata || {};
      setMeta(md);

      const rm = data.raw?.meta || {};
      setRawMeta(rm);

      // ✅ Step D: robustly pull games array regardless of backend key naming
      const safeGames = pickGamesArray(data);
      setGamesToday(safeGames);

      const countFromMeta =
        data.summary?.metadata?.games_today_count ??
        data.raw?.meta?.source_counts?.games_today;

      const count =
        typeof countFromMeta === "number" ? countFromMeta : safeGames.length;

      setGamesTodayCount(count);

      // Keep our local state in sync with what backend reports, if present
      // (backend returns raw.meta.trends_override as true/false/null)
      if (Object.prototype.hasOwnProperty.call(rm || {}, "trends_override")) {
        setTrendsOverride(parseTrendsOverride(rm?.trends_override));
      }

      console.log(
        "✅ [NarrativeDashboard D2] Loaded. games_today_count =",
        count,
        "| trends_override =",
        rm?.trends_override
      );
    } catch (err) {
      console.error("❌ [NarrativeDashboard D2] Fetch error:", err);
      setError(err.message || "Failed to load narrative");
    } finally {
      setLoading(false);
      setIsRegenerating(false);
    }
  };

  useEffect(() => {
    console.log("🧩 [NarrativeDashboard D2] Component mounted. API_BASE =", API_BASE);
    fetchMarkdown();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSetTrends = (nextOverride) => {
    setTrendsOverride(nextOverride);
    // immediately refresh narrative using the new override
    fetchMarkdown(true, nextOverride);
  };

  if (loading)
    return (
      <div style={{ padding: 16, color: "white" }}>
        ⏳ Generating narrative...
      </div>
    );

  if (error) {
    return (
      <div style={{ padding: 16, color: "#fca5a5" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
          ❌ Error
        </h2>
        <p>{error}</p>
      </div>
    );
  }

  const generatedAt = safeToLocalString(meta?.generated_at);
  const slateDateLabel = guessSlateDateLabel(gamesToday);
  const slateTz = pickTimezone(gamesToday, rawMeta?.timezone);
  const matchups = buildMatchups(gamesToday, 5);

  const backendTrendsEnabled = !!rawMeta?.trends_enabled_in_narrative;

  return (
    <div style={{ padding: 24, color: "white", maxWidth: 980, margin: "0 auto" }}>
      {/* Header + Actions */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>
              AI Narrative Dashboard
            </h1>
            <span
              style={{
                fontSize: 12,
                padding: "3px 8px",
                borderRadius: 999,
                border: "1px solid #334155",
                background: "#0b1220",
              }}
            >
              Version: D2
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            Frontend trends toggle wired to <code style={{ color: "#e5e7eb" }}>trends=0/1</code>.
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {/* F4: Trends toggle */}
          <div
            style={{
              display: "flex",
              gap: 6,
              alignItems: "center",
              padding: 6,
              borderRadius: 12,
              border: "1px solid #334155",
              background: "rgba(11,18,32,0.85)",
            }}
          >
            <span style={{ fontSize: 12, color: "#9ca3af", paddingLeft: 6 }}>
              Trends:
            </span>

            <button
              onClick={() => onSetTrends(null)}
              disabled={isRegenerating}
              style={{
                padding: "8px 10px",
                borderRadius: 10,
                fontWeight: 800,
                fontSize: 12,
                border: "1px solid #334155",
                background: trendsOverride === null ? "#1f2937" : "transparent",
                color: trendsOverride === null ? "white" : "#e5e7eb",
                cursor: isRegenerating ? "not-allowed" : "pointer",
              }}
              title="Use backend default / env behavior (no trends query param)"
            >
              Default
            </button>

            <button
              onClick={() => onSetTrends(true)}
              disabled={isRegenerating}
              style={{
                padding: "8px 10px",
                borderRadius: 10,
                fontWeight: 800,
                fontSize: 12,
                border: "1px solid #334155",
                background: trendsOverride === true ? "#064e3b" : "transparent",
                color: trendsOverride === true ? "#d1fae5" : "#e5e7eb",
                cursor: isRegenerating ? "not-allowed" : "pointer",
              }}
              title="Force trends ON (adds trends=1)"
            >
              On
            </button>

            <button
              onClick={() => onSetTrends(false)}
              disabled={isRegenerating}
              style={{
                padding: "8px 10px",
                borderRadius: 10,
                fontWeight: 800,
                fontSize: 12,
                border: "1px solid #334155",
                background: trendsOverride === false ? "#7f1d1d" : "transparent",
                color: trendsOverride === false ? "#fee2e2" : "#e5e7eb",
                cursor: isRegenerating ? "not-allowed" : "pointer",
              }}
              title="Force trends OFF (adds trends=0)"
            >
              Off
            </button>

            <span style={{ fontSize: 12, color: "#9ca3af", paddingRight: 6 }}>
              {trendsLabel}
            </span>
          </div>

          {/* Regenerate */}
          <button
            onClick={() => {
              setIsRegenerating(true);
              fetchMarkdown(true);
            }}
            disabled={isRegenerating}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              fontWeight: 700,
              border: "1px solid #334155",
              background: isRegenerating ? "#111827" : "#2563eb",
              color: isRegenerating ? "#9ca3af" : "white",
              cursor: isRegenerating ? "not-allowed" : "pointer",
            }}
          >
            {isRegenerating ? "Generating..." : "Regenerate Narrative"}
          </button>
        </div>
      </div>

      {/* Slate Header (Step D) */}
      <div
        style={{
          marginBottom: 16,
          border: "1px solid #334155",
          background: "rgba(17,24,39,0.75)",
          borderRadius: 14,
          padding: 14,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 14, fontWeight: 800 }}>
              Today’s Slate{slateDateLabel ? ` • ${slateDateLabel}` : ""}
            </div>
            <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>
              Games:{" "}
              <span style={{ color: "white", fontWeight: 800 }}>
                {gamesTodayCount}
              </span>{" "}
              <span style={{ margin: "0 8px" }}>•</span>
              Timezone:{" "}
              <span style={{ color: "white", fontWeight: 800 }}>{slateTz}</span>{" "}
              <span style={{ margin: "0 8px" }}>•</span>
              Trends in narrative:{" "}
              <span style={{ color: "white", fontWeight: 800 }}>
                {backendTrendsEnabled ? "ON" : "OFF"}
              </span>
              <span style={{ margin: "0 8px" }}>•</span>
              Override:{" "}
              <span style={{ color: "white", fontWeight: 800 }}>
                {rawMeta?.trends_override === null || rawMeta?.trends_override === undefined
                  ? "None"
                  : String(rawMeta?.trends_override)}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <span
              style={{
                fontSize: 12,
                padding: "4px 10px",
                borderRadius: 999,
                border: "1px solid rgba(56,189,248,0.35)",
                background: "rgba(3,105,161,0.25)",
                color: "#bae6fd",
              }}
            >
              Source: API-Basketball
            </span>
            <span
              style={{
                fontSize: 12,
                padding: "4px 10px",
                borderRadius: 999,
                border: "1px solid #334155",
                background: "#0b1220",
                color: "#e5e7eb",
              }}
            >
              Mode: {rawMeta?.mode || "ai"}
            </span>
          </div>
        </div>

        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6 }}>
            Matchups (first {Math.min(matchups.length, 5)}):
          </div>

          {matchups.length ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {matchups.map((m, idx) => (
                <span
                  key={`${idx}-${m}`}
                  style={{
                    fontSize: 12,
                    padding: "6px 10px",
                    borderRadius: 10,
                    border: "1px solid #334155",
                    background: "rgba(0,0,0,0.25)",
                  }}
                >
                  {m}
                </span>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "#9ca3af" }}>
              No games returned (or games payload missing team names).
            </div>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 12 }}>
        <div>
          Model:{" "}
          <span style={{ color: "#e5e7eb", fontWeight: 700 }}>
            {meta?.model || "Unknown"}
          </span>
        </div>
        <div>
          Generated:{" "}
          <span style={{ color: "#e5e7eb", fontWeight: 700 }}>
            {generatedAt}
          </span>
        </div>
        <div>
          Digest:{" "}
          <span style={{ color: "#e5e7eb", fontWeight: 700 }}>
            {meta?.inputs_digest || "—"}
          </span>
        </div>
      </div>

      {/* Markdown content */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #334155",
          borderRadius: 18,
          padding: 18,
          minHeight: 420,
          overflow: "auto",
        }}
      >
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
};

export default NarrativeDashboard;
