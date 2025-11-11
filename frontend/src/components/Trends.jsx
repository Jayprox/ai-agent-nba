import React, { useState, useEffect } from "react";

const Trends = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/nba/trends/live");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrends();
  }, []);

  const arrow = (dir) => {
    if (dir === "up") return "🔺";
    if (dir === "down") return "🔻";
    return "⏺️";
  };

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif", color: "white" }}>
      <h2>📈 NBA Trends</h2>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <button
          onClick={fetchTrends}
          disabled={loading}
          style={{
            background: "#007bff",
            color: "white",
            border: "none",
            borderRadius: 6,
            padding: "6px 12px",
            cursor: "pointer",
          }}
        >
          {loading ? "Refreshing..." : "Refresh Trends"}
        </button>

        {lastUpdated && (
          <span style={{ color: "#aaa", fontSize: 14 }}>
            Last updated: {lastUpdated}
          </span>
        )}
      </div>

      {error && <p style={{ color: "red" }}>Error: {error}</p>}

      {data && (
        <>
          <p style={{ fontSize: 14, color: "#ccc" }}>
            Generated: {data.date_generated}
          </p>

          {/* Player Trends */}
          <h3 style={{ marginTop: 20 }}>👤 Player Trends</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {data.player_trends.map((p, i) => (
              <div
                key={i}
                style={{
                  background: "#1a1a1a",
                  padding: 12,
                  borderRadius: 8,
                  boxShadow: "0 0 8px rgba(255,255,255,0.05)",
                }}
              >
                <strong style={{ color: "white" }}>{p.player_name}</strong>
                <p style={{ margin: 0, color: "#bbb" }}>
                  {p.stat_type}: {p.average.toFixed(2)} avg {arrow(p.trend_direction)}{" "}
                  ({p.trend_direction})
                </p>
                <small style={{ color: "#666" }}>
                  Last {p.last_n_games} games • Weighted: {p.weighted_avg.toFixed(2)} • Var:{" "}
                  {p.variance.toFixed(2)}
                </small>
              </div>
            ))}
          </div>

          {/* Team Trends */}
          <h3 style={{ marginTop: 30 }}>🏀 Team Trends</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {data.team_trends.map((t, i) => (
              <div
                key={i}
                style={{
                  background: "#1a1a1a",
                  padding: 12,
                  borderRadius: 8,
                  boxShadow: "0 0 8px rgba(255,255,255,0.05)",
                }}
              >
                <strong style={{ color: "white" }}>{t.team_name}</strong>
                <p style={{ margin: 0, color: "#bbb" }}>
                  {t.stat_type}: {t.average} avg {arrow(t.trend_direction)}{" "}
                  ({t.trend_direction})
                </p>
                <small style={{ color: "#666" }}>
                  Last {t.last_n_games} games
                </small>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default Trends;
