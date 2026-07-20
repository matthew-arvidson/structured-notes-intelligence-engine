# Structured Notes Intelligence Engine

> RAG-powered analysis pipeline for equity structured note term sheets.  
> Ingests a PDF → extracts 50+ fields → flags risks → scores confidence → generates an analyst report → answers plain-English questions about any note.

![RAG answer: is this contract high risk?](docs/rag-answer.png)

---

## What It Does

- **Ingests** PDF term sheets, chunks them with section-aware context, and stores embeddings in ChromaDB
- **Analyses** each note through a LangGraph pipeline: triage → field extraction → risk flagging → baseline comparison → confidence scoring → conflict detection → report generation
- **Answers questions** in plain language ("is this contract high risk?", "what is the maximum loss?") with every claim cited back to the exact source section of the relevant note

Built as a ground-up rewrite combining the code quality of `llm_practice` (LangGraph, triage routing, clean tool separation) with the domain knowledge of `structured-notes-final` (UEQSN schema, Prompts_v2, AG Grid UI) — plus RAG, which neither predecessor had.

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
│       ├── page.tsx          # Notes index (AG Grid)
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
  ↓ confidence  (per-field 0-100 scores + structural conflict detection)
  ↓ persist → Azure PostgreSQL
  ↓ generate_report → output/{cusip}_report.md
```

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

Already-ingested files are skipped automatically. Each PDF takes roughly 30–60 seconds through the full LangGraph pipeline.

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
| 6 | Hardening — tests, retry logic, Docker Compose, Key Vault prod | 🔲 Pending |

---

See [DEMO.md](DEMO.md) for a full walkthrough with screenshots.
