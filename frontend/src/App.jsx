import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import TeamOffensePage from "./components/TeamOffensePage";
import TeamDefensePage from "./components/TeamDefensePage";
import TrendsPage from "./components/TrendsPage";
import OddsPage from "./components/OddsPage";
import PlayerPerformancePage from "./components/PlayerPerformancePage";
import PlayerTrendsPage from "./components/PlayerTrendsPage";
import PlayerInsightsPage from "./components/PlayerInsightsPape";
import TeamSummary from "./components/TeamSummary";
import PlayerLive from "./components/PlayerLive";
import PlayerLiveCombined from "./components/PlayerLiveCombined";
import LiveDashboard from "./components/LiveDashboard";
import Trends from "./components/Trends";
import NarrativeDashboard from "./components/NarrativeDashboard";




function App() {
  return (
    <Router>
      <div style={{ backgroundColor: "#000", minHeight: "100vh" }}>
        <Navbar />
        <Routes>
          <Route path="/" element={<Navigate to="/offense" />} />
          <Route path="/offense" element={<TeamOffensePage />} />
          <Route path="/defense" element={<TeamDefensePage />} />
          <Route path="/trends" element={<TrendsPage />} />
          <Route path="/odds" element={<OddsPage />} />
          <Route path="/player-performance" element={<PlayerPerformancePage />} />
          <Route path="/player-trends" element={<PlayerTrendsPage />} />
          <Route path="/player-insights" element={<PlayerInsightsPage />} />
          <Route path="/team-summary" element={<TeamSummary />} />
          <Route path="/player-live" element={<PlayerLive />} />
          <Route path="/player-live-combined" element={<PlayerLiveCombined />} />
          <Route path="/live-dashboard" element={<LiveDashboard />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/narrative-dashboard" element={<NarrativeDashboard />} />       
        </Routes>
      </div>
    </Router>
  );
}

export default App;
