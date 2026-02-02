import { useEffect, useState } from "react";
import TrendsModal from "./TrendsModal";
import { API_BASE_URL } from "../config/api";

const TeamOffensePage = () => {
  const [offenseData, setOffenseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedTeam, setSelectedTeam] = useState(null);

  useEffect(() => {
    const fetchOffenseData = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/nba/offense/teams`);
        if (!res.ok) throw new Error(`Failed to fetch data (${res.status})`);
        const data = await res.json();
        setOffenseData(data);
      } catch (err) {
        console.error("❌ Error fetching offense data:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchOffenseData();
  }, []);

  if (loading) return <p style={{ color: "#ccc" }}>Loading team offense data...</p>;
  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;
  if (!offenseData) return <p>No offense data available.</p>;

  return (
    <div style={{ padding: "1.5rem", fontFamily: "system-ui" }}>
      <h2 style={{ color: "#fff", marginBottom: "0.25rem" }}>NBA Team Offense Rankings</h2>
      <p style={{ color: "#888" }}>Generated: {offenseData.date_generated}</p>

      <section style={{ marginTop: "1.5rem" }}>
        {offenseData.teams.map((team, index) => (
          <div
            key={index}
            onClick={() => setSelectedTeam(team.team_name)}
            style={{
              border: "1px solid #333",
              borderRadius: "10px",
              padding: "1rem",
              marginBottom: "1rem",
              backgroundColor: "#1a1a1a",
              color: "#eee",
              boxShadow: "0 2px 6px rgba(0,0,0,0.4)",
              cursor: "pointer",
              transition: "transform 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.02)")}
            onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
          >
            <h3 style={{ margin: "0 0 0.5rem", color: "#fff" }}>
              #{team.rank_overall} — {team.team_name}
            </h3>
            <p><strong>Points:</strong> {team.points_per_game} PPG</p>
            <p><strong>Assists:</strong> {team.assists_per_game} APG</p>
            <p><strong>Rebounds:</strong> {team.rebounds_per_game} RPG</p>
            <div style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "#bbb" }}>
              <p>
                <strong>Positional Ranks:</strong><br />
                PG: {team.rank_pg} | SG: {team.rank_sg} | SF: {team.rank_sf} | PF: {team.rank_pf} | C: {team.rank_c}
              </p>
            </div>
          </div>
        ))}
      </section>

      {selectedTeam && (
        <TrendsModal teamName={selectedTeam} onClose={() => setSelectedTeam(null)} />
      )}
    </div>
  );
};

export default TeamOffensePage;
