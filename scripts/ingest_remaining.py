"""Ingest the 3 remaining sample PDFs and print a routing summary."""
import sys
import requests
import json

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:3001"

samples = [
    ("sample_term_sheets/0001918704-25-008024.pdf", "001918724"),
    ("sample_term_sheets/apac-termsheet.pdf",        "APAC00001"),
    ("sample_term_sheets/FT-FRCASA010175-3.pdf",     "FRCASA0101"),
]

for path, cusip in samples:
    print(f"\n{'='*60}")
    print(f"Ingesting: {path}  (CUSIP={cusip})")
    print("="*60)
    with open(path, "rb") as f:
        r = requests.post(
            f"{BASE}/api/ingest/upload",
            data={"cusip": cusip},
            files={"file": f},
        )
    d = r.json()
    print(f"  note_type        : {d.get('note_type')}")
    print(f"  risk_tier        : {d.get('risk_tier')}")
    print(f"  structure_tags   : {d.get('structure_tags')}")
    print(f"  fields_extracted : {d.get('fields_extracted')}")
    print(f"  risk_findings    : {d.get('risk_findings')}")
    print(f"  deviations       : {len(d.get('baseline_deviations', []))}")
    print(f"  conflicts        : {len(d.get('conflicts', []))}")
    print(f"  matches_baseline : {d.get('matches_baseline')}")
    print(f"  low_conf_fields  : {d.get('low_confidence_fields')}")
    print(f"  errors           : {d.get('errors')}")
    if d.get("baseline_deviations"):
        print("  --- deviations ---")
        for dev in d["baseline_deviations"]:
            print(f"    [{dev['severity'].upper()}] {dev['field']}: expected={dev['expected']} actual={dev['actual']}")
