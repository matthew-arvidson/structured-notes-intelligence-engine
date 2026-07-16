"""
Tests for pdf_parser chunking logic.

The section-detection and sub-chunking logic is pure Python — no API needed.
Full PDF parsing tests (which need real PDFs) are marked with a custom marker
so they can be skipped in CI without the sample files.

    pytest backend/tests/test_pdf_parser.py -v
    pytest backend/tests/test_pdf_parser.py -v -m "not requires_pdf"
"""

import pytest
from backend.tools.pdf_parser import (
    _clean_text,
    _split_into_sections,
    _sub_chunk,
    TARGET_CHUNK_CHARS,
    OVERLAP_CHARS,
)


class TestCleanText:

    def test_collapses_multiple_blank_lines(self):
        text = "Line one\n\n\n\nLine two"
        assert _clean_text(text) == "Line one\n\nLine two"

    def test_strips_leading_trailing_whitespace(self):
        assert _clean_text("  hello  ") == "hello"

    def test_handles_empty_string(self):
        assert _clean_text("") == ""


class TestSplitIntoSections:

    def test_no_headers_returns_single_document_section(self):
        text = "This is a plain document with no headers."
        sections = _split_into_sections(text)
        assert len(sections) == 1
        assert sections[0][0] == "document"

    def test_detects_terms_header(self):
        text = "Some intro text.\n\nTerms\nAll the term details here."
        sections = _split_into_sections(text)
        names = [s[0] for s in sections]
        assert any("terms" in n for n in names)

    def test_detects_multiple_headers(self):
        text = (
            "Terms\nTerm details.\n\n"
            "Underlying\nUnderlying details.\n\n"
            "Payment\nPayment details."
        )
        sections = _split_into_sections(text)
        names = [s[0] for s in sections]
        assert len(sections) >= 3

    def test_preamble_captured_before_first_header(self):
        text = "Preamble content here.\n\nTerms\nTerm stuff."
        sections = _split_into_sections(text)
        names = [s[0] for s in sections]
        assert "preamble" in names

    def test_empty_sections_excluded(self):
        text = "Terms\n\nUnderlying\nSome content."
        sections = _split_into_sections(text)
        for _, body in sections:
            assert body.strip() != ""


class TestSubChunk:

    def test_short_text_returned_as_single_chunk(self):
        text = "Short text that fits within the chunk size limit."
        chunks = _sub_chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_split_into_multiple_chunks(self):
        text = "A" * (TARGET_CHUNK_CHARS * 3)
        chunks = _sub_chunk(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        text = "word " * 1000     # ~5000 chars
        chunks = _sub_chunk(text)
        if len(chunks) > 1:
            # The start of chunk[1] should appear in the tail of chunk[0]
            overlap_check = chunks[1][:OVERLAP_CHARS]
            assert overlap_check in chunks[0] or len(overlap_check) == 0

    def test_no_empty_chunks(self):
        text = "B" * (TARGET_CHUNK_CHARS * 2)
        chunks = _sub_chunk(text)
        for c in chunks:
            assert c.strip() != ""


@pytest.mark.requires_pdf
class TestParsePdf:
    """Integration tests that require real PDF files in sample_term_sheets/."""

    SAMPLE_PDF = "sample_term_sheets/48136CCJ6_Product_Termsheet.pdf"

    def test_parse_returns_chunks(self):
        from backend.tools.pdf_parser import parse_pdf
        chunks = parse_pdf(self.SAMPLE_PDF)
        assert len(chunks) > 0

    def test_chunks_have_required_fields(self):
        from backend.tools.pdf_parser import parse_pdf
        chunks = parse_pdf(self.SAMPLE_PDF)
        for c in chunks:
            assert c.text
            assert c.page >= 1
            assert c.section
            assert c.chunk_index >= 0
            assert c.source_file

    def test_file_not_found_raises(self):
        from backend.tools.pdf_parser import parse_pdf
        with pytest.raises(FileNotFoundError):
            parse_pdf("nonexistent_file.pdf")
