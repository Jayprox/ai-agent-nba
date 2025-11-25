// frontend/src/components/Odds.jsx
import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const Odds = () => {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTodayGames = async () => {
      try {
        setLoading(true);
        setError(null);

        console.log("🔍 Fetching today's slate from:", `${API_BASE}/nba/games/today`);

        const res = await fetch(`${API_BASE}/nba/games/today`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status} ${res.statusText}`);
        }

        const data = await res.json();
        console.log("📦 /nba/games/today response:", data);

        if (!data.ok) {
          throw new Error(data.error || "Backend returned ok: false");
        }

        setGames(data.games || []);
      } catch (err) {
        console.error("❌ Error loading today's games:", err);
        setError(err.message || "Failed to fetch today's slate");
      } finally {
        setLoading(false);
      }
    };

    fetchTodayGames();
  }, []);

  if (loading) {
    return (
      <div className="p-4 text-white">
        ⏳ Loading today&apos;s NBA slate...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-400">
        <p className="font-semibold">Error loading today&apos;s games</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (!games.length) {
    return (
      <div className="p-4 text-gray-300">
        No NBA games found for today.
      </div>
    );
  }

  return (
    <div className="p-6 text-white max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">📅 Today&apos;s NBA Slate</h1>
      <p className="text-sm text-gray-300 mb-4">
        Data from API-Basketball — showing today&apos;s scheduled games.
      </p>

      <div className="space-y-3">
        {games.map((game) => {
          const {
            id,
            date,
            time,
            timezone,
            venue,
            league,
            home_team,
            away_team,
            status,
          } = game;

          // Convert to a nicer local time label if possible
          let tipLabel = time;
          try {
            if (date) {
              const d = new Date(date);
              tipLabel = d.toLocaleTimeString([], {
                hour: "numeric",
                minute: "2-digit",
              });
            }
          } catch {
            // fall back to raw `time`
          }

          return (
            <div
              key={id}
              className="bg-gray-900/80 border border-gray-700 rounded-xl p-4 flex flex-col md:flex-row md:items-center md:justify-between shadow-lg"
            >
              <div className="mb-3 md:mb-0">
                <div className="text-sm text-gray-400 mb-1">
                  {league?.name || "NBA"} • {league?.season} • {timezone}
                </div>
                <div className="font-semibold text-lg">
                  {away_team?.name} @ {home_team?.name}
                </div>
                {venue && (
                  <div className="text-xs text-gray-400 mt-1">
                    {venue}
                  </div>
                )}
              </div>

              <div className="text-right">
                <div className="text-sm text-gray-300">
                  Tip: <span className="font-semibold">{tipLabel}</span>
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  Status: {status?.long || status?.short || "Scheduled"}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Odds;
