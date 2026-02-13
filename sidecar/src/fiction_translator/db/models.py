"""SQLAlchemy database models for Fiction Translator v2.0."""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TranslationStatus(enum.StrEnum):
    """Status of a translation."""
    PENDING = "pending"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class PipelineStatus(enum.StrEnum):
    """Status of a pipeline run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Project(Base):
    """A translation project."""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False, default="ko")
    target_language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")
    genre: Mapped[str | None] = mapped_column(String(50), nullable=True)
    style_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pipeline_type: Mapped[str] = mapped_column(String(30), default="cot_batch")
    llm_provider: Mapped[str] = mapped_column(String(20), default="gemini")
    # llm_config removed - keys handled via IPC
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter", back_populates="project", cascade="all, delete-orphan"
    )
    glossary_entries: Mapped[list["GlossaryEntry"]] = relationship(
        "GlossaryEntry", back_populates="project", cascade="all, delete-orphan"
    )
    personas: Mapped[list["Persona"]] = relationship(
        "Persona", back_populates="project", cascade="all, delete-orphan"
    )
    exports: Mapped[list["Export"]] = relationship(
        "Export", back_populates="project", cascade="all, delete-orphan"
    )


class Chapter(Base):
    """A chapter within a project."""
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    source_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # v2.0: Cached connected prose for export
    translated_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v2.0: Flag to invalidate cache when segments change
    translation_stale: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="chapters")
    segments: Mapped[list["Segment"]] = relationship(
        "Segment", back_populates="chapter", cascade="all, delete-orphan"
    )
    translation_batches: Mapped[list["TranslationBatch"]] = relationship(
        "TranslationBatch", back_populates="chapter", cascade="all, delete-orphan"
    )
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(
        "PipelineRun", back_populates="chapter", cascade="all, delete-orphan"
    )
    exports: Mapped[list["Export"]] = relationship(
        "Export", back_populates="chapter", cascade="all, delete-orphan"
    )
    personas_last_seen: Mapped[list["Persona"]] = relationship(
        "Persona", back_populates="last_seen_chapter", foreign_keys="[Persona.last_seen_chapter_id]"
    )


class Segment(Base):
    """A translatable unit (sentence, paragraph, or dialogue line)."""
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    # v2.0: Character offsets for click-to-highlight in source text
    source_start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Legacy fields for migration compatibility
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TranslationStatus] = mapped_column(
        SQLEnum(TranslationStatus), default=TranslationStatus.PENDING
    )
    speaker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    segment_type: Mapped[str] = mapped_column(String(50), default="narrative")
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="segments")
    translations: Mapped[list["Translation"]] = relationship(
        "Translation", back_populates="segment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_segments_chapter_order", "chapter_id", "order"),
    )


class Translation(Base):
    """Per-language translation for each segment."""
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    segment_id: Mapped[int] = mapped_column(Integer, ForeignKey("segments.id", ondelete="CASCADE"), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v2.0: Character offsets for click-to-highlight in translated text
    translated_start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    translated_end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # v2.0: Protect user edits from being overwritten
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[TranslationStatus] = mapped_column(
        SQLEnum(TranslationStatus), default=TranslationStatus.PENDING
    )
    batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("translation_batches.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    segment: Mapped["Segment"] = relationship("Segment", back_populates="translations")
    batch: Mapped[Optional["TranslationBatch"]] = relationship("TranslationBatch", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("segment_id", "target_language", name="uq_translation_segment_lang"),
        Index("ix_translations_segment_lang", "segment_id", "target_language"),
    )


class TranslationBatch(Base):
    """Store batch CoT reasoning and review feedback."""
    __tablename__ = "translation_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    batch_order: Mapped[int] = mapped_column(Integer, default=0)
    situation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    character_events: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    full_cot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    segment_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # v2.0: Reviewer agent feedback
    review_feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # v2.0: Review iteration count for tracking improvement cycles
    review_iteration: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="translation_batches")
    translations: Mapped[list["Translation"]] = relationship(
        "Translation", back_populates="batch"
    )
    persona_suggestions: Mapped[list["PersonaSuggestion"]] = relationship(
        "PersonaSuggestion", back_populates="source_batch"
    )


class GlossaryEntry(Base):
    """Terminology glossary for consistent translation."""
    __tablename__ = "glossary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_term: Mapped[str] = mapped_column(String(255), nullable=False)
    translated_term: Mapped[str] = mapped_column(String(255), nullable=False)
    term_type: Mapped[str] = mapped_column(String(50), default="general")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v2.0: Track pipeline-discovered terms
    auto_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="glossary_entries")

    __table_args__ = (
        Index("ix_glossary_project_term", "project_id", "source_term"),
    )


class Persona(Base):
    """Character persona for consistent voice in dialogue translation."""
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list | None] = mapped_column(JSON, nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    formality_level: Mapped[int] = mapped_column(Integer, default=3)
    age_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    example_dialogues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_chapter_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    # v2.0: Cross-chapter tracking
    appearance_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_chapter_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="personas")
    suggestions: Mapped[list["PersonaSuggestion"]] = relationship(
        "PersonaSuggestion", back_populates="persona", cascade="all, delete-orphan"
    )
    source_chapter: Mapped[Optional["Chapter"]] = relationship(
        "Chapter", foreign_keys=[source_chapter_id]
    )
    last_seen_chapter: Mapped[Optional["Chapter"]] = relationship(
        "Chapter", foreign_keys=[last_seen_chapter_id], back_populates="personas_last_seen"
    )


class PersonaSuggestion(Base):
    """LLM-suggested persona updates awaiting approval."""
    __tablename__ = "persona_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    persona_id: Mapped[int] = mapped_column(Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("translation_batches.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    persona: Mapped["Persona"] = relationship("Persona", back_populates="suggestions")
    source_batch: Mapped[Optional["TranslationBatch"]] = relationship(
        "TranslationBatch", back_populates="persona_suggestions"
    )


class PipelineRun(Base):
    """Audit trail for pipeline executions."""
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[PipelineStatus] = mapped_column(
        SQLEnum(PipelineStatus), default=PipelineStatus.PENDING
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pipeline configuration snapshot
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Execution statistics
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="pipeline_runs")

    __table_args__ = (
        Index("ix_pipeline_runs_chapter_status", "chapter_id", "status"),
    )


class Export(Base):
    """Track exported files."""
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="exports")
    project: Mapped["Project"] = relationship("Project", back_populates="exports")

    __table_args__ = (
        Index("ix_exports_chapter_format", "chapter_id", "format"),
    )
