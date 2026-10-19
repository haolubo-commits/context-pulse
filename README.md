# ⚡ ContextPulse — LLM Context Caching & Token Economy Optimizer

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red.svg?style=flat)](https://www.sqlalchemy.org)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **ContextPulse** is an intelligent context caching proxy and token economy analyzer designed for LLM applications. It detects prefix patterns across multi-turn agent conversations, simulates KV-cache checkpointing (e.g., Anthropic Prompt Caching & OpenAI Prefix Matching), and quantifies cost reduction and latency improvements in real-time.

---

## 🏗️ Architecture & Context Caching Pipeline

```mermaid
graph TD
    ClientApp[Client LLM Request] --> Proxy[ContextPulse Proxy / Cache Engine]
    Proxy --> Tokenizer[Tokenizer & Prefix Segmenter]
    Tokenizer --> Fingerprinter["SHA-256 Prefix Hasher (Min 1024 Tokens)"]
    Fingerprinter --> DBCache[("PostgreSQL 16: CacheCheckpoints")]

    DBCache -- Cache Hit (Prefix Found) --> HitProcessor["Compute Savings (up to 90% cost cut, 80% latency drop)"]
    DBCache -- Cache Miss (New Prefix) --> MissProcessor["Register Checkpoint & Allocate TTL"]

    HitProcessor --> MetricsAggregator["Token Economy Aggregator"]
    MissProcessor --> MetricsAggregator
    MetricsAggregator --> AnalyticsAPI[FastAPI Analytics Engine]
    AnalyticsAPI --> Dashboard[React Token Cockpit]
```

---

## 🌟 Key Features (4-Day Sprint Roadmap)

- [x] **Day 1: Scaffolding & Architecture**: PostgreSQL relational schema design, SQLAlchemy 2.0 models, Pydantic v2 schemas for checkpoints and requests, application settings, and DB session pooling.
- [x] **Day 2: Core Logic & Context Caching APIs**: Prefix matching algorithms (exact prefix match, longest common prefix), token cost valuation models, checkpoint eviction & TTL management, and inference proxy endpoints.
- [ ] **Day 3: Frontend UI / Token Economy Cockpit**: React dashboard with interactive cache hit ratio gauge, real-time cost savings graph, prefix breakdown inspector, and token burn charts.
- [ ] **Day 4: Benchmarks, Testing & Polish**: Pytest integration suites, context caching benchmarks against Claude 3.5 & GPT-4o pricing tiers, sample trace seeding scripts, and Docker Compose stack.

---

## 🔌 API Endpoints Reference (`/api/v1`)

| Module | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Proxy** | `POST` | `/api/v1/proxy/simulate` | Dry-run token savings and latency speedup simulation |
| **Proxy** | `POST` | `/api/v1/proxy/ingest` | Process request, evaluate cache hit, ledger cost & speedup |
| **Checkpoints** | `GET` | `/api/v1/checkpoints` | List active KV-cache checkpoints by model & status |
| **Checkpoints** | `POST` | `/api/v1/checkpoints/lookup` | Query whether a prompt prefix matches existing cache |
| **Checkpoints** | `DELETE`| `/api/v1/checkpoints/{id}` | Manually evict a checkpoint from memory/table |
| **Checkpoints** | `POST` | `/api/v1/checkpoints/purge-expired`| Garbage-collect all TTL-expired checkpoints |
| **Templates** | `POST` | `/api/v1/templates` | Create versioned prompt template with automatic prefix hash |
| **Templates** | `GET` | `/api/v1/templates` | List registered system prompt templates |
| **Analytics** | `GET` | `/api/v1/analytics/summary` | Token economy overview (total savings, hit ratio %, latency) |
| **Analytics** | `GET` | `/api/v1/analytics/model-breakdown` | Financial savings and token counts by model |
| **Analytics** | `GET` | `/api/v1/analytics/snapshots` | Daily time-series metrics for charting |

### Sample: Ingest Request via Context Caching Proxy
```bash
curl -X POST "http://localhost:8000/api/v1/proxy/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-agent-992",
    "model_name": "claude-3-5-sonnet",
    "prompt_text": "You are FinPulse, an elite quantitative financial analyst... [>1024 tokens] What is NVIDIA Q3 revenue?",
    "completion_tokens": 150
  }'
```

**Response (`201 Created`):**
```json
{
  "id": 1,
  "session_id": "session-agent-992",
  "model_name": "claude-3-5-sonnet",
  "cache_status": "HIT",
  "total_prompt_tokens": 1280,
  "cached_prompt_tokens": 1150,
  "completion_tokens": 150,
  "raw_cost_usd": 0.00609,
  "cached_cost_usd": 0.002985,
  "dollars_saved": 0.003105,
  "latency_ms": 285.2,
  "latency_savings_ms": 112.5,
  "created_at": "2026-10-19T09:45:00"
}
```

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or SQLite for quick local test)

### Setup
```bash
# Clone the repository
git clone https://github.com/haolubo-commits/context-pulse.git
cd context-pulse/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed sample templates and checkpoints
python3 -m app.db.init_db

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
