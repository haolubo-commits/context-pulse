"""
Cache Checkpoint Manager Service.
Handles registration, fingerprint-based lookup, TTL expiration, and eviction for KV context checkpoints.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from app.core.config import settings
from app.models.context_cache import CacheCheckpoint
from app.services.tokenizer_service import TokenizerService


class CheckpointService:
    @staticmethod
    def register_checkpoint(
        db: Session,
        model_name: str,
        prefix_text: str,
        token_count: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> CacheCheckpoint:
        """
        Registers a new checkpoint or refreshes an existing one with identical fingerprint.
        """
        fingerprint = TokenizerService.compute_sha256(prefix_text)
        if token_count is None:
            token_count = TokenizerService.count_tokens(prefix_text)

        effective_ttl = ttl_seconds if ttl_seconds is not None else settings.DEFAULT_CACHE_TTL_SECONDS
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=effective_ttl)

        existing = db.execute(
            select(CacheCheckpoint).where(
                and_(
                    CacheCheckpoint.fingerprint == fingerprint,
                    CacheCheckpoint.model_name == model_name,
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.expires_at = expires_at
            existing.hit_count += 1
            existing.last_hit_at = now
            db.commit()
            db.refresh(existing)
            return existing

        checkpoint = CacheCheckpoint(
            fingerprint=fingerprint,
            prefix_text=prefix_text,
            model_name=model_name,
            token_count=token_count,
            ttl_seconds=effective_ttl,
            hit_count=0,
            created_at=now,
            expires_at=expires_at,
            last_hit_at=None,
        )
        db.add(checkpoint)
        db.commit()
        db.refresh(checkpoint)
        return checkpoint

    @staticmethod
    def find_matching_checkpoint(
        db: Session,
        model_name: str,
        prompt_text: str,
    ) -> Tuple[Optional[CacheCheckpoint], str, int]:
        """
        Searches for an active checkpoint that matches either exact prefix or longest common prefix.
        Returns (checkpoint, match_type, matched_tokens).
        """
        now = datetime.utcnow()
        prompt_fingerprint = TokenizerService.compute_sha256(prompt_text)

        # 1. Exact match check
        exact_match = db.execute(
            select(CacheCheckpoint).where(
                and_(
                    CacheCheckpoint.model_name == model_name,
                    CacheCheckpoint.fingerprint == prompt_fingerprint,
                    CacheCheckpoint.expires_at > now,
                )
            )
        ).scalar_one_or_none()

        if exact_match:
            exact_match.hit_count += 1
            exact_match.last_hit_at = now
            exact_match.expires_at = now + timedelta(seconds=exact_match.ttl_seconds)
            db.commit()
            return exact_match, "EXACT", exact_match.token_count

        # 2. Check candidate prefixes meeting the MIN_CACHE_PREFIX_TOKENS threshold
        candidates = db.execute(
            select(CacheCheckpoint).where(
                and_(
                    CacheCheckpoint.model_name == model_name,
                    CacheCheckpoint.expires_at > now,
                )
            ).order_by(desc(CacheCheckpoint.token_count))
        ).scalars().all()

        best_checkpoint = None
        best_lcp_tokens = 0

        for candidate in candidates:
            if prompt_text.startswith(candidate.prefix_text):
                # Candidate prefix is a full prefix of prompt_text
                best_checkpoint = candidate
                best_lcp_tokens = candidate.token_count
                break
            else:
                lcp = TokenizerService.longest_common_prefix(prompt_text, candidate.prefix_text)
                lcp_tokens = TokenizerService.count_tokens(lcp)
                if lcp_tokens >= settings.MIN_CACHE_PREFIX_TOKENS and lcp_tokens > best_lcp_tokens:
                    best_checkpoint = candidate
                    best_lcp_tokens = lcp_tokens

        if best_checkpoint and best_lcp_tokens >= settings.MIN_CACHE_PREFIX_TOKENS:
            best_checkpoint.hit_count += 1
            best_checkpoint.last_hit_at = now
            best_checkpoint.expires_at = now + timedelta(seconds=best_checkpoint.ttl_seconds)
            db.commit()
            match_type = "EXACT" if best_lcp_tokens == best_checkpoint.token_count else "PARTIAL"
            return best_checkpoint, match_type, best_lcp_tokens

        return None, "NONE", 0

    @staticmethod
    def list_checkpoints(
        db: Session,
        model_name: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> List[CacheCheckpoint]:
        query = select(CacheCheckpoint)
        conditions = []
        if active_only:
            conditions.append(CacheCheckpoint.expires_at > datetime.utcnow())
        if model_name:
            conditions.append(CacheCheckpoint.model_name == model_name)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(desc(CacheCheckpoint.created_at)).offset(skip).limit(limit)
        return list(db.execute(query).scalars().all())

    @staticmethod
    def get_by_fingerprint(db: Session, fingerprint: str) -> Optional[CacheCheckpoint]:
        return db.execute(
            select(CacheCheckpoint).where(CacheCheckpoint.fingerprint == fingerprint)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, checkpoint_id: int) -> Optional[CacheCheckpoint]:
        return db.execute(
            select(CacheCheckpoint).where(CacheCheckpoint.id == checkpoint_id)
        ).scalar_one_or_none()

    @staticmethod
    def delete_checkpoint(db: Session, checkpoint_id: int) -> bool:
        ckpt = db.execute(
            select(CacheCheckpoint).where(CacheCheckpoint.id == checkpoint_id)
        ).scalar_one_or_none()
        if ckpt:
            db.delete(ckpt)
            db.commit()
            return True
        return False

    @staticmethod
    def purge_expired(db: Session) -> int:
        now = datetime.utcnow()
        expired = db.execute(
            select(CacheCheckpoint).where(CacheCheckpoint.expires_at <= now)
        ).scalars().all()
        count = len(expired)
        for ckpt in expired:
            db.delete(ckpt)
        if count > 0:
            db.commit()
        return count
