# Structured Notes Intelligence Engine

> RAG-powered analysis pipeline for equity structured note term sheets.  
> Ingests a PDF → extracts 50+ fields → flags risks → scores per-field confidence with source citations → detects structural conflicts → supports analyst review workflow → generates a report → answers plain-English questions about any note.

---

## What It Does

- **Ingests** PDF term sheets, chunks them with section-aware context, and stores embeddings in ChromaDB
- **Analyses** each note through a LangGraph pipeline: triage → field extraction → risk flagging → baseline comparison → confidence scoring → source attribution → conflict detection → report generation
- **Shows its work** — every extracted field carries a confidence score (0–100), the LLM's reasoning, and a verbatim excerpt from the exact page and section of the source document
- **Tracks analyst work** — analysts can accept or flag individual fields; review state persists to PostgreSQL and survives re-ingestion
- **Answers questions** in plain language ("is this contract high risk?", "what is the maximum loss?") with every claim cited back to the source section

---

## Stack

| Layer | Choice |
|---|---|
| LLM | Azure OpenAI `gpt-5.4` |
| Orchestration | LangGraph `StateGraph` |
| Vector store | ChromaDB (local `PersistentClient` → cloud) |
| Embeddings | `text-embedding-3-small` via Azure OpenAI |
| PDF parsing | `pdfplumber` |
| API | FastAPI + Uvicorn |
| Database | Azure PostgreSQL Flexible Server via SQLAlchemy |
| Frontend | Next.js 16 + AG Grid + DaisyUI + Tailwind v4 |
| Infrastructure | Azure Bicep (fully repeatable — `az deployment group create`) |

---

## Prerequisites

Before running locally, ensure the following are installed:

