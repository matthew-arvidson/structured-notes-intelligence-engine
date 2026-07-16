"""
Retrieve node: ChromaDB semantic search → top-k chunks.

Phase 1: Fully implemented.

Queries ChromaDB with field-name-based queries to surface the most relevant
sections for downstream extraction. Multiple queries cover different schema
sections so no single section dominates the retrieved context.

Input state keys:  cusip
Output state keys: retrieved_chunks, errors (appended)
"""

import logging
from backend.pipeline.state import NoteAnalysisState
from backend.tools.chroma_client import get_collection
from backend.tools.llm_client import get_embeddings

logger = logging.getLogger(__name__)

# Number of chunks to retrieve per query
TOP_K = 5

# Query strings that target different sections of the UEQSN schema.
# Each query is embedded and used to retrieve semantically similar chunks.
RETRIEVAL_QUERIES = [
    "coupon rate barrier level contingent payment",
    "call schedule autocall trigger redemption",
    "underlying asset starting value observation dates",
    "barrier knock-in downside risk principal protection",
    "issuer settlement date maturity CUSIP ISIN",
    "accrual range participation rate calculation agent",
]


def run(state: NoteAnalysisState) -> dict:
    """
    Run semantic retrieval for the given CUSIP across all schema-section queries.
    Deduplicates results by chunk id and returns up to TOP_K * len(queries) chunks.
    """
    cusip = state["cusip"]
    errors: list[str] = list(state.get("errors", []))

    try:
        collection = get_collection()
        embeddings = get_embeddings()

        seen_ids: set[str] = set()
        retrieved: list[dict] = []

        for query in RETRIEVAL_QUERIES:
            query_vector = embeddings.embed_query(query)
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=TOP_K,
                where={"cusip": cusip},
                include=["documents", "metadatas", "distances"],
            )

            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    retrieved.append(
                        {
                            "id": chunk_id,
                            "text": doc,
                            "metadata": meta,
                            "distance": dist,
                        }
                    )

        # Sort by distance (lower = more similar for cosine)
        retrieved.sort(key=lambda x: x["distance"])

        logger.info(
            f"[retrieve] {len(retrieved)} unique chunks retrieved for CUSIP={cusip}"
        )
        return {"retrieved_chunks": retrieved, "errors": errors}

    except Exception as exc:
        msg = f"retrieve: unexpected error — {exc}"
        logger.exception(msg)
        errors.append(msg)
        return {"retrieved_chunks": [], "errors": errors}
