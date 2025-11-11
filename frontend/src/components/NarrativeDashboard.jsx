// frontend/src/pages/NarrativeDashboard.jsx
import { useState, useEffect } from "react";

export default function NarrativeDashboard() {
  const [data, setData] = useState(null);
  const [mode, setMode] = useState("template");
  const [loading, setLoading] = useState(false);
  const [timestamp, setTimestamp] = useState("");

  const fetchNarrative = async (m = "template") => {
    setLoading(true);
    const res = await fetch(`http://127.0.0.1:8000/nba/narrative/today?mode=${m}`);
    const json = await res.json();
    setData(json);
    setMode(m);
    setTimestamp(new Date().toLocaleTimeString());
    setLoading(false);
  };

  useEffect(() => {
    fetchNarrative("template");
  }, []);

  return (
    <div
      className="min-h-screen bg-zinc-900 p-8 font-sans text-gray-100 transition-all duration-500"
      style={{ color: "#e5e7eb" }}
    >
      {/* Header */}
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2 animate-fadeIn">
        📈 NBA Narrative Dashboard
      </h1>

      {/* Controls */}
      <div className="flex items-center gap-3 mb-6 animate-fadeIn delay-200">
        <button
          onClick={() => fetchNarrative("template")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            mode === "template"
              ? "bg-blue-600 text-white shadow-lg"
              : "bg-zinc-700 hover:bg-zinc-600 text-gray-200"
          }`}
        >
          Template
        </button>
        <button
          onClick={() => fetchNarrative("ai")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            mode === "ai"
              ? "bg-green-600 text-white shadow-lg"
              : "bg-zinc-700 hover:bg-zinc-600 text-gray-200"
          }`}
        >
          AI Narrative
        </button>
        <button
          onClick={() => fetchNarrative(mode)}
          className="px-4 py-2 rounded-lg bg-gray-600 hover:bg-gray-500 font-medium text-white transition shadow-md"
        >
          Refresh
        </button>

        {timestamp && (
          <span className="text-sm text-gray-400 ml-3 italic">
            Last updated: {timestamp}
          </span>
        )}
      </div>

      {/* Mode Indicator */}
      <p className="mb-6 text-lg animate-fadeIn delay-300">
        <strong>Mode:</strong>{" "}
        {mode === "ai" ? (
          <span className="text-pink-400 font-semibold">AI-enhanced 🧠</span>
        ) : (
          <span className="text-blue-400 font-semibold">Template</span>
        )}
      </p>

      {/* Split layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Narrative */}
        <div className="bg-zinc-800/90 p-6 rounded-2xl shadow-xl border border-zinc-700 animate-fadeIn delay-500 hover:shadow-pink-600/20 transition-all duration-300">
          {loading ? (
            <p className="text-gray-400 italic">Loading narrative...</p>
          ) : (
            <p className="leading-relaxed text-base tracking-wide">
              {data?.summary || "No summary available."}
            </p>
          )}
        </div>

        {/* Right: Trends + Odds */}
        <div className="space-y-6">
          {/* Key Trends */}
          <div className="bg-zinc-800/90 p-5 rounded-2xl shadow-lg border border-zinc-700 animate-fadeIn delay-700 hover:shadow-pink-600/20 transition-all duration-300">
            <h3 className="font-semibold mb-3 text-xl text-pink-400 flex items-center gap-2">
              🧠 Key Trends
            </h3>
            <ul className="list-disc ml-5 text-gray-200 space-y-1 text-sm">
              {data?.raw?.trends?.player_trends?.slice(0, 5).map((t, i) => (
                <li key={i}>
                  <span className="font-medium">{t.player_name}</span> —{" "}
                  {t.stat_type} avg {t.average.toFixed(1)} ({t.trend_direction})
                </li>
              ))}
            </ul>
          </div>

          {/* Odds */}
          <div className="bg-zinc-800/90 p-5 rounded-2xl shadow-lg border border-zinc-700 animate-fadeIn delay-900 hover:shadow-green-600/20 transition-all duration-300">
            <h3 className="font-semibold mb-3 text-xl text-green-400 flex items-center gap-2">
              💸 Top Odds Matchups
            </h3>
            <ul className="list-disc ml-5 text-gray-200 space-y-1 text-sm">
              {data?.raw?.odds?.games?.slice(0, 5).map((g, i) => (
                <li key={i}>
                  <span className="font-medium">{g.away_team}</span> @{" "}
                  <span className="font-medium">{g.home_team}</span> —{" "}
                  <span className="text-gray-400">
                    {g.moneyline.home.american}/{g.moneyline.away.american}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Animation styles */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.6s ease forwards;
        }
        .delay-200 { animation-delay: 0.2s; }
        .delay-300 { animation-delay: 0.3s; }
        .delay-500 { animation-delay: 0.5s; }
        .delay-700 { animation-delay: 0.7s; }
        .delay-900 { animation-delay: 0.9s; }
      `}</style>
    </div>
  );
}
