import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../config/api";

const LiveDashboard = () => {
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchGames = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/nba/games/today`);
      const json = await res.json();
      setGames(json.games || []);
    } catch (e) {
      console.error("Failed to fetch games", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGames();
  }, []);

  const handleSelect = (game) => {
    setSelectedGame(game);
  };

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
      <h2>🏀 NBA Live Dashboard</h2>

      {loading ? (
        <p>Loading games...</p>
      ) : (
        <div style={{ display: "flex", gap: 20 }}>
          {/* --- Game Picker --- */}
          <div
            style={{
              flex: 1,
              borderRight: "1px solid #444",
              paddingRight: 20,
              maxWidth: 250,
            }}
          >
            <h3>Today's Games</h3>
            {games.length === 0 ? (
              <p style={{ color: "#888" }}>No games today.</p>
            ) : (
              <ul style={{ listStyle: "none", padding: 0 }}>
                {games.map((g) => (
                  <li
                    key={g.id}
                    style={{
                      cursor: "pointer",
                      background:
                        selectedGame?.id === g.id ? "#1e90ff" : "transparent",
                      color:
                        selectedGame?.id === g.id ? "#fff" : "#ddd",
                      padding: "8px 10px",
                      borderRadius: 6,
                      marginBottom: 6,
                    }}
                    onClick={() => handleSelect(g)}
                  >
                    {g.away_team.name} @ {g.home_team.name}
                    <br />
                    <small style={{ color: "#aaa" }}>{g.status}</small>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* --- Live Panels --- */}
          <div style={{ flex: 3 }}>
            {!selectedGame ? (
              <p style={{ color: "#888" }}>Select a game to view live data.</p>
            ) : (
              <>
                <h3>
                  {selectedGame.away_team.name} @ {selectedGame.home_team.name}
                </h3>

                <div style={{ display: "flex", gap: 20, marginTop: 20 }}>
                  <iframe
                    src={`/team-summary?team=${selectedGame.home_team.id}`}
                    style={{
                      width: "48%",
                      height: "400px",
                      border: "1px solid #444",
                      borderRadius: 8,
                      background: "#000",
                    }}
                    title="Home Team Summary"
                  />
                  <iframe
                    src={`/player-live-combined?team=${selectedGame.home_team.id}`}
                    style={{
                      width: "48%",
                      height: "400px",
                      border: "1px solid #444",
                      borderRadius: 8,
                      background: "#000",
                    }}
                    title="Home Player Insights"
                  />
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveDashboard;
