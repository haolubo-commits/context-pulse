"""
Context Caching Proxy & Ingestion Pipeline Service.
Simulates and executes LLM request routing, KV cache inspection, and token economics ledgering.
"""

from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.config import settings
from app.models.context_cache import (
    CacheCheckpoint,
    CacheStatus,
    InferenceRequest,
    DailyTokenSnapshot,
    PromptTemplate,
)
from app.schemas.context_cache import InferenceRequestCreate
from app.services.tokenizer_service import TokenizerService
from app.services.pricing_service import PricingService
from app.services.checkpoint_service import CheckpointService
from app.services.template_service import TemplateService


class ProxyService:
    @staticmethod
    def _update_daily_snapshot(
        db: Session,
        is_hit: bool,
        total_prompt_tokens: int,
        cached_tokens: int,
        dollars_saved: float,
    ) -> None:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        snapshot = db.execute(
            select(DailyTokenSnapshot).where(DailyTokenSnapshot.snapshot_date == today_str)
        ).scalar_one_or_none()

        if not snapshot:
            snapshot = DailyTokenSnapshot(
                snapshot_date=today_str,
                total_requests=0,
                cache_hits=0,
                cache_misses=0,
                hit_ratio=0.0,
                total_prompt_tokens=0,
                cached_tokens_read=0,
                dollars_saved=0.0,
                updated_at=datetime.utcnow(),
            )
            db.add(snapshot)

        snapshot.total_requests += 1
        if is_hit:
            snapshot.cache_hits += 1
            snapshot.cached_tokens_read += cached_tokens
        else:
            snapshot.cache_misses += 1

        snapshot.total_prompt_tokens += total_prompt_tokens
        snapshot.dollars_saved = round(snapshot.dollars_saved + dollars_saved, 6)
        snapshot.hit_ratio = round(
            (snapshot.cache_hits / snapshot.total_requests) * 100.0, 2
        ) if snapshot.total_requests > 0 else 0.0
        snapshot.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def process_request(
        db: Session,
        request_in: InferenceRequestCreate,
    ) -> InferenceRequest:
        """
        Executes end-to-end caching proxy pipeline:
        1. Resolves template if referenced
        2. Calculates prompt tokens
        3. Queries checkpoint table for prefix matches
        4. Evaluates token savings and simulated latency
        5. Registers new checkpoint if qualifying
        6. Persists transaction to database ledger
        """
        prompt_text = request_in.prompt_text
        template_id: Optional[int] = None

        if request_in.template_name:
            template = TemplateService.get_by_name(db, request_in.template_name)
            if template:
                template_id = template.id
                prompt_text = f"{template.system_prompt}\n\n{prompt_text}"

        total_prompt_tokens = TokenizerService.count_tokens(prompt_text)

        # Lookup matching checkpoint
        matched_checkpoint, match_type, matched_tokens = CheckpointService.find_matching_checkpoint(
            db, request_in.model_name, prompt_text
        )

        checkpoint_id: Optional[int] = None
        if matched_checkpoint and matched_tokens >= settings.MIN_CACHE_PREFIX_TOKENS:
            checkpoint_id = matched_checkpoint.id
            if match_type == "EXACT":
                cache_status = CacheStatus.HIT
            else:
                cache_status = CacheStatus.PARTIAL_HIT
            cached_tokens = matched_tokens
        else:
            cache_status = CacheStatus.MISS
            cached_tokens = 0

            # Register new checkpoint if prompt prefix is substantial enough for caching
            if total_prompt_tokens >= settings.MIN_CACHE_PREFIX_TOKENS:
                prefix_str, _, prefix_tokens = TokenizerService.extract_prefix(
                    prompt_text, settings.MIN_CACHE_PREFIX_TOKENS
                )
                new_ckpt = CheckpointService.register_checkpoint(
                    db=db,
                    model_name=request_in.model_name,
                    prefix_text=prefix_str,
                    token_count=prefix_tokens,
                )
                checkpoint_id = new_ckpt.id

        # Calculate financial savings & latency speedup
        metrics = PricingService.calculate_cost_and_latency(
            model_name=request_in.model_name,
            total_prompt_tokens=total_prompt_tokens,
            cached_prompt_tokens=cached_tokens,
            completion_tokens=request_in.completion_tokens,
            cache_status=cache_status,
            simulated_raw_latency=request_in.simulated_latency_ms,
        )

        inference_record = InferenceRequest(
            session_id=request_in.session_id,
            template_id=template_id,
            checkpoint_id=checkpoint_id,
            model_name=request_in.model_name,
            total_prompt_tokens=total_prompt_tokens,
            cached_prompt_tokens=cached_tokens,
            completion_tokens=request_in.completion_tokens,
            cache_status=cache_status,
            raw_cost_usd=metrics["raw_cost_usd"],
            cached_cost_usd=metrics["cached_cost_usd"],
            dollars_saved=metrics["dollars_saved"],
            latency_ms=metrics["latency_ms"],
            latency_savings_ms=metrics["latency_savings_ms"],
            created_at=datetime.utcnow(),
        )

        db.add(inference_record)
        db.commit()
        db.refresh(inference_record)

        # Update aggregated daily snapshot
        is_hit = cache_status in (CacheStatus.HIT, CacheStatus.PARTIAL_HIT)
        ProxyService._update_daily_snapshot(
            db=db,
            is_hit=is_hit,
            total_prompt_tokens=total_prompt_tokens,
            cached_tokens=cached_tokens,
            dollars_saved=metrics["dollars_saved"],
        )

        return inference_record
