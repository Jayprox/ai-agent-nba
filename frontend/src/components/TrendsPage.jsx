import { useEffect, useState } from "react";

const TrendsPage = () => {
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [useLive, setUseLive] = useState(true); // 🔄 toggle between live & mock

  const fetchTrends = async () => {
    setLoading(true);
    setError("");
    try {
      const endpoint = useLive
        ? "http://127.0.0.1:8000/nba/trends/live"
        : "http://127.0.0.1:8000/nba/trends";
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error(`Failed to fetch data from ${endpoint}`);
      const data = await res.json();
      setTrends(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrends();
  }, [useLive]); // refetch when toggled

  const toggleSource = () => {
    setUseLive((prev) => !prev);
  };

  if (loading)
    return (
      <div style={{ padding: "1rem", color: "#ccc" }}>
        <p>Loading trends...</p>
      </div>
    );

  if (error)
    return (
      <div style={{ padding: "1rem", color: "red" }}>
        <p>Error: {error}</p>
      </div>
    );

  if (!trends)
    return (
      <div style={{ padding: "1rem", color: "#888" }}>
        <p>No trend data available.</p>
      </div>
    );

  return (
    <div style={{ padding: "1.5rem", fontFamily: "system-ui" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h2 style={{ color: "#fff" }}>NBA Trends</h2>
        <button
          onClick={toggleSource}
          style={{
            padding: "0.5rem 1rem",
            borderRadius: "6px",
            border: "1px solid #444",
            backgroundColor: useLive ? "#1e90ff" : "#444",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          {useLive ? "🔵 Live Mode" : "⚪ Mock Mode"}
        </button>
      </div>

      <p style={{ color: "#888" }}>
        Generated: {trends.date_generated || "N/A"}
      </p>

      <section style={{ marginTop: "1.5rem" }}>
        <h3 style={{ color: "#eee" }}>Player Trends</h3>
        {trends.player_trends.length === 0 ? (
          <p style={{ color: "#aaa" }}>No player trend data.</p>
        ) : (
          trends.player_trends.map((p, index) => (
            <div
              key={index}
              style={{
                border: "1px solid #333",
                borderRadius: "10px",
                padding: "12px",
                marginBottom: "10px",
                backgroundColor: "#1c1c1c",
                color: "#eee",
                transition: "all 0.2s ease",
              }}
            >
              <h4>{p.player_name}</h4>
              <p>
                <strong>{p.stat_type}</strong>: {p.average} avg (
                {p.trend_direction})
              </p>
              <p>
                <small>Last {p.last_n_games} games</small>
              </p>
            </div>
          ))
        )}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h3 style={{ color: "#eee" }}>Team Trends</h3>
        {trends.team_trends.length === 0 ? (
          <p style={{ color: "#aaa" }}>No team trend data.</p>
        ) : (
          trends.team_trends.map((t, index) => (
            <div
              key={index}
              style={{
                border: "1px solid #333",
                borderRadius: "10px",
                padding: "12px",
                marginBottom: "10px",
                backgroundColor: "#1c1c1c",
                color: "#eee",
                transition: "all 0.2s ease",
              }}
            >
              <h4>{t.team_name}</h4>
              <p>
                <strong>{t.stat_type}</strong>: {t.average} avg (
                {t.trend_direction})
              </p>
              <p>
                <small>Last {t.last_n_games} games</small>
              </p>
            </div>
          ))
        )}
      </section>
    </div>
  );
};

export default TrendsPage;
