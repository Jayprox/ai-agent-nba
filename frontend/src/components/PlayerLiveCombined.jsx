import React, { useEffect, useRef, useState } from "react";

const Badge = ({ stale }) => (
  <span
    style={{
      marginLeft: 12,
      padding: "4px 10px",
      borderRadius: 6,
      background: stale ? "#c2a800" : "#3cb371",
      color: "#000",
      fontWeight: "bold",
    }}
  >
    {stale ? "🟡 Stale (>60s)" : "🟢 Synced"}
  </span>
);

const PlayerLiveCombined = () => {
  const [teamId, setTeamId] = useState("134");
  const [data, setData] = useState({ players: [], count: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [liveMode, setLiveMode] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isStale, setIsStale] = useState(false);

  const refreshRef = useRef(null);
  const staleCheckRef = useRef(null);

  const fetchCombined = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/nba/player/live/combined/${teamId}`
      );
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const json = await res.json();
      setData(json || { players: [], count: 0 });
      setLastUpdated(new Date());
      setIsStale(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // initial + live loop
  useEffect(() => {
    if (liveMode) fetchCombined();
    if (refreshRef.current) clearInterval(refreshRef.current);
    if (liveMode) refreshRef.current = setInterval(fetchCombined, 60_000);
    return () => refreshRef.current && clearInterval(refreshRef.current);
  }, [liveMode, teamId]);

  // staleness checker
  useEffect(() => {
    if (staleCheckRef.current) clearInterval(staleCheckRef.current);
    staleCheckRef.current = setInterval(() => {
      if (!lastUpdated) return;
      const elapsed = (Date.now() - lastUpdated.getTime()) / 1000;
      setIsStale(elapsed > 60);
    }, 5000);
    return () => clearInterval(staleCheckRef.current);
  }, [lastUpdated]);

  const formattedTime = lastUpdated
    ? lastUpdated.toLocaleTimeString()
    : "—";

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
      <h2>🏀 Live Player Insights (Unified)</h2>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <label>Team ID:</label>
        <input
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          style={{ width: 80 }}
        />
        <button onClick={fetchCombined}>Fetch</button>

        <button
          onClick={() => setLiveMode((v) => !v)}
          style={{
            marginLeft: 8,
            padding: "6px 10px",
            borderRadius: 6,
            border: "1px solid #444",
            background: liveMode ? "#1e90ff" : "#555",
            color: "#fff",
          }}
        >
          {liveMode ? "🔵 Live Mode" : "⚪ Manual"}
        </button>

        {loading && <span style={{ color: "#aaa" }}>Refreshing…</span>}
        <Badge stale={isStale} />
        <span style={{ color: "#888" }}>Last updated {formattedTime}</span>
      </div>

      {error && <p style={{ color: "tomato" }}>Error: {error}</p>}

      <p style={{ color: "#bbb", marginTop: 0 }}>
        Total Players: {data?.count ?? 0}
      </p>

      <table
        border="1"
        cellPadding="6"
        style={{ borderCollapse: "collapse", minWidth: 720 }}
      >
        <thead style={{ background: "#333", color: "#fff" }}>
          <tr>
            <th>Player</th>
            <th>PTS</th>
            <th>REB</th>
            <th>AST</th>
            <th>FG%</th>
            <th>3PT%</th>
            <th>Trend</th>
            <th>Verdict</th>
          </tr>
        </thead>
        <tbody style={{ color: "#ccc" }}>
          {(data?.players ?? []).length === 0 ? (
            <tr>
              <td colSpan="8" style={{ textAlign: "center", color: "#888" }}>
                No live data
              </td>
            </tr>
          ) : (
            data.players.map((p) => (
              <tr key={p.id ?? p.name}>
                <td>{p.name}</td>
                <td>{p.pts ?? "—"}</td>
                <td>{p.reb ?? "—"}</td>
                <td>{p.ast ?? "—"}</td>
                <td>{p.fg_pct ?? "—"}</td>
                <td>{p.three_pct ?? "—"}</td>
                <td>{p.trend ?? "—"}</td>
                <td>{p.verdict ?? "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default PlayerLiveCombined;
