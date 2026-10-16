"""
ContextPulse — LLM Context Caching & Token Economy Optimizer
FastAPI main application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize relational tables on startup if database is accessible
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"Notice: PostgreSQL connection deferred or unavailable: {exc}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="LLM Context Caching Proxy & Token Economy Optimizer API",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "status": "online",
        "docs": "/docs",
        "supported_models": list(settings.PRICING_TABLE.keys()),
        "min_cache_tokens": settings.MIN_CACHE_PREFIX_TOKENS,
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "postgresql",
        "service": settings.PROJECT_NAME,
    }
