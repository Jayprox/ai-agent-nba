import React, { useState } from "react";
import { API_BASE_URL } from "../config/api";

const PlayerLive = () => {
  const [teamId, setTeamId] = useState("134");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLiveStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/nba/player/live/${teamId}`);
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const json = await res.json();
      setData(json.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif", color: "#fff" }}>
      <h2>🏀 Live Player Stats</h2>
      <div style={{ marginBottom: 16 }}>
        <label>Team ID:&nbsp;</label>
        <input
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          style={{ width: 80 }}
        />
        <button onClick={fetchLiveStats} style={{ marginLeft: 8 }}>
          Fetch
        </button>
      </div>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: "red" }}>Error: {error}</p>}

      {data && (
        <>
          <h3>Season {data.season}</h3>
          <p>Total Players: {data.count}</p>

          <table
            border="1"
            cellPadding="6"
            style={{ borderCollapse: "collapse", minWidth: 600, background: "#111", color: "#fff" }}
          >
            <thead style={{ background: "#333" }}>
              <tr>
                <th>Player</th>
                <th>Team</th>
                <th>PTS</th>
                <th>REB</th>
                <th>AST</th>
                <th>STL</th>
                <th>BLK</th>
                <th>FG%</th>
                <th>3PT%</th>
                <th>FT%</th>
              </tr>
            </thead>
            <tbody>
              {data.players.length === 0 ? (
                <tr><td colSpan="10" style={{ textAlign: "center" }}>No live data</td></tr>
              ) : (
                data.players.map((p) => (
                  <tr key={p.id}>
                    <td>{p.name}</td>
                    <td>{p.team}</td>
                    <td>{p.points ?? "—"}</td>
                    <td>{p.rebounds ?? "—"}</td>
                    <td>{p.assists ?? "—"}</td>
                    <td>{p.steals ?? "—"}</td>
                    <td>{p.blocks ?? "—"}</td>
                    <td>{p.fg_pct ?? "—"}</td>
                    <td>{p.three_pct ?? "—"}</td>
                    <td>{p.ft_pct ?? "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
};

export default PlayerLive;
