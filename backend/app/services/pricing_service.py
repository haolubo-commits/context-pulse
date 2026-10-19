"""
Pricing & Token Economy Valuation Service.
Calculates cost differentials, dollar savings, and prefill latency reductions for LLM context caching.
"""

from typing import Dict, Any, Tuple
from app.core.config import settings
from app.models.context_cache import CacheStatus


class PricingService:
    DEFAULT_PRICING: Dict[str, float] = {
        "base_input": 3.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
        "output": 15.00,
    }

    @classmethod
    def get_model_pricing(cls, model_name: str) -> Dict[str, float]:
        """
        Retrieves pricing per 1M tokens for the given model, or returns default fallback.
        """
        normalized_name = model_name.lower().strip()
        for key, rates in settings.PRICING_TABLE.items():
            if key in normalized_name or normalized_name in key:
                return rates
        return cls.DEFAULT_PRICING

    @classmethod
    def calculate_cost_and_latency(
        cls,
        model_name: str,
        total_prompt_tokens: int,
        cached_prompt_tokens: int,
        completion_tokens: int = 0,
        cache_status: CacheStatus = CacheStatus.MISS,
        simulated_raw_latency: float | None = None,
    ) -> Dict[str, float]:
        """
        Calculates raw cost, cached cost, dollars saved, and simulated latency metrics.
        All pricing is scaled per million (1,000,000) tokens.
        """
        pricing = cls.get_model_pricing(model_name)
        base_rate = pricing["base_input"]
        cache_read_rate = pricing.get("cache_read", base_rate * 0.1)
        output_rate = pricing.get("output", 15.00)

        # 1. Raw Cost (no caching applied)
        raw_prompt_cost = (total_prompt_tokens / 1_000_000.0) * base_rate
        completion_cost = (completion_tokens / 1_000_000.0) * output_rate
        raw_total_cost = round(raw_prompt_cost + completion_cost, 6)

        # 2. Cached Cost
        if cache_status in (CacheStatus.HIT, CacheStatus.PARTIAL_HIT) and cached_prompt_tokens > 0:
            uncached_tokens = max(0, total_prompt_tokens - cached_prompt_tokens)
            cached_part = (cached_prompt_tokens / 1_000_000.0) * cache_read_rate
            uncached_part = (uncached_tokens / 1_000_000.0) * base_rate
            cached_prompt_cost = cached_part + uncached_part
        else:
            cached_prompt_cost = raw_prompt_cost

        cached_total_cost = round(cached_prompt_cost + completion_cost, 6)
        dollars_saved = round(max(0.0, raw_total_cost - cached_total_cost), 6)

        # 3. Latency Simulation (Prefill & Decode Time)
        # Prefill base: 120ms + 0.12ms per uncached token vs 0.015ms per cached token
        if simulated_raw_latency is not None:
            raw_latency = simulated_raw_latency
        else:
            raw_latency = 120.0 + (total_prompt_tokens * 0.12) + (completion_tokens * 10.5)

        if cache_status in (CacheStatus.HIT, CacheStatus.PARTIAL_HIT) and cached_prompt_tokens > 0:
            uncached_tokens = max(0, total_prompt_tokens - cached_prompt_tokens)
            cached_latency = 120.0 + (uncached_tokens * 0.12) + (cached_prompt_tokens * 0.018) + (completion_tokens * 10.5)
        else:
            cached_latency = raw_latency

        raw_latency = round(raw_latency, 2)
        cached_latency = round(cached_latency, 2)
        latency_savings_ms = round(max(0.0, raw_latency - cached_latency), 2)

        return {
            "raw_cost_usd": raw_total_cost,
            "cached_cost_usd": cached_total_cost,
            "dollars_saved": dollars_saved,
            "raw_latency_ms": raw_latency,
            "latency_ms": cached_latency,
            "latency_savings_ms": latency_savings_ms,
        }
