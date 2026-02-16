import React, { useEffect, useState } from "react";
import { API_BASE_URL } from "../config/api";

const MOCK_URL = `${API_BASE_URL}/nba/player/insights`;
const LIVE_URL = `${API_BASE_URL}/nba/player/insights/live`; // placeholder for live data later


const PlayerInsightsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [useLive, setUseLive] = useState(true);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const endpoint = useLive ? LIVE_URL : MOCK_URL;
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, [useLive]);

  if (loading)
    return (
      <div style={{ color: "#ccc", padding: "1rem" }}>
        Loading player insights...
      </div>
    );

  if (error)
    return (
      <div style={{ color: "red", padding: "1rem" }}>
        Error loading insights: {error}
      </div>
    );

  if (!data)
    return (
      <div style={{ color: "#888", padding: "1rem" }}>
        No insights available.
      </div>
    );

  return (
    <div
      style={{
        backgroundColor: "#000",
        color: "#fff",
        minHeight: "100vh",
        padding: "2rem",
        fontFamily: "system-ui",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h1>🏀 Player Insights ({useLive ? "Live" : "Mock"})</h1>
        <div>
          <button
            onClick={() => setUseLive((prev) => !prev)}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              border: "1px solid #444",
              backgroundColor: useLive ? "#1e90ff" : "#444",
              color: "#fff",
              cursor: "pointer",
              marginRight: "0.5rem",
            }}
          >
            {useLive ? "🔵 Live Mode" : "⚪ Mock Mode"}
          </button>

          <button
            onClick={fetchInsights}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              border: "1px solid #444",
              backgroundColor: "#222",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Timestamp */}
      <p style={{ color: "#888" }}>Generated: {data.generated_at}</p>
      <hr style={{ margin: "1rem 0" }} />

      {/* Player Cards */}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {data.insights.map((p, idx) => (
          <li
            key={idx}
            style={{
              border: "1px solid #333",
              borderRadius: "10px",
              padding: "1rem",
              marginBottom: "1rem",
              backgroundColor: "#1a1a1a",
            }}
          >
            <h3 style={{ color: "#1e90ff" }}>{p.player_name}</h3>
            <p>PPG: {p.ppg}</p>
            <p>RPG: {p.rpg}</p>
            <p>APG: {p.apg}</p>
            <p>3PM: {p.tpm}</p>
            <p>Season PPG: {p.season_ppg}</p>
            <p>Trend: {p.trend}</p>
            <p>Verdict: {p.verdict}</p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PlayerInsightsPage;
