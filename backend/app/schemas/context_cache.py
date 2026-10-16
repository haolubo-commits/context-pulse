"""
Pydantic v2 schemas for ContextPulse prompt caching, token economics, and savings analytics.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.context_cache import CacheStatus


# Prompt Template Schemas
class PromptTemplateBase(BaseModel):
    name: str = Field(..., max_length=150)
    version: str = Field(default="1.0.0", max_length=30)
    system_prompt: str
    few_shot_examples: List[Dict[str, Any]] = Field(default_factory=list)


class PromptTemplateCreate(PromptTemplateBase):
    pass


class PromptTemplateResponse(PromptTemplateBase):
    id: int
    token_count: int
    prefix_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Cache Checkpoint Schemas
class CacheCheckpointBase(BaseModel):
    model_name: str = Field(..., max_length=80)
    prefix_text: str
    token_count: int
    ttl_seconds: int = 300


class CacheCheckpointCreate(CacheCheckpointBase):
    fingerprint: Optional[str] = None


class CacheCheckpointResponse(CacheCheckpointBase):
    id: int
    fingerprint: str
    hit_count: int
    created_at: datetime
    expires_at: datetime
    last_hit_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Inference Request & Cache Lookup Schemas
class InferenceRequestCreate(BaseModel):
    session_id: str = Field(..., max_length=100)
    model_name: str = Field(default="claude-3-5-sonnet")
    template_name: Optional[str] = None
    prompt_text: str
    completion_tokens: int = Field(default=0, ge=0)
    simulated_latency_ms: Optional[float] = None


class InferenceRequestResponse(BaseModel):
    id: int
    session_id: str
    model_name: str
    cache_status: CacheStatus
    total_prompt_tokens: int
    cached_prompt_tokens: int
    completion_tokens: int
    raw_cost_usd: float
    cached_cost_usd: float
    dollars_saved: float
    latency_ms: float
    latency_savings_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CacheLookupQuery(BaseModel):
    model_name: str
    prompt_prefix: str


class CacheLookupResult(BaseModel):
    fingerprint: str
    is_hit: bool
    matched_tokens: int
    discount_percentage: float
    estimated_cost_saved_usd: float


# High-Level Token Economy Summary
class TokenEconomySummary(BaseModel):
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_ratio_percent: float
    total_prompt_tokens: int
    cached_tokens_read: int
    total_dollars_saved_usd: float
    average_latency_savings_ms: float
