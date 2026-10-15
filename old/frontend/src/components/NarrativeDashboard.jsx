// frontend/src/components/NarrativeDashboard.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { API_BASE_URL } from "../config/api";

// -----------------------------
// Storage keys
// -----------------------------
const LS_TRENDS_OVERRIDE = "narrative.trendsOverride"; // "default" | "on" | "off"
const LS_COMPACT = "narrative.compact"; // "1" | "0"
const LS_CACHE_TTL = "narrative.cacheTtl"; // "0" | "15" | "60" | "120"
const LS_SHOW_CONTRACT = "narrative.showContract"; // "1" | "0"
const LS_SHOW_TRENDS_PREVIEW = "narrative.showTrendsPreview"; // "1" | "0"

const ALLOWED_TTLS = [0, 15, 60, 120];
const SOFT_ERROR_LABELS = {
  ai: "AI",
  trends: "Trends",
  odds: "Odds",
  games_today: "Games",
  player_props: "Player Props",
  markdown: "Markdown",
  template: "Template",
};
const SOURCE_LABELS = {
  games_today: "Games",
  odds: "Odds",
  trends: "Trends",
  player_props: "Player Props",
};
const SOURCE_STATUS_STYLES = {
  ok: {
    border: "1px solid rgba(16,185,129,0.35)",
    background: "rgba(16,185,129,0.12)",
    color: "#bbf7d0",
  },
  no_data: {
    border: "1px solid rgba(148,163,184,0.35)",
    background: "rgba(148,163,184,0.12)",
    color: "#e5e7eb",
  },
  disabled: {
    border: "1px solid rgba(251,191,36,0.35)",
    background: "rgba(251,191,36,0.12)",
    color: "#fde68a",
  },
  error: {
    border: "1px solid rgba(239,68,68,0.35)",
    background: "rgba(239,68,68,0.12)",
    color: "#fecaca",
  },
};

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

function loadShowContractFromStorage() {
  try {
    return localStorage.getItem(LS_SHOW_CONTRACT) !== "0";
  } catch {
    return true;
  }
}

function loadShowTrendsPreviewFromStorage() {
  try {
    return localStorage.getItem(LS_SHOW_TRENDS_PREVIEW) !== "0";
  } catch {
    return true;
  }
}

