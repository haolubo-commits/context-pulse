"""
Prompt Template Endpoints.
CRUD interfaces for managing versioned system prompts and few-shot caches.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.context_cache import (
    PromptTemplateCreate,
    PromptTemplateResponse,
)
from app.services.template_service import TemplateService

router = APIRouter()


@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template_in: PromptTemplateCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new system prompt template and automatically compute its token count and SHA-256 prefix hash.
    """
    existing = TemplateService.get_by_name(db=db, name=template_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prompt template with name '{template_in.name}' already exists",
        )
    return TemplateService.create_template(db=db, template_in=template_in)


@router.get("", response_model=List[PromptTemplateResponse])
def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List all configured prompt templates.
    """
    return TemplateService.list_templates(db=db, skip=skip, limit=limit)


@router.get("/{template_id}", response_model=PromptTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve details of a prompt template by ID.
    """
    template = TemplateService.get_by_id(db=db, template_id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found",
        )
    return template


@router.put("/{template_id}", response_model=PromptTemplateResponse)
def update_template(
    template_id: int,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Update prompt template fields and recompute prefix signatures.
    """
    updated = TemplateService.update_template(
        db=db, template_id=template_id, update_data=update_data
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found",
        )
    return updated


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """
    Remove a prompt template.
    """
    success = TemplateService.delete_template(db=db, template_id=template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found",
        )
    return {"status": "success", "message": f"Template {template_id} deleted"}
