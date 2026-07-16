"""
Embedding wrapper.

Converts Chunk objects into (embedding_vector, id, metadata, document) tuples
ready for upsert into ChromaDB.

Batching
--------
Azure OpenAI's embedding endpoint accepts up to 2048 inputs per request.
We batch in groups of EMBED_BATCH_SIZE to stay well within limits and
avoid rate-limit errors on large PDFs.

Retry
-----
Uses tenacity for exponential backoff on transient Azure API errors.
"""

import hashlib
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APIConnectionError
from backend.tools.pdf_parser import Chunk
from backend.tools.llm_client import get_embeddings

EMBED_BATCH_SIZE = 100


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    reraise=True,
)
def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, with retry on rate limit / connection errors."""
    embeddings = get_embeddings()
    return embeddings.embed_documents(texts)


def embed_chunks(
    chunks: list[Chunk],
    cusip: str,
    issuer: str = "",
    settlement_date: str = "",
) -> list[dict]:
    """
    Embed a list of Chunk objects and return a list of ChromaDB-ready records.

    Each record has keys: id, embedding, document, metadata.
    The id is a deterministic hash of cusip + chunk_index so re-ingestion
    of the same note is idempotent (upsert replaces the old record).

    Args:
        chunks: output of pdf_parser.parse_pdf()
        cusip: note identifier — used as a metadata filter key
        issuer: issuer name (optional, improves filter queries)
        settlement_date: ISO date string (optional)

    Returns:
        List of dicts ready to pass to collection.upsert()
    """
    records: list[dict] = []

    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i : i + EMBED_BATCH_SIZE]
        texts = [c.text for c in batch]
        vectors = _embed_batch(texts)

        for chunk, vector in zip(batch, vectors):
            chunk_id = _make_id(cusip, chunk.chunk_index)
            records.append(
                {
                    "id": chunk_id,
                    "embedding": vector,
                    "document": chunk.text,
                    "metadata": {
                        "cusip": cusip,
                        "issuer": issuer,
                        "settlement_date": settlement_date,
                        "page": chunk.page,
                        "section": chunk.section,
                        "chunk_index": chunk.chunk_index,
                        "source_file": chunk.source_file,
                    },
                }
            )

    return records


def _make_id(cusip: str, chunk_index: int) -> str:
    """Deterministic chunk ID — same cusip + index always produces the same id."""
    raw = f"{cusip}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
