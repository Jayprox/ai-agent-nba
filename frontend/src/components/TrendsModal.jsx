import { useEffect, useState } from "react";
import { API_BASE_URL } from "../config/api";

const modalOverlay = {
  position: "fixed",
  top: 0,
  left: 0,
  width: "100vw",
  height: "100vh",
  backgroundColor: "rgba(0,0,0,0.7)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  zIndex: 999,
};

const modalContent = {
  backgroundColor: "#111",
  color: "#fff",
  width: "90%",
  maxWidth: "600px",
  maxHeight: "80vh",
  borderRadius: "10px",
  padding: "1rem",
  overflowY: "auto",
  boxShadow: "0 4px 20px rgba(0,0,0,0.6)",
};

const TrendsModal = ({ teamName, onClose }) => {
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

useEffect(() => {
  if (!teamName) return;

  const fetchTrends = async () => {
    try {
      const res = await fetch(
        `${API_BASE_URL}/nba/trends/live?team=${encodeURIComponent(teamName)}`
      );
      if (!res.ok) throw new Error("Failed to fetch trends data");
      const data = await res.json();
      setTrends(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  fetchTrends();
}, [teamName]);

  if (!teamName) return null;

  return (
    <div style={modalOverlay} onClick={onClose}>
      <div
        style={modalContent}
        onClick={(e) => e.stopPropagation()} // prevent closing when clicking inside
      >
        <button
          onClick={onClose}
          style={{
            float: "right",
            background: "none",
            color: "#fff",
            border: "none",
            fontSize: "1.2rem",
            cursor: "pointer",
          }}
        >
          ✕
        </button>

        <h2 style={{ marginTop: "0", color: "#fff" }}>📊 {teamName} Trends</h2>

        {loading && <p style={{ color: "#aaa" }}>Loading trends...</p>}
        {error && <p style={{ color: "red" }}>Error: {error}</p>}

        {!loading && !error && trends && (
          <>
            <p style={{ color: "#888" }}>Generated: {trends.date_generated}</p>

            <section style={{ marginTop: "1rem" }}>
              <h3 style={{ color: "#eee" }}>Player Trends</h3>
              {trends.player_trends.map((p, index) => (
                <div
                  key={index}
                  style={{
                    background: "#1c1c1c",
                    margin: "0.5rem 0",
                    padding: "0.75rem",
                    borderRadius: "8px",
                  }}
                >
                  <h4>{p.player_name}</h4>
                  <p>
                    <strong>{p.stat_type}</strong>: {p.average} avg (
                    {p.trend_direction})
                  </p>
                  <small>Last {p.last_n_games} games</small>
                </div>
              ))}
            </section>

            <section style={{ marginTop: "1.5rem" }}>
              <h3 style={{ color: "#eee" }}>Team Trends</h3>
              {trends.team_trends.map((t, index) => (
                <div
                  key={index}
                  style={{
                    background: "#1c1c1c",
                    margin: "0.5rem 0",
                    padding: "0.75rem",
                    borderRadius: "8px",
                  }}
                >
                  <h4>{t.team_name}</h4>
                  <p>
                    <strong>{t.stat_type}</strong>: {t.average} avg (
                    {t.trend_direction})
                  </p>
                  <small>Last {t.last_n_games} games</small>
                </div>
              ))}
            </section>
          </>
        )}
      </div>
    </div>
  );
};

export default TrendsModal;