async function copyToClipboard(text) {
  const value = String(text ?? "");
  if (!value) return false;

  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    // fall through
  }

  // Fallback
  try {
    const ta = document.createElement("textarea");
    ta.value = value;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    ta.style.left = "-1000px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
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
  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth : 1024
  );
  const [showContractSnapshot, setShowContractSnapshot] = useState(() =>
    loadShowContractFromStorage()
  );
  const [showTrendsPreview, setShowTrendsPreview] = useState(() =>
    loadShowTrendsPreviewFromStorage()
  );

  // Last-good snapshot (used to avoid "blank page" on error)
  const [lastGood, setLastGood] = useState(null);

  // Copy feedback
  const [copyStatus, setCopyStatus] = useState(null); // string | null
  const copyTimerRef = useRef(null);

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
      localStorage.setItem(LS_SHOW_CONTRACT, showContractSnapshot ? "1" : "0");
      localStorage.setItem(LS_SHOW_TRENDS_PREVIEW, showTrendsPreview ? "1" : "0");
    } catch {
      // no-op
    }
  }, [trendsOverride, compact, cacheTtl, showContractSnapshot, showTrendsPreview]);

  // Abort fetch on unmount
  useEffect(() => {
    return () => {
      try {
        if (abortRef.current) abortRef.current.abort();
      } catch {
        // no-op
      }
      try {
        if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      } catch {
        // no-op
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const onResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const flashCopyStatus = (msg) => {
    setCopyStatus(msg);
    try {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopyStatus(null), 1200);
    } catch {
      // no-op
    }
  };

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

      // cache ttl: use ttlOverride if provided, otherwise use state, default to 0
      const effectiveTtl = typeof ttlOverride === "number" ? ttlOverride : cacheTtl;
      if (effectiveTtl > 0) {
        params.set("cache_ttl", String(effectiveTtl));
      } else {
        params.set("cache_ttl", "0");
      }

      // Only include trends param if override is not null
      if (override === true) params.set("trends", "1");
      if (override === false) params.set("trends", "0");

      const url = `${API_BASE_URL}/nba/narrative/markdown?${params.toString()}`;

      console.log("🔍 [NarrativeDashboard D7] Fetching:", {
        url,
        reason,
        requestId: myRequestId,
      });

      const res = await fetch(url, { signal: controller.signal });

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

      const data = await res.json();

      // If another request has started since this one, ignore this response
      if (myRequestId !== requestIdRef.current) {
        console.log("🟡 [NarrativeDashboard D7] Stale response ignored:", myRequestId);
        return;
      }

      if (!data.ok) throw new Error(data.error || "Backend returned ok: false");
      if (!data.markdown) throw new Error("No markdown field in response");

      const md = data.summary?.metadata || {};
      const rm = data.raw?.meta || {};
      const safeGames = pickGamesArray(data);

      const countFromMeta =
        data.summary?.metadata?.games_today_count ??
        data.raw?.meta?.source_counts?.games_today;

      const count = typeof countFromMeta === "number" ? countFromMeta : safeGames.length;

      const pt = safeArray(data?.raw?.player_trends);
      const tt = safeArray(data?.raw?.team_trends);

      // Commit UI state
      setMarkdown(data.markdown);
      setMeta(md);
      setRawMeta(rm);
      setGamesToday(safeGames);
      setGamesTodayCount(count);
      setPlayerTrends(pt);
      setTeamTrends(tt);

      // Update last-good snapshot
      setLastGood({
        markdown: data.markdown,
        meta: md,
        rawMeta: rm,
        gamesToday: safeGames,
        gamesTodayCount: count,
        playerTrends: pt,
        teamTrends: tt,
        savedAt: new Date().toISOString(),
      });

      // Sync local toggle state with backend, if present
      if (Object.prototype.hasOwnProperty.call(rm || {}, "trends_override")) {
        setTrendsOverride(parseTrendsOverride(rm?.trends_override));
      }

      console.log("✅ [NarrativeDashboard D7] Loaded:", {
        requestId: myRequestId,
        games_today_count: count,
        trends_override: rm?.trends_override,
        trends_enabled_in_narrative: rm?.trends_enabled_in_narrative,
        player_trends_len: pt.length,
        team_trends_len: tt.length,
      });
    } catch (err) {
      if (err?.name === "AbortError") {
        console.log("🟡 [NarrativeDashboard D7] Fetch aborted (expected).");
        return;
      }
      console.error("❌ [NarrativeDashboard D7] Fetch error:", err);

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
    console.log("🧩 [NarrativeDashboard D7] Mount. API_BASE_URL =", API_BASE_URL);
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

  const onRetry = () => {
    setIsRegenerating(true);
    fetchMarkdown({ forceRefresh: true, reason: "retry" });
  };

  const onCopyMarkdown = async (text) => {
    const ok = await copyToClipboard(text);
    flashCopyStatus(ok ? "Copied" : "Copy failed");
  };

  // -----------------------------
  // Derived values (NO HOOKS)
  // These must be safe even during loading/error renders.
  // -----------------------------
  const displayMarkdown = markdown || lastGood?.markdown || "";
  const displayMeta = Object.keys(meta || {}).length ? meta : lastGood?.meta || {};
  const displayRawMeta =
    Object.keys(rawMeta || {}).length ? rawMeta : lastGood?.rawMeta || {};
  const displayGamesToday = Array.isArray(gamesToday) && gamesToday.length
    ? gamesToday
    : lastGood?.gamesToday || [];
  const displayGamesTodayCount =
    typeof gamesTodayCount === "number" && gamesTodayCount > 0
      ? gamesTodayCount
      : lastGood?.gamesTodayCount || 0;

  const safePlayerTrends = safeArray(
    (Array.isArray(playerTrends) && playerTrends.length ? playerTrends : lastGood?.playerTrends) || []
  );
  const safeTeamTrends = safeArray(
    (Array.isArray(teamTrends) && teamTrends.length ? teamTrends : lastGood?.teamTrends) || []
  );

  const playerTrendsTop = safePlayerTrends.slice(0, 5);
  const teamTrendsTop = safeTeamTrends.slice(0, 5);

  const playerTrendsCount = safePlayerTrends.length;
  const teamTrendsCount = safeTeamTrends.length;

  const backendTrendsEnabled = !!displayRawMeta?.trends_enabled_in_narrative;
  const trendsSoftError = displayRawMeta?.soft_errors?.trends || null;

  // Contract snapshot fields
  const latencyMs = formatMaybeNumber(displayRawMeta?.latency_ms);
  const cacheUsed = displayRawMeta?.cache_used;
  const cacheTtlS = displayRawMeta?.cache_ttl_s;
  const sourceCounts = displayRawMeta?.source_counts || {};
  const scGames = sourceCounts?.games_today;
  const scPlayerTrends = sourceCounts?.player_trends;
  const scTeamTrends = sourceCounts?.team_trends;
  const scPlayerProps = sourceCounts?.player_props;
  const scOddsGames = sourceCounts?.odds_games;

  // Phase 4: Enhanced observability
  const softErrors = displayRawMeta?.soft_errors || {};
  const softErrorEntries = Object.entries(softErrors).filter(
    ([key, value]) => SOFT_ERROR_LABELS[key] && String(value || "").trim() !== ""
  );
  const sourceStatus = displayRawMeta?.source_status || {};
  const sourceStatusEntries = Object.entries(sourceStatus).filter(
    ([key]) => SOURCE_LABELS[key]
  );
  const sourceStatusSummary = sourceStatusEntries.reduce(
    (acc, [, value]) => {
      const status = String(value?.status || "no_data");
      if (status === "ok") acc.ok += 1;
      else if (status === "error") acc.error += 1;
      else if (status === "disabled") acc.disabled += 1;
      else acc.noData += 1;
      return acc;
    },
    { ok: 0, error: 0, disabled: 0, noData: 0 }
  );
  const diagnosticsLevel =
    softErrorEntries.length > 0 || sourceStatusSummary.error > 0
      ? "attention"
      : sourceStatusSummary.noData > 0 || sourceStatusSummary.disabled > 0
      ? "partial"
      : "healthy";
  const diagnosticsLabel =
    diagnosticsLevel === "attention"
      ? "Attention"
      : diagnosticsLevel === "partial"
      ? "Partial Data"
      : "Healthy";
  const diagnosticsStyle =
    diagnosticsLevel === "attention"
      ? {
          border: "1px solid rgba(239,68,68,0.35)",
          background: "rgba(239,68,68,0.12)",
          color: "#fecaca",
        }
      : diagnosticsLevel === "partial"
      ? {
          border: "1px solid rgba(251,191,36,0.35)",
          background: "rgba(251,191,36,0.12)",
          color: "#fde68a",
        }
      : {
          border: "1px solid rgba(16,185,129,0.35)",
          background: "rgba(16,185,129,0.12)",
          color: "#bbf7d0",
        };
  const contractVersion = displayRawMeta?.contract_version || "—";
  const requestId = displayRawMeta?.request_id || "—";
  const cacheExpiresInS = displayRawMeta?.cache_expires_in_s;
  const cacheKey = displayRawMeta?.cache_key || "—";

  if (loading) {
    return (
      <div style={{ padding: 16, color: "white" }}>
        ⏳ Generating narrative...
      </div>
    );
  }

  // If we have no last-good and no markdown to show, then a hard error view is reasonable.
  if (error && !displayMarkdown) {
    return (
      <div style={{ padding: 16, color: "#fca5a5" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>❌ Error</h2>
        <p style={{ marginBottom: 12 }}>{error}</p>
        <button
          onClick={onRetry}
          disabled={isRegenerating}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            fontWeight: 800,
            border: "1px solid #334155",
            background: isRegenerating ? "#111827" : "#2563eb",
            color: isRegenerating ? "#9ca3af" : "white",
            cursor: isRegenerating ? "not-allowed" : "pointer",
          }}
        >
          {isRegenerating ? "Retrying..." : "Retry"}
        </button>
      </div>
    );
  }

  const generatedAt = safeToLocalString(displayMeta?.generated_at);
  const slateDateLabel = guessSlateDateLabel(displayGamesToday);
  const slateTz = pickTimezone(displayGamesToday, displayRawMeta?.timezone);
  const matchups = buildMatchups(displayGamesToday, 5);
  const isMobile = viewportWidth < 768;
  const containerPad = isMobile ? 14 : 24;
  const cardPad = isMobile ? 12 : 14;
  const sectionGap = isMobile ? 8 : 10;
  const trendsRowPad = isMobile ? "8px 10px" : "9px 11px";
  const trendsTitleSize = isMobile ? 12 : 13;
  const trendsMetaSize = isMobile ? 11 : 12;
  const trendsBadgePad = isMobile ? "4px 8px" : "5px 10px";

  return (
    <div style={{ padding: containerPad, color: "white", maxWidth: 980, margin: "0 auto" }}>
      {/* Error banner (but keep rendering last-good) */}
      {error ? (
        <div
          style={{
            marginBottom: 14,
            borderRadius: 14,
            border: "1px solid rgba(239,68,68,0.35)",
            background: "rgba(185,28,28,0.15)",
            padding: 12,
            color: "#fecaca",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
            <div style={{ fontSize: 12 }}>
              <span style={{ fontWeight: 900 }}>Fetch failed:</span> {String(error)}
              {lastGood?.savedAt ? (
                <span style={{ color: "#cbd5e1" }}>
                  {" "}
                  • Showing last successful narrative from{" "}
                  <span style={{ fontWeight: 900, color: "white" }}>
                    {safeToLocalString(lastGood.savedAt)}
                  </span>
                </span>
              ) : null}
            </div>

            <button
              onClick={onRetry}
              disabled={isRegenerating}
              style={{
                ...btnBase,
                padding: "8px 12px",
                background: isRegenerating ? "#111827" : "rgba(239,68,68,0.15)",
                color: isRegenerating ? "#9ca3af" : "#fee2e2",
                cursor: isRegenerating ? "not-allowed" : "pointer",
              }}
              title="Retry (force refresh)"
            >
              {isRegenerating ? "Retrying..." : "Retry"}
            </button>
          </div>
        </div>
      ) : null}

      {/* Header + Actions */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: isMobile ? 10 : 12,
          marginBottom: isMobile ? 12 : 16,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h1 style={{ fontSize: isMobile ? 18 : 22, fontWeight: 800, margin: 0 }}>
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
              Version: D7
            </span>

            {copyStatus ? (
              <span
                style={{
                  fontSize: 12,
                  padding: "3px 8px",
                  borderRadius: 999,
                  border: "1px solid rgba(148,163,184,0.35)",
                  background: "rgba(148,163,184,0.12)",
                  color: "#e5e7eb",
                }}
              >
                {copyStatus}
              </span>
            ) : null}
          </div>

          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            Resilient UI: Retry + last-good fallback + copy tools. Controls:{" "}
            <code style={{ color: "#e5e7eb" }}>trends</code>,{" "}
            <code style={{ color: "#e5e7eb" }}>compact</code>,{" "}
            <code style={{ color: "#e5e7eb" }}>cache_ttl</code>.
          </div>
        </div>

        <div style={{ display: "flex", gap: sectionGap, flexWrap: "wrap", alignItems: "center", width: isMobile ? "100%" : "auto" }}>
          {/* Copy buttons */}
          <button
            onClick={() => onCopyMarkdown(displayMarkdown)}
            style={{
              padding: isMobile ? "8px 10px" : "10px 12px",
              borderRadius: 10,
              fontWeight: 800,
              border: "1px solid #334155",
              background: "rgba(11,18,32,0.85)",
              color: "#e5e7eb",
              cursor: "pointer",
            }}
            title="Copy the rendered markdown to clipboard"
          >
            Copy Markdown
          </button>

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
              width: isMobile ? "100%" : "auto",
              overflowX: isMobile ? "auto" : "visible",
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
              gap: sectionGap,
              alignItems: "center",
              padding: 6,
              borderRadius: 12,
              border: "1px solid #334155",
              background: "rgba(11,18,32,0.85)",
              width: isMobile ? "100%" : "auto",
              flexWrap: "wrap",
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
              padding: isMobile ? "8px 12px" : "10px 14px",
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
          marginBottom: isMobile ? 10 : 12,
          border: "1px solid #334155",
          background: "rgba(17,24,39,0.75)",
          borderRadius: 14,
          padding: cardPad,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: sectionGap,
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
                {displayGamesTodayCount}
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
                {displayRawMeta?.trends_override === null ||
                displayRawMeta?.trends_override === undefined
                  ? "None"
                  : String(displayRawMeta?.trends_override)}
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
            <span style={{ ...pillStyle }}>Mode: {displayRawMeta?.mode || "ai"}</span>
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
          marginBottom: isMobile ? 12 : 16,
          border: "1px solid #334155",
          background: "rgba(11,18,32,0.75)",
          borderRadius: 14,
          padding: cardPad,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: sectionGap,
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 14, fontWeight: 900 }}>Contract Snapshot</div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>
              Quick visibility into <code style={{ color: "#e5e7eb" }}>raw.meta</code> +{" "}
              <code style={{ color: "#e5e7eb" }}>source_counts</code>.
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button
              onClick={() => setShowContractSnapshot((v) => !v)}
              style={{
                ...btnBase,
                background: "rgba(11,18,32,0.85)",
                color: "#e5e7eb",
                cursor: "pointer",
              }}
              title="Show or hide Contract Snapshot details"
            >
              {showContractSnapshot ? "Hide" : "Show"}
            </button>
            <button
              onClick={() => onCopyMarkdown(String(requestId))}
              style={{
                ...btnBase,
                background: "rgba(11,18,32,0.85)",
                color: "#e5e7eb",
                cursor: "pointer",
              }}
              title="Copy request ID"
            >
              Copy Request ID
            </button>
            <button
              onClick={() => onCopyMarkdown(String(cacheKey))}
              style={{
                ...btnBase,
                background: "rgba(11,18,32,0.85)",
                color: "#e5e7eb",
                cursor: "pointer",
              }}
              title="Copy cache key"
            >
              Copy Cache Key
            </button>
            <button
              onClick={() =>
                onCopyMarkdown(
                  JSON.stringify(
                    {
                      request_id: requestId,
                      cache_key: cacheKey,
                      source_counts: sourceCounts,
                      source_status: sourceStatus,
                      soft_errors: softErrors,
                    },
                    null,
                    2
                  )
                )
              }
              style={{
                ...btnBase,
                background: "rgba(11,18,32,0.85)",
                color: "#e5e7eb",
                cursor: "pointer",
              }}
              title="Copy core diagnostics snapshot"
            >
              Copy Diagnostics
            </button>
          </div>
        </div>

        {!showContractSnapshot && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 10 }}>
            <span style={{ ...pillStyle, ...diagnosticsStyle }}>Status: {diagnosticsLabel}</span>
            <span style={{ ...pillStyle }}>
              Sources: ok {sourceStatusSummary.ok} • no_data {sourceStatusSummary.noData}
              {sourceStatusSummary.disabled ? ` • disabled ${sourceStatusSummary.disabled}` : ""}
              {sourceStatusSummary.error ? ` • error ${sourceStatusSummary.error}` : ""}
            </span>
            {softErrorEntries.length > 0 && (
              <span style={{ ...pillStyle, border: "1px solid rgba(251,191,36,0.35)", color: "#fde68a" }}>
                soft_errors: {softErrorEntries.length}
              </span>
            )}
            <span style={{ ...pillStyle }}>
              Latency: <span style={{ color: "white", fontWeight: 900 }}>{latencyMs ?? "—"}</span> ms
            </span>
            <span style={{ ...pillStyle }}>
              Cache:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>
                {cacheUsed === true ? "Used" : cacheUsed === false ? "No" : "—"}
              </span>
            </span>
          </div>
        )}

        {showContractSnapshot && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 10 }}>
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

            <span style={{ ...pillStyle }} title="raw.meta.source_counts.player_props">
              player_props:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{scPlayerProps ?? "—"}</span>
            </span>

            <span style={{ ...pillStyle }} title="raw.meta.source_counts.odds_games">
              odds_games:{" "}
              <span style={{ color: "white", fontWeight: 900 }}>{scOddsGames ?? "—"}</span>
            </span>
          </div>
        )}

        {showContractSnapshot && sourceStatusEntries.length > 0 && (
          <div
            style={{
              marginTop: 12,
              border: "1px dashed #334155",
              borderRadius: 12,
              padding: 12,
              background: "rgba(0,0,0,0.12)",
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 900, color: "#cbd5e1", marginBottom: 8 }}>
              Source Status
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {sourceStatusEntries.map(([key, value]) => {
                const status = String(value?.status || "no_data");
                const count = Number.isFinite(Number(value?.count)) ? Number(value?.count) : 0;
                const err = String(value?.error || "").trim();
                const style = SOURCE_STATUS_STYLES[status] || SOURCE_STATUS_STYLES.no_data;
                return (
                  <span key={key} style={{ ...pillStyle, ...style }} title={err || `${SOURCE_LABELS[key]} status`}>
                    {SOURCE_LABELS[key]}: {status} ({count})
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Phase 4: Enhanced Soft Errors Display */}
        {showContractSnapshot && softErrorEntries.length > 0 && (
          <div
            style={{
              marginTop: 12,
              fontSize: 12,
              color: "#cbd5e1",
              border: "1px dashed #fbbf24",
              borderRadius: 12,
              padding: 12,
              background: "rgba(251, 191, 36, 0.08)",
            }}
          >
            <div style={{ fontWeight: 900, color: "#fbbf24", marginBottom: 8, display: "flex", alignItems: "center", gap: 6, justifyContent: "space-between" }}>
              <span>⚠️ Soft Errors Detected ({softErrorEntries.length})</span>
              <button
                onClick={() => onCopyMarkdown(JSON.stringify(softErrors, null, 2))}
                style={{
                  ...btnBase,
                  padding: "6px 10px",
                  background: "rgba(251,191,36,0.15)",
                  color: "#fde68a",
                  border: "1px solid rgba(251,191,36,0.4)",
                  cursor: "pointer",
                }}
                title="Copy raw.meta.soft_errors JSON"
              >
                Copy soft_errors
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {softErrorEntries.map(([key, value]) => (
                <div key={key} style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                  <span style={{ color: "#fbbf24", fontWeight: 800 }}>{SOFT_ERROR_LABELS[key]}:</span>
                  <span>{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Phase 4: Cache Status Indicator */}
        {showContractSnapshot && cacheUsed !== undefined && (
          <div
            style={{
              marginTop: 12,
              fontSize: 12,
              color: "#cbd5e1",
              border: cacheUsed ? "1px solid #10b981" : "1px dashed #64748b",
              borderRadius: 12,
              padding: 12,
              background: cacheUsed ? "rgba(16, 185, 129, 0.08)" : "rgba(0,0,0,0.12)",
            }}
          >
            <div style={{ fontWeight: 900, color: cacheUsed ? "#10b981" : "#94a3b8", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
              {cacheUsed ? "✅ Cache Hit" : "🔄 Cache Miss"}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {cacheUsed && cacheExpiresInS !== undefined && (
                <div>
                  <span style={{ color: "#94a3b8" }}>Expires in:</span>{" "}
                  <span style={{ fontWeight: 800, color: "white" }}>{cacheExpiresInS}s</span>
                </div>
              )}
              <div style={{ wordBreak: "break-all", color: "#64748b", fontSize: 11 }}>
                <span style={{ color: "#94a3b8" }}>Key:</span> {cacheKey}
              </div>
            </div>
          </div>
        )}

        {/* Phase 4: Contract Version & Request ID */}
        {showContractSnapshot && (
        <div
          style={{
            marginTop: 12,
            fontSize: 11,
            color: "#64748b",
            display: "flex",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div>
            <span style={{ color: "#94a3b8" }}>Contract:</span>{" "}
            <span style={{ fontWeight: 700, color: "#cbd5e1" }}>{contractVersion}</span>
          </div>
          <div style={{ wordBreak: "break-all" }}>
            <span style={{ color: "#94a3b8" }}>Request ID:</span>{" "}
            <span style={{ fontWeight: 700, color: "#cbd5e1", fontFamily: "monospace" }}>{requestId}</span>
          </div>
        </div>
        )}
      </div>

      {/* Trends Preview */}
      <div
        style={{
          marginBottom: isMobile ? 12 : 16,
          border: "1px solid #334155",
          background: "rgba(17,24,39,0.55)",
          borderRadius: 14,
          padding: cardPad,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: sectionGap,
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
            <button
              onClick={() => setShowTrendsPreview((v) => !v)}
              style={{
                ...btnBase,
                background: "rgba(11,18,32,0.85)",
                color: "#e5e7eb",
                cursor: "pointer",
              }}
              title="Show or hide Trends Preview details"
            >
              {showTrendsPreview ? "Hide" : "Show"}
            </button>
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

        {showTrendsPreview && !backendTrendsEnabled ? (
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
        ) : showTrendsPreview ? (
          <div style={{ display: "flex", flexDirection: "column", gap: isMobile ? 10 : 12 }}>
            {/* Player trends list */}
            <div>
              <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6 }}>
                Player Trends (top {Math.min(playerTrendsTop.length, 5)}):
              </div>

              {playerTrendsTop.length ? (
                <div style={{ display: "flex", flexDirection: "column", gap: isMobile ? 6 : 8 }}>
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
                          gap: isMobile ? 8 : 10,
                          alignItems: "center",
                          border: "1px solid #334155",
                          background: "rgba(0,0,0,0.18)",
                          borderRadius: 12,
                          padding: trendsRowPad,
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "flex", flexDirection: "column", gap: isMobile ? 2 : 3 }}>
                          <div style={{ fontSize: trendsTitleSize, fontWeight: 900 }}>{String(f.player)}</div>
                          <div style={{ fontSize: trendsMetaSize, color: "#9ca3af" }}>
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
                            fontSize: trendsMetaSize,
                            padding: trendsBadgePad,
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
                <div style={{ display: "flex", flexDirection: "column", gap: isMobile ? 6 : 8 }}>
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
                          gap: isMobile ? 8 : 10,
                          alignItems: "center",
                          border: "1px solid #334155",
                          background: "rgba(0,0,0,0.18)",
                          borderRadius: 12,
                          padding: trendsRowPad,
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "flex", flexDirection: "column", gap: isMobile ? 2 : 3 }}>
                          <div style={{ fontSize: trendsTitleSize, fontWeight: 900 }}>{String(f.team)}</div>
                          <div style={{ fontSize: trendsMetaSize, color: "#9ca3af" }}>
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
                            fontSize: trendsMetaSize,
                            padding: trendsBadgePad,
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
        ) : null}
      </div>

      {/* Metadata */}
      <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 12 }}>
        <div>
          Model:{" "}
          <span style={{ color: "#e5e7eb", fontWeight: 700 }}>
            {displayMeta?.model || "Unknown"}
          </span>
        </div>
        <div>
          Generated:{" "}
          <span style={{ color: "#e5e7eb", fontWeight: 700 }}>{generatedAt}</span>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            Digest:{" "}
            <span style={{ color: "#e5e7eb", fontWeight: 700 }}>
              {displayMeta?.inputs_digest || "—"}
            </span>
          </div>

          <button
            onClick={() => onCopyMarkdown(displayMeta?.inputs_digest || "")}
            style={{
              ...btnBase,
              padding: "6px 10px",
              background: "rgba(11,18,32,0.85)",
              color: "#e5e7eb",
              cursor: "pointer",
            }}
            title="Copy inputs_digest"
          >
            Copy Digest
          </button>
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
        <ReactMarkdown>{displayMarkdown}</ReactMarkdown>
      </div>
    </div>
  );
};

export default NarrativeDashboard;
