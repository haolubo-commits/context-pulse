"""
Aggregated v1 API Router for ContextPulse.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import checkpoints, templates, proxy, analytics

api_router = APIRouter()

api_router.include_router(checkpoints.router, prefix="/checkpoints", tags=["Cache Checkpoints"])
api_router.include_router(templates.router, prefix="/templates", tags=["Prompt Templates"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["Context Caching Proxy"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Token Economy Analytics"])
