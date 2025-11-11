// frontend/src/pages/TeamSummary.jsx
import React, { useState, useEffect, useRef } from "react";

const TeamSummary = () => {
  const [teamId, setTeamId] = useState("134");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [liveMode, setLiveMode] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isStale, setIsStale] = useState(false);
  const timerRef = useRef(null);
  const staleCheckerRef = useRef(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://127.0.0.1:8000/nba/team/summary/${teamId}`);
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastUpdated(new Date());
      setIsStale(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 🔁 Auto-refresh every 60s in Live Mode
  useEffect(() => {
    if (liveMode) fetchSummary();
    if (timerRef.current) clearInterval(timerRef.current);

    if (liveMode) timerRef.current = setInterval(fetchSummary, 60_000);

    return () => timerRef.current && clearInterval(timerRef.current);
  }, [liveMode, teamId]);

  // ⏱️ Check staleness every 5s
  useEffect(() => {
    if (staleCheckerRef.current) clearInterval(staleCheckerRef.current);
    staleCheckerRef.current = setInterval(() => {
      if (!lastUpdated) return;
      const elapsed = (Date.now() - lastUpdated.getTime()) / 1000;
      setIsStale(elapsed > 60);
    }, 5000);

    return () => clearInterval(staleCheckerRef.current);
  }, [lastUpdated]);

  const formattedTime = lastUpdated
    ? lastUpdated.toLocaleTimeString()
    : "—";

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
      <h2>🏀 NBA Team Summary (Live)</h2>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <label>Team ID:</label>
        <input
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          style={{ width: 80 }}
        />
        <button onClick={fetchSummary}>Fetch</button>

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

        <span
          style={{
            marginLeft: 12,
            padding: "4px 10px",
            borderRadius: 6,
            background: isStale ? "#c2a800" : "#3cb371",
            color: "#000",
            fontWeight: "bold",
          }}
        >
          {isStale ? "🟡 Stale (>60s)" : "🟢 Synced"}
        </span>

        <span style={{ color: "#888" }}>Last updated {formattedTime}</span>
      </div>

      {error && <p style={{ color: "red" }}>Error: {error}</p>}

      {data && (
        <div style={{ marginTop: 20 }}>
          <h3>Season {data.season}</h3>

          <table
            border="1"
            cellPadding="6"
            style={{ borderCollapse: "collapse", minWidth: 400 }}
          >
            <thead style={{ background: "#333", color: "#fff" }}>
              <tr>
                <th>Metric</th>
                <th>Offense</th>
                <th>Defense</th>
              </tr>
            </thead>
            <tbody style={{ color: "#ccc" }}>
              <tr>
                <td>Points</td>
                <td>{data.offense.points_per_game ?? "—"}</td>
                <td>{data.defense.points_allowed ?? "—"}</td>
              </tr>
              <tr>
                <td>FG%</td>
                <td>{data.offense.fg_pct ?? "—"}</td>
                <td>{data.defense.opp_fg_pct ?? "—"}</td>
              </tr>
              <tr>
                <td>3PT%</td>
                <td>{data.offense.three_pct ?? "—"}</td>
                <td>{data.defense.opp_three_pct ?? "—"}</td>
              </tr>
              <tr>
                <td>Assists / Turnovers</td>
                <td>
                  {data.offense.assists ?? "—"} / {data.offense.turnovers ?? "—"}
                </td>
                <td>{data.defense.turnovers_forced ?? "—"}</td>
              </tr>
              <tr>
                <td>Pace / Rebounds Allowed</td>
                <td>{data.offense.pace ?? "—"}</td>
                <td>{data.defense.rebounds_allowed ?? "—"}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TeamSummary;
