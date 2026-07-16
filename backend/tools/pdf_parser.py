"""
PDF parsing and section-aware chunking.

Strategy
--------
Term sheet PDFs have inconsistent layouts (tables, dense prose, bullets).
We use a two-pass approach:

  Pass 1 — Section detection:
    Split pages on known section header patterns (e.g. "Terms", "Underlying",
    "Payment", "Risk Factors"). Each detected section becomes a logical unit.

  Pass 2 — Sub-chunking:
    If a section exceeds MAX_CHUNK_TOKENS, split it into overlapping sub-chunks
    of TARGET_CHUNK_TOKENS with OVERLAP_TOKENS overlap.

This preserves semantic coherence better than blind fixed-size sliding windows
and makes retrieval easier to debug (chunk metadata includes section name).

Tuning
------
Adjust TARGET_CHUNK_TOKENS and OVERLAP_TOKENS in Phase 2 after reviewing
retrieval quality on the four sample PDFs. Store chunk_index + section_header
in ChromaDB metadata to trace retrieval back to source.
"""

import re
import os
from dataclasses import dataclass, field
import pdfplumber

# ─── Tuning constants (adjust after Phase 2 evaluation) ───────────────────────
TARGET_CHUNK_TOKENS = 500
OVERLAP_TOKENS = 100
# Rough chars-per-token for English financial text (conservative)
CHARS_PER_TOKEN = 4

TARGET_CHUNK_CHARS = TARGET_CHUNK_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN

# Section header patterns — case-insensitive, match line-start
SECTION_HEADERS = re.compile(
    r"^("
    r"terms|underlying|payment|risk factors?|description|"
    r"call|coupon|barrier|redemption|accrual|observation|"
    r"general information|product details?|key dates?|"
    r"summary|overview|structure"
    r")\b",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class Chunk:
    text: str
    page: int
    section: str
    chunk_index: int
    source_file: str
    metadata: dict = field(default_factory=dict)


def parse_pdf(pdf_path: str) -> list[Chunk]:
    """
    Parse a term sheet PDF and return a list of text chunks with metadata.

    Raises FileNotFoundError if the path does not exist.
    Raises ValueError if no text can be extracted (likely a scanned image PDF).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    filename = os.path.basename(pdf_path)
    pages_text: list[tuple[int, str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            # pdfplumber sometimes returns table text as None rows; strip clean
            text = _clean_text(text)
            if text:
                pages_text.append((i, text))

    if not pages_text:
        raise ValueError(
            f"No text extracted from '{filename}'. "
            "The PDF may be scanned/image-based and requires OCR."
        )

    full_text = "\n".join(t for _, t in pages_text)
    page_boundaries = _build_page_map(pages_text)

    sections = _split_into_sections(full_text)
    chunks: list[Chunk] = []
    chunk_index = 0

    for section_name, section_text in sections:
        page_num = _page_for_offset(section_text, page_boundaries, pages_text)
        sub_chunks = _sub_chunk(section_text)
        for sub in sub_chunks:
            chunks.append(
                Chunk(
                    text=sub,
                    page=page_num,
                    section=section_name,
                    chunk_index=chunk_index,
                    source_file=filename,
                )
            )
            chunk_index += 1

    return chunks


# ─── Internal helpers ──────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Normalise whitespace without destroying structure."""
    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove form feeds and other control chars
    text = re.sub(r"[\x0c\x0d]", "\n", text)
    return text.strip()


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """
    Split document text on section header matches.
    Returns list of (section_name, section_text) tuples.
    The text before the first header is labelled 'preamble'.
    """
    matches = list(SECTION_HEADERS.finditer(text))
    if not matches:
        return [("document", text)]

    sections: list[tuple[str, str]] = []

    # Text before first header
    if matches[0].start() > 0:
        sections.append(("preamble", text[: matches[0].start()].strip()))

    for i, match in enumerate(matches):
        section_name = match.group(0).strip().lower()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((section_name, text[start:end].strip()))

    return [(name, body) for name, body in sections if body]


def _sub_chunk(text: str) -> list[str]:
    """
    Split a section into overlapping character chunks.
    Returns the section as-is if it fits within TARGET_CHUNK_CHARS.
    """
    if len(text) <= TARGET_CHUNK_CHARS:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + TARGET_CHUNK_CHARS
        chunk = text[start:end]
        # Prefer splitting on a sentence boundary (". ") within the last 20%
        if end < len(text):
            boundary = chunk.rfind(". ", int(TARGET_CHUNK_CHARS * 0.8))
            if boundary != -1:
                end = start + boundary + 2  # include the period + space
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - OVERLAP_CHARS  # overlap with previous chunk

    return [c for c in chunks if c]


def _build_page_map(pages_text: list[tuple[int, str]]) -> list[tuple[int, int]]:
    """
    Returns list of (page_num, cumulative_char_end) so we can map a text
    offset back to a page number.
    """
    boundaries = []
    total = 0
    for page_num, text in pages_text:
        total += len(text) + 1  # +1 for the joining newline
        boundaries.append((page_num, total))
    return boundaries


def _page_for_offset(
    section_text: str,
    boundaries: list[tuple[int, int]],
    pages_text: list[tuple[int, str]],
) -> int:
    """Best-effort: find which page the section starts on."""
    # Find the section in the full document text
    full = "\n".join(t for _, t in pages_text)
    offset = full.find(section_text[:50])  # match on first 50 chars
    if offset == -1:
        return pages_text[0][0]
    for page_num, end in boundaries:
        if offset < end:
            return page_num
    return pages_text[-1][0]
