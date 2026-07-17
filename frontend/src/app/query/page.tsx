"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import Header from "../Components/HeaderSubComponents/header";
import { QueryResponse } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";

const EXAMPLE_QUESTIONS = [
  "What is the maximum loss an investor can suffer, and under what conditions?",
  "Which underlying indices are referenced and what is the participation rate?",
  "What is the barrier level and how does it affect the payoff at maturity?",
  "Does this note have a memory coupon feature?",
  "What is the issuer's credit rating and who is the guarantor?",
];

const RELEVANCE_COLOR = (r: number) =>
  r >= 0.5 ? "text-green-400" : r >= 0.35 ? "text-yellow-400" : "text-gray-500";

export default function QueryPage() {
  const [question,  setQuestion]  = useState("");
  const [cusip,     setCusip]     = useState("");
  const [nResults,  setNResults]  = useState(5);
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState<QueryResponse | null>(null);
  const [error,     setError]     = useState<string | null>(null);

  const ask = async (q?: string) => {
    const finalQ = (q ?? question).trim();
    if (!finalQ) return;
    if (q) setQuestion(q);

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const body: Record<string, unknown> = { question: finalQ, n_results: nResults };
      if (cusip.trim()) body.cusip = cusip.trim().toUpperCase();

      const r = await fetch(`${API}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      setResult(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <Header />

      <div className="flex-1 overflow-auto p-4 max-w-4xl mx-auto w-full">
        <h1 className="text-xl font-bold text-white mb-1">Ask a Question</h1>
        <p className="text-gray-500 text-sm mb-4">
          Natural language search across all ingested term sheets. Every answer cites the source sections it was drawn from.
        </p>

        {/* Input area */}
        <div className="bg-[#1c1d1e] rounded p-4 space-y-3 mb-4">
          <textarea
            className="textarea textarea-bordered w-full bg-[#141516] text-white placeholder-gray-500 text-sm"
            rows={3}
            placeholder="e.g. What is the barrier level and how does it affect the payoff?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ask(); }}
          />

          <div className="flex gap-3 flex-wrap items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Filter by CUSIP (optional)</label>
              <input
                className="input input-bordered input-sm bg-[#141516] text-white font-mono w-40"
                placeholder="48136CCJ6"
                value={cusip}
                onChange={(e) => setCusip(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Sources to retrieve</label>
              <select
                className="select select-bordered select-sm bg-[#141516] text-white w-24"
                value={nResults}
                onChange={(e) => setNResults(Number(e.target.value))}
              >
                {[3, 5, 8, 10].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <button
              className="btn btn-primary btn-sm self-end"
              onClick={() => ask()}
              disabled={loading || !question.trim()}
            >
              {loading ? <span className="animate-spin">⏳</span> : "Ask"}
            </button>
          </div>
        </div>

        {/* Example questions */}
        {!result && !loading && (
          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-2">Example questions:</p>
            <div className="flex flex-col gap-1">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  className="text-left text-xs text-blue-400 hover:text-blue-300 hover:underline"
                  onClick={() => ask(q)}
                >
                  → {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="alert alert-error text-sm mb-4">{error}</div>
        )}

        {/* Answer */}
        {result && (
          <div className="space-y-4">
            <div className="bg-[#1c1d1e] rounded p-4">
              <p className="text-xs text-gray-500 mb-2 font-semibold uppercase tracking-wider">Answer</p>
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{result.answer}</ReactMarkdown>
              </div>
            </div>

            {/* Source citations */}
            <div className="bg-[#1c1d1e] rounded p-4">
              <p className="text-xs text-gray-500 mb-2 font-semibold uppercase tracking-wider">
                Sources ({result.sources.length})
              </p>
              <div className="space-y-2">
                {result.sources.map((s) => (
                  <div key={s.rank} className="flex gap-3 text-xs border-b border-gray-800 pb-2">
                    <span className="text-gray-500 shrink-0 w-5">[{s.rank}]</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex gap-3 flex-wrap mb-1">
                        <span className="font-mono text-white">{s.cusip}</span>
                        {s.section && <span className="text-gray-400">§ {s.section}</span>}
                        {s.page && <span className="text-gray-500">p.{s.page}</span>}
                        <span className={`ml-auto font-semibold ${RELEVANCE_COLOR(s.relevance)}`}>
                          {Math.round(s.relevance * 100)}% match
                        </span>
                      </div>
                      <p className="text-gray-500 truncate">{s.excerpt}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <button
              className="btn btn-sm btn-ghost w-full"
              onClick={() => { setResult(null); setQuestion(""); }}
            >
              Ask another question
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
