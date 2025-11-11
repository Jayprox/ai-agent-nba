import React, { useState, useEffect, useRef } from "react";

const Odds = () => {
  const [odds, setOdds] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [status, setStatus] = useState("Idle");
  const prevOddsRef = useRef([]);

  // --- Fetch odds ---
  const fetchOdds = async (auto = false) => {
    if (!auto) setStatus("Syncing");
    try {
      const res = await fetch("http://127.0.0.1:8000/nba/odds/today");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const newGames = data.games || [];
      const prevGames = prevOddsRef.current;

      const merged = newGames.map((g) => {
        const prev = prevGames.find(
          (pg) => pg.home_team === g.home_team && pg.away_team === g.away_team
        );
        let trend = "none";
        if (prev) {
          if (g.moneyline.home.american > prev.moneyline.home.american) trend = "up";
          else if (g.moneyline.home.american < prev.moneyline.home.american)
            trend = "down";
        }
        return { ...g, trend };
      });

      setOdds(merged);
      prevOddsRef.current = newGames;
      setLastUpdated(new Date().toLocaleTimeString());
      setStatus("Synced");
      setTimeout(() => setStatus("Idle"), 2500);
    } catch (err) {
      console.error(err);
      setStatus("Error");
    }
  };

  // --- Auto refresh every 60s ---
  useEffect(() => {
    fetchOdds();
    const interval = setInterval(() => fetchOdds(true), 60000);
    return () => clearInterval(interval);
  }, []);

  const badgeColor = {
    Idle: "#444",
    Syncing: "#007bff",
    Synced: "#0f0",
    Error: "#f00",
  }[status];

  return (
    <div style={{ padding: 20, color: "white", fontFamily: "Arial, sans-serif" }}>
      <h2>🏀 NBA Moneyline Odds (Live)</h2>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <button
          onClick={() => fetchOdds()}
          style={{
            background: "#007bff",
            color: "white",
            border: "none",
            borderRadius: 6,
            padding: "6px 12px",
            cursor: "pointer",
          }}
        >
          Refresh Now
        </button>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: badgeColor,
            borderRadius: 8,
            padding: "4px 8px",
            color: "black",
            fontWeight: "bold",
          }}
        >
          {status === "Synced" && (
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "limegreen",
                animation: "pulse 1.2s infinite",
              }}
            ></span>
          )}
          <span>{status}</span>
        </div>

        {lastUpdated && (
          <span style={{ color: "#aaa", fontSize: 14 }}>
            Last updated: {lastUpdated}
          </span>
        )}
      </div>

      {odds.length === 0 ? (
        <p style={{ color: "#888" }}>No games available today.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {odds.map((game, i) => (
            <div
              key={i}
              style={{
                background:
                  game.trend === "up"
                    ? "rgba(0,128,0,0.2)"
                    : game.trend === "down"
                    ? "rgba(255,0,0,0.2)"
                    : "#1a1a1a",
                padding: 14,
                borderRadius: 8,
                boxShadow: "0 0 8px rgba(255,255,255,0.05)",
                transition: "background 0.8s ease",
              }}
            >
              <strong style={{ fontSize: 16 }}>
                {game.away_team} @ {game.home_team}
              </strong>
              <p style={{ margin: "6px 0", color: "#ccc" }}>
                🏠 {game.moneyline.home.team}:{" "}
                <span
                  style={{
                    color:
                      game.trend === "up"
                        ? "#0f0"
                        : game.trend === "down"
                        ? "#f66"
                        : "#0f0",
                    transition: "color 0.8s ease",
                  }}
                >
                  {game.moneyline.home.american}
                </span>{" "}
                ({game.moneyline.home.bookmaker})
              </p>
              <p style={{ margin: "6px 0", color: "#ccc" }}>
                🛫 {game.moneyline.away.team}:{" "}
                <span
                  style={{
                    color:
                      game.trend === "up"
                        ? "#0f0"
                        : game.trend === "down"
                        ? "#f66"
                        : "#0f0",
                    transition: "color 0.8s ease",
                  }}
                >
                  {game.moneyline.away.american}
                </span>{" "}
                ({game.moneyline.away.bookmaker})
              </p>
              <small style={{ color: "#666" }}>
                Commence → {new Date(game.commence_time).toLocaleString()}
              </small>
            </div>
          ))}
        </div>
      )}

      {/* Keyframe for pulsing dot */}
      <style>{`
        @keyframes pulse {
          0% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.5); }
          100% { opacity: 0.4; transform: scale(1); }
        }
      `}</style>
    </div>
  );
};

export default Odds;
