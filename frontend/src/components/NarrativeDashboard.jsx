// frontend/src/components/NarrativeDashboard.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

// -----------------------------
// Storage keys
// -----------------------------
const LS_TRENDS_OVERRIDE = "narrative.trendsOverride"; // "default" | "on" | "off"
const LS_COMPACT = "narrative.compact"; // "1" | "0"
const LS_CACHE_TTL = "narrative.cacheTtl"; // "0" | "15" | "60" | "120"

const ALLOWED_TTLS = [0, 15, 60, 120];

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

function safeArray(v) {
  return Array.isArray(v) ? v : [];
}

function safeNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function formatMaybeNumber(v) {
  const n = safeNum(v);
  if (n === null) return v ?? "—";
  return Math.round(n * 10) / 10;
}

function normalizeDirection(dir) {
  const d = String(dir || "").toLowerCase();
  if (d.includes("up")) return "up";
  if (d.includes("down")) return "down";
  if (d.includes("neutral")) return "neutral";
  return dir || "—";
}

function trendDirBadgeStyle(direction) {
  const d = normalizeDirection(direction);
  if (d === "up") {
    return {
      border: "1px solid rgba(34,197,94,0.35)",
      background: "rgba(22,163,74,0.18)",
      color: "#bbf7d0",
    };
  }
  if (d === "down") {
    return {
      border: "1px solid rgba(239,68,68,0.35)",
      background: "rgba(185,28,28,0.18)",
      color: "#fecaca",
    };
  }
  if (d === "neutral") {
    return {
      border: "1px solid rgba(148,163,184,0.35)",
      background: "rgba(148,163,184,0.12)",
      color: "#e5e7eb",
    };
  }
  return {
    border: "1px solid rgba(148,163,184,0.35)",
    background: "rgba(148,163,184,0.12)",
    color: "#e5e7eb",
  };
}

function extractPlayerTrendFields(t) {
  const player =
    t?.player_name ||
    t?.player ||
    t?.name ||
    t?.playerName ||
    t?.player_full_name ||
    "Unknown Player";

  const stat = t?.stat_type || t?.stat || t?.metric || t?.category || "stat";

  const avg = t?.average ?? t?.avg ?? t?.mean ?? t?.value ?? null;
  const dir = t?.trend_direction ?? t?.direction ?? t?.trend ?? "—";
  const lastN = t?.last_n_games ?? t?.lastN ?? t?.sample_size ?? null;

  return { player, stat, average: avg, direction: dir, lastN, raw: t };
}

function extractTeamTrendFields(t) {
  const team =
    t?.team_name || t?.team || t?.name || t?.teamName || "Unknown Team";

  const stat = t?.stat_type || t?.stat || t?.metric || t?.category || "stat";

  const avg = t?.average ?? t?.avg ?? t?.mean ?? t?.value ?? null;
  const dir = t?.trend_direction ?? t?.direction ?? t?.trend ?? "—";
  const lastN = t?.last_n_games ?? t?.lastN ?? t?.sample_size ?? null;

  return { team, stat, average: avg, direction: dir, lastN, raw: t };
}

// -----------------------------
// UI shared styles
// -----------------------------
const pillStyle = {
  fontSize: 12,
  padding: "4px 10px",
  borderRadius: 999,
  border: "1px solid #334155",
  background: "#0b1220",
  color: "#e5e7eb",
};

const btnBase = {
  padding: "8px 10px",
  borderRadius: 10,
  fontWeight: 800,
  fontSize: 12,
  border: "1px solid #334155",
};

function loadTrendsOverrideFromStorage() {
  try {
    const v = localStorage.getItem(LS_TRENDS_OVERRIDE);
    if (v === "on") return true;
    if (v === "off") return false;
    return null;
  } catch {
    return null;
  }
}

function loadCompactFromStorage() {
  try {
    return localStorage.getItem(LS_COMPACT) === "1";
  } catch {
    return false;
  }
}

function loadCacheTtlFromStorage() {
  try {
    const raw = localStorage.getItem(LS_CACHE_TTL);
    const n = Number(raw);
    if (ALLOWED_TTLS.includes(n)) return n;
    return 0;
  } catch {
    return 0;
  }
}

