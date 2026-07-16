# Structured Notes Intelligence Engine

A ground-up rewrite combining the best of two prior projects:
- **Code quality & architecture** from `llm_practice` (LangGraph, triage routing, clean tool separation)
- **Domain knowledge & UI** from `structured-notes-final` (UEQSN schema, Prompts_v2, FastAPI + Next.js shell)
- **RAG with ChromaDB** — replaces the one-shot PDF-dump approach in both predecessors

## What It Does

Ingests equity structured-note term sheets (PDF or URL), extracts structured fields via a
LangGraph pipeline with triage-based routing, stores results in Azure SQL, and surfaces them
through a Next.js dashboard with natural-language semantic search via ChromaDB.

## Pipeline

```
Term Sheet PDF / URL
  → Chunk (section-aware) → Embed → ChromaDB
  → Retrieve relevant chunks
  → Triage (note type + risk tier: HIGH / MEDIUM / LOW)
  → Extract (UEQSN schema fields, depth by tier)
  → Flag Risks (rule-based: barrier, worst-of, autocall)
  → Compare Baseline (vs firm-standard structure)
  → Confidence Scoring + Conflict Detection
  → Persist to Azure SQL
  → Generate Analyst Report
```

## Stack

| Layer | Choice |
|---|---|
| LLM | Azure OpenAI (configurable deployment) |
| Orchestration | LangGraph StateGraph |
| Vector store | ChromaDB (local dev → cloud prod) |
| Embeddings | text-embedding-3-small via Azure OpenAI |
| PDF parsing | pdfplumber |
| API | FastAPI + Uvicorn |
| Database | Azure SQL via SQLAlchemy |
| Frontend | Next.js 15 + AG Grid + Tailwind (Phase 5) |

## Quick Start

```bash
# 1. Clone and set up environment
cp .env.example .env
# Fill in all values in .env — the app raises loudly if any are missing

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the API
cd backend
uvicorn main:app --reload --port 3001

# 4. Run tests
pytest backend/tests/ -v
```

## Project Structure

```
structured-notes-intelligence-engine/
├── .env.example          # Required env var names (no values)
├── requirements.txt      # Pinned dependencies
├── sample_term_sheets/   # 4 test PDFs from prior project
│
└── backend/
    ├── main.py           # FastAPI entry point
    ├── config.py         # Centralized env loading (fail-fast)
    ├── tools/            # Stateless utilities (pdf_parser, embedder, chroma, llm)
    ├── pipeline/         # LangGraph graph + nodes
    │   └── nodes/        # One file per pipeline stage
    ├── db/               # SQLAlchemy engine, models, CRUD
    ├── domain/           # Schema, prompts, risk terms, glossary
    └── tests/            # pytest suite
```

## Build Phases

See `plan.md` in the `llm_practice` workspace for the full phased build plan.

| Phase | Focus | Status |
|---|---|---|
| 1 | Foundation — config, LLM factory, ChromaDB, PDF parser, embedder | In progress |
| 2 | RAG extraction loop — ingest → retrieve → extract → persist | Pending |
| 3 | Intelligence layer — triage, risk flags, baseline comparison, confidence | Pending |
| 4 | Report generation + remaining API routes | Pending |
| 5 | Next.js frontend port | Pending |
| 6 | Hardening — tests, logging, retries, Docker Compose | Pending |
