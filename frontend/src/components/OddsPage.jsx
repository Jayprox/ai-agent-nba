import { useEffect, useState } from "react";

const OddsPage = () => {
  const [odds, setOdds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [source, setSource] = useState("today"); // Track if data is from today or upcoming

  const fetchOdds = async (endpoint, fallback = false) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/nba/odds/${endpoint}`);
      if (!res.ok) throw new Error(`Failed to fetch /${endpoint}`);
      const data = await res.json();

      // If /today returns no games, try /upcoming automatically
      if (!fallback && data.games && data.games.length === 0 && endpoint === "today") {
        console.warn("No games today, fetching upcoming...");
        setSource("upcoming");
        return fetchOdds("upcoming", true);
      }

      setOdds(data.games || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOdds("today");
  }, []);

  if (loading) return <p style={{ color: "#ccc" }}>Loading odds...</p>;
  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;

  return (
    <div style={{ padding: "1rem", fontFamily: "system-ui" }}>
      <h2 style={{ color: "#fff" }}>
        NBA Odds ({source === "today" ? "Today" : "Upcoming"})
      </h2>

      {odds.length === 0 ? (
        <p style={{ color: "#999" }}>No games found.</p>
      ) : (
        odds.map((game, index) => (
          <div
            key={index}
            style={{
              border: "1px solid #333",
              borderRadius: "10px",
              padding: "12px",
              marginBottom: "10px",
              backgroundColor: "#1c1c1c",
              color: "#eee",
            }}
          >
            <h3>{game.away_team} @ {game.home_team}</h3>
            <p><strong>Home:</strong> {game.moneyline.home.price} ({game.moneyline.home.american}) via {game.moneyline.home.bookmaker}</p>
            <p><strong>Away:</strong> {game.moneyline.away.price} ({game.moneyline.away.american}) via {game.moneyline.away.bookmaker}</p>
            <small style={{ color: "#888" }}>Bookmakers: {game.all_bookmakers.join(", ")}</small>
          </div>
        ))
      )}
    </div>
  );
};

export default OddsPage;