| Tool | Purpose | Install |
|---|---|---|
| Python 3.11+ | Backend runtime | [python.org](https://www.python.org/downloads/) |
| Node.js 20+ | Frontend runtime | [nodejs.org](https://nodejs.org/) |
| Azure CLI | Provision infra via `deploy.ps1` | [aka.ms/installazurecli](https://aka.ms/installazurecli) |

Then authenticate with Azure:

```bash
az login
```

> **Already have a `.env` from a prior deployment?** You can skip `az login` and go straight to Quick Start — the app reads API keys directly from `.env` and does not call Azure CLI at runtime. `az login` is only required when running `.\infra\deploy.ps1` to provision new Azure resources.

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd structured-notes-intelligence-engine

# 2. Configure environment
cp .env.example .env
# Fill in all values — the app raises immediately on startup if any are missing

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Start the API (from project root)
python -m uvicorn backend.main:app --reload --port 3001

# 5. Start the frontend (new terminal)
cd frontend
npm install
npm run dev   # → http://localhost:3000

# 6. Ingest term sheets
#    PDFs are not in git — see "Adding New Contracts" below for sourcing instructions.
python scripts/ingest_remaining.py
```

> **Azure infra**: deploy with `.\infra\deploy.ps1 -SqlPassword <yourpassword>`.  
> All resources (OpenAI, PostgreSQL, Key Vault) are provisioned via `infra/main.bicep`.

---

## Project Structure

```
structured-notes-intelligence-engine/
├── .env.example              # Required env var names (no values)
├── requirements.txt          # Pinned Python dependencies
├── sample_term_sheets/       # PDF term sheets (not in git — see "Adding New Contracts")
├── output/                   # Generated analyst reports (gitignored)
├── scripts/                  # Ingest + test utilities
│
├── backend/
│   ├── main.py               # FastAPI entry point + all routes
│   ├── config.py             # Centralized env loading (fail-fast)
│   ├── tools/                # Stateless utilities (pdf_parser, embedder, chroma, llm)
│   ├── pipeline/
│   │   ├── graph.py          # LangGraph StateGraph + triage routing
│   │   ├── state.py          # NoteAnalysisState TypedDict
│   │   └── nodes/            # One file per stage (ingest, triage, extract, ...)
│   ├── db/                   # SQLAlchemy engine, models, CRUD
│   └── domain/               # UEQSN schema, prompts, risk terms, baseline rules
│
├── frontend/                 # Next.js 16 dashboard
│   └── src/app/
│       ├── page.tsx          # Notes index (AG Grid) + tabbed detail panel
│       ├── Components/
│       │   ├── CusipDetailsPanel/
│       │   │   └── SelectedCusipDetails.tsx  # 3-tab detail: Overview, Confidence Review, Conflicts
│       │   ├── ImportComponents/             # Ingest panel + polling
│       │   ├── IndexGridComponents/          # AG Grid notes list
│       │   └── HeaderSubComponents/          # Filter bar
│       └── query/page.tsx    # RAG semantic search
│
└── infra/                    # Azure Bicep IaC
    ├── main.bicep
    ├── modules/              # openai, postgres, keyvault, app-service
    └── params/               # dev.parameters.json, prod.parameters.json
```

---

## Pipeline Detail

```
PDF
  ↓ section-aware chunking (pdfplumber)
  ↓ embed → ChromaDB
  ↓ retrieve top-k chunks
  ↓ triage  →  HIGH / MEDIUM / LOW  (routes depth of downstream analysis)
  ↓ extract  (52 UEQSN fields for HIGH, core fields for MEDIUM, meta-only for LOW)
  ↓ flag_risks  (rule-based: worst-of, barrier, autocall, leverage terms)
  ↓ compare_baseline  (barrier ≥ 60%, required fields, CouponMemory, CallSettlementLag)
  ↓ confidence  (per-field score 0–100 + LLM reasoning)
  ↓ source attribution  (embedding query per field → ChromaDB → page, section, verbatim excerpt)
  ↓ conflict detection  (cross-field structural inconsistencies with severity + recommendation)
  ↓ persist → Azure PostgreSQL
  ↓ generate_report → output/{cusip}_report.md
```

---

## Confidence Review & Analyst Workflow

The Confidence Review system is one of the core differentiators of this tool. Rather than presenting raw extracted fields as authoritative, it exposes the full reasoning chain so analysts can verify, accept, or flag each field.

### Per-field confidence entries

Every scored field stores four properties:

| Property | Description |
|---|---|
| `score` | 0–100 integer — how confident the LLM is in the extraction |
| `reason` | LLM's natural-language explanation of that score |
| `source_section` | Section of the contract where evidence was found (e.g. "coupon") |
| `source_page` | Page number in the source PDF |
| `source_excerpt` | Verbatim text extracted from that page/section via ChromaDB |

The excerpt is the raw text from `pdfplumber` — it can be Ctrl+F'd in the original PDF to locate the exact passage.

### Three confidence tiers

| Tier | Score range | Meaning |
|---|---|---|
| Needs Verification | < 70% | Analyst should manually confirm against source document |
| Monitor | 70–89% | LLM is reasonably confident but flagged uncertainty in reasoning |
| High Confidence | ≥ 90% | Extraction is well-supported by clear contract language |

### Analyst review workflow

Analysts can mark each field directly in the Confidence Review tab:

- **✓ Accept** — confirms the extraction is correct; persisted to `field_reviews` table in PostgreSQL
- **⚑ Flag** — marks the field for further attention or correction
- Review state survives re-ingestion and page refreshes
- The tab bar shows a live `X / Y reviewed` counter so analysts can track progress without scrolling

### Conflict detection

Structural conflicts are cross-field inconsistencies detected by the pipeline — areas where two or more extracted fields are logically contradictory or ambiguous. Each conflict includes:

- Severity (high / medium / low)
- The fields involved (clickable — navigate directly to those fields in Confidence Review)
- A recommendation from the analysis
- Source citations cross-referenced from the involved fields' confidence entries

Conflicts live in their own dedicated tab to keep them clearly separated from per-field confidence review.

---

## Database Schema

| Table | Purpose |
|---|---|
| `structured_notes` | Core note identity, typed fields, extracted JSON, confidence scores JSON |
| `note_risk_findings` | Per-note risk term matches (barrier, worst-of, autocall, etc.) |
| `note_baseline_deviations` | Deviations from firm baseline rules |
| `note_conflicts` | Cross-field structural conflicts from the confidence node |
| `field_reviews` | Analyst accept/flag state per field, keyed by `(note_id, field)` |

Schema migrations are applied automatically at startup via `crud.run_migrations()`.

---

## API Routes

| Method | Route | Description |
|---|---|---|
| GET | `/api/health` | ChromaDB + PostgreSQL status |
| POST | `/api/ingest/upload` | Upload PDF + CUSIP, starts background pipeline |
| GET | `/api/ingest/status/{job_id}` | Poll ingest job result |
| GET | `/api/notes` | List notes with optional filters |
| GET | `/api/notes/{cusip}` | Full note detail (fields, scores, conflicts, reviews) |
| PATCH | `/api/notes/{cusip}/fields/{field}/review` | Set/clear analyst review state for a field |
| POST | `/api/query` | RAG semantic search across ingested notes |
| GET | `/api/notes/{cusip}/report` | Markdown analyst report (cached or generated on demand) |

---

## Adding New Contracts

PDFs are not committed to git. Every developer sources their own term sheets and ingests them locally. The recommended free source is **[SEC EDGAR](https://efts.sec.gov/LATEST/search-index?q=%22autocallable%22+%22barrier%22&forms=424B2)**, which hosts structured note prospectuses (form 424B2) from all major issuers.

### Finding term sheets on EDGAR

Go to [EDGAR](https://www.sec.gov) → **Search Filings** → **Full Text Search**.

In the search form:
- **Search text**: `autocallable "barrier level"` (or swap in `"worst-of"`, `"buffered"`, `"principal protected"`)
- **Form type**: `424B2`

This returns filings from all major issuers. Click any result to open the Filing Detail page.

**Getting the PDF** — most 424B2 filings are `.htm`, not `.pdf`. In the Document Format Files table:
1. Click the Seq 1 document (the `.htm` link — the main filing)
2. The term sheet opens in your browser
3. Print → **Save as PDF** → save to `sample_term_sheets/`

The CUSIP is on the first page of the document, usually labeled "CUSIP:" — copy the 9-character code before saving.

For a varied demo, aim for a mix of issuers: Goldman Sachs, JPMorgan, Barclays, Morgan Stanley, Citigroup, Royal Bank of Canada. Each has a distinct risk and structure profile that exercises different pipeline paths.

### Option A — Upload via the UI (one at a time)

With the app running, click **+ Ingest PDF** in the top-right corner of the Notes page. Enter the CUSIP, choose the PDF, and click **Ingest & Analyse**. The full pipeline runs in the background and the note appears in the grid when complete.

### Option B — Bulk ingest via script

Drop PDFs into `sample_term_sheets/`, register each one in `scripts/ingest_remaining.py`:

```python
CUSIP_MAP = {
    # existing entries ...
    "my-new-note.pdf": "48136CCJ6",
}
```

Then run:

```bash
python scripts/ingest_remaining.py
```

Already-ingested files are skipped automatically. Each PDF takes roughly 30–60 seconds through the full LangGraph pipeline (longer for HIGH-tier notes due to source attribution embedding queries per field).

---

## Build Status

| Phase | Focus | Status |
|---|---|---|
| 0 | Project scaffold, config, .env, gitignore | ✅ Complete |
| 1 | LLM factory, ChromaDB, PDF parser, embedder, ingest node | ✅ Complete |
| 2 | RAG extraction loop — triage, extract, persist, FastAPI routes | ✅ Complete |
| 3 | Intelligence layer — flag_risks, compare_baseline, confidence | ✅ Complete |
| 4 | Report generation + `/api/query` RAG endpoint | ✅ Complete |
| 5 | Next.js frontend — notes grid, detail panel, query page | ✅ Complete |
| 5.1 | Confidence Review UI — per-field scores, source citations, tabbed detail panel | ✅ Complete |
| 5.2 | Analyst workflow — accept/flag per field, PostgreSQL persistence, review progress | ✅ Complete |
| 5.3 | Conflicts tab — dedicated view with source cross-reference and field navigation | ✅ Complete |
| 6 | Hardening — tests, retry logic, Docker Compose, Key Vault prod | 🔲 Pending |

### Roadmap (post-demo)

| Item | Description |
|---|---|
| Conflict resolution workflow | Same accept/flag pattern as fields, keyed by issue hash for re-ingest stability |
| Multi-user identity | Track which analyst accepted/flagged each field |
| Adaptive schema | Type-specific field extraction based on triage note_type |
| Adversarial review step | Second LLM re-extracts high-stakes fields; disagreements lower confidence |
| Booking system integration | Phase 4 — reconciliation against live positions |

---

See [DEMO.md](DEMO.md) for a full walkthrough with screenshots.
