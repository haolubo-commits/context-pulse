"""
Context Caching Proxy & Simulation Endpoints.
Routes LLM inference requests, simulates cache benefits, and persists execution records.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.context_cache import (
    InferenceRequestCreate,
    InferenceRequestResponse,
)
from app.models.context_cache import CacheStatus
from app.services.proxy_service import ProxyService
from app.services.tokenizer_service import TokenizerService
from app.services.pricing_service import PricingService
from app.services.checkpoint_service import CheckpointService
from app.services.template_service import TemplateService
from app.core.config import settings

router = APIRouter()


@router.post("/ingest", response_model=InferenceRequestResponse, status_code=status.HTTP_201_CREATED)
def ingest_request(
    request_in: InferenceRequestCreate,
    db: Session = Depends(get_db),
):
    """
    Ingest an LLM inference request through ContextPulse:
    1. Inspects prefix against active checkpoints
    2. Measures token savings and speedup
    3. Allocates or refreshes TTL
    4. Persists transaction to database ledger
    """
    return ProxyService.process_request(db=db, request_in=request_in)


@router.post("/simulate", response_model=InferenceRequestResponse)
def simulate_request(
    request_in: InferenceRequestCreate,
    db: Session = Depends(get_db),
):
    """
    Dry-run simulation of caching behavior without persisting records or altering active cache checkpoints.
    """
    prompt_text = request_in.prompt_text
    if request_in.template_name:
        template = TemplateService.get_by_name(db, request_in.template_name)
        if template:
            prompt_text = f"{template.system_prompt}\n\n{prompt_text}"

    total_prompt_tokens = TokenizerService.count_tokens(prompt_text)
    matched_ckpt, match_type, matched_tokens = CheckpointService.find_matching_checkpoint(
        db, request_in.model_name, prompt_text
    )

    if matched_ckpt and matched_tokens >= settings.MIN_CACHE_PREFIX_TOKENS:
        cache_status = CacheStatus.HIT if match_type == "EXACT" else CacheStatus.PARTIAL_HIT
        cached_tokens = matched_tokens
    else:
        cache_status = CacheStatus.MISS
        cached_tokens = 0

    metrics = PricingService.calculate_cost_and_latency(
        model_name=request_in.model_name,
        total_prompt_tokens=total_prompt_tokens,
        cached_prompt_tokens=cached_tokens,
        completion_tokens=request_in.completion_tokens,
        cache_status=cache_status,
        simulated_raw_latency=request_in.simulated_latency_ms,
    )

    from datetime import datetime
    return InferenceRequestResponse(
        id=0,
        session_id=request_in.session_id,
        model_name=request_in.model_name,
        cache_status=cache_status,
        total_prompt_tokens=total_prompt_tokens,
        cached_prompt_tokens=cached_tokens,
        completion_tokens=request_in.completion_tokens,
        raw_cost_usd=metrics["raw_cost_usd"],
        cached_cost_usd=metrics["cached_cost_usd"],
        dollars_saved=metrics["dollars_saved"],
        latency_ms=metrics["latency_ms"],
        latency_savings_ms=metrics["latency_savings_ms"],
        created_at=datetime.utcnow(),
    )
