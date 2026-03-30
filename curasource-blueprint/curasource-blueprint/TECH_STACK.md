# TECH_STACK.md — CuraSource Technology Decisions

---

## Stack at a Glance

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| Frontend | Next.js | 14 (App Router) | SSR, streaming, file-based routing |
| Frontend Lang | TypeScript | 5.x | Type safety across component contracts |
| Styling | Tailwind CSS | 3.x | Utility-first, rapid iteration |
| UI Components | shadcn/ui | latest | Unstyled, composable, not opinionated |
| Backend | FastAPI | 0.110+ | Async Python, automatic OpenAPI docs |
| Backend Lang | Python | 3.11+ | Strong ML/NLP ecosystem |
| Vector DB | Qdrant | Cloud | Metadata filtering, hybrid search built-in |
| Relational DB | PostgreSQL | 16 | Users, logs, feedback, structured queries |
| ORM | SQLAlchemy + Alembic | 2.x | Async ORM + migrations |
| Cache | Redis | 7.x | Query cache + rate limiting |
| Embeddings | OpenAI text-embedding-3-large | — | Best quality for domain-specific retrieval |
| LLM | Claude claude-sonnet-4-20250514 | — | Best citation adherence, large context |
| Reranker | Cohere Rerank v3 | — | State-of-art reranking for RAG |
| NLI Verifier | DeBERTa-v3-large (NLI) | — | Fast, accurate entailment checking |
| PDF Parser (primary) | PyMuPDF | 1.24+ | Fast native text extraction |
| PDF Parser (complex) | LlamaParse | — | Tables, multi-column, complex layouts |
| PDF Parser (scanned) | Tesseract OCR | 5.x | Fallback for image-only PDFs |
| BM25 | rank_bm25 (dev) / Elasticsearch (prod) | — | Keyword matching complement to vectors |
| Auth | Clerk | — | Production-ready auth with minimal setup |
| Frontend Deploy | Vercel | — | Zero-config Next.js deployment |
| Backend Deploy | Koyeb | — | Persistent Python deployment |
| PDF Storage | Cloudflare R2 | — | Cheap object storage, CDN delivery |
| Monitoring | Sentry | — | Error tracking frontend + backend |
| Logging | Loguru (backend) | — | Structured logging |
| Testing (backend) | pytest + pytest-asyncio | — | Async-native test runner |
| Testing (frontend) | Vitest + React Testing Library | — | Fast unit/integration tests |
| E2E Testing | Playwright | — | Full browser automation |
| CI/CD | GitHub Actions | — | Automated test + deploy pipeline |

---

## Detailed Rationale

### Why FastAPI over Django/Flask?
- Async-native — critical for concurrent retrieval + LLM calls
- Automatic OpenAPI/Swagger docs with Pydantic models
- Performance: comparable to Node.js for I/O-bound workloads
- Python ecosystem access (ML libraries, embedding models, NLI models)

### Why Qdrant over Pinecone/Weaviate/pgvector?
- **Metadata filtering:** Rich payload filters before vector search — essential for domain routing (filter to `domain: "medical"` before searching)
- **Hybrid search:** Built-in sparse vector support (can run BM25-style in Qdrant itself)
- **Self-hostable + Cloud:** Same API, avoid vendor lock-in
- **Performance:** Faster than pgvector at 130k+ chunks with complex filters
- pgvector rejected: Too slow at scale with metadata filtering; better for <10k vectors

### Why text-embedding-3-large over alternatives?
- Best retrieval quality in benchmarks for knowledge-dense domains
- 3072 dims (truncatable to 1536 for cost savings with minimal quality loss)
- Strong on medical terminology — doesn't lose meaning of clinical terms
- Cohere Embed rejected: slightly lower quality on domain-specific content in testing

### Why Claude over GPT-4o for generation?
- Superior instruction following for constrained generation ("only use provided sources")
- Better at maintaining citation format consistently across long responses
- 200k context window — future-proof for multi-chunk synthesis
- Lower hallucination rate when grounded with source context

### Why DeBERTa-v3 NLI over similarity scoring for verification?
- Similarity: "are these semantically close?" — passes hallucinations that use related vocab
- NLI entailment: "does source LOGICALLY SUPPORT this claim?" — catches fabricated specifics
- DeBERTa-v3-large achieves 92%+ on MNLI — production quality
- Runs on CPU in < 500ms for 5 claims — acceptable latency

### Why Clerk over NextAuth?
- Handles email/password + OAuth out of the box with minimal code
- Built-in user management UI
- Webhook support for user events
- For a solo/small team project, development speed > customization

### Why Cloudflare R2 over S3 for PDF storage?
- Zero egress fees — PDFs are served to users frequently (citation source viewer)
- S3 charges per GB egress; at scale with 2GB+ corpus this matters
- Same S3-compatible API, trivial migration if needed

---

## Python Backend Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.6.0"
pydantic-settings = "^2.2.0"

# Database
sqlalchemy = {extras = ["asyncio"], version = "^2.0.0"}
alembic = "^1.13.0"
asyncpg = "^0.29.0"
redis = {extras = ["asyncio"], version = "^5.0.0"}

# Vector DB
qdrant-client = {extras = ["fastembed"], version = "^1.8.0"}

# AI / ML
openai = "^1.12.0"               # Embeddings
anthropic = "^0.21.0"            # Claude generation
cohere = "^4.47.0"               # Reranker
transformers = "^4.38.0"         # DeBERTa NLI model
torch = "^2.2.0"                 # NLI inference

# PDF Parsing
pymupdf = "^1.24.0"
pytesseract = "^0.3.10"
llama-parse = "^0.3.0"           # LlamaParse API client

# BM25
rank-bm25 = "^0.2.2"

# Utilities
httpx = "^0.27.0"
loguru = "^0.7.0"
python-multipart = "^0.0.9"
```

---

## Frontend Dependencies

```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x",
    "typescript": "5.x",
    "@clerk/nextjs": "latest",
    "tailwindcss": "3.x",
    "shadcn-ui": "latest",
    "lucide-react": "latest",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "framer-motion": "^11.0.0",
    "react-pdf": "^7.0.0",
    "zustand": "^4.5.0",
    "swr": "^2.2.0"
  }
}
```

---

## Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/curasource
REDIS_URL=redis://localhost:6379
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
COHERE_API_KEY=...
LLAMAPARSE_API_KEY=...
CLERK_SECRET_KEY=sk_live_...
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=curasource-pdfs
SENTRY_DSN=https://...

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://api.curasource.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
SENTRY_DSN=https://...
```
