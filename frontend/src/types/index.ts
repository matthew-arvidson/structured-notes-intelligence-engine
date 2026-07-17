// Types matching the Structured Notes Intelligence Engine API

export type RiskFinding = {
  term: string;
  category: string;
  severity: "high" | "medium" | "low";
  note: string;
  excerpt: string;
  source_section: string;
};

export type BaselineDeviation = {
  field: string;
  expected: string;
  actual: string;
  severity: "high" | "medium" | "low";
};

export type Conflict = {
  issue: string;
  fields_involved: string[];
  severity: "high" | "medium" | "low";
  recommendation: string;
};

export type StructuredNote = {
  id: number;
  cusip: string;
  isin: string | null;
  issuer: string | null;
  guarantor: string | null;
  trade_date: string | null;
  settlement_date: string | null;
  maturity_date: string | null;
  note_type: string | null;
  structure_tags: string[];
  risk_tier: "high" | "medium" | "low" | null;
  barrier_level: number | null;
  principal_protection_pct: number | null;
  has_worst_of: boolean;
  has_memory_coupon: boolean;
  source_file: string | null;
  chunks_stored: number;
  created_at: string | null;
  updated_at: string | null;
};

export type StructuredNoteDetail = StructuredNote & {
  extracted_fields: Record<string, unknown>;
  risk_findings: RiskFinding[];
  baseline_deviations: BaselineDeviation[];
};

export type NoteListResponse = {
  count: number;
  notes: StructuredNote[];
};

export type IngestResponse = {
  cusip: string;
  status: string;
  note_type: string | null;
  risk_tier: string | null;
  structure_tags: string[];
  chunks_stored: number;
  db_record_id: number | null;
  fields_extracted: number;
  risk_findings: number;
  baseline_deviations: BaselineDeviation[];
  matches_baseline: boolean;
  conflicts: Conflict[];
  low_confidence_fields: string[];
  report_path: string | null;
  errors: string[];
};

export type QuerySource = {
  rank: number;
  cusip: string;
  section: string;
  page: number | string;
  relevance: number;
  excerpt: string;
};

export type QueryResponse = {
  question: string;
  answer: string;
  sources: QuerySource[];
};
