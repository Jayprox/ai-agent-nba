// frontend/src/components/NarrativeDashboard.jsx
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

const NarrativeDashboard = () => {
  const [markdown, setMarkdown] = useState("");
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  const fetchMarkdown = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_BASE}/nba/narrative/markdown?mode=ai${forceRefresh ? "&cache_ttl=0" : ""}`;
      console.log("🔍 Fetching from:", url);
      const res = await fetch(url);
      console.log("📡 Response status:", res.status);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

      const data = await res.json();
      console.log("📦 Response data:", data);

      if (!data.ok) throw new Error(data.error || "Backend returned ok: false");
      if (!data.markdown) throw new Error("No markdown field in response");

      setMarkdown(data.markdown);
      setMeta(data.summary?.metadata || {});
      console.log("✅ Markdown loaded successfully");
    } catch (err) {
      console.error("❌ Fetch error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
      setIsRegenerating(false);
    }
  };

  useEffect(() => {
    fetchMarkdown();
  }, [API_BASE]);

  if (loading) return <div className="p-4 text-white">⏳ Generating narrative...</div>;

  if (error) {
    return (
      <div className="p-4 text-red-400">
        <h2 className="text-xl font-bold mb-2">❌ Error</h2>
        <p className="mb-4">{error}</p>
      </div>
    );
  }

  const generatedAt = meta?.generated_at
    ? new Date(meta.generated_at).toLocaleString()
    : "N/A";

  return (
    <div className="p-6 text-white max-w-4xl mx-auto">
      {/* Header + Regenerate */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">🧠 AI Narrative Dashboard</h1>
        <button
          onClick={() => {
            setIsRegenerating(true);
            fetchMarkdown(true);
          }}
          disabled={isRegenerating}
          className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
            isRegenerating
              ? "bg-gray-700 text-gray-400 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {isRegenerating ? "Generating..." : "Regenerate Narrative"}
        </button>
      </div>

      {/* Metadata */}
      <div className="text-sm text-gray-400 mb-4">
        <p>Model: {meta?.model || "Unknown"}</p>
        <p>Generated: {generatedAt}</p>
        <p>Digest: {meta?.inputs_digest || "—"}</p>
      </div>

      {/* Markdown content */}
      <div
        className="prose max-w-none bg-gray-900 p-6 rounded-2xl shadow-lg overflow-auto min-h-[400px]"
        style={{
          color: "white",
        }}
      >
        <style>
          {`
            .prose h1, .prose h2, .prose h3, .prose h4, .prose h5, .prose h6 {
              color: #f8fafc !important;
            }
            .prose p, .prose li, .prose span, .prose strong {
              color: #f1f5f9 !important;
            }
            .prose a {
              color: #60a5fa !important;
            }
            .prose code {
              color: #facc15 !important;
              background-color: #1e293b !important;
              padding: 0.15em 0.35em;
              border-radius: 4px;
            }
          `}
        </style>
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
};

export default NarrativeDashboard;
