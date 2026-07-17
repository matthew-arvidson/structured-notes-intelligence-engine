"use client";

import { useState, Fragment } from "react";
import ReactMarkdown from "react-markdown";
import { StructuredNoteDetail } from "@/types";

const API = "";

const SEVERITY_COLOR: Record<string, string> = {
  high: "text-red-400", medium: "text-yellow-400", low: "text-green-400",
};
const SEVERITY_BADGE: Record<string, string> = {
  high: "badge-error", medium: "badge-warning", low: "badge-success",
};

const formatVal = (v: unknown): string => {
  if (v == null) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
};

interface Props {
  note: StructuredNoteDetail;
  onClose: () => void;
}

function Section({ title, defaultOpen = false, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-700 rounded mb-2">
      <button
        className="w-full flex justify-between items-center px-3 py-2 bg-[#2a2b2c] text-sm font-semibold text-white hover:bg-[#333] rounded-t"
        onClick={() => setOpen(!open)}
      >
        {title}
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="p-3 bg-[#1c1d1e]">{children}</div>}
    </div>
  );
}

export default function SelectedCusipDetails({ note, onClose }: Props) {
  const [reportMd, setReportMd]   = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const loadReport = async () => {
    setReportLoading(true);
    try {
      const r = await fetch(`${API}/api/notes/${note.cusip}/report`);
      const d = await r.json();
      setReportMd(d.report ?? null);
    } finally {
      setReportLoading(false);
    }
  };

  const fields = note.extracted_fields ?? {};
  const nonNullFields = Object.entries(fields).filter(([, v]) => v != null && v !== "");

  return (
    <div className="flex flex-col h-full text-sm text-gray-200">
      {/* Sticky header */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#2E3436] rounded-t shrink-0">
        <div>
          <span className="font-mono font-bold text-white text-base">{note.cusip}</span>
          {note.note_type && <span className="ml-2 text-gray-400">{note.note_type}</span>}
        </div>
        <div className="flex items-center gap-2">
          {note.risk_tier && (
            <span className={`badge badge-sm font-semibold uppercase ${SEVERITY_BADGE[note.risk_tier]}`}>
              {note.risk_tier}
            </span>
          )}
          <button className="btn btn-xs btn-ghost" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-2 space-y-1">

        {/* Identity */}
        <Section title="Identity" defaultOpen>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            {[
              ["Issuer",      note.issuer],
              ["Guarantor",   note.guarantor],
              ["Trade Date",  note.trade_date],
              ["Settlement",  note.settlement_date],
              ["Maturity",    note.maturity_date],
              ["ISIN",        note.isin],
              ["Barrier",     note.barrier_level != null ? `${note.barrier_level}%` : null],
              ["Worst-of",    note.has_worst_of ? "Yes" : "No"],
              ["Memory Cpn",  note.has_memory_coupon ? "Yes" : "No"],
              ["Chunks",      note.chunks_stored],
            ].filter(([, val]) => val != null && val !== "")
             .map(([label, val]) => (
              <Fragment key={String(label)}>
                <span className="text-gray-500">{label}</span>
                <span>{String(val)}</span>
              </Fragment>
            ))}
          </div>
          {note.structure_tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {note.structure_tags.map((t) => (
                <span key={t} className="badge badge-xs badge-outline text-gray-300">{t}</span>
              ))}
            </div>
          )}
        </Section>

        {/* Risk Findings */}
        {note.risk_findings?.length > 0 && (
          <Section title={`Risk Findings (${note.risk_findings.length})`}>
            <div className="space-y-2">
              {note.risk_findings.map((f, i) => (
                <div key={i} className="border-l-2 border-gray-600 pl-2">
                  <div className="flex gap-2 items-baseline">
                    <span className={`text-xs font-semibold uppercase ${SEVERITY_COLOR[f.severity]}`}>{f.severity}</span>
                    <span className="font-semibold text-white">{f.term}</span>
                    <span className="text-gray-500 text-xs">{f.category}</span>
                  </div>
                  {f.excerpt && <p className="text-gray-400 text-xs mt-1 italic">&ldquo;{f.excerpt}&rdquo;</p>}
                  {f.source_section && <p className="text-gray-600 text-xs">section: {f.source_section}</p>}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Baseline Deviations */}
        {note.baseline_deviations?.length > 0 && (
          <Section title={`Baseline Deviations (${note.baseline_deviations.length})`}>
            <div className="space-y-1">
              {note.baseline_deviations.map((d, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className={`shrink-0 font-semibold uppercase ${SEVERITY_COLOR[d.severity]}`}>[{d.severity}]</span>
                  <div>
                    <span className="text-white font-semibold">{d.field}</span>
                    <span className="text-gray-400"> — expected {d.expected}, got </span>
                    <span className="text-yellow-300">{d.actual}</span>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Extracted Fields */}
        {nonNullFields.length > 0 && (
          <Section title={`Extracted Fields (${nonNullFields.length})`}>
            <div className="space-y-1 max-h-64 overflow-auto">
              {nonNullFields.map(([k, v]) => {
                const display = formatVal(v);
                return (
                  <div key={k} className="flex gap-2 text-xs border-b border-gray-700 py-0.5">
                    <span className="text-gray-500 w-40 shrink-0">{k}</span>
                    <span className="text-gray-200 break-all" title={display}>
                      {display.length > 120 ? display.slice(0, 120) + "…" : display}
                    </span>
                  </div>
                );
              })}
            </div>
          </Section>
        )}

        {/* Analyst Report */}
        <Section title="Analyst Report">
          {!reportMd ? (
            <button
              className="btn btn-sm btn-outline w-full"
              onClick={loadReport}
              disabled={reportLoading}
            >
              {reportLoading ? "Loading…" : "Load Report"}
            </button>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none overflow-auto max-h-[50vh] text-xs">
              <ReactMarkdown>{reportMd}</ReactMarkdown>
            </div>
          )}
        </Section>

      </div>
    </div>
  );
}
