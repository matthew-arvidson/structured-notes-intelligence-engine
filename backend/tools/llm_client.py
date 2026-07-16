"""
Shared LLM and embedding client factory.

Import these instead of instantiating ChatOpenAI / AzureOpenAI directly in
each module. Keeps model/API config in one place and makes mocking easy in tests.
"""

from functools import lru_cache
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from backend.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_CHAT_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
)


@lru_cache(maxsize=1)
def get_chat_llm(temperature: float = 0.0) -> AzureChatOpenAI:
    """
    Returns a cached AzureChatOpenAI instance.

    temperature=0 for extraction/triage/comparison (deterministic).
    Pass temperature=0.2 for report generation (light creativity).
    Note: lru_cache keys on temperature, so each unique value gets its own instance.
    """
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_deployment=AZURE_OPENAI_CHAT_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=temperature,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> AzureOpenAIEmbeddings:
    """
    Returns a cached AzureOpenAIEmbeddings instance.
    Used by the embedder tool and ChromaDB ingestion.
    """
    return AzureOpenAIEmbeddings(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
    )