const NarrativeDashboard = () => {
  const [markdown, setMarkdown] = useState("");
  const [meta, setMeta] = useState({});
  const [rawMeta, setRawMeta] = useState({});
  const [gamesToday, setGamesToday] = useState([]);
  const [gamesTodayCount, setGamesTodayCount] = useState(0);

  // Trends payload (raw.player_trends + raw.team_trends)
  const [playerTrends, setPlayerTrends] = useState([]);
  const [teamTrends, setTeamTrends] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // Controls (persisted)
  const [trendsOverride, setTrendsOverride] = useState(() =>
    loadTrendsOverrideFromStorage()
  );
  const [compact, setCompact] = useState(() => loadCompactFromStorage());
  const [cacheTtl, setCacheTtl] = useState(() => loadCacheTtlFromStorage());

  // Latest-request-wins + abort
  const requestIdRef = useRef(0);
  const abortRef = useRef(null);

  const trendsLabel = useMemo(() => {
    if (trendsOverride === true) return "ON (forced)";
    if (trendsOverride === false) return "OFF (forced)";
    return "DEFAULT (env)";
  }, [trendsOverride]);

  // Persist controls
  useEffect(() => {
    try {
      localStorage.setItem(
        LS_TRENDS_OVERRIDE,
        trendsOverride === true ? "on" : trendsOverride === false ? "off" : "default"
      );
      localStorage.setItem(LS_COMPACT, compact ? "1" : "0");
      localStorage.setItem(LS_CACHE_TTL, String(cacheTtl));
    } catch {
      // no-op
    }
  }, [trendsOverride, compact, cacheTtl]);

  const fetchMarkdown = async (opts = {}) => {
    const {
      forceRefresh = false,
      override = trendsOverride,
      compactOverride = compact,
      ttlOverride = cacheTtl,
      reason = "manual",
    } = opts;

    // Abort any prior in-flight request
    try {
      if (abortRef.current) abortRef.current.abort();
    } catch {
      // no-op
    }
    const controller = new AbortController();
    abortRef.current = controller;

    const myRequestId = ++requestIdRef.current;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.set("mode", "ai");

      // compact toggle
      if (compactOverride) params.set("compact", "true");

      // cache ttl: if forceRefresh, bust cache (0). Otherwise use selected TTL when > 0.
      if (forceRefresh) {
        params.set("cache_ttl", "0");
      } else if (typeof ttlOverride === "number" && ttlOverride > 0) {
        params.set("cache_ttl", String(ttlOverride));
      }

      // Only include trends param if override is not null
      if (override === true) params.set("trends", "1");
      if (override === false) params.set("trends", "0");

      const url = `${API_BASE}/nba/narrative/markdown?${params.toString()}`;

      console.log("🔍 [NarrativeDashboard D6] Fetching:", {
        url,
        reason,
        requestId: myRequestId,
      });

      const res = await fetch(url, { signal: controller.signal });

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

      const data = await res.json();

      // If another request has started since this one, ignore this response
      if (myRequestId !== requestIdRef.current) {
        console.log("🟡 [NarrativeDashboard D6] Stale response ignored:", myRequestId);
        return;
      }

      if (!data.ok) throw new Error(data.error || "Backend returned ok: false");
      if (!data.markdown) throw new Error("No markdown field in response");

      setMarkdown(data.markdown);

      const md = data.summary?.metadata || {};
      setMeta(md);

      const rm = data.raw?.meta || {};
      setRawMeta(rm);

      const safeGames = pickGamesArray(data);
      setGamesToday(safeGames);

      const countFromMeta =
        data.summary?.metadata?.games_today_count ??
        data.raw?.meta?.source_counts?.games_today;

      const count = typeof countFromMeta === "number" ? countFromMeta : safeGames.length;
      setGamesTodayCount(count);

      // trends payload
      setPlayerTrends(safeArray(data?.raw?.player_trends));
      setTeamTrends(safeArray(data?.raw?.team_trends));

      // Sync local toggle state with backend, if present
      if (Object.prototype.hasOwnProperty.call(rm || {}, "trends_override")) {
        setTrendsOverride(parseTrendsOverride(rm?.trends_override));
      }

      console.log("✅ [NarrativeDashboard D6] Loaded:", {
        requestId: myRequestId,
        games_today_count: count,
        trends_override: rm?.trends_override,
        trends_enabled_in_narrative: rm?.trends_enabled_in_narrative,
        player_trends_len: safeArray(data?.raw?.player_trends).length,
        team_trends_len: safeArray(data?.raw?.team_trends).length,
      });
    } catch (err) {
      if (err?.name === "AbortError") {
        console.log("🟡 [NarrativeDashboard D6] Fetch aborted (expected).");
        return;
      }
      console.error("❌ [NarrativeDashboard D6] Fetch error:", err);

      // If stale, ignore setting error/loading
      if (myRequestId !== requestIdRef.current) return;

      setError(err?.message || "Failed to load narrative");
    } finally {
      // If stale, don't touch UI state
      if (myRequestId !== requestIdRef.current) return;

      setLoading(false);
      setIsRegenerating(false);
    }
  };

  useEffect(() => {
    console.log("🧩 [NarrativeDashboard D6] Mount. API_BASE =", API_BASE);
    fetchMarkdown({ reason: "mount" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onChangeCompact = (next) => {
    setCompact(next);
    fetchMarkdown({
      forceRefresh: true,
      compactOverride: next,
      reason: "compact-toggle",
    });
  };

  const onChangeCacheTtl = (nextTtl) => {
    setCacheTtl(nextTtl);
    fetchMarkdown({ forceRefresh: false, ttlOverride: nextTtl, reason: "ttl-change" });
  };

  const onSetTrends = (nextOverride) => {
    setTrendsOverride(nextOverride);
    fetchMarkdown({ forceRefresh: true, override: nextOverride, reason: "trends-toggle" });
  };

  // -----------------------------
  // Derived values (NO HOOKS)
  // These must be safe even during loading/error renders.
  // -----------------------------
  const safePlayerTrends = safeArray(playerTrends);
  const safeTeamTrends = safeArray(teamTrends);

  const playerTrendsTop = safePlayerTrends.slice(0, 5);
  const teamTrendsTop = safeTeamTrends.slice(0, 5);

  const playerTrendsCount = safePlayerTrends.length;
  const teamTrendsCount = safeTeamTrends.length;

  const backendTrendsEnabled = !!rawMeta?.trends_enabled_in_narrative;
  const trendsSoftError = rawMeta?.soft_errors?.trends || null;

  // Contract snapshot fields
  const latencyMs = formatMaybeNumber(rawMeta?.latency_ms);
  const cacheUsed = rawMeta?.cache_used;
  const cacheTtlS = rawMeta?.cache_ttl_s;
  const sourceCounts = rawMeta?.source_counts || {};
  const scGames = sourceCounts?.games_today;
  const scPlayerTrends = sourceCounts?.player_trends;
  const scTeamTrends = sourceCounts?.team_trends;

  if (loading) {
    return (
      <div style={{ padding: 16, color: "white" }}>
        ⏳ Generating narrative...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 16, color: "#fca5a5" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>❌ Error</h2>
        <p>{error}</p>
      </div>
    );
  }

  const generatedAt = safeToLocalString(meta?.generated_at);
  const slateDateLabel = guessSlateDateLabel(gamesToday);
  const slateTz = pickTimezone(gamesToday, rawMeta?.timezone);
  const matchups = buildMatchups(gamesToday, 5);

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
              Version: D6
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            Fixed hooks crash (no hooks after early returns). Controls:{" "}
            <code style={{ color: "#e5e7eb" }}>trends</code>,{" "}
            <code style={{ color: "#e5e7eb" }}>compact</code>,{" "}
            <code style={{ color: "#e5e7eb" }}>cache_ttl</code>.
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {/* Trends toggle */}
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
                ...btnBase,
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
                ...btnBase,
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
                ...btnBase,
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

          {/* Compact + TTL controls */}
          <div
            style={{
              display: "flex",
              gap: 10,
              alignItems: "center",
              padding: 6,
              borderRadius: 12,
              border: "1px solid #334155",
              background: "rgba(11,18,32,0.85)",
            }}
          >
            <span style={{ fontSize: 12, color: "#9ca3af", paddingLeft: 6 }}>
              Format:
            </span>

            <button
              onClick={() => onChangeCompact(!compact)}
              disabled={isRegenerating}
              style={{
                ...btnBase,
                background: compact ? "#1f2937" : "transparent",
                color: compact ? "white" : "#e5e7eb",
                cursor: isRegenerating ? "not-allowed" : "pointer",
              }}
              title="Toggle compact markdown (adds compact=true)"
            >
              {compact ? "Compact: ON" : "Compact: OFF"}
            </button>

            <span style={{ fontSize: 12, color: "#9ca3af" }}>Cache TTL:</span>
            <select
              value={String(cacheTtl)}
              disabled={isRegenerating}
              onChange={(e) => onChangeCacheTtl(Number(e.target.value))}
              style={{
                fontSize: 12,
                padding: "8px 10px",
                borderRadius: 10,
                border: "1px solid #334155",
                background: "#0b1220",
                color: "white",
                fontWeight: 800,
                cursor: isRegenerating ? "not-allowed" : "pointer",
              }}
              title="Controls caching behavior (cache_ttl)"
            >
              <option value="0">0s</option>
              <option value="15">15s</option>
              <option value="60">60s</option>
              <option value="120">120s</option>
            </select>
          </div>

          {/* Regenerate */}
          <button
            onClick={() => {
              setIsRegenerating(true);
              fetchMarkdown({ forceRefresh: true, reason: "regenerate" });
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

      {/* Slate Header */}
      <div
        style={{
          marginBottom: 12,
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
              <span style={{ color: "white", fontWeight: 800 }}>{gamesTodayCount}</span>{" "}
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
            <span style={{ ...pillStyle }}>Mode: {rawMeta?.mode || "ai"}</span>
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

      {/* Contract Snapshot */}
      <div
        style={{
          marginBottom: 16,
          border: "1px solid #334155",
          background: "rgba(11,18,32,0.75)",
          borderRadius: 14,
          padding: 14,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 14, fontWeight: 900 }}>Contract Snapshot</div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>
              Quick visibility into <code style={{ color: "#e5e7eb" }}>raw.meta</code> +{" "}
              <code style={{ color: "#e5e7eb" }}>source_counts</code>.
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ ...pillStyle }} title="raw.meta.latency_ms">
              Latency:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{latencyMs ?? "—"}</span> ms
            </span>

            <span style={{ ...pillStyle }} title="raw.meta.cache_used">
              Cache:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>
                {cacheUsed === true ? "Used" : cacheUsed === false ? "No" : "—"}
              </span>
            </span>

            <span style={{ ...pillStyle }} title="raw.meta.cache_ttl_s">
              TTL:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{cacheTtlS ?? "—"}</span>s
            </span>

            <span style={{ ...pillStyle }} title="raw.meta.source_counts.games_today">
              games_today:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{scGames ?? "—"}</span>
            </span>

            <span style={{ ...pillStyle }} title="raw.meta.source_counts.player_trends">
              player_trends:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{scPlayerTrends ?? "—"}</span>
            </span>

            <span style={{ ...pillStyle }} title="raw.meta.source_counts.team_trends">
              team_trends:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{scTeamTrends ?? "—"}</span>
            </span>
          </div>
        </div>

        {trendsSoftError ? (
          <div
            style={{
              marginTop: 12,
              fontSize: 12,
              color: "#cbd5e1",
              border: "1px dashed #334155",
              borderRadius: 12,
              padding: 12,
              background: "rgba(0,0,0,0.12)",
            }}
          >
            <span style={{ fontWeight: 900 }}>soft_errors.trends:</span> {String(trendsSoftError)}
          </div>
        ) : null}
      </div>

      {/* Trends Preview */}
      <div
        style={{
          marginBottom: 16,
          border: "1px solid #334155",
          background: "rgba(17,24,39,0.55)",
          borderRadius: 14,
          padding: 14,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 10,
            alignItems: "center",
            flexWrap: "wrap",
            marginBottom: 10,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 14, fontWeight: 900 }}>Trends Preview</div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>
              Pulled from backend raw payload. Use the toggles above to force ON/OFF.
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span style={{ ...pillStyle }}>
              Player trends:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{playerTrendsCount}</span>
            </span>

            <span style={{ ...pillStyle }}>
              Team trends:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{teamTrendsCount}</span>
            </span>

            <span
              style={{
                fontSize: 12,
                padding: "4px 10px",
                borderRadius: 999,
                ...trendDirBadgeStyle(backendTrendsEnabled ? "up" : "neutral"),
              }}
              title="This reflects raw.meta.trends_enabled_in_narrative"
            >
              {backendTrendsEnabled ? "Enabled" : "Disabled"}
            </span>
          </div>
        </div>

        {!backendTrendsEnabled ? (
          <div
            style={{
              fontSize: 12,
              color: "#9ca3af",
              border: "1px dashed #334155",
              borderRadius: 12,
              padding: 12,
              background: "rgba(0,0,0,0.15)",
            }}
          >
            <div style={{ fontWeight: 800, color: "#e5e7eb", marginBottom: 6 }}>
              Trends are currently disabled.
            </div>
            <div>
              Toggle <span style={{ color: "white", fontWeight: 800 }}>On</span> to include trends in
              the narrative request.
            </div>
            {trendsSoftError ? (
              <div style={{ marginTop: 8, color: "#cbd5e1" }}>
                <span style={{ fontWeight: 800 }}>Reason:</span> {String(trendsSoftError)}
              </div>
            ) : null}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Player trends list */}
            <div>
              <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6 }}>
                Player Trends (top {Math.min(playerTrendsTop.length, 5)}):
              </div>

              {playerTrendsTop.length ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {playerTrendsTop.map((t, idx) => {
                    const f = extractPlayerTrendFields(t);
                    const dir = normalizeDirection(f.direction);
                    const lastN = f.lastN === null || f.lastN === undefined ? "—" : String(f.lastN);

                    return (
                      <div
                        key={`pt-${idx}`}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 10,
                          alignItems: "center",
                          border: "1px solid #334155",
                          background: "rgba(0,0,0,0.18)",
                          borderRadius: 12,
                          padding: "10px 12px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ fontSize: 13, fontWeight: 900 }}>{String(f.player)}</div>
                          <div style={{ fontSize: 12, color: "#9ca3af" }}>
                            Stat:{" "}
                            <span style={{ color: "#e5e7eb", fontWeight: 800 }}>
                              {String(f.stat)}
                            </span>{" "}
                            • Avg:{" "}
                            <span style={{ color: "#e5e7eb", fontWeight: 800 }}>
                              {String(formatMaybeNumber(f.average))}
                            </span>{" "}
                            • Last N:{" "}
                            <span style={{ color: "#e5e7eb", fontWeight: 800 }}>{lastN}</span>
                          </div>
                        </div>

                        <span
                          style={{
                            fontSize: 12,
                            padding: "5px 10px",
                            borderRadius: 999,
                            fontWeight: 900,
                            ...trendDirBadgeStyle(dir),
                          }}
                        >
                          {String(dir).toUpperCase()}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: "#9ca3af" }}>
                  Trends are enabled, but no player trends were returned.
                </div>
              )}
            </div>

            {/* Team trends list */}
            <div>
              <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6 }}>
                Team Trends (top {Math.min(teamTrendsTop.length, 5)}):
              </div>

              {teamTrendsTop.length ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {teamTrendsTop.map((t, idx) => {
                    const f = extractTeamTrendFields(t);
                    const dir = normalizeDirection(f.direction);
                    const lastN = f.lastN === null || f.lastN === undefined ? "—" : String(f.lastN);

                    return (
                      <div
                        key={`tt-${idx}`}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 10,
                          alignItems: "center",
                          border: "1px solid #334155",
                          background: "rgba(0,0,0,0.18)",
                          borderRadius: 12,
                          padding: "10px 12px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ fontSize: 13, fontWeight: 900 }}>{String(f.team)}</div>
                          <div style={{ fontSize: 12, color: "#9ca3af" }}>
                            Stat:{" "}
                            <span style={{ color: "#e5e7eb", fontWeight: 800 }}>
                              {String(f.stat)}
                            </span>{" "}
                            • Avg:{" "}
                            <span style={{ color: "#e5e7eb", fontWeight: 800 }}>
                              {String(formatMaybeNumber(f.average))}
                            </span>{" "}
                            • Last N:{" "}
                            <span style={{ color: "#e5e7eb", fontWeight: 800 }}>{lastN}</span>
                          </div>
                        </div>

                        <span
                          style={{
                            fontSize: 12,
                            padding: "5px 10px",
                            borderRadius: 999,
                            fontWeight: 900,
                            ...trendDirBadgeStyle(dir),
                          }}
                        >
                          {String(dir).toUpperCase()}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: "#9ca3af" }}>
                  Trends are enabled, but no team trends were returned.
                </div>
              )}
            </div>

            {trendsSoftError ? (
              <div
                style={{
                  fontSize: 12,
                  color: "#cbd5e1",
                  border: "1px dashed #334155",
                  borderRadius: 12,
                  padding: 12,
                  background: "rgba(0,0,0,0.12)",
                }}
              >
                <span style={{ fontWeight: 900 }}>Note:</span> {String(trendsSoftError)}
              </div>
            ) : null}
          </div>
        )}
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
          <span style={{ color: "#e5e7eb", fontWeight: 700 }}>{generatedAt}</span>
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
