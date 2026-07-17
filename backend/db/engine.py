"""
SQLAlchemy engine for Azure PostgreSQL Flexible Server.

Uses psycopg2 driver with SSL required (mandatory for Azure PostgreSQL).
The engine is cached so all nodes share one connection pool.
"""

from functools import lru_cache
from sqlalchemy import create_engine, Engine
from sqlalchemy.engine import URL
from backend.config import (
    AZURE_PG_HOST,
    AZURE_PG_DATABASE,
    AZURE_PG_USER,
    AZURE_PG_PASSWORD,
    AZURE_PG_PORT,
)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Returns a cached SQLAlchemy engine for Azure PostgreSQL Flexible Server.

    Uses URL.create() to safely handle any special characters in credentials
    (e.g. the @ in user@servername format that Azure outputs).
    sslmode=require is mandatory for Azure PostgreSQL.
    """
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=AZURE_PG_USER,
        password=AZURE_PG_PASSWORD,
        host=AZURE_PG_HOST,
        port=AZURE_PG_PORT,
        database=AZURE_PG_DATABASE,
        query={"sslmode": "require"},
    )
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def ping() -> bool:
    """Return True if the database is reachable. Used in the health check."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False
