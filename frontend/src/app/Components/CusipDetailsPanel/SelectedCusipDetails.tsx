"use client";

import React, { useState, Fragment } from "react";
import ReactMarkdown from "react-markdown";
import { StructuredNoteDetail, ConfidenceEntry, Conflict } from "@/types";

const API = "";

const SEVERITY_COLOR: Record<string, string> = {
  high: "text-red-400", medium: "text-yellow-400", low: "text-green-400",
};
const SEVERITY_BADGE: Record<string, string> = {
  high: "badge-error", medium: "badge-warning", low: "badge-success",
};
const SEVERITY_DOT: Record<string, string> = {
  high: "bg-red-400", medium: "bg-yellow-400", low: "bg-green-400",
};

const humanField = (field: string) => field.replace(/([a-z])([A-Z])/g, "$1 $2");
const deviationMessage = (expected: string, actual: string) =>
  actual === "null" || actual == null ? "not found in document" : `expected ${expected}, found ${actual}`;
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

function ScoreBadge({ field, entry }: { field: string; entry: ConfidenceEntry | number | undefined }) {
  if (entry == null) return null;
  const s = typeof entry === "object" ? (entry as ConfidenceEntry).score : entry as number;
  const reason = typeof entry === "object" ? (entry as ConfidenceEntry).reason : "";
  const dotColor  = s >= 90 ? "bg-green-400"  : s >= 70 ? "bg-yellow-400"  : "bg-red-400";
  const textColor = s >= 90 ? "text-green-400" : s >= 70 ? "text-yellow-400" : "text-red-400";
  return (
    <span className="flex items-center gap-1 cursor-help shrink-0" title={reason || `Confidence: ${s}%`}>
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span className={`text-[10px] ${textColor}`}>{s}%</span>
    </span>
  );
}

function SourceCitation({ ce }: { ce: ConfidenceEntry | null | undefined }) {
  if (!ce || (!ce.source_section && ce.source_page == null)) return null;
  return (
    <div className="mt-1.5 px-2 py-1.5 bg-[#131720] border border-blue-900/50 rounded text-[10px] space-y-1">
      <div className="flex items-center gap-1.5 text-blue-400 font-semibold">
        <span>📄</span>
        {ce.source_page != null && <span>Page {ce.source_page}</span>}
        {ce.source_page != null && ce.source_section && <span>·</span>}
        {ce.source_section && <span className="truncate max-w-[180px] capitalize">{ce.source_section}</span>}
      </div>
      {ce.source_excerpt && (
        <p className="text-gray-400 italic leading-relaxed">
          &ldquo;{ce.source_excerpt}&rdquo;
        </p>
      )}
    </div>
  );
}

type ReviewState = "accepted" | "flagged";
function ReviewButtons({
  field,
  reviews,
  onUpdate,
}: {
  field: string;
  reviews: Record<string, ReviewState>;
  onUpdate: (field: string, state: ReviewState | null) => void;
}) {
  const current = reviews[field] ?? null;
  return (
    <div className="flex gap-1 mt-2">
      <button
        onClick={(e) => { e.stopPropagation(); onUpdate(field, current === "accepted" ? null : "accepted"); }}
        className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border transition-colors ${
          current === "accepted"
            ? "bg-green-800/50 text-green-300 border-green-600/60"
            : "text-gray-500 border-transparent hover:text-green-400 hover:bg-green-900/30 hover:border-green-800/50"
        }`}
        title="Accept this extraction"
      >
        ✓ Accept
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onUpdate(field, current === "flagged" ? null : "flagged"); }}
        className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border transition-colors ${
          current === "flagged"
            ? "bg-orange-800/50 text-orange-300 border-orange-600/60"
            : "text-gray-500 border-transparent hover:text-orange-400 hover:bg-orange-900/30 hover:border-orange-800/50"
        }`}
        title="Flag for further review"
      >
        ⚑ Flag
      </button>
    </div>
  );
}

