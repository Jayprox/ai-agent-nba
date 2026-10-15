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
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

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

  useEffect(() => {
    fetchPickLab();
  }, [query]);

  const recommendation = String(data?.decision?.recommendation || "pass").toUpperCase();
  const recColor =
    recommendation === "BET"
      ? "#22c55e"
      : recommendation === "LEAN"
      ? "#f59e0b"
      : "#ef4444";

  const sourceStatus = data?.data_quality?.source_status || {};
  const sourceCounts = data?.data_quality?.source_counts || {};
  const unavailable = data?.data_quality?.unavailable_sources || [];
  const rationale = data?.decision?.rationale || [];
  const riskFlags = data?.decision?.risk_flags || [];

  return (
    <div style={{ color: "#e5e7eb", padding: "16px", maxWidth: 1160, margin: "0 auto" }}>
      <div style={{ ...baseCard, marginBottom: 12 }}>
        <h1 style={{ margin: 0, fontSize: 32, lineHeight: 1.1 }}>Research-to-Pick Lab</h1>
        <p style={{ margin: "8px 0 0", color: "#9ca3af" }}>
          Decision-support workflow. No lock language, no guarantees.
        </p>
      </div>

      <div
        style={{
          ...baseCard,
          marginBottom: 12,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 10,
        }}
      >
        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Pick Type</div>
          <select value={pickType} onChange={(e) => setPickType(e.target.value)} style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
            {PICK_TYPES.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Legs</div>
          <input
            type="number"
            min={1}
            max={12}
            value={legs}
            onChange={(e) => setLegs(Math.max(1, Math.min(12, Number(e.target.value || 1))))}
            disabled={pickType === "straight" || pickType === "sleeper"}
            style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}
          />
        </label>

        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Odds Band</div>
          <select value={oddsBand} onChange={(e) => setOddsBand(e.target.value)} style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
            {ODDS_BANDS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label>
          <div style={{ marginBottom: 4, color: "#93c5fd", fontWeight: 700 }}>Risk Profile</div>
          <select value={riskProfile} onChange={(e) => setRiskProfile(e.target.value)} style={{ width: "100%", padding: 8, borderRadius: 8, background: "#0b1220", color: "#fff", border: "1px solid #334155" }}>
            {RISK_PROFILES.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <button
          onClick={fetchPickLab}
          disabled={loading}
          style={{
            alignSelf: "end",
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #2563eb",
            background: loading ? "#1e3a8a" : "#2563eb",
            color: "#fff",
            fontWeight: 800,
            cursor: "pointer",
          }}
        >
          {loading ? "Refreshing..." : "Run Decision"}
        </button>
      </div>

      {error && <div style={{ ...baseCard, borderColor: "#7f1d1d", color: "#fecaca", marginBottom: 12 }}>Error: {error}</div>}

      <div style={{ ...baseCard, marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Data Quality Snapshot</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
          {Object.entries(sourceStatus).map(([key, value]) => (
            <SourceStatusPill key={key} name={key} entry={value} />
          ))}
          {Object.keys(sourceStatus).length === 0 && <span style={{ color: "#93a4bf" }}>No source status available.</span>}
        </div>
        <div style={{ fontSize: 13, color: "#cbd5e1" }}>
          Counts: games={Number(sourceCounts?.games_today || 0)}, odds_games={Number(sourceCounts?.odds_games || 0)}, player_props={Number(sourceCounts?.player_props || 0)}, player_trends={Number(sourceCounts?.player_trends || 0)}, team_trends={Number(sourceCounts?.team_trends || 0)}
        </div>
        {unavailable.length > 0 && (
          <div style={{ marginTop: 8, color: "#fca5a5", fontSize: 13 }}>
            Unavailable sources: {unavailable.join(", ")}
          </div>
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
      </div>
    </div>
  );
}
