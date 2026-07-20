"""
Ingest all PDF term sheets in sample_term_sheets/ that are not already in the database.

Usage:
    python scripts/ingest_remaining.py

How to add new term sheets:
    1. Drop a PDF into sample_term_sheets/
    2. Add an entry to CUSIP_MAP below (filename → CUSIP)
    3. Re-run this script — already-ingested files are skipped automatically

CUSIP_MAP keys are filenames only (no path). If a file is not in the map,
the script derives a synthetic CUSIP from the filename so it still ingests.
"""

import sys
import os
import re
import requests
import json

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:3001"
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_term_sheets")

# Map filename → CUSIP.
# Add an entry here whenever you drop in a new PDF.
# Filenames are case-sensitive on Linux; match exactly what is on disk.
CUSIP_MAP = {
    # --- original samples ---
    "0001918704-25-008024.pdf": "001918724",
    "apac-termsheet.pdf":       "APAC00001",
    "FT-FRCASA010175-3.pdf":    "FRCASA0101",
    # --- add new samples below ---
    "citi-17333HPN8.pdf":   "17333HPN8",
    # "my-new-note.pdf": "GS00000001",
}


def derive_cusip(filename: str) -> str:
    """Fallback: turn filename into a short uppercase identifier."""
    stem = os.path.splitext(filename)[0]
    cleaned = re.sub(r"[^A-Z0-9]", "", stem.upper())
    return cleaned[:9].ljust(9, "0")


def already_ingested(cusip: str) -> bool:
    try:
        r = requests.get(f"{BASE}/api/notes/{cusip}", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def ingest(pdf_path: str, cusip: str) -> None:
    print(f"\n{'='*60}")
    print(f"  File : {os.path.basename(pdf_path)}")
    print(f"  CUSIP: {cusip}")
    print("="*60)
    with open(pdf_path, "rb") as f:
        r = requests.post(
            f"{BASE}/api/ingest/upload",
            data={"cusip": cusip},
            files={"file": f},
            timeout=120,
        )
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:200]}")
        return
    d = r.json()
    print(f"  note_type        : {d.get('note_type')}")
    print(f"  risk_tier        : {d.get('risk_tier')}")
    print(f"  structure_tags   : {d.get('structure_tags')}")
    print(f"  fields_extracted : {d.get('fields_extracted')}")
    print(f"  risk_findings    : {d.get('risk_findings')}")
    print(f"  deviations       : {len(d.get('baseline_deviations', []))}")
    print(f"  errors           : {d.get('errors')}")
    if d.get("baseline_deviations"):
        for dev in d["baseline_deviations"]:
            print(f"    [{dev['severity'].upper()}] {dev['field']}: "
                  f"expected={dev['expected']} actual={dev['actual']}")


# --- Main ---
pdfs = sorted(
    f for f in os.listdir(SAMPLES_DIR) if f.lower().endswith(".pdf")
)

if not pdfs:
    print("No PDFs found in sample_term_sheets/")
    sys.exit(0)

print(f"Found {len(pdfs)} PDF(s) in sample_term_sheets/\n")

skipped = 0
ingested = 0

for filename in pdfs:
    cusip = CUSIP_MAP.get(filename) or derive_cusip(filename)
    if already_ingested(cusip):
        print(f"  [SKIP] {filename} (CUSIP={cusip} already in DB)")
        skipped += 1
        continue
    ingest(os.path.join(SAMPLES_DIR, filename), cusip)
    ingested += 1

print(f"\nDone. Ingested: {ingested}  Skipped (already in DB): {skipped}")
