"use client";

import { useState } from "react";
import { IngestResponse } from "@/types";

const API = "";

interface ImportPanelProps {
  onClose: () => void;
  onIngestComplete?: (cusip?: string) => void;
  onOpenNote?: (cusip: string) => void;
}

export default function ImportPanel({ onClose, onIngestComplete, onOpenNote }: ImportPanelProps) {
  const [cusip, setCusip]       = useState("");
  const [file, setFile]         = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [result, setResult]     = useState<IngestResponse | null>(null);
  const [error, setError]       = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file)        { setError("Please select a PDF file."); return; }
    if (!cusip.trim()) { setError("Please enter the CUSIP for this note."); return; }

    setIsUploading(true);
    setError(null);
    setResult(null);
    setProgress("Uploading…");

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("cusip", cusip.trim().toUpperCase());

      // Submit — returns immediately with a job_id
      const res = await fetch(`${API}/api/ingest/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || `HTTP ${res.status}`);
      }

      const { job_id } = await res.json();
      setProgress("Pipeline running — this takes 30–60 seconds…");

      // Poll until done
      const data = await poll(job_id);
      setResult(data);
      onIngestComplete?.(cusip.trim().toUpperCase());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setIsUploading(false);
      setProgress(null);
    }
  };

  const poll = async (job_id: string): Promise<IngestResponse> => {
    for (;;) {
      await new Promise((r) => setTimeout(r, 3000));
      const r = await fetch(`${API}/api/ingest/status/${job_id}`);
      if (!r.ok) throw new Error(`Status check failed: HTTP ${r.status}`);
      const data = await r.json();
      if (data.status === "processing") continue;
      if (data.status === "error") throw new Error(data.error ?? "Pipeline error");
      return data as IngestResponse;
    }
  };

  const SEVERITY_COLOR: Record<string, string> = {
    high: "text-red-400", medium: "text-yellow-400", low: "text-green-400",
  };

  const SEVERITY_DOT: Record<string, string> = {
    high: "bg-red-400", medium: "bg-yellow-400", low: "bg-green-400",
  };

  /** "SettlementDate" → "Settlement Date", "CUSIP" stays "CUSIP" */
  function humanField(field: string) {
    return field.replace(/([a-z])([A-Z])/g, "$1 $2");
  }

  function deviationMessage(expected: string, actual: string) {
    if (actual === "null" || actual == null) return "not found in document";
    return `expected ${expected}, found ${actual}`;
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-gray-800 rounded p-4 gap-3">
      {!result ? (
        <>
          <h3 className="text-white font-semibold text-sm">Ingest Term Sheet PDF</h3>

          <input
            type="text"
            placeholder="CUSIP (e.g. 48136CCJ6)"
            className="input input-bordered input-sm w-full bg-gray-700 text-white placeholder-gray-400 font-mono"
            value={cusip}
            onChange={(e) => { setCusip(e.target.value); setError(null); }}
          />

          <input
            type="file"
            accept=".pdf"
            className="file-input file-input-bordered file-input-sm w-full bg-gray-700 text-white"
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError(null); }}
          />
          {file && <p className="text-gray-400 text-xs">Selected: {file.name}</p>}

          {error && <p className="text-red-400 text-xs">{error}</p>}

          {progress && (
            <p className="text-blue-400 text-xs animate-pulse">{progress}</p>
          )}

          <div className="flex gap-2 mt-auto">
            <button
              className="btn btn-primary btn-sm flex-1"
              onClick={handleUpload}
              disabled={isUploading}
            >
              {isUploading && <span className="animate-spin mr-2">⏳</span>}
              {isUploading ? "Analysing…" : "Ingest & Analyse"}
            </button>
            <button className="btn btn-sm flex-1" onClick={onClose} disabled={isUploading}>Cancel</button>
          </div>
        </>
      ) : (
        <div className="flex-1 overflow-auto space-y-3 text-sm">
          <div className="flex items-center gap-2">
            <span className={`font-bold ${result.status === "ok" ? "text-green-400" : "text-yellow-400"}`}>
              {result.status === "ok" ? "✓ Ingested" : "⚠ Completed with errors"}
            </span>
            <span className="font-mono text-white">{result.cusip}</span>
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-300">
            <span className="text-gray-500">Note type</span>   <span>{result.note_type}</span>
            <span className="text-gray-500">Risk tier</span>   <span className={`font-semibold uppercase ${SEVERITY_COLOR[result.risk_tier ?? ""] ?? ""}`}>{result.risk_tier}</span>
            <span className="text-gray-500">Fields extracted</span> <span>{result.fields_extracted}</span>
            <span className="text-gray-500">Risk findings</span>    <span>{result.risk_findings}</span>
            <span className="text-gray-500">Matches baseline</span> <span>{result.matches_baseline ? "Yes" : "No"}</span>
            <span className="text-gray-500">Chunks stored</span>    <span>{result.chunks_stored}</span>
          </div>

          {result.structure_tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {result.structure_tags.map((t) => (
                <span key={t} className="badge badge-sm badge-outline text-gray-300">{t}</span>
              ))}
            </div>
          )}

          {result.baseline_deviations.length > 0 && (
            <div>
              <p className="text-xs text-gray-400 font-semibold mb-1">Review Items</p>
              {result.baseline_deviations.map((d, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-gray-300 py-0.5">
                  <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${SEVERITY_DOT[d.severity] ?? "bg-gray-400"}`} />
                  <span>{humanField(d.field)} — {deviationMessage(d.expected, d.actual)}</span>
                </div>
              ))}
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="text-xs text-red-400 font-semibold mb-1">Errors</p>
              {result.errors.map((e, i) => (
                <p key={i} className="text-xs text-red-300">{e}</p>
              ))}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              className="btn btn-primary btn-sm flex-1"
              onClick={() => { onOpenNote?.(result.cusip); onClose(); }}
            >
              Open Note
            </button>
            <button className="btn btn-sm flex-1" onClick={onClose}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
