# ARCHITECTURE.md — CuraSource System Architecture

---

## High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────▼───────────────────────────────────────┐
│                   Next.js 14 Frontend (Vercel)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Chat UI     │  │ Source Viewer│  │  Corpus Browser        │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST / SSE (streaming)
┌─────────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend (Koyeb)                       │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Query Pipeline                          │ │
│  │                                                            │ │
│  │  Query → [Domain Router] → [Hybrid Retriever]             │ │
│  │              │                    │                        │ │
│  │         Domain Tags          BM25 + Vector                 │ │
│  │                                   │                        │ │
│  │                            [Cohere Reranker]               │ │
│  │                                   │                        │ │
│  │                           Top-5 Chunks                     │ │
│  │                                   │                        │ │
│  │                      [Claude Generation]                   │ │
│  │                                   │                        │ │
│  │                      [NLI Citation Verifier]               │ │
│  │                                   │                        │ │
│  │                         Verified Response                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────┬──────────────┬───────────────┬────────────────┬──────────┘
       │              │               │                │
┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐
│   Qdrant    │ │  BM25     │ │  PostgreSQL │ │   Redis     │
│ Vector DB   │ │  Index    │ │  (users,    │ │  (cache,    │
│(Qdrant Cloud│ │(Elastic / │ │   logs,     │ │  rate limit)│
│             │ │ rank_bm25)│ │   feedback) │ │             │
└─────────────┘ └───────────┘ └─────────────┘ └─────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Ingestion Pipeline (Offline)                  │
│                                                                 │
│  PDF Corpus → [Parser] → [Chunker] → [Embedder] → [Qdrant]     │
│                  │           │            │                     │
│             PyMuPDF/     Structure-    text-                    │
│             LlamaParse/  Aware         embedding-               │
│             Tesseract    Chunker       3-large                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Ingestion Pipeline (Offline / One-Time + On-Demand)

**Responsibilities:**
- Parse PDFs into structured text, tables, and figure references
- Chunk content with structure-awareness
- Embed chunks and store in Qdrant
- Build/update BM25 index

**Components:**
```
ingestion/
├── parsers/
│   ├── pymupdf_parser.py      # Primary: fast native text extraction
│   ├── llamaparse_parser.py   # Secondary: complex layouts, tables
│   └── ocr_parser.py          # Fallback: scanned/image-only PDFs
├── chunkers/
│   ├── structure_chunker.py   # Main chunker — prose/table/figure logic
│   └── deduplicator.py        # Hash-based chunk dedup
├── extractors/
│   ├── table_extractor.py     # Tables → markdown, keep intact
│   └── figure_extractor.py    # Caption + surrounding text + image path
├── embedder.py                # OpenAI text-embedding-3-large
├── metadata_tagger.py         # Attach full metadata to every chunk
└── pipeline.py                # Orchestrator
```

**Data Flow:**
```
PDF File
  → Parser (detect: native/scanned/complex)
  → Structure Extractor (headings, tables, figures, lists)
  → Chunker (prose=300-400tok, table=intact, figure=caption+context)
  → Metadata Tagger (domain, edition, page, content_type, hash)
  → Deduplicator (skip if hash exists)
  → Embedder (text-embedding-3-large)
  → Qdrant (vector + payload)
  → BM25 Index Update
```

---

### 2. Query Pipeline (Real-Time)

**Responsibilities:**
- Route query to correct domain(s)
- Retrieve relevant chunks via hybrid search
- Rerank results
- Generate grounded response
- Verify citations via NLI entailment

**Components:**
```
backend/
├── pipeline/
│   ├── domain_router.py       # Classify query domain (medical/fitness/both)
│   ├── retriever.py           # Hybrid BM25 + Vector + RRF
│   ├── reranker.py            # Cohere Rerank v3
│   ├── generator.py           # Claude API constrained generation
│   └── verifier.py            # NLI-based citation entailment check
└── query_orchestrator.py      # Ties all pipeline steps together
```

**Data Flow:**
```
User Query
  → Domain Router → [domain tags]
  → BM25 Search (filtered by domain) → top-20
  → Vector Search (filtered by domain) → top-20
  → RRF Fusion → top-20 merged
  → Cohere Reranker → top-5 chunks
  → Claude Generation (chunks as context) → draft response + citations
  → NLI Verifier (batch: all claims vs source chunks)
  → Verified Response (flag/drop unverified claims)
  → Stream to frontend
```

---

### 3. Frontend (Next.js 14)

**Responsibilities:**
- Chat interface with streaming
- Citation rendering and source viewer
- Corpus browser
- User authentication and session management

**Key Pages/Routes:**
```
app/
├── (auth)/
│   ├── login/page.tsx
│   └── register/page.tsx
├── chat/
│   ├── page.tsx               # Main chat interface
│   └── [sessionId]/page.tsx   # Specific session
├── sources/
│   ├── page.tsx               # Corpus browser
│   └── [sourceId]/page.tsx    # Source viewer (PDF page, table)
├── api/
│   ├── query/route.ts         # Proxy to FastAPI
│   └── auth/[...nextauth]/    # Auth handlers
└── layout.tsx
```

---

### 4. Data Stores

#### Qdrant (Vector DB)
- **Collection:** `curasource_chunks`
- **Vector size:** 1536 (text-embedding-3-large, truncated)
- **Distance:** Cosine
- **Payload filters:** domain, content_type, edition, publication_year, source_file
- **Index:** HNSW (ef_construction=200, m=16)

#### PostgreSQL
```sql
-- Users
users (id, email, name, tier, created_at)

-- Query sessions
sessions (id, user_id, created_at)

-- Individual queries and responses
queries (id, session_id, query_text, response_text, 
         domain_tags, chunks_used, latency_ms, 
         citation_scores, created_at)

-- User feedback on responses
feedback (id, query_id, user_id, rating, flagged_citation_ids, comment, created_at)

-- Source metadata (mirrors Qdrant payload, for SQL queries)
sources (id, source_file, title, domain, edition, publication_year, total_chunks)
```

#### Redis
- Query result cache (TTL: 1 hour for identical queries)
- Rate limiting counters (per user, per IP)
- Session tokens

---

### 5. Content Type Architecture

Three tiers of content, each handled differently:

| Tier | Content | Searchable? | Citable? | Strategy |
|------|---------|-------------|----------|---------|
| 1 | Prose / text | ✅ Fully | ✅ Fully | Standard chunking |
| 2 | Tables / structured data | ✅ If extracted correctly | ✅ If extracted correctly | Keep intact, markdown format |
| 3 | Images / diagrams | ⚠️ Via caption only (now) | ⚠️ As figure reference | Caption extraction → Layer 2: multimodal descriptions |

**For ECG images specifically:**
- System cites the *textual explanation* from the book
- References the figure: "See Figure 7.3, page 143 for example strip"
- Never claims to interpret the image itself
- Layer 2: AI-generated descriptions tagged `generated_description: true`

---

### 6. Citation Verification Architecture

**Why NLI, not similarity:**
- Similarity asks: "are these semantically close?" → misses hallucinations that sound similar
- NLI asks: "does the source ENTAIL this claim?" → catches fabricated specifics

```python
# Verification flow
for claim, source_chunk in zip(claims, source_chunks):
    result = nli_model.predict(premise=source_chunk, hypothesis=claim)
    # result: {"entailment": 0.92, "neutral": 0.06, "contradiction": 0.02}
    if result["entailment"] > 0.75:
        status = "verified"
    elif result["entailment"] > 0.50:
        status = "low_confidence"  # Show with warning
    else:
        status = "failed"  # Drop from response
```

**Model:** `cross-encoder/nli-deberta-v3-large`
**Batched:** All claims verified in single forward pass
**Latency target:** < 500ms for 5 citations

---

## Scalability Considerations

| Component | Current (MVP) | At Scale |
|-----------|--------------|----------|
| Vector DB | Qdrant Cloud single node | Qdrant Cloud cluster |
| BM25 | In-memory rank_bm25 | Elasticsearch |
| Backend | Single Koyeb instance | Koyeb auto-scale |
| Embedding | OpenAI API | Self-hosted (later) |
| NLI Verifier | CPU inference | GPU inference endpoint |
| PDFs | Static storage | S3 / Cloudflare R2 |
