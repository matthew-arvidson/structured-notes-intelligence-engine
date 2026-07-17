# Demo Walkthrough

A step-by-step guide to what the Structured Notes Intelligence Engine does and how to see it in action.

---

## Scene 1 — The Notes Index

Start the app and you see the full notes grid — every ingested term sheet with its risk tier, barrier level, structure type, and key dates at a glance.

![Notes grid and analyst report panel](docs/notes-report.png)

Click any CUSIP and the detail panel opens on the right with the full intelligence output:

- **Risk Findings** — rule-based scan for worst-of provisions, leverage terms, autocall triggers, and credit risk language
- **Baseline Deviations** — automated comparison against firm-standard rules (barrier minimums, required fields, settlement lag limits)
- **Extracted Fields** — all 50+ UEQSN schema fields pulled from the source document
- **Analyst Report** — LLM-generated markdown with confidence icons (✅ high confidence, ⚠️ moderate, ➖ structurally not applicable), a plain-language summary, and a conflict review section

The `48136CCJ6` JPMorgan Buffered Note shown here was correctly identified as a worst-of, principal-at-risk structure. The report flagged an ambiguity in the contract wording around "barrier level" vs. "buffer amount" — a genuine drafting issue in the source document.

---

## Scene 2 — Ask a Question

Navigate to **Ask a Question** in the header. Use the scope dropdown to target a specific note or leave it on **All Notes** to search across your entire book.

![Query page with scope dropdown](docs/query-page.png)

Questions can be as broad or specific as you need:

- *"Which notes have a worst-of structure?"*
- *"What is the maximum loss on this note and under what conditions?"*
- *"Are there any notes where the barrier is below 60%?"*
- *"What is the issuer's credit rating and who is the guarantor?"*

---

## Scene 3 — A Grounded, Cited Answer

Every answer is grounded in the source document. The engine retrieves the most relevant chunks from ChromaDB, passes them to the LLM with the question, and returns an answer where every claim cites the exact section it came from.

![RAG answer: is this contract high risk?](docs/rag-answer.png)

The response to *"is this contract high risk?"* returned five specific risk factors — principal loss up to 80%, worst-of structure, no income, issuer credit risk, liquidity and valuation risk — each cited back to the payment or preamble section of the term sheet. The engine answers from retrieved source material rather than relying on general model knowledge, so every claim ties back to a specific section of the document.

---

## Scene 4 — Global Cross-Note Queries

Because all notes share a single ChromaDB collection, queries naturally span your entire book when no scope is selected:

> *"Which notes have a dual directional payoff?"*

> *"Find all notes where the participation rate is at least 1.2x."*

> *"Are there any notes issued by Credit Agricole?"*

Each answer cites the CUSIP and source section for every claim — fully auditable across the whole portfolio.

---

## Running It

```bash
# Start the API (from project root)
python -m uvicorn backend.main:app --reload --port 3001

# Start the frontend (separate terminal)
cd frontend && npm run dev
# → http://localhost:3000
```

Ingest a term sheet via **+ Ingest PDF** in the header, or call the API directly:

```python
import requests

with open("your_termsheet.pdf", "rb") as f:
    r = requests.post(
        "http://localhost:3001/api/ingest/upload",
        data={"cusip": "YOUR_CUSIP"},
        files={"file": f},
    )
print(r.json())
```

Azure infrastructure (OpenAI, PostgreSQL, Key Vault) is fully defined in `infra/` — deploy with one command:

```powershell
.\infra\deploy.ps1 -SqlPassword <yourpassword>
```

See [README.md](README.md) for full environment setup.

---

## Capability Summary

| Capability | How It Works |
|---|---|
| Grounded answers | Every claim cites the retrieved chunk — no LLM memory |
| Cost-aware routing | LOW-tier notes skip the full chain (6 fields vs 52) |
| Auditable risk flags | Barrier, worst-of, autocall caught by deterministic rules |
| Reproducible infra | Bicep IaC — spin up or tear down with a single command |
| Cross-note search | All notes in one ChromaDB collection — global queries work out of the box |
