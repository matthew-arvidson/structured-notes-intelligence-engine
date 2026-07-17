"""Test the /api/query RAG endpoint with a series of questions."""
import sys
import requests
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:3001"

questions = [
    {
        "question": "What is the maximum loss an investor can suffer, and under what conditions does it occur?",
        "cusip": "48136CCJ6",
    },
    {
        "question": "What is the barrier level and how does it affect the payoff at maturity?",
        "cusip": "48136CCJ6",
    },
    {
        "question": "Which underlying indices are referenced in this note and what is the participation rate?",
        "cusip": "48136CCJ6",
    },
]

for q in questions:
    print("\n" + "="*70)
    print(f"Q: {q['question']}")
    print("="*70)
    r = requests.post(f"{BASE}/api/query", json=q)
    d = r.json()
    print(f"\nANSWER:\n{d.get('answer')}\n")
    print("SOURCES:")
    for s in d.get("sources", []):
        rank = s["rank"]
        cusip = s["cusip"]
        section = s["section"]
        relevance = s["relevance"]
        print(f"  [{rank}] cusip={cusip}  section={section}  relevance={relevance}")
