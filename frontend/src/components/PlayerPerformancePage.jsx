import React, { useEffect, useState } from "react";
import { API_BASE_URL } from "../config/api";

const API_URL = `${API_BASE_URL}/nba/player/performance`;

const trendColor = (trend) => {
  switch (trend.toLowerCase()) {
    case "up":
      return "text-green-400";
    case "down":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
};

const PlayerPerformancePage = () => {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(API_URL);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setPlayers(data.players || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="text-center mt-10 text-gray-400">Loading player data...</div>;
  if (error) return <div className="text-center mt-10 text-red-400">Error: {error}</div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white px-6 py-10">
      <h1 className="text-3xl font-bold mb-8 text-center text-blue-400">
        🏀 Player Performance (Live)
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {players.map((p, i) => (
          <div
            key={i}
            className="bg-gray-900 shadow-lg rounded-2xl p-6 border border-gray-800 hover:border-blue-500 transition-all duration-300"
          >
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-xl font-semibold text-blue-300">{p.player_name}</h2>
              <span className={`text-sm font-medium ${trendColor(p.trend)}`}>
                {p.trend === "up" ? "⬆️ Up" : p.trend === "down" ? "⬇️ Down" : "➖ Neutral"}
              </span>
            </div>

            <div className="text-sm space-y-1 text-gray-300">
              <p>PPG: <span className="text-white">{p.ppg}</span></p>
              <p>RPG: <span className="text-white">{p.rpg}</span></p>
              <p>APG: <span className="text-white">{p.apg}</span></p>
              <p>3PM: <span className="text-white">{p.tpm}</span></p>
            </div>

            <div className="mt-4 border-t border-gray-700 pt-2 text-xs text-gray-500">
              Season Avg: {p.season_ppg ?? 0} PPG | {p.season_rpg ?? 0} RPG | {p.season_apg ?? 0} APG | {p.season_tpm ?? 0} 3PM
              <br />
              <span className="text-gray-600">Generated: {p.generated_at}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PlayerPerformancePage;
