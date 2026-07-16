"""
SQLAlchemy engine for Azure SQL.

Phase 2: Implement and test.
Phase 1: Stub — function exists but is not called yet.
"""

from functools import lru_cache
from sqlalchemy import create_engine, Engine
from backend.config import (
    AZURE_SQL_SERVER,
    AZURE_SQL_DATABASE,
    AZURE_SQL_USER,
    AZURE_SQL_PASSWORD,
)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Returns a cached SQLAlchemy engine for Azure SQL Server.

    Connection string uses pyodbc with ODBC Driver 17 for SQL Server.
    Adjust driver name if your environment has a different version installed.
    """
    connection_string = (
        f"mssql+pyodbc://{AZURE_SQL_USER}:{AZURE_SQL_PASSWORD}"
        f"@{AZURE_SQL_SERVER}/{AZURE_SQL_DATABASE}"
        f"?driver=ODBC+Driver+17+for+SQL+Server"
        f"&Encrypt=yes&TrustServerCertificate=no"
    )
    return create_engine(connection_string, pool_pre_ping=True)
