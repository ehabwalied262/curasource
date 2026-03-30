# DEPLOYMENT.md — CuraSource Infrastructure & CI/CD

---

## Infrastructure Overview

```
Production Environment:
├── Frontend        → Vercel (Next.js)
├── Backend API     → Koyeb (FastAPI, Python)
├── Vector DB       → Qdrant Cloud
├── PostgreSQL      → Neon (serverless Postgres) or Supabase
├── Redis           → Upstash (serverless Redis)
├── PDF Storage     → Cloudflare R2
├── Auth            → Clerk
├── Monitoring      → Sentry (errors) + Vercel Analytics (frontend)
├── Uptime          → UptimeRobot (keep-alive + alerting)
└── CDN             → Cloudflare (R2 + DNS)
```

---

## Koyeb Backend Configuration

```yaml
# koyeb.yaml
name: curasource-api
service:
  type: web
  git:
    repository: github.com/bebo/curasource
    branch: main
    build_command: pip install -r requirements.txt
    run_command: uvicorn backend.main:app --host 0.0.0.0 --port 8000
  instance_type: medium  # 2 vCPU, 4GB RAM — needed for DeBERTa NLI model
  regions: [was1]        # Washington DC — low latency for US users
  scaling:
    min: 1
    max: 3
    target_concurrent_requests: 50
  health_check:
    path: /health
    interval: 30
    timeout: 10
  env:
    - name: DATABASE_URL
      secret: curasource-db-url
    - name: ANTHROPIC_API_KEY
      secret: anthropic-key
    # ... other secrets
```

### Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    checks = {
        "api": "ok",
        "qdrant": await check_qdrant(),
        "postgres": await check_postgres(),
        "redis": await check_redis(),
    }
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks, "version": APP_VERSION}
```

### Keep-Alive (UptimeRobot)
Configure UptimeRobot to ping `GET /health` every 5 minutes to prevent Koyeb cold starts.

---

## Vercel Frontend Configuration

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1"],
  "env": {
    "NEXT_PUBLIC_API_URL": "https://api.curasource.com"
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {"key": "X-Frame-Options", "value": "DENY"},
        {"key": "X-Content-Type-Options", "value": "nosniff"}
      ]
    }
  ]
}
```

---

## Database Setup (Neon)

```sql
-- Run via Alembic migrations
-- alembic upgrade head

CREATE TABLE users (
    id VARCHAR(128) PRIMARY KEY,  -- Clerk user ID
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE sessions (
    id VARCHAR(128) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(128) REFERENCES users(id),
    title VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE queries (
    id VARCHAR(128) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(128) REFERENCES sessions(id),
    user_id VARCHAR(128) REFERENCES users(id),
    query_text TEXT NOT NULL,
    response_text TEXT,
    domain_tags TEXT[],
    chunks_used JSONB,  -- array of chunk IDs used
    citation_scores JSONB,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE feedback (
    id VARCHAR(128) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    query_id VARCHAR(128) REFERENCES queries(id),
    user_id VARCHAR(128) REFERENCES users(id),
    rating VARCHAR(10),  -- 'up' | 'down'
    reason VARCHAR(50),
    flagged_citation_indices INTEGER[],
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sources (
    id VARCHAR(128) PRIMARY KEY,
    source_file VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(500),
    domain VARCHAR(50),
    edition VARCHAR(50),
    publication_year INTEGER,
    chunk_count INTEGER,
    ingested_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_queries_user_id ON queries(user_id);
CREATE INDEX idx_queries_session_id ON queries(session_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_feedback_query_id ON feedback(query_id);
```

---

## Qdrant Collection Setup

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, HnswConfigDiff

def setup_qdrant_collection(client: QdrantClient):
    client.create_collection(
        collection_name="curasource_chunks",
        vectors_config=VectorParams(
            size=1536,  # text-embedding-3-large truncated
            distance=Distance.COSINE,
        ),
        hnsw_config=HnswConfigDiff(
            ef_construct=200,
            m=16,
        ),
        # Payload indexes for fast filtering
    )
    
    # Create payload indexes for frequent filter fields
    for field in ["domain", "content_type", "source_file", "edition"]:
        client.create_payload_index(
            collection_name="curasource_chunks",
            field_name=field,
            field_schema="keyword"
        )
    
    client.create_payload_index(
        collection_name="curasource_chunks",
        field_name="page_number",
        field_schema="integer"
    )
```

---

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml

name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/unit tests/integration --cov=backend --cov-report=xml
      - run: pip-audit  # Security audit

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run type-check
      - run: npm run lint
      - run: npm run test
      - run: npm audit --audit-level=high

  e2e:
    runs-on: ubuntu-latest
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: npx playwright install --with-deps
      - run: npx playwright test
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}

  deploy-backend:
    needs: [e2e]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: koyeb/action-git-deploy@v1
        with:
          api-token: ${{ secrets.KOYEB_API_TOKEN }}
          app-name: curasource-api

  deploy-frontend:
    needs: [e2e]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

---

## Monitoring

### Sentry Setup
```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% of requests
    environment=settings.ENVIRONMENT,
    release=settings.APP_VERSION,
)
```

### Custom Metrics to Track
```python
# Log these for every query (to PostgreSQL + Sentry)
metrics = {
    "retrieval_latency_ms": elapsed_retrieval,
    "generation_latency_ms": elapsed_generation,
    "verification_latency_ms": elapsed_verification,
    "total_latency_ms": total_elapsed,
    "chunks_retrieved": len(chunks),
    "citations_verified": len(verified_citations),
    "citations_failed_verification": len(failed),
    "domain_tags": domain_tags,
    "out_of_scope": out_of_scope,
}
```

### Alerts to Configure in UptimeRobot / Sentry
- Backend `/health` returns non-200 for > 2 minutes → PagerDuty/email
- P95 latency exceeds 5s (measured via Sentry performance)
- Error rate exceeds 5% in 5-minute window
- Qdrant cluster health degraded

---

## Rollback Strategy

```bash
# Koyeb — rollback to previous deployment
koyeb deployments rollback --app curasource-api --deployment <previous_id>

# Vercel — instant rollback via dashboard or CLI
vercel rollback <deployment_url>

# Database — Alembic migration rollback
alembic downgrade -1

# Qdrant — collections are immutable (re-ingest if corrupted)
# Always keep the last successful ingestion snapshot
```
