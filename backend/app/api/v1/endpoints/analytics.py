"""
Token Economy Analytics & Financial Dashboards API Endpoints.
Provides aggregations, hit ratios, model savings distributions, and historical trends.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.context_cache import (
    TokenEconomySummary,
    InferenceRequestResponse,
)
from app.models.context_cache import CacheStatus
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/summary", response_model=TokenEconomySummary)
def get_summary(
    db: Session = Depends(get_db),
):
    """
    Get aggregated token economy metrics including total savings, hit ratio %, and average latency saved.
    """
    return AnalyticsService.get_token_economy_summary(db=db)


@router.get("/model-breakdown", response_model=List[Dict[str, Any]])
def get_model_breakdown(
    db: Session = Depends(get_db),
):
    """
    Get financial savings and token volumes grouped across LLM providers/models.
    """
    return AnalyticsService.get_model_breakdown(db=db)


@router.get("/recent-requests", response_model=List[InferenceRequestResponse])
def get_recent_requests(
    model_name: Optional[str] = Query(None, description="Filter requests by LLM model"),
    cache_status: Optional[CacheStatus] = Query(None, description="Filter by HIT, MISS, or PARTIAL_HIT"),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List recent inference requests processed through the ContextPulse proxy.
    """
    return AnalyticsService.get_recent_requests(
        db=db,
        model_name=model_name,
        cache_status=cache_status,
        skip=skip,
        limit=limit,
    )


@router.get("/snapshots")
def get_daily_snapshots(
    limit: int = Query(14, ge=1, le=60),
    db: Session = Depends(get_db),
):
    """
    Get daily historical time-series snapshots for hit ratio trends and dollar savings charts.
    """
    snapshots = AnalyticsService.get_daily_snapshots(db=db, limit=limit)
    return [
        {
            "id": s.id,
            "snapshot_date": s.snapshot_date,
            "total_requests": s.total_requests,
            "cache_hits": s.cache_hits,
            "cache_misses": s.cache_misses,
            "hit_ratio": s.hit_ratio,
            "total_prompt_tokens": s.total_prompt_tokens,
            "cached_tokens_read": s.cached_tokens_read,
            "dollars_saved": s.dollars_saved,
            "updated_at": s.updated_at,
        }
        for s in snapshots
    ]
