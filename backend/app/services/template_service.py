"""
Prompt Template Service for ContextPulse.
Manages versioned system prompt templates and calculates prefix signatures.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.context_cache import PromptTemplate
from app.schemas.context_cache import PromptTemplateCreate
from app.services.tokenizer_service import TokenizerService


class TemplateService:
    @staticmethod
    def _compile_template_text(system_prompt: str, few_shot_examples: List[Dict[str, Any]]) -> str:
        parts = [system_prompt.strip()]
        for idx, ex in enumerate(few_shot_examples, 1):
            user_part = ex.get("user", "")
            assistant_part = ex.get("assistant", "")
            parts.append(f"\n[Example {idx}]\nUser: {user_part}\nAssistant: {assistant_part}")
        return "\n".join(parts)

    @staticmethod
    def create_template(db: Session, template_in: PromptTemplateCreate) -> PromptTemplate:
        compiled_text = TemplateService._compile_template_text(
            template_in.system_prompt, template_in.few_shot_examples
        )
        token_count = TokenizerService.count_tokens(compiled_text)
        prefix_hash = TokenizerService.compute_sha256(compiled_text)

        db_template = PromptTemplate(
            name=template_in.name,
            version=template_in.version,
            system_prompt=template_in.system_prompt,
            few_shot_examples=template_in.few_shot_examples,
            token_count=token_count,
            prefix_hash=prefix_hash,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        return db_template

    @staticmethod
    def get_by_id(db: Session, template_id: int) -> Optional[PromptTemplate]:
        return db.execute(
            select(PromptTemplate).where(PromptTemplate.id == template_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[PromptTemplate]:
        return db.execute(
            select(PromptTemplate).where(PromptTemplate.name == name)
        ).scalar_one_or_none()

    @staticmethod
    def list_templates(db: Session, skip: int = 0, limit: int = 50) -> List[PromptTemplate]:
        return list(
            db.execute(
                select(PromptTemplate)
                .order_by(desc(PromptTemplate.updated_at))
                .offset(skip)
                .limit(limit)
            ).scalars().all()
        )

    @staticmethod
    def update_template(
        db: Session, template_id: int, update_data: Dict[str, Any]
    ) -> Optional[PromptTemplate]:
        template = db.execute(
            select(PromptTemplate).where(PromptTemplate.id == template_id)
        ).scalar_one_or_none()
        if not template:
            return None

        for field, value in update_data.items():
            if hasattr(template, field) and value is not None:
                setattr(template, field, value)

        # Recalculate prefix hash & token count
        compiled_text = TemplateService._compile_template_text(
            template.system_prompt, template.few_shot_examples
        )
        template.token_count = TokenizerService.count_tokens(compiled_text)
        template.prefix_hash = TokenizerService.compute_sha256(compiled_text)
        template.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete_template(db: Session, template_id: int) -> bool:
        template = db.execute(
            select(PromptTemplate).where(PromptTemplate.id == template_id)
        ).scalar_one_or_none()
        if template:
            db.delete(template)
            db.commit()
            return True
        return False
