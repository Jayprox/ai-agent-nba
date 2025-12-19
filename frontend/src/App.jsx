import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";

import TeamOffensePage from "./components/TeamOffensePage";
import TeamDefensePage from "./components/TeamDefensePage";
import TrendsPage from "./components/TrendsPage";
import Odds from "./components/Odds"; // ✅ use the updated Odds.jsx
import PlayerPerformancePage from "./components/PlayerPerformancePage";
import PlayerTrendsPage from "./components/PlayerTrendsPage";
import PlayerInsightsPage from "./components/PlayerInsightsPape"; // NOTE: verify filename matches (possible typo)
import TeamSummary from "./components/TeamSummary";
import PlayerLive from "./components/PlayerLive";
import PlayerLiveCombined from "./components/PlayerLiveCombined";
import LiveDashboard from "./components/LiveDashboard";
import NarrativeDashboard from "./components/NarrativeDashboard";

function App() {
  return (
    <Router>
      <div style={{ backgroundColor: "#000", minHeight: "100vh" }}>
        <Navbar />
        <Routes>
          <Route path="/" element={<Navigate to="/offense" replace />} />

          <Route path="/offense" element={<TeamOffensePage />} />
          <Route path="/defense" element={<TeamDefensePage />} />

          {/* Keep a single /trends route */}
          <Route path="/trends" element={<TrendsPage />} />

          {/* ✅ Updated route for today's slate */}
          <Route path="/odds" element={<Odds />} />

          <Route path="/player-performance" element={<PlayerPerformancePage />} />
          <Route path="/player-trends" element={<PlayerTrendsPage />} />
          <Route path="/player-insights" element={<PlayerInsightsPage />} />

          <Route path="/team-summary" element={<TeamSummary />} />
          <Route path="/player-live" element={<PlayerLive />} />
          <Route path="/player-live-combined" element={<PlayerLiveCombined />} />
          <Route path="/live-dashboard" element={<LiveDashboard />} />

          <Route path="/narrative-dashboard" element={<NarrativeDashboard />} />

          {/* Optional fallback */}
          <Route path="*" element={<Navigate to="/odds" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
