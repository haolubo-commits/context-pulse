"""
Database initialization and sample data seeding utility for ContextPulse.
"""

from datetime import datetime, timedelta
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.context_cache import (
    PromptTemplate,
    CacheCheckpoint,
    InferenceRequest,
    CacheStatus,
    DailyTokenSnapshot,
)
from app.services.tokenizer_service import TokenizerService
from app.services.pricing_service import PricingService


SAMPLE_TEMPLATES = [
    {
        "name": "financial-analyst-agent",
        "version": "1.2.0",
        "system_prompt": (
            "You are FinPulse, an elite quantitative financial analyst and SEC filing inspector. "
            "Your objective is to analyze corporate earnings, balance sheets, and 10-K filings with utmost precision. "
            "Guidelines: Always calculate EBITDA margin, Free Cash Flow yield, and year-over-year debt service ratios. "
            "Cross-reference GAAP vs Non-GAAP reconciliations and flag any aggressive revenue recognition patterns. "
            "Cite all findings with exact filing section headers and table numbers. "
            "Maintain an objective, rigorous tone appropriate for institutional investment committees."
        ) * 10,  # Ensure robust token length (> 1024 tokens)
        "few_shot_examples": [
            {
                "user": "Analyze NVIDIA FY25 Q3 revenue drivers by segment.",
                "assistant": "Data Center compute grew 112% YoY driven by Hopper architecture and early Blackwell shipments.",
            },
            {
                "user": "Summarize free cash flow conversion rate for Microsoft.",
                "assistant": "Free cash flow conversion stood at 64% reflecting heightened cloud infrastructure CapEx.",
            },
        ],
    },
    {
        "name": "code-review-architect",
        "version": "2.0.1",
        "system_prompt": (
            "You are CodePulse, a principal software architect specializing in distributed systems, security audits, "
            "and latency-critical backend applications. You review pull requests with extreme attention to detail. "
            "Key evaluation vectors: Thread safety, database query N+1 detection, memory leak prevention, "
            "proper connection pool recycling, and adherence to clean architecture principles. "
            "Provide concrete, idiomatic refactoring suggestions with diffs whenever identifying antipatterns."
        ) * 8,
        "few_shot_examples": [
            {
                "user": "Review this async SQLAlchemy session management snippet.",
                "assistant": "Use scoped async sessions or lifespan context managers to prevent unclosed connections during timeouts.",
            }
        ],
    },
]


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if templates already exist
        existing = db.query(PromptTemplate).first()
        if not existing:
            print("Seeding initial prompt templates and cache checkpoints...")
            for t_data in SAMPLE_TEMPLATES:
                compiled = t_data["system_prompt"]
                toks = TokenizerService.count_tokens(compiled)
                fingerprint = TokenizerService.compute_sha256(compiled)

                template = PromptTemplate(
                    name=t_data["name"],
                    version=t_data["version"],
                    system_prompt=t_data["system_prompt"],
                    few_shot_examples=t_data["few_shot_examples"],
                    token_count=toks,
                    prefix_hash=fingerprint,
                )
                db.add(template)
                db.flush()

                # Seed corresponding active KV checkpoint
                now = datetime.utcnow()
                ckpt = CacheCheckpoint(
                    fingerprint=fingerprint,
                    prefix_text=compiled,
                    model_name="claude-3-5-sonnet",
                    token_count=toks,
                    ttl_seconds=1800,
                    hit_count=12,
                    created_at=now - timedelta(hours=2),
                    expires_at=now + timedelta(hours=4),
                    last_hit_at=now - timedelta(minutes=5),
                )
                db.add(ckpt)
                db.flush()

                # Seed sample inference records
                pricing = PricingService.calculate_cost_and_latency(
                    model_name="claude-3-5-sonnet",
                    total_prompt_tokens=toks + 120,
                    cached_prompt_tokens=toks,
                    completion_tokens=180,
                    cache_status=CacheStatus.HIT,
                )
                req = InferenceRequest(
                    session_id=f"session-{template.name}-001",
                    template_id=template.id,
                    checkpoint_id=ckpt.id,
                    model_name="claude-3-5-sonnet",
                    total_prompt_tokens=toks + 120,
                    cached_prompt_tokens=toks,
                    completion_tokens=180,
                    cache_status=CacheStatus.HIT,
                    raw_cost_usd=pricing["raw_cost_usd"],
                    cached_cost_usd=pricing["cached_cost_usd"],
                    dollars_saved=pricing["dollars_saved"],
                    latency_ms=pricing["latency_ms"],
                    latency_savings_ms=pricing["latency_savings_ms"],
                    created_at=now - timedelta(minutes=15),
                )
                db.add(req)

            # Seed daily snapshot
            today = datetime.utcnow().strftime("%Y-%m-%d")
            db.add(
                DailyTokenSnapshot(
                    snapshot_date=today,
                    total_requests=24,
                    cache_hits=19,
                    cache_misses=5,
                    hit_ratio=79.17,
                    total_prompt_tokens=48600,
                    cached_tokens_read=36200,
                    dollars_saved=0.1086,
                    updated_at=datetime.utcnow(),
                )
            )
            db.commit()
            print("Database initialized with seed data successfully.")
        else:
            print("Database already contains records. Skipping seed.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
