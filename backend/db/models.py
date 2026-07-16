"""
SQLAlchemy ORM models for the structured notes database.

Schema design principles:
  - Core identity fields (CUSIP, Issuer, dates) are typed columns for filtering
  - Full extracted payload stored as JSON text for schema flexibility
  - Risk findings, confidence scores, and baseline deviations in separate tables
    so they can be queried and updated independently

Phase 2: Wire models into crud.py and create tables.
Phase 1: Models defined, not yet used.
"""

import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class StructuredNote(Base):
    __tablename__ = "structured_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cusip = Column(String(12), unique=True, nullable=False, index=True)
    isin = Column(String(20), nullable=True)

    # Core identity — typed for filtering in the dashboard
    issuer = Column(String(255), nullable=True)
    guarantor = Column(String(255), nullable=True)
    trade_date = Column(String(20), nullable=True)       # ISO date string
    settlement_date = Column(String(20), nullable=True, index=True)
    maturity_date = Column(String(20), nullable=True)

    # Classification
    note_type = Column(String(100), nullable=True)       # primary structure tag
    structure_tags = Column(Text, nullable=True)         # JSON array of tags
    risk_tier = Column(String(10), nullable=True)        # high / medium / low

    # Key risk fields — typed for dashboard filtering
    barrier_level = Column(Float, nullable=True)
    principal_protection_pct = Column(Float, nullable=True)
    has_worst_of = Column(Boolean, default=False)
    has_memory_coupon = Column(Boolean, default=False)

    # Full extraction payload
    extracted_fields_json = Column(Text, nullable=True)  # full UEQSN schema JSON

    # Source
    source_file = Column(String(500), nullable=True)
    source_url = Column(String(2000), nullable=True)
    chunks_stored = Column(Integer, default=0)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    risk_findings = relationship("NoteRiskFinding", back_populates="note", cascade="all, delete-orphan")
    baseline_deviations = relationship("NoteBaselineDeviation", back_populates="note", cascade="all, delete-orphan")

    def get_structure_tags(self) -> list[str]:
        if not self.structure_tags:
            return []
        return json.loads(self.structure_tags)

    def set_structure_tags(self, tags: list[str]) -> None:
        self.structure_tags = json.dumps(tags)


class NoteRiskFinding(Base):
    __tablename__ = "note_risk_findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("structured_notes.id"), nullable=False)
    term = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    note_text = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    source_section = Column(String(255), nullable=True)

    note = relationship("StructuredNote", back_populates="risk_findings")

    __table_args__ = (Index("ix_risk_findings_note_id", "note_id"),)


class NoteBaselineDeviation(Base):
    __tablename__ = "note_baseline_deviations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("structured_notes.id"), nullable=False)
    field = Column(String(255), nullable=False)
    expected = Column(Text, nullable=True)
    actual = Column(Text, nullable=True)
    severity = Column(String(10), nullable=False)

    note = relationship("StructuredNote", back_populates="baseline_deviations")

    __table_args__ = (Index("ix_baseline_deviations_note_id", "note_id"),)
