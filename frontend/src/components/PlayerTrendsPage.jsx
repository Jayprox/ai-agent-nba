import React, { useEffect, useState } from "react";

const MOCK_URL = "http://127.0.0.1:8000/nba/player/trends";
// future live endpoint (placeholder)
const LIVE_URL = "http://127.0.0.1:8000/nba/player/trends?mode=live";

const PlayerTrendsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [useLive, setUseLive] = useState(false); // 🔄 toggle live/mock

  const fetchTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(useLive ? LIVE_URL : MOCK_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // fetch on mount or toggle change
  useEffect(() => {
    fetchTrends();
  }, [useLive]);

  if (loading)
    return (
      <div style={{ color: "#ccc", padding: "2rem" }}>
        Loading player trend data...
      </div>
    );
  if (error)
    return (
      <div style={{ color: "red", padding: "2rem" }}>
        Error loading trends: {error}
      </div>
    );

  return (
    <div style={{ color: "#fff", backgroundColor: "#000", minHeight: "100vh", padding: "2rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
        }}
      >
        <h1>🏀 Player Trend Analysis ({useLive ? "Live" : "Mock"})</h1>
        <div style={{ display: "flex", gap: "1rem" }}>
          <button
            onClick={() => setUseLive((prev) => !prev)}
            style={{
              padding: "0.4rem 1rem",
              borderRadius: "6px",
              border: "1px solid #333",
              backgroundColor: useLive ? "#1e90ff" : "#444",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            {useLive ? "🔵 Live Mode" : "⚪ Mock Mode"}
          </button>

          <button
            onClick={fetchTrends}
            style={{
              padding: "0.4rem 1rem",
              borderRadius: "6px",
              border: "1px solid #333",
              backgroundColor: "#222",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            ♻️ Refresh
          </button>
        </div>
      </div>

      <p>Generated: {data.generated_at}</p>
      <hr style={{ margin: "1rem 0", borderColor: "#333" }} />

      <ul>
        {data.summary.map((p, idx) => (
          <li
            key={idx}
            style={{
              margin: "1rem 0",
              border: "1px solid #222",
              borderRadius: "8px",
              padding: "1rem",
              backgroundColor: "#111",
            }}
          >
            <strong style={{ color: "#4fc3f7" }}>{p.player_name}</strong>
            <ul style={{ listStyleType: "none", paddingLeft: "0.8rem" }}>
              <li>PPG: {p.ppg}</li>
              <li>Season PPG: {p.season_ppg}</li>
              <li>Trend: {p.trend}</li>
              <li>Verdict: {p.verdict}</li>
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PlayerTrendsPage;
