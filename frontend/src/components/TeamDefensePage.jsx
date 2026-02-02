import { useEffect, useState } from "react";
import { API_BASE_URL } from "../config/api";

const TeamDefensePage = () => {
  const [defenseData, setDefenseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchDefense = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/nba/defense/teams`);
        if (!res.ok) throw new Error("Failed to fetch team defense data");
        const data = await res.json();
        setDefenseData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDefense();
  }, []);

  if (loading) return <p style={{ color: "#ccc" }}>Loading defensive data...</p>;
  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;

  if (!defenseData) return <p>No defense data available.</p>;

  return (
    <div style={{ padding: "1rem", fontFamily: "system-ui" }}>
      <h2 style={{ color: "#fff" }}>NBA Team Defense Rankings</h2>
      <p style={{ color: "#888" }}>Generated: {defenseData.date_generated}</p>

      {defenseData.teams.map((team, index) => (
        <div
          key={index}
          style={{
            border: "1px solid #333",
            borderRadius: "10px",
            padding: "16px",
            marginBottom: "12px",
            backgroundColor: "#1c1c1c",
            color: "#eee",
            textAlign: "center",
            boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
          }}
        >
          <h3 style={{ color: "#fff", fontWeight: "600" }}>
            #{team.rank_overall} — {team.team_name}
          </h3>

          <p><strong>Defensive Rating:</strong> {team.defensive_rating}</p>
          <p><strong>Opponent Points:</strong> {team.opp_points_per_game} PPG</p>
          <p><strong>Opponent Rebounds:</strong> {team.opp_rebounds_per_game} RPG</p>
          <p><strong>Opponent Assists:</strong> {team.opp_assists_per_game} APG</p>

          <p style={{ marginTop: "8px", color: "#bbb" }}>
            <strong>Positional Defense Ranks:</strong><br />
            PG: {team.rank_pg_def} | SG: {team.rank_sg_def} | SF: {team.rank_sf_def} | PF: {team.rank_pf_def} | C: {team.rank_c_def}
          </p>
        </div>
      ))}
    </div>
  );
};

export default TeamDefensePage;
