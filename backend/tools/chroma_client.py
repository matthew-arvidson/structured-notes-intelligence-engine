"""
ChromaDB client and collection management.

Supports two modes controlled by env vars:
  - Local (default): PersistentClient writing to CHROMA_PATH on disk.
  - Remote: HttpClient connecting to a hosted ChromaDB instance.

Usage:
    from backend.tools.chroma_client import get_collection
    collection = get_collection()
    collection.add(...)
    results = collection.query(...)
"""

from functools import lru_cache
import chromadb
from chromadb import Collection
from backend.config import CHROMA_PATH, CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION


@lru_cache(maxsize=1)
def _get_client() -> chromadb.ClientAPI:
    """
    Returns a cached ChromaDB client.
    Local mode when CHROMA_HOST is blank; HttpClient otherwise.
    """
    if CHROMA_HOST:
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection(collection_name: str = CHROMA_COLLECTION) -> Collection:
    """
    Returns (or creates) the named ChromaDB collection.

    Metadata stored per chunk:
        cusip          - note identifier
        issuer         - issuer name
        settlement_date
        page           - source PDF page number
        section        - detected section header
        chunk_index    - position within the document

    cosine distance is appropriate for semantic search on embeddings.
    """
    client = _get_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def health_check() -> dict:
    """Ping ChromaDB and return a status dict for the /api/health endpoint."""
    try:
        client = _get_client()
        client.heartbeat()
        col = get_collection()
        return {"status": "ok", "collection": col.name, "count": col.count()}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def delete_by_cusip(cusip: str) -> int:
    """Remove all chunks for a given CUSIP (useful for re-ingestion)."""
    col = get_collection()
    results = col.get(where={"cusip": cusip})
    if results["ids"]:
        col.delete(ids=results["ids"])
    return len(results["ids"])
