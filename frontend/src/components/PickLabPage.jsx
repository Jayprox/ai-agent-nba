import { useEffect, useMemo, useState } from "react";
import { API_BASE_URL } from "../config/api";

const PICK_TYPES = [
  { value: "straight", label: "Straight" },
  { value: "smart_parlay", label: "Smart Parlay" },
  { value: "lotto_parlay", label: "Lotto Parlay" },
  { value: "sleeper", label: "Sleeper" },
];

const ODDS_BANDS = [
  { value: "minus_100_to_plus_500", label: "-100 to +500" },
  { value: "plus_100_to_plus_500", label: "+100 to +500" },
  { value: "plus_500_to_plus_1000", label: "+500 to +1000" },
  { value: "plus_1000_plus", label: "+1000+" },
];

const RISK_PROFILES = [
  { value: "conservative", label: "Conservative" },
  { value: "standard", label: "Standard" },
  { value: "aggressive", label: "Aggressive" },
];

const baseCard = {
  border: "1px solid #23344f",
  background: "#07132a",
  borderRadius: 16,
  padding: "16px 18px",
};

function SourceStatusPill({ name, entry }) {
  const status = String(entry?.status || "unknown");
  let colors = { border: "#334155", bg: "#0b1220", text: "#e5e7eb" };
  if (status === "ok") colors = { border: "#166534", bg: "#052e1a", text: "#bbf7d0" };
  if (status === "no_data") colors = { border: "#334155", bg: "#111827", text: "#cbd5e1" };
  if (status === "disabled") colors = { border: "#854d0e", bg: "#2a1a07", text: "#fde68a" };
  if (status === "error") colors = { border: "#7f1d1d", bg: "#2a0d0d", text: "#fecaca" };

  return (
    <div
      style={{
        border: `1px solid ${colors.border}`,
        background: colors.bg,
        color: colors.text,
        borderRadius: 999,
        padding: "6px 10px",
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {name}: {status} ({Number(entry?.count || 0)})
    </div>
  );
}

export default function PickLabPage() {
  const [pickType, setPickType] = useState("straight");
  const [legs, setLegs] = useState(2);
  const [oddsBand, setOddsBand] = useState("minus_100_to_plus_500");
  const [riskProfile, setRiskProfile] = useState("standard");

  const [loading, setLoading] = useState(false);
  const [trackLoading, setTrackLoading] = useState(false);
  const [error, setError] = useState("");
  const [trackMessage, setTrackMessage] = useState("");

  const [data, setData] = useState(null);
  const [sportsbookOdds, setSportsbookOdds] = useState("");
  const [performance, setPerformance] = useState(null);
  const [recentPicks, setRecentPicks] = useState([]);

  const [filterPickType, setFilterPickType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterResult, setFilterResult] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  const query = useMemo(() => {
    const p = new URLSearchParams();
    p.set("pick_type", pickType);
    p.set("legs", String(legs));
    p.set("odds_band", oddsBand);
    p.set("risk_profile", riskProfile);
    p.set("mode", "ai");
    p.set("cache_ttl", "0");
    p.set("trends", "1");
    return p.toString();
  }, [pickType, legs, oddsBand, riskProfile]);

  const fetchPickLab = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/nba/picks/lab?${query}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e?.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformance = async () => {
    try {
      const trackedParams = new URLSearchParams();
      trackedParams.set("limit", "50");
      if (filterPickType) trackedParams.set("pick_type", filterPickType);
      if (filterStatus) trackedParams.set("status", filterStatus);
      if (filterResult) trackedParams.set("result", filterResult);
      if (filterDateFrom) trackedParams.set("date_from", filterDateFrom);
      if (filterDateTo) trackedParams.set("date_to", filterDateTo);

      const [perfRes, recentRes] = await Promise.all([
        fetch(`${API_BASE_URL}/nba/picks/performance`),
        fetch(`${API_BASE_URL}/nba/picks/tracked?${trackedParams.toString()}`),
      ]);
      if (perfRes.ok) setPerformance(await perfRes.json());
      if (recentRes.ok) {
        const r = await recentRes.json();
        setRecentPicks(r?.picks || []);
      }
    } catch {
      // keep resilient
    }
  };

  const exportCsv = () => {
    const p = new URLSearchParams();
    if (filterPickType) p.set("pick_type", filterPickType);
    if (filterStatus) p.set("status", filterStatus);
    if (filterResult) p.set("result", filterResult);
    if (filterDateFrom) p.set("date_from", filterDateFrom);
    if (filterDateTo) p.set("date_to", filterDateTo);
    const url = `${API_BASE_URL}/nba/picks/tracked/export.csv${p.toString() ? `?${p.toString()}` : ""}`;
    window.open(url, "_blank");
  };

  const editPick = async (pick) => {
    if (!pick || pick.status !== "open") return;
    const nextOddsRaw = window.prompt("Edit sportsbook odds (decimal):", String(pick.sportsbook_odds_decimal ?? ""));
    if (nextOddsRaw === null) return;
    const nextStakeRaw = window.prompt("Edit stake units:", String(pick.stake_units ?? 1));
    if (nextStakeRaw === null) return;
    const nextNotes = window.prompt("Edit notes:", String(pick.notes ?? "")) ?? "";

    const payload = {
      sportsbook_odds_decimal: nextOddsRaw === "" ? null : Number(nextOddsRaw),
      stake_units: nextStakeRaw === "" ? null : Number(nextStakeRaw),
      notes: nextNotes,
    };

    try {
      const res = await fetch(`${API_BASE_URL}/nba/picks/${pick.pick_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchPerformance();
      setTrackMessage(`Updated pick ${pick.pick_id}`);
    } catch (e) {
      setTrackMessage(`Edit failed: ${e?.message || "Unknown error"}`);
    }
  };

  const deletePick = async (pick) => {
    if (!pick) return;
    const ok = window.confirm(`Delete pick ${pick.pick_id}?`);
    if (!ok) return;
    try {
      const res = await fetch(`${API_BASE_URL}/nba/picks/${pick.pick_id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchPerformance();
      setTrackMessage(`Deleted pick ${pick.pick_id}`);
    } catch (e) {
      setTrackMessage(`Delete failed: ${e?.message || "Unknown error"}`);
    }
  };

  const trackCurrentPick = async () => {
    if (!data) return;
    setTrackLoading(true);
    setTrackMessage("");
    try {
      const payload = {
        constraints: data?.constraints || {},
        decision: data?.decision || {},
        data_quality: data?.data_quality || {},
        sportsbook_odds_decimal: sportsbookOdds === "" ? null : Number(sportsbookOdds),
      };
      const res = await fetch(`${API_BASE_URL}/nba/picks/track`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const saved = await res.json();
      const pickId = saved?.pick?.pick_id;
      setTrackMessage(pickId ? `Tracked pick: ${pickId}` : "Pick tracked.");
      await fetchPerformance();
    } catch (e) {
      setTrackMessage(`Track failed: ${e?.message || "Unknown error"}`);
    } finally {
      setTrackLoading(false);
    }
  };

  useEffect(() => {
    fetchPickLab();
  }, [query]);

  useEffect(() => {
    fetchPerformance();
  }, [filterPickType, filterStatus, filterResult, filterDateFrom, filterDateTo]);

  const recommendation = String(data?.decision?.recommendation || "pass").toUpperCase();
  const recColor = recommendation === "BET" ? "#22c55e" : recommendation === "LEAN" ? "#f59e0b" : "#ef4444";

  const sourceStatus = data?.data_quality?.source_status || {};
  const sourceCounts = data?.data_quality?.source_counts || {};
  const unavailable = data?.data_quality?.unavailable_sources || [];
  const rationale = data?.decision?.rationale || [];
  const riskFlags = data?.decision?.risk_flags || [];
  const refreshCheckpoint = data?.data_quality?.refresh_checkpoint || null;
  const parlayQualityScore = data?.decision?.parlay_quality_score;
  const parlayQualityLabel = data?.decision?.parlay_quality_label;
  const parlayQualityReasons = data?.decision?.parlay_quality_reasons || [];
  const isParlay = pickType === "smart_parlay" || pickType === "lotto_parlay";

  return (
    <div style={{ color: "#e5e7eb", padding: "16px", maxWidth: 1160, margin: "0 auto" }}>
      <div style={{ ...baseCard, marginBottom: 12 }}>
        <h1 style={{ margin: 0, fontSize: 32, lineHeight: 1.1 }}>Research-to-Pick Lab</h1>
        <p style={{ margin: "8px 0 0", color: "#9ca3af" }}>Decision-support workflow. No lock language, no guarantees.</p>
      </div>

      <div style={{ ...baseCard, marginBottom: 12, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Pick Type</div>
          <select value={pickType} onChange={(e) => setPickType(e.target.value)} style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
            {PICK_TYPES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>

        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Legs</div>
          <input type="number" min={1} max={12} value={legs} onChange={(e) => setLegs(Math.max(1, Math.min(12, Number(e.target.value || 1))))} disabled={pickType === "straight" || pickType === "sleeper"} style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }} />
        </label>

        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Odds Band</div>
          <select value={oddsBand} onChange={(e) => setOddsBand(e.target.value)} style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
            {ODDS_BANDS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>

        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Risk Profile</div>
          <select value={riskProfile} onChange={(e) => setRiskProfile(e.target.value)} style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
            {RISK_PROFILES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>

        <button onClick={fetchPickLab} disabled={loading} style={{ alignSelf: "end", padding: "10px 12px", borderRadius: 10, border: "1px solid #2563eb", background: loading ? "#1e3a8a" : "#2563eb", color: "#fff", fontWeight: 800, cursor: "pointer" }}>
          {loading ? "Refreshing..." : "Run Decision"}
        </button>
      </div>

      {error && <div style={{ ...baseCard, borderColor: "#7f1d1d", color: "#fecaca", marginBottom: 12 }}>Error: {error}</div>}

      <div style={{ ...baseCard, marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Data Quality Snapshot</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
          {Object.entries(sourceStatus).map(([key, value]) => <SourceStatusPill key={key} name={key} entry={value} />)}
          {Object.keys(sourceStatus).length === 0 && <span style={{ color: "#93a4bf" }}>No source status available.</span>}
        </div>
        <div style={{ fontSize: 13, color: "#cbd5e1" }}>
          Counts: games={Number(sourceCounts?.games_today || 0)}, odds_games={Number(sourceCounts?.odds_games || 0)}, player_props={Number(sourceCounts?.player_props || 0)}, player_trends={Number(sourceCounts?.player_trends || 0)}, team_trends={Number(sourceCounts?.team_trends || 0)}
        </div>
        {unavailable.length > 0 && <div style={{ marginTop: 8, color: "#fca5a5", fontSize: 13 }}>Unavailable sources: {unavailable.join(", ")}</div>}
      </div>

      <div style={{ ...baseCard, marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Pre-Bet Refresh Checkpoint</h2>
        {!refreshCheckpoint ? (
          <p style={{ color: "#93a4bf" }}>No refresh checkpoint available.</p>
        ) : (
          <>
            <p style={{ marginTop: 0, color: refreshCheckpoint?.is_stale ? "#fca5a5" : "#86efac" }}>
              Status: {refreshCheckpoint?.is_stale ? "STALE / RECHECK REQUIRED" : "FRESH ENOUGH TO REVIEW"}
            </p>
            <p style={{ color: "#cbd5e1", fontSize: 13 }}>
              Captured: {refreshCheckpoint?.captured_at || "N/A"} | Narrative generated: {refreshCheckpoint?.narrative_generated_at || "N/A"} | Cache used: {String(refreshCheckpoint?.cache_used)}
            </p>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Stale Reasons</div>
            <ul style={{ marginTop: 0 }}>
              {(refreshCheckpoint?.stale_reasons || []).map((r, idx) => <li key={idx}>{r}</li>)}
              {(refreshCheckpoint?.stale_reasons || []).length === 0 && <li>None detected.</li>}
            </ul>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Pre-Bet Checklist</div>
            <ul style={{ marginTop: 0 }}>
              {(refreshCheckpoint?.pre_bet_checklist || []).map((r, idx) => <li key={idx}>{r}</li>)}
            </ul>
          </>
        )}
      </div>

      <div style={{ ...baseCard, marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Decision Output</h2>
        <div style={{ display: "inline-block", border: `1px solid ${recColor}`, color: recColor, borderRadius: 999, fontWeight: 900, padding: "8px 14px", marginBottom: 10 }}>
          Recommendation: {recommendation}
        </div>
        <div style={{ color: "#93a4bf", fontSize: 13, marginBottom: 10 }}>{data?.disclaimer || "Decision-support only."}</div>

        <div style={{ marginBottom: 8, fontWeight: 700 }}>Rationale</div>
        <ul style={{ marginTop: 0 }}>
          {rationale.map((r, idx) => <li key={idx}>{r}</li>)}
          {rationale.length === 0 && <li>No rationale available.</li>}
        </ul>

        <div style={{ marginBottom: 8, fontWeight: 700 }}>Risk Flags</div>
        <ul style={{ marginTop: 0 }}>
          {riskFlags.map((r, idx) => <li key={idx}>{r}</li>)}
          {riskFlags.length === 0 && <li>No explicit flags returned.</li>}
        </ul>

        {isParlay && (
          <div style={{ marginTop: 10, border: "1px solid #334155", borderRadius: 10, padding: 10, background: "#0b1220" }}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>
              Parlay Quality Score: {parlayQualityScore ?? "N/A"}{parlayQualityLabel ? ` (${parlayQualityLabel})` : ""}
            </div>
            <ul style={{ margin: 0 }}>
              {parlayQualityReasons.map((r, idx) => <li key={idx}>{r}</li>)}
              {parlayQualityReasons.length === 0 && <li>No additional parlay guardrail notes.</li>}
            </ul>
          </div>
        )}

        <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "end" }}>
          <label>
            <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700, fontSize: 12 }}>Sportsbook Odds (decimal)</div>
            <input type="number" step="0.01" min="1.01" value={sportsbookOdds} onChange={(e) => setSportsbookOdds(e.target.value)} style={{ padding: "8px 10px", borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }} placeholder="e.g. 1.91" />
          </label>
          <button onClick={trackCurrentPick} disabled={trackLoading || !data} style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #16a34a", background: trackLoading ? "#166534" : "#15803d", color: "#fff", fontWeight: 800, cursor: "pointer" }}>
            {trackLoading ? "Tracking..." : "Track This Pick"}
          </button>
          {trackMessage && <span style={{ color: "#cbd5e1", fontSize: 13 }}>{trackMessage}</span>}
        </div>
      </div>

      <div style={{ ...baseCard, marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Post-Bet Review Snapshot</h2>
        {!performance ? (
          <p style={{ color: "#93a4bf" }}>Loading performance...</p>
        ) : (
          <>
            <p style={{ marginTop: 0, color: "#cbd5e1" }}>
              Settled: {performance?.overall?.settled ?? 0} | Win rate: {performance?.overall?.win_rate ?? "N/A"} | ROI: {performance?.overall?.roi ?? "N/A"} | PnL: {performance?.overall?.pnl_units ?? 0}u
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8 }}>
              {Object.entries(performance?.by_pick_type || {}).map(([k, v]) => (
                <div key={k} style={{ border: "1px solid #334155", borderRadius: 10, padding: 10, background: "#0b1220" }}>
                  <div style={{ fontWeight: 800, marginBottom: 6 }}>{k}</div>
                  <div style={{ fontSize: 13, color: "#cbd5e1" }}>
                    settled={v?.settled ?? 0}, win_rate={v?.win_rate ?? "N/A"}, roi={v?.roi ?? "N/A"}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Tracked Picks</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8, marginBottom: 10 }}>
                <select value={filterPickType} onChange={(e) => setFilterPickType(e.target.value)} style={{ padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
                  <option value="">All pick types</option>
                  <option value="straight">straight</option>
                  <option value="smart_parlay">smart_parlay</option>
                  <option value="lotto_parlay">lotto_parlay</option>
                  <option value="sleeper">sleeper</option>
                </select>
                <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
                  <option value="">All status</option>
                  <option value="open">open</option>
                  <option value="settled">settled</option>
                </select>
                <select value={filterResult} onChange={(e) => setFilterResult(e.target.value)} style={{ padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
                  <option value="">All results</option>
                  <option value="win">win</option>
                  <option value="loss">loss</option>
                  <option value="push">push</option>
                </select>
                <input type="date" value={filterDateFrom} onChange={(e) => setFilterDateFrom(e.target.value)} style={{ padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }} />
                <input type="date" value={filterDateTo} onChange={(e) => setFilterDateTo(e.target.value)} style={{ padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }} />
                <button onClick={exportCsv} style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #334155", background: "#111827", color: "#e5e7eb", cursor: "pointer", fontWeight: 700 }}>
                  Export CSV
                </button>
              </div>

              <ul style={{ marginTop: 0 }}>
                {recentPicks.map((p) => (
                  <li key={p.pick_id} style={{ marginBottom: 8 }}>
                    <span>{p.pick_type} | {p.recommendation} | status={p.status}</span>
                    <span style={{ marginLeft: 8, color: "#93a4bf", fontSize: 12 }}>odds={p.sportsbook_odds_decimal ?? "N/A"} | stake={p.stake_units ?? "N/A"}</span>
                    {p.notes ? <span style={{ marginLeft: 8, color: "#93a4bf", fontSize: 12 }}>notes="{p.notes}"</span> : null}
                    <span style={{ marginLeft: 8, display: "inline-flex", gap: 6 }}>
                      {p.status === "open" && (
                        <button onClick={() => editPick(p)} style={{ padding: "2px 8px", borderRadius: 8, border: "1px solid #334155", background: "#0f172a", color: "#e5e7eb", cursor: "pointer" }}>
                          Edit
                        </button>
                      )}
                      <button onClick={() => deletePick(p)} style={{ padding: "2px 8px", borderRadius: 8, border: "1px solid #7f1d1d", background: "#2a0d0d", color: "#fecaca", cursor: "pointer" }}>
                        Delete
                      </button>
                    </span>
                  </li>
                ))}
                {recentPicks.length === 0 && <li>No tracked picks yet.</li>}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
