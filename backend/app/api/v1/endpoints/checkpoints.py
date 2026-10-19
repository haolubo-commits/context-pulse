"""
Cache Checkpoint API Endpoints.
Allows querying active KV-cache fingerprints, prefix inspection, and manual eviction.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.context_cache import (
    CacheCheckpointResponse,
    CacheLookupQuery,
    CacheLookupResult,
)
from app.services.checkpoint_service import CheckpointService
from app.services.pricing_service import PricingService
from app.models.context_cache import CacheStatus

router = APIRouter()


@router.get("", response_model=List[CacheCheckpointResponse])
def list_checkpoints(
    model_name: Optional[str] = Query(None, description="Filter checkpoints by LLM model"),
    active_only: bool = Query(True, description="Only return checkpoints that have not expired"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List registered KV-cache checkpoints ordered by newest creation date.
    """
    return CheckpointService.list_checkpoints(
        db=db, model_name=model_name, active_only=active_only, skip=skip, limit=limit
    )


@router.get("/{checkpoint_id}", response_model=CacheCheckpointResponse)
def get_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve details and hit metrics for a specific cache checkpoint.
    """
    checkpoint = CheckpointService.get_by_id(db=db, checkpoint_id=checkpoint_id)
    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint with id {checkpoint_id} not found",
        )
    return checkpoint


@router.post("/lookup", response_model=CacheLookupResult)
def lookup_cache(
    query: CacheLookupQuery,
    db: Session = Depends(get_db),
):
    """
    Pre-flight inspection to check whether a given prompt prefix would trigger a cache hit.
    """
    matched_ckpt, match_type, matched_tokens = CheckpointService.find_matching_checkpoint(
        db=db, model_name=query.model_name, prompt_text=query.prompt_prefix
    )

    if matched_ckpt and matched_tokens > 0:
        pricing = PricingService.get_model_pricing(query.model_name)
        base_rate = pricing["base_input"]
        cache_read = pricing.get("cache_read", base_rate * 0.1)
        discount_pct = round(((base_rate - cache_read) / base_rate) * 100.0, 1)
        est_savings = round((matched_tokens / 1_000_000.0) * (base_rate - cache_read), 6)

        return CacheLookupResult(
            fingerprint=matched_ckpt.fingerprint,
            is_hit=True,
            matched_tokens=matched_tokens,
            discount_percentage=discount_pct,
            estimated_cost_saved_usd=est_savings,
        )

    return CacheLookupResult(
        fingerprint="",
        is_hit=False,
        matched_tokens=0,
        discount_percentage=0.0,
        estimated_cost_saved_usd=0.0,
    )


@router.delete("/{checkpoint_id}")
def evict_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
):
    """
    Manually evict a checkpoint from the cache before its natural TTL expiration.
    """
    success = CheckpointService.delete_checkpoint(db=db, checkpoint_id=checkpoint_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint with id {checkpoint_id} not found",
        )
    return {"status": "success", "message": f"Checkpoint {checkpoint_id} evicted"}


@router.post("/purge-expired")
def purge_expired_checkpoints(
    db: Session = Depends(get_db),
):
    """
    Run proactive garbage collection to purge all TTL-expired checkpoints.
    """
    purged_count = CheckpointService.purge_expired(db=db)
    return {
        "status": "success",
        "purged_count": purged_count,
        "message": f"Successfully evicted {purged_count} expired checkpoints",
    }
