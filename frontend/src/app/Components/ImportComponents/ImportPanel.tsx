"use client";

import { useState } from "react";
import { IngestResponse } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";

interface ImportPanelProps {
  onClose: () => void;
  onIngestComplete?: () => void;
}

export default function ImportPanel({ onClose, onIngestComplete }: ImportPanelProps) {
  const [cusip, setCusip]       = useState("");
  const [file, setFile]         = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult]     = useState<IngestResponse | null>(null);
  const [error, setError]       = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file)  { setError("Please select a PDF file."); return; }
    if (!cusip.trim()) { setError("Please enter the CUSIP for this note."); return; }

    setIsUploading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("cusip", cusip.trim().toUpperCase());

      const res = await fetch(`${API}/api/ingest/upload`, { method: "POST", body: form });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || `HTTP ${res.status}`);
      }

      const data: IngestResponse = await res.json();
      setResult(data);
      onIngestComplete?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const SEVERITY_COLOR: Record<string, string> = {
    high: "text-red-400", medium: "text-yellow-400", low: "text-green-400",
  };

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
            onChange={(e) => setCusip(e.target.value)}
          />

          <input
            type="file"
            accept=".pdf"
            className="file-input file-input-bordered file-input-sm w-full bg-gray-700 text-white"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file && <p className="text-gray-400 text-xs">Selected: {file.name}</p>}

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <div className="flex gap-2 mt-auto">
            <button
              className="btn btn-primary btn-sm flex-1"
              onClick={handleUpload}
              disabled={isUploading}
            >
              {isUploading && <span className="animate-spin mr-2">⏳</span>}
              {isUploading ? "Analysing…" : "Ingest & Analyse"}
            </button>
            <button className="btn btn-sm flex-1" onClick={onClose}>Cancel</button>
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
              <p className="text-xs text-gray-400 font-semibold mb-1">Baseline Deviations</p>
              {result.baseline_deviations.map((d, i) => (
                <div key={i} className={`text-xs ${SEVERITY_COLOR[d.severity]}`}>
                  [{d.severity.toUpperCase()}] {d.field}: expected {d.expected}, got {d.actual}
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
            <button className="btn btn-sm flex-1" onClick={() => setResult(null)}>Ingest Another</button>
            <button className="btn btn-sm flex-1" onClick={onClose}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
