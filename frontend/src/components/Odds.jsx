// frontend/src/components/Odds.jsx
import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function safeLocalTimeLabel(isoDateString, fallbackTime) {
  try {
    if (!isoDateString) return fallbackTime || "—";
    const d = new Date(isoDateString);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return fallbackTime || "—";
  }
}

function safeLocalDateLabel(isoDateString) {
  try {
    if (!isoDateString) return null;
    const d = new Date(isoDateString);
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

export default function Odds() {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);        // initial load
  const [refreshing, setRefreshing] = useState(false); // button refresh
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const styles = {
    page: {
      color: "#ffffff",
      maxWidth: 980,
      margin: "0 auto",
      padding: 24,
    },
    badge: {
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      padding: "6px 10px",
      borderRadius: 999,
      border: "1px solid rgba(56,189,248,0.45)",
      background: "rgba(7,89,133,0.35)",
      color: "rgba(224,242,254,0.95)",
      fontSize: 12,
      marginBottom: 12,
    },
    headerRow: {
      display: "flex",
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "flex-start",
      gap: 16,
      flexWrap: "wrap",
      marginBottom: 16,
    },
    title: {
      fontSize: 26,
      fontWeight: 800,
      margin: 0,
    },
    subText: {
      fontSize: 14,
      color: "rgba(209,213,219,0.95)",
      marginTop: 6,
    },
    hintText: {
      fontSize: 12,
      color: "rgba(156,163,175,0.95)",
      marginTop: 6,
    },
    rightHeader: {
      display: "flex",
      alignItems: "center",
      gap: 12,
    },
    lastUpdated: {
      fontSize: 12,
      color: "rgba(156,163,175,0.95)",
      whiteSpace: "nowrap",
    },
    button: (disabled) => ({
      padding: "8px 12px",
      borderRadius: 10,
      fontWeight: 700,
      border: "1px solid rgba(59,130,246,0.55)",
      background: disabled ? "rgba(55,65,81,0.85)" : "rgba(37,99,235,0.95)",
      color: disabled ? "rgba(209,213,219,0.95)" : "#fff",
      cursor: disabled ? "not-allowed" : "pointer",
    }),
    list: {
      display: "flex",
      flexDirection: "column",
      gap: 14,
      marginTop: 8,
    },
    card: {
      borderRadius: 18,
      border: "1px solid rgba(75,85,99,0.9)",
      background: "rgba(17,24,39,0.85)",
      padding: 16,
      boxShadow: "0 12px 30px rgba(0,0,0,0.35)",
    },
    cardRow: {
      display: "flex",
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "flex-start",
      gap: 16,
      flexWrap: "wrap",
    },
    matchup: {
      fontSize: 18,
      fontWeight: 800,
      margin: 0,
    },
    metaLine: {
      marginTop: 6,
      fontSize: 12,
      color: "rgba(156,163,175,0.95)",
    },
    venueLine: {
      marginTop: 10,
      fontSize: 14,
      color: "rgba(209,213,219,0.95)",
    },
    gameId: {
      marginTop: 6,
      fontSize: 12,
      color: "rgba(107,114,128,0.95)",
    },
    chipRow: {
      display: "flex",
      gap: 10,
      flexWrap: "wrap",
      justifyContent: "flex-end",
    },
    chip: {
      padding: "6px 10px",
      borderRadius: 999,
      border: "1px solid rgba(75,85,99,0.9)",
      background: "rgba(0,0,0,0.25)",
      fontSize: 13,
      color: "#fff",
      whiteSpace: "nowrap",
    },
    errorBox: {
      maxWidth: 980,
      margin: "0 auto",
      padding: 24,
      color: "#fecaca",
    },
  };

  const fetchTodayGames = async ({ isRefresh = false } = {}) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);

      setError(null);

      const url = `${API_BASE}/nba/games/today`;
      console.log("🔍 [Odds] Fetching today's slate from:", url);

      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);

      const data = await res.json();
      console.log("📦 [Odds] /nba/games/today response:", data);

      if (!data.ok) throw new Error(data.error || "Backend returned ok: false");

      setGames(Array.isArray(data.games) ? data.games : []);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }));
    } catch (err) {
      console.error("❌ [Odds] Error loading today's games:", err);
      setError(err?.message || "Failed to fetch today's slate");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTodayGames({ isRefresh: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sortedGames = useMemo(() => {
    if (!Array.isArray(games)) return [];
    return [...games].sort((a, b) => {
      const ta = typeof a?.timestamp === "number" ? a.timestamp : null;
      const tb = typeof b?.timestamp === "number" ? b.timestamp : null;
      if (ta != null && tb != null) return ta - tb;

      const da = a?.date ? new Date(a.date).getTime() : null;
      const db = b?.date ? new Date(b.date).getTime() : null;
      if (da != null && db != null) return da - db;

      return 0;
    });
  }, [games]);

  const slateDateLabel = safeLocalDateLabel(sortedGames?.[0]?.date);
  const slateTimezone = sortedGames?.[0]?.timezone || "—";
  const gamesCount = sortedGames.length;

  if (loading) return <div style={styles.page}>⏳ Loading today&apos;s NBA slate...</div>;

  if (error) {
    return (
      <div style={styles.errorBox}>
        <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 8 }}>
          ❌ Error loading today&apos;s games
        </div>
        <div style={{ fontSize: 13, marginBottom: 14 }}>{error}</div>
        <button style={styles.button(false)} onClick={() => fetchTodayGames({ isRefresh: true })}>
          Retry
        </button>
      </div>
    );
  }

  if (!gamesCount) return <div style={styles.page}>No NBA games found for today.</div>;

  return (
    <div style={styles.page}>
      <div style={styles.badge}>
        <span>📡</span>
        <span>Data source: API-Basketball (Pro)</span>
      </div>

      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.title}>
            📅 Today&apos;s NBA Slate{slateDateLabel ? ` • ${slateDateLabel}` : ""}
          </h1>

          <div style={styles.subText}>
            Showing <span style={{ fontWeight: 800, color: "#fff" }}>{gamesCount}</span> games •
            Timezone: <span style={{ fontWeight: 800, color: "#fff" }}>{slateTimezone}</span>
          </div>

          <div style={styles.hintText}>
            Tip times render in your browser&apos;s local time. Status is provider-derived.
          </div>
        </div>

        <div style={styles.rightHeader}>
          <div style={styles.lastUpdated}>
            Last updated:{" "}
            <span style={{ fontWeight: 800, color: "rgba(229,231,235,0.95)" }}>
              {lastUpdated || "—"}
            </span>
          </div>

          <button
            onClick={() => fetchTodayGames({ isRefresh: true })}
            disabled={refreshing}
            title="Refresh today's slate"
            style={styles.button(refreshing)}
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      <div style={styles.list}>
        {sortedGames.map((game) => {
          const key = game?.id ?? `${game?.away_team?.name}-${game?.home_team?.name}-${game?.date}`;
          const away = game?.away_team?.name || "Away Team";
          const home = game?.home_team?.name || "Home Team";
          const venue = game?.venue || "—";
          const leagueName = game?.league?.name || "NBA";
          const season = game?.league?.season || "—";
          const tz = game?.timezone || "—";
          const status = game?.status?.long || game?.status?.short || "Scheduled";

          const tipLabel = safeLocalTimeLabel(game?.date, game?.time);

          return (
            <div key={key} style={styles.card}>
              <div style={styles.cardRow}>
                <div style={{ minWidth: 320 }}>
                  <p style={styles.matchup}>
                    {away} @ {home}
                  </p>

                  <div style={styles.metaLine}>
                    {leagueName} • {season} • {tz}
                  </div>

                  <div style={styles.venueLine}>
                    <span style={{ color: "rgba(156,163,175,0.95)" }}>Venue:</span>{" "}
                    <span style={{ fontWeight: 800, color: "rgba(229,231,235,0.95)" }}>
                      {venue}
                    </span>
                  </div>

                  <div style={styles.gameId}>Game ID: {game?.id ?? "—"}</div>
                </div>

                <div style={styles.chipRow}>
                  <div style={styles.chip}>
                    Tip: <span style={{ fontWeight: 800 }}>{tipLabel}</span>
                  </div>
                  <div style={styles.chip}>
                    Status: <span style={{ fontWeight: 800 }}>{status}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
