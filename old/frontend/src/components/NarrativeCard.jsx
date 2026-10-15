import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { fetchNarrative } from "../services/narrativeAPI";

export default function NarrativeCard() {
  const [data, setData] = useState(null);
  const [mode, setMode] = useState("ai");

  useEffect(() => {
    fetchNarrative(mode).then(setData);
  }, [mode]);

  if (!data) return <div className="text-gray-400">Loading narrative...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6 bg-gray-900 text-white rounded-2xl shadow-lg mt-10">
      <div className="flex justify-between mb-4">
        <h2 className="text-xl font-semibold">NBA Narrative</h2>
        <button
          onClick={() => setMode(mode === "ai" ? "template" : "ai")}
          className="bg-blue-600 hover:bg-blue-500 text-sm px-3 py-1 rounded"
        >
          Mode: {mode}
        </button>
      </div>

      <article className="prose prose-invert max-w-none">
        <ReactMarkdown>{data.markdown}</ReactMarkdown>
      </article>
    </div>
  );
}
