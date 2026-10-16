"""
SQLAlchemy 2.0 ORM models for Prompt Templates, Cache Checkpoints, and Inference Requests.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CacheStatus(str, Enum):
    HIT = "HIT"
    MISS = "MISS"
    PARTIAL_HIT = "PARTIAL_HIT"


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0", nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    few_shot_examples: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prefix_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    requests: Mapped[List["InferenceRequest"]] = relationship("InferenceRequest", back_populates="template")


class CacheCheckpoint(Base):
    __tablename__ = "cache_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    prefix_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_hit_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    requests: Mapped[List["InferenceRequest"]] = relationship("InferenceRequest", back_populates="checkpoint")

    __table_args__ = (
        Index("ix_checkpoint_model_expires", "model_name", "expires_at"),
    )


class InferenceRequest(Base):
    __tablename__ = "inference_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    template_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("prompt_templates.id"), nullable=True)
    checkpoint_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("cache_checkpoints.id"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)

    # Token Economics
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cached_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cache_status: Mapped[CacheStatus] = mapped_column(SQLEnum(CacheStatus), default=CacheStatus.MISS, nullable=False, index=True)

    # Financial & Latency Savings
    raw_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    cached_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    dollars_saved: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    latency_savings_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    template: Mapped[Optional[PromptTemplate]] = relationship("PromptTemplate", back_populates="requests")
    checkpoint: Mapped[Optional[CacheCheckpoint]] = relationship("CacheCheckpoint", back_populates="requests")


class DailyTokenSnapshot(Base):
    __tablename__ = "daily_token_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_date: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)  # YYYY-MM-DD
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cache_hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cache_misses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hit_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_tokens_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dollars_saved: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
