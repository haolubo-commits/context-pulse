"""
Token Economy Analytics & Aggregation Service.
Computes real-time savings dashboards, cache hit rates, model comparisons, and historical snapshots.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from app.models.context_cache import InferenceRequest, CacheStatus, DailyTokenSnapshot
from app.schemas.context_cache import TokenEconomySummary


class AnalyticsService:
    @staticmethod
    def get_token_economy_summary(db: Session) -> TokenEconomySummary:
        """
        Calculates aggregate economy metrics across all recorded inference requests.
        """
        total_requests = db.execute(select(func.count(InferenceRequest.id))).scalar() or 0
        if total_requests == 0:
            return TokenEconomySummary(
                total_requests=0,
                cache_hits=0,
                cache_misses=0,
                hit_ratio_percent=0.0,
                total_prompt_tokens=0,
                cached_tokens_read=0,
                total_dollars_saved_usd=0.0,
                average_latency_savings_ms=0.0,
            )

        hits = db.execute(
            select(func.count(InferenceRequest.id)).where(
                InferenceRequest.cache_status.in_([CacheStatus.HIT, CacheStatus.PARTIAL_HIT])
            )
        ).scalar() or 0

        misses = total_requests - hits
        hit_ratio = round((hits / total_requests) * 100.0, 2)

        total_prompt_tokens = db.execute(
            select(func.coalesce(func.sum(InferenceRequest.total_prompt_tokens), 0))
        ).scalar() or 0

        cached_tokens_read = db.execute(
            select(func.coalesce(func.sum(InferenceRequest.cached_prompt_tokens), 0))
        ).scalar() or 0

        total_dollars_saved = db.execute(
            select(func.coalesce(func.sum(InferenceRequest.dollars_saved), 0.0))
        ).scalar() or 0.0

        avg_latency_savings = db.execute(
            select(func.coalesce(func.avg(InferenceRequest.latency_savings_ms), 0.0))
        ).scalar() or 0.0

        return TokenEconomySummary(
            total_requests=total_requests,
            cache_hits=hits,
            cache_misses=misses,
            hit_ratio_percent=hit_ratio,
            total_prompt_tokens=total_prompt_tokens,
            cached_tokens_read=cached_tokens_read,
            total_dollars_saved_usd=round(float(total_dollars_saved), 4),
            average_latency_savings_ms=round(float(avg_latency_savings), 2),
        )

    @staticmethod
    def get_model_breakdown(db: Session) -> List[Dict[str, Any]]:
        """
        Returns token and financial breakdown grouped by LLM model.
        """
        records = db.execute(
            select(
                InferenceRequest.model_name,
                func.count(InferenceRequest.id).label("requests"),
                func.sum(InferenceRequest.dollars_saved).label("dollars_saved"),
                func.sum(InferenceRequest.cached_prompt_tokens).label("cached_tokens"),
                func.sum(InferenceRequest.total_prompt_tokens).label("total_tokens"),
            ).group_by(InferenceRequest.model_name)
        ).all()

        breakdown = []
        for r in records:
            breakdown.append({
                "model_name": r.model_name,
                "requests": r.requests,
                "dollars_saved": round(float(r.dollars_saved or 0.0), 4),
                "cached_tokens": int(r.cached_tokens or 0),
                "total_tokens": int(r.total_tokens or 0),
            })
        return breakdown

    @staticmethod
    def get_recent_requests(
        db: Session,
        model_name: Optional[str] = None,
        cache_status: Optional[CacheStatus] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> List[InferenceRequest]:
        query = select(InferenceRequest)
        conditions = []
        if model_name:
            conditions.append(InferenceRequest.model_name == model_name)
        if cache_status:
            conditions.append(InferenceRequest.cache_status == cache_status)
        if conditions:
            query = query.where(*conditions)
        query = query.order_by(desc(InferenceRequest.created_at)).offset(skip).limit(limit)
        return list(db.execute(query).scalars().all())

    @staticmethod
    def get_daily_snapshots(db: Session, limit: int = 14) -> List[DailyTokenSnapshot]:
        return list(
            db.execute(
                select(DailyTokenSnapshot)
                .order_by(desc(DailyTokenSnapshot.snapshot_date))
                .limit(limit)
            ).scalars().all()
        )