export default function SelectedCusipDetails({ note, onClose }: Props) {
  const [activeTab, setActiveTab]         = useState<"overview" | "confidence" | "conflicts">("overview");
  const [reportMd, setReportMd]           = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError]     = useState<string | null>(null);

  // Confidence tab — section open state driven by parent so summary badges can open them
  const [openVerify,    setOpenVerify]    = useState(true);
  const [openMonitor,   setOpenMonitor]   = useState(false);
  const [openHigh,      setOpenHigh]      = useState(false);
  const [highlightedField, setHighlightedField] = useState<string | null>(null);
  const [selectedConflict, setSelectedConflict] = useState<number | null>(null);
  const [fieldReviews, setFieldReviews] = useState<Record<string, "accepted" | "flagged">>(
    note.field_reviews ?? {}
  );

  const updateReview = async (field: string, state: "accepted" | "flagged" | null) => {
    // Optimistic update
    setFieldReviews(prev => {
      const next = { ...prev };
      if (state === null) delete next[field];
      else next[field] = state;
      return next;
    });
    try {
      await fetch(`${API}/api/notes/${note.cusip}/fields/${encodeURIComponent(field)}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state }),
      });
    } catch (e) {
      console.error("Failed to save review state", e);
    }
  };

  const verifyRef    = React.useRef<HTMLDivElement>(null);
  const monitorRef   = React.useRef<HTMLDivElement>(null);
  const highRef      = React.useRef<HTMLDivElement>(null);

  const jumpTo = (
    setter: React.Dispatch<React.SetStateAction<boolean>>,
    ref: React.RefObject<HTMLDivElement | null>,
  ) => {
    setter(true);
    setTimeout(() => ref.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };

  const jumpToField = (field: string) => {
    // Toggle off if already selected
    if (highlightedField === field) {
      setHighlightedField(null);
      return;
    }
    const score = getScore(field);
    setActiveTab("confidence");
    if (score != null) {
      if (score < 70)       setOpenVerify(true);
      else if (score < 90)  setOpenMonitor(true);
      else                  setOpenHigh(true);
    }
    setHighlightedField(field);
    setTimeout(() => {
      document.getElementById(`conf-field-${field}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
  };

  const loadReport = async () => {
    setReportLoading(true);
    setReportError(null);
    try {
      const r = await fetch(`${API}/api/notes/${note.cusip}/report`);
      const d = await r.json();
      if (d.report) setReportMd(d.report);
      else setReportError(d.message ?? "Report could not be generated for this note.");
    } catch {
      setReportError("Failed to reach the API — ensure the backend is running.");
    } finally {
      setReportLoading(false);
    }
  };

  // ── Normalize confidence scores ──────────────────────────────────────────────
  const fields = note.extracted_fields ?? {};
  const rawScores = note.confidence_scores ?? {};
  const scores: Record<string, ConfidenceEntry | number> = Array.isArray(rawScores)
    ? (rawScores.length > 0 && typeof rawScores[0] === "object" ? rawScores[0] as Record<string, ConfidenceEntry> : {})
    : rawScores as Record<string, ConfidenceEntry>;

  const getScore = (field: string): number | null => {
    const e = scores[field];
    if (e == null) return null;
    return typeof e === "object" ? (e as ConfidenceEntry).score : e as number;
  };

  const nonNullFields = Object.entries(fields).filter(([, v]) => v != null && v !== "");

  // ── Confidence Review derived data ───────────────────────────────────────────
  const scoredFields = nonNullFields
    .map(([k, v]) => ({ field: k, value: v, score: getScore(k) }))
    .filter((x) => x.score != null) as { field: string; value: unknown; score: number }[];

  const needsReview  = scoredFields.filter((x) => x.score < 70).sort((a, b) => a.score - b.score);
  const monitor      = scoredFields.filter((x) => x.score >= 70 && x.score < 90).sort((a, b) => a.score - b.score);
  const highConf     = scoredFields.filter((x) => x.score >= 90).sort((a, b) => b.score - a.score);
  const conflicts    = (note.conflicts ?? []) as Conflict[];

  const tabClass = (tab: "overview" | "confidence" | "conflicts") =>
    `px-3 py-1.5 text-xs font-semibold border-b-2 transition-colors ${
      activeTab === tab
        ? "border-blue-400 text-white"
        : "border-transparent text-gray-500 hover:text-gray-300"
    }`;

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

      {/* Tab bar */}
      <div className="flex items-center border-b border-gray-700 bg-[#222] shrink-0">
        <button className={tabClass("overview")} onClick={() => setActiveTab("overview")}>
          Overview
        </button>
        <button className={tabClass("confidence")} onClick={() => setActiveTab("confidence")}>
          Confidence Review
          {needsReview.length > 0 && (
            <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold">
              {needsReview.length}
            </span>
          )}
        </button>
        <button className={tabClass("conflicts")} onClick={() => setActiveTab("conflicts")}>
          Conflicts
          {conflicts.length > 0 && (
            <span className={`ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-white text-[9px] font-bold ${conflicts.some(c => c.severity === "high") ? "bg-red-500" : "bg-orange-500"}`}>
              {conflicts.length}
            </span>
          )}
        </button>
        {scoredFields.length > 0 && (
          <div className="ml-auto pr-3 flex items-center gap-1 text-[10px] shrink-0">
            <span className="text-blue-400 font-semibold">{Object.keys(fieldReviews).length}</span>
            <span className="text-gray-500">/ {scoredFields.length} reviewed</span>
          </div>
        )}
      </div>

      {/* ── TAB 1: Overview ─────────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="flex-1 overflow-auto p-2 space-y-1">

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

          {note.baseline_deviations?.length > 0 && (
            <Section title={`Review Items (${note.baseline_deviations.length})`}>
              <div className="space-y-1">
                {note.baseline_deviations.map((d, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs text-gray-300">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${SEVERITY_DOT[d.severity] ?? "bg-gray-400"}`} />
                    <span>{humanField(d.field)} — {deviationMessage(d.expected, d.actual)}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {nonNullFields.length > 0 && (
            <Section title={`Extracted Fields (${nonNullFields.length})`}>
              <div className="space-y-1 max-h-64 overflow-auto">
                {nonNullFields.map(([k, v]) => {
                  const display = formatVal(v);
                  const scored = scores[k] != null;
                  return (
                    <div
                      key={k}
                      className={`flex gap-2 items-center text-xs border-b border-gray-700 py-0.5 rounded px-1 -mx-1 transition-colors ${scored ? "cursor-pointer hover:bg-blue-900/20" : ""} ${highlightedField === k ? "bg-blue-900/20 border-b-blue-800/60" : ""}`}
                      onClick={() => scored ? jumpToField(k) : undefined}
                      title={scored ? (highlightedField === k ? `Deselect ${humanField(k)}` : `View confidence detail for ${humanField(k)}`) : undefined}
                    >
                      <span className={`w-40 shrink-0 ${highlightedField === k ? "text-blue-300" : scored ? "text-gray-400" : "text-gray-500"}`}>{k}</span>
                      <span className="text-gray-200 break-all flex-1" title={display}>
                        {display.length > 120 ? display.slice(0, 120) + "…" : display}
                      </span>
                      <ScoreBadge field={k} entry={scores[k]} />
                      {fieldReviews[k] === "accepted" && <span className="text-green-400 text-[10px] shrink-0" title="Accepted">✓</span>}
                      {fieldReviews[k] === "flagged"  && <span className="text-orange-400 text-[10px] shrink-0" title="Flagged">⚑</span>}
                    </div>
                  );
                })}
              </div>
              {Object.keys(scores).length > 0 && (
                <div className="flex gap-3 mt-2 text-[10px] text-gray-500">
                  <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />≥90%</span>
                  <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-yellow-400 inline-block" />70–89%</span>
                  <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />&lt;70% — verify</span>
                </div>
              )}
            </Section>
          )}

          <Section title="Analyst Report">
            {!reportMd ? (
              <div className="space-y-2">
                <button className="btn btn-sm btn-outline w-full" onClick={loadReport} disabled={reportLoading}>
                  {reportLoading ? "Generating…" : "Load Report"}
                </button>
                {reportError && <p className="text-xs text-red-400 text-center">{reportError}</p>}
              </div>
            ) : (
              <div>
                <div className="flex justify-end mb-1">
                  <button className="btn btn-xs btn-ghost text-gray-400 hover:text-white" onClick={loadReport} disabled={reportLoading} title="Reload report">
                    {reportLoading ? "…" : "↻ Refresh"}
                  </button>
                </div>
                <div className="prose prose-invert prose-sm max-w-none overflow-auto max-h-[50vh] text-xs">
                  <ReactMarkdown>{reportMd}</ReactMarkdown>
                </div>
              </div>
            )}
          </Section>

        </div>
      )}

      {/* Sticky navigation bar — confidence tier jump links, visible on Confidence Review tab */}
      {activeTab === "confidence" && scoredFields.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-2 py-1.5 bg-[#1a1b1c] border-b border-gray-700 shrink-0 text-xs">
          <button
            onClick={() => jumpTo(setOpenHigh, highRef)}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#1c2c1c] hover:bg-[#243424] transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
            <span className="text-green-400 font-semibold">{highConf.length}</span>
            <span className="text-gray-500">high confidence</span>
          </button>
          <button
            onClick={() => jumpTo(setOpenMonitor, monitorRef)}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#2c2a1c] hover:bg-[#343220] transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 inline-block" />
            <span className="text-yellow-400 font-semibold">{monitor.length}</span>
            <span className="text-gray-500">monitor</span>
          </button>
          <button
            onClick={() => jumpTo(setOpenVerify, verifyRef)}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#2c1c1c] hover:bg-[#341f1f] transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
            <span className="text-red-400 font-semibold">{needsReview.length}</span>
            <span className="text-gray-500">verify</span>
          </button>
          {conflicts.length > 0 && (
            <button
              onClick={() => setActiveTab("conflicts")}
              className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#2c251c] hover:bg-[#342d20] transition-colors"
              title="View Conflicts tab"
            >
              <span className="text-orange-400">⚠</span>
              <span className="text-orange-400 font-semibold">{conflicts.length}</span>
              <span className="text-gray-500">conflicts</span>
            </button>
          )}
        </div>
      )}
      {activeTab === "confidence" && (
        <div className="flex-1 overflow-auto p-2 space-y-2">

          {/* ── Confidence sections ── */}
          <div className="space-y-2">

            {/* Needs Verification */}
            {needsReview.length > 0 && (
              <div ref={verifyRef}>
                <button
                  className="w-full flex justify-between items-center px-3 py-2 bg-[#2a2b2c] text-sm font-semibold text-white hover:bg-[#333] rounded-t border border-gray-700"
                  onClick={() => setOpenVerify(v => !v)}
                >
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
                      Needs Verification — &lt;70% ({needsReview.length})
                      <span
                        className="text-gray-500 hover:text-gray-300 cursor-help text-[10px] font-normal"
                        title="Score below 70 — the LLM flagged meaningful uncertainty in this extraction. Manual verification against the source document is recommended before relying on this field."
                      >ℹ</span>
                    </span>
                  <span className="text-gray-400">{openVerify ? "▲" : "▼"}</span>
                </button>
                {openVerify && (
                  <div className="p-3 bg-[#1c1d1e] border border-t-0 border-gray-700 rounded-b space-y-2">
                    {needsReview.map(({ field, value }) => {
                      const entry = scores[field];
                      const ce = typeof entry === "object" ? (entry as ConfidenceEntry) : null;
                      const reason = ce?.reason ?? "";
                      return (
                        <div
                          key={field}
                          id={`conf-field-${field}`}
                          onClick={() => setHighlightedField(highlightedField === field ? null : field)}
                          className={`border-l-2 border-red-500 pl-2 py-1 rounded-r cursor-pointer transition-all duration-300 ${highlightedField === field ? "bg-blue-900/30 ring-2 ring-blue-400/70" : "hover:bg-white/5"}`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-white text-xs font-semibold">{humanField(field)}</span>
                            <ScoreBadge field={field} entry={entry} />
                          </div>
                          <p className="text-gray-400 text-xs mt-0.5">
                            Value: <span className="text-gray-200">{formatVal(value).slice(0, 100)}</span>
                          </p>
                          {reason && <p className="text-red-300 text-xs mt-0.5 italic">{reason}</p>}
                          <SourceCitation ce={ce} />
                          <ReviewButtons field={field} reviews={fieldReviews} onUpdate={updateReview} />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Monitor */}
            {monitor.length > 0 && (
              <div ref={monitorRef}>
                <button
                  className="w-full flex justify-between items-center px-3 py-2 bg-[#2a2b2c] text-sm font-semibold text-white hover:bg-[#333] rounded-t border border-gray-700"
                  onClick={() => setOpenMonitor(v => !v)}
                >
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />
                      Monitor — 70–89% ({monitor.length})
                      <span
                        className="text-gray-500 hover:text-gray-300 cursor-help text-[10px] font-normal"
                        title="Score 70–89 — the LLM is reasonably confident but noted some uncertainty. Worth a secondary check, especially on high-stakes fields."
                      >ℹ</span>
                    </span>
                  <span className="text-gray-400">{openMonitor ? "▲" : "▼"}</span>
                </button>
                {openMonitor && (
                  <div className="p-3 bg-[#1c1d1e] border border-t-0 border-gray-700 rounded-b space-y-2">
                    {monitor.map(({ field, value }) => {
                      const entry = scores[field];
                      const ce = typeof entry === "object" ? (entry as ConfidenceEntry) : null;
                      const reason = ce?.reason ?? "";
                      return (
                        <div
                          key={field}
                          id={`conf-field-${field}`}
                          onClick={() => setHighlightedField(highlightedField === field ? null : field)}
                          className={`border-l-2 border-yellow-500 pl-2 py-1 rounded-r cursor-pointer transition-all duration-300 ${highlightedField === field ? "bg-blue-900/30 ring-2 ring-blue-400/70" : "hover:bg-white/5"}`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-white text-xs font-semibold">{humanField(field)}</span>
                            <ScoreBadge field={field} entry={entry} />
                          </div>
                          <p className="text-gray-400 text-xs mt-0.5">
                            Value: <span className="text-gray-200">{formatVal(value).slice(0, 100)}</span>
                          </p>
                          {reason && <p className="text-yellow-300 text-xs mt-0.5 italic">{reason}</p>}
                          <SourceCitation ce={ce} />
                          <ReviewButtons field={field} reviews={fieldReviews} onUpdate={updateReview} />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* High Confidence */}
            {highConf.length > 0 && (
              <div ref={highRef}>
                <button
                  className="w-full flex justify-between items-center px-3 py-2 bg-[#2a2b2c] text-sm font-semibold text-white hover:bg-[#333] rounded-t border border-gray-700"
                  onClick={() => setOpenHigh(v => !v)}
                >
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
                      High Confidence — ≥90% ({highConf.length})
                      <span
                        className="text-gray-500 hover:text-gray-300 cursor-help text-[10px] font-normal"
                        title="Score 90 or above — the LLM found clear, unambiguous supporting language in the contract. Source citations are still attached for audit purposes."
                      >ℹ</span>
                    </span>
                  <span className="text-gray-400">{openHigh ? "▲" : "▼"}</span>
                </button>
                {openHigh && (
                  <div className="p-3 bg-[#1c1d1e] border border-t-0 border-gray-700 rounded-b space-y-2">
                    {highConf.map(({ field, value }) => {
                      const entry = scores[field];
                      const ce = typeof entry === "object" ? (entry as ConfidenceEntry) : null;
                      const reason = ce?.reason ?? "";
                      return (
                        <div
                          key={field}
                          id={`conf-field-${field}`}
                          onClick={() => setHighlightedField(highlightedField === field ? null : field)}
                          className={`border-l-2 border-green-600 pl-2 py-1 rounded-r cursor-pointer transition-all duration-300 ${highlightedField === field ? "bg-blue-900/30 ring-2 ring-blue-400/70" : "hover:bg-white/5"}`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-gray-300 text-xs font-semibold">{humanField(field)}</span>
                            <ScoreBadge field={field} entry={entry} />
                          </div>
                          <p className="text-gray-500 text-xs mt-0.5">
                            <span className="text-gray-300">{formatVal(value).slice(0, 100)}</span>
                          </p>
                          {reason && <p className="text-green-400/70 text-xs mt-0.5 italic">{reason}</p>}
                          <SourceCitation ce={ce} />
                          <ReviewButtons field={field} reviews={fieldReviews} onUpdate={updateReview} />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

          </div>

          {scoredFields.length === 0 && (
            <div className="text-xs text-gray-500 text-center py-8">
              No confidence data yet — re-ingest this note to generate scores.
            </div>
          )}

        </div>
      )}

      {/* ── TAB 3: Conflicts ────────────────────────────────────────────────── */}
      {activeTab === "conflicts" && (
        <div className="flex-1 overflow-auto p-3 space-y-4">

          {/* Explainer */}
          <div className="px-3 py-2.5 bg-[#1a1a14] border border-orange-900/40 rounded text-xs text-gray-400 leading-relaxed">
            <p className="text-orange-300 font-semibold mb-1">What are conflicts?</p>
            Conflicts are structural inconsistencies detected by the analysis pipeline across two or more extracted fields.
            They surface areas where the contract language may be ambiguous, internally contradictory, or where extraction logic
            identified a logical tension between related terms. Each conflict cites the fields involved and links back to the
            relevant contract passage. Use these findings to guide your manual review of affected fields.
          </div>

          {conflicts.length === 0 ? (
            <div className="text-xs text-gray-500 text-center py-10">
              No conflicts detected for this note.
            </div>
          ) : (
                  <div className="space-y-3">
                    {conflicts.map((c, i) => {
                      const fieldCEs = (c.fields_involved ?? [])
                        .map((f) => (typeof scores[f] === "object" ? scores[f] as ConfidenceEntry : null))
                        .filter((ce): ce is ConfidenceEntry => !!(ce && (ce.source_section || ce.source_page != null)));
                      const uniqueSources = fieldCEs.filter((ce, idx, arr) =>
                        arr.findIndex((x) => x.source_page === ce.source_page && x.source_section === ce.source_section) === idx
                      );
                      const isSelected = selectedConflict === i;
                      return (
                        <div
                          key={i}
                          onClick={() => setSelectedConflict(isSelected ? null : i)}
                          className={`border rounded overflow-hidden cursor-pointer transition-all duration-300 ${
                            isSelected
                              ? "border-blue-500/60 ring-2 ring-blue-400/70 bg-blue-900/10"
                              : "border-orange-900/40 bg-[#1c1a16] hover:bg-[#221e16]"
                          }`}
                        >
                    <div className="flex items-center gap-2 px-3 py-2 bg-[#221e14] border-b border-orange-900/30">
                      <span className={`text-xs font-bold uppercase ${SEVERITY_COLOR[c.severity]}`}>{c.severity}</span>
                      <span className="text-white text-xs font-semibold">{c.issue}</span>
                    </div>
                    <div className="px-3 py-2 space-y-2">
                      {c.fields_involved?.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {c.fields_involved.map((f) => (
                            <button
                              key={f}
                              onClick={(e) => { e.stopPropagation(); setActiveTab("confidence"); jumpToField(f); }}
                              className="badge badge-xs badge-outline text-orange-300 border-orange-700 hover:bg-orange-900/30 cursor-pointer transition-colors"
                              title={`Jump to ${f} in Confidence Review`}
                            >
                              {f} ↗
                            </button>
                          ))}
                        </div>
                      )}
                      {c.recommendation && (
                        <p className="text-gray-400 text-xs italic">{c.recommendation}</p>
                      )}
                      {uniqueSources.map((ce, si) => (
                        <SourceCitation key={si} ce={ce} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

    </div>
  );
}


