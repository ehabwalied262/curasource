# PLAN.md — CuraSource Implementation Roadmap

> 5 Phases | ~14 Weeks to Production-Ready MVP

---

## Phase Overview

```
Phase 1 ──── Parsing & Ingestion (Weeks 1–4)
Phase 2 ──── Retrieval Core     (Weeks 5–7)
Phase 3 ──── Generation & Trust (Weeks 8–10)
Phase 4 ──── Product Layer      (Weeks 11–14)
Phase 5 ──── Iteration          (Ongoing)
```

---

## Phase 1 — Foundation: Parsing & Ingestion Pipeline
**Weeks 1–4 | Priority: CRITICAL — spend 40% of total effort here**

### Week 1 — Setup & Dataset Preparation
- [ ] Initialize monorepo structure (`/frontend`, `/backend`, `/ingestion`, `/evaluation`)
- [ ] Set up Qdrant instance (local Docker for dev, Qdrant Cloud for prod)
- [ ] Set up PostgreSQL schema (users, sessions, query_logs, feedback)
- [ ] Set up Redis (caching, rate limiting)
- [ ] Deduplicate dataset:
  - Hash every file by content (SHA-256)
  - Identify duplicates across `Medical Textbooks/` and `others (medicide)/`
  - Confirm duplicates: Davidson's Essentials vs 24th Ed, Harrison's Manual vs 21st Ed, Lyle McDonald Rapid Fat Loss duplicates
  - Keep the version with richer metadata; discard the other
- [ ] Tag every file with structured metadata:
  ```json
  {
    "source_file": "Harrisons_21st_Edition.pdf",
    "domain": "medical",
    "subdomain": "internal_medicine",
    "title": "Harrison's Principles of Internal Medicine",
    "edition": "21st",
    "publication_year": 2022,
    "authors": ["Loscalzo", "Fauci", ...],
    "is_scanned": false,
    "has_tables": true,
    "has_images": true
  }
  ```

### Week 2 — Parser Evaluation & Pipeline Build
- [ ] Test representative samples through parser candidates:
  - 1 chapter from Harrison's 21st Ed (multi-column, dense)
  - 1 chapter from ACE/ISSA (possibly scanned)
  - 1 chapter from Oxford Handbook Emergency Medicine (sidebars, boxes)
  - 1 Nippard training program (tables, sets/reps)
  - 1 ECG chapter (images + captions)
- [ ] Evaluate PyMuPDF vs LlamaParse vs Unstructured on each
- [ ] Decide OCR strategy for scanned documents (Tesseract vs LlamaParse OCR)
- [ ] Build primary parsing pipeline with fallback chain:
  ```
  PyMuPDF (fast, native text) 
    → LlamaParse (complex layouts)
    → Tesseract OCR (scanned/image-only)
  ```
- [ ] Extract and preserve document structure:
  - Headings (H1/H2/H3 mapped from font size/style)
  - Tables (extract as markdown, store as single units)
  - Figures (extract caption + surrounding text + image path)
  - Lists and clinical algorithms

### Week 3 — Structure-Aware Chunker
- [ ] Build chunker with these rules:
  - **Prose:** 300–400 tokens, overlap 50 tokens, chunk within heading boundaries
  - **Tables:** NEVER split. One table = one chunk, regardless of token count. Tag `content_type: "table"`
  - **Clinical algorithms/decision trees:** Keep intact. Tag `content_type: "algorithm"`
  - **Figure references:** Caption + surrounding 2 paragraphs. Tag `content_type: "figure_reference"`, store `image_path`
  - **Lists:** Keep list items together if under 600 tokens
- [ ] Attach full metadata to every chunk:
  ```json
  {
    "chunk_id": "uuid",
    "source_file": "...",
    "domain": "medical|fitness",
    "content_type": "prose|table|figure_reference|algorithm",
    "page_number": 142,
    "section_heading": "Chapter 7: Cardiovascular Disorders",
    "subsection": "Acute MI Management",
    "edition": "21st",
    "publication_year": 2022,
    "generated_description": false,
    "chunk_hash": "sha256..."
  }
  ```
- [ ] Build chunk-level deduplication (hash content, skip duplicates on re-ingest)
- [ ] Build image handling pipeline:
  - Layer 1 (now): Extract caption + page reference → store as searchable chunk
  - Layer 2 (later): Feed image to Claude/GPT-4o during ingestion → generate text description → tag as `generated_description: true`

### Week 4 — Full Corpus Ingestion & Validation
- [ ] Run full ingestion pipeline across all ~130 PDFs
- [ ] Validate output:
  - Sample 50 random chunks manually
  - Verify metadata accuracy
  - Verify tables were not split
  - Verify figure references have captions
  - Check scanned docs were OCR'd correctly
- [ ] Fix issues, re-ingest affected files
- [ ] Final corpus stats: total chunks, breakdown by domain/content_type
- [ ] Store all chunks in Qdrant with metadata filters

**Phase 1 Exit Criteria:**
- All 130 PDFs parsed and ingested
- Zero split tables in Qdrant
- Every chunk has complete metadata
- Deduplication confirmed
- Manual sample validation passed

---

## Phase 2 — Retrieval Core: Search That Works
**Weeks 5–7**

### Week 5 — Embedding + BM25
- [ ] Embed all chunks using `text-embedding-3-large` (3072 dims, truncate to 1536)
- [ ] Store vectors in Qdrant with payload metadata
- [ ] Build BM25 index (using `rank_bm25` or Elasticsearch)
- [ ] Implement hybrid retrieval with Reciprocal Rank Fusion (RRF):
  ```python
  def hybrid_retrieve(query, top_k=20):
      bm25_results = bm25_search(query, top_k=top_k)
      vector_results = vector_search(query, top_k=top_k)
      return reciprocal_rank_fusion([bm25_results, vector_results])
  ```

### Week 6 — Reranker + Query Router
- [ ] Integrate Cohere Rerank v3 on top of hybrid results (top-20 → top-5)
- [ ] Build query routing / domain classifier:
  ```python
  # Lightweight GPT-4o-mini call
  def classify_query_domain(query: str) -> list[str]:
      # Returns: ["medical"], ["fitness"], or ["medical", "fitness"]
  ```
- [ ] Apply domain filter to Qdrant queries before retrieval
- [ ] Test retrieval quality:
  - 30 real questions across all domains
  - Manually verify correct chunks are returned in top-5
  - Track: MRR (Mean Reciprocal Rank), Recall@5

### Week 7 — Retrieval Tuning
- [ ] Tune: top-k values, RRF weights, reranker threshold
- [ ] Build evaluation harness:
  - 100 question → expected source pairs
  - Automated: Run query, check if expected source appears in top-5
  - Track metrics per domain
- [ ] Document final retrieval configuration

**Phase 2 Exit Criteria:**
- Retrieval Recall@5 > 85% on evaluation set
- Domain routing correctly classifies 95%+ of test queries
- P95 retrieval latency < 800ms

---

## Phase 3 — Generation & Trust Layer
**Weeks 8–10**

### Week 8 — Constrained Generation
- [ ] Build generation pipeline with Claude API
- [ ] System prompt engineering:
  - Constrain to retrieved chunks only
  - Enforce citation format: `[Source: Title, Chapter X, Page Y]`
  - Handle "not found in sources" gracefully
  - Handle multi-source synthesis
  - Handle conflicting sources (flag explicitly)
- [ ] Response format spec:
  ```
  Answer text with inline citations [1][2].

  Sources:
  [1] Harrison's 21st Edition, Chapter 7, Page 142
  [2] Davidson's 24th Edition, Chapter 4, Page 89
  ```
- [ ] Edge case handling:
  - Query out of corpus scope → decline and say so
  - Conflicting editions → show both, flag discrepancy
  - Image-only content → cite figure reference, show image

### Week 9 — Citation Verification (The Trust Layer)
- [ ] Implement NLI-based entailment verification (NOT similarity scoring):
  - Model: `cross-encoder/nli-deberta-v3-large`
  - For each claim → source chunk pair, check: "does chunk ENTAIL this claim?"
  - Threshold: entailment score > 0.75 → verified
  - Below threshold → flag with reduced confidence or drop
- [ ] Batch verification (all claims + chunks in one pass, not per-citation):
  ```python
  def verify_citations(claims: list[str], chunks: list[str]) -> list[VerificationResult]:
      # Returns: [{"claim": ..., "chunk": ..., "entailed": bool, "score": float}]
  ```
- [ ] UI treatment for verification results:
  - ✅ Verified citation — shown normally
  - ⚠️ Low-confidence citation — shown with warning
  - ❌ Failed verification — dropped from response

### Week 10 — End-to-End Testing
- [ ] 100 queries across all domains
- [ ] Measure:
  - Citation accuracy rate (manual review of 50)
  - Hallucination rate (claims not supported by any chunk)
  - Retrieval relevance (does top-5 contain the answer?)
  - P95 end-to-end latency
- [ ] Fix top-10 failure cases
- [ ] Document known limitations

**Phase 3 Exit Criteria:**
- Citation accuracy > 90% on manual review
- Hallucination rate < 5%
- P95 end-to-end latency < 3s

---

## Phase 4 — Product Layer
**Weeks 11–14**

### Week 11–12 — Frontend
- [ ] Next.js 14 App Router setup
- [ ] Chat interface with streaming responses
- [ ] Clickable citations → open source viewer (PDF page, table, figure)
- [ ] Domain filter UI (Medical / Fitness / Both)
- [ ] Source browser (browse corpus by category)
- [ ] Confidence indicators on citations
- [ ] Mobile-responsive

### Week 13 — Production Hardening
- [ ] User authentication (NextAuth.js / Clerk)
- [ ] Rate limiting per user tier
- [ ] Query logging (for feedback loop)
- [ ] Error handling and graceful degradation
- [ ] Monitoring setup (Sentry, Datadog or equivalent)
- [ ] Cost tracking (API usage per query)

### Week 14 — Deployment & Soft Launch
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Koyeb
- [ ] Deploy Qdrant to Qdrant Cloud
- [ ] Load testing (target: 100 concurrent users)
- [ ] Security review (see SECURITY.md)
- [ ] Soft launch to 10–20 beta testers (medical professionals + fitness coaches)
- [ ] Feedback collection system live

**Phase 4 Exit Criteria:**
- System handles 100 concurrent users without degradation
- All monitoring alerts configured
- Beta feedback collected from ≥10 users

---

## Phase 5 — Iteration (Ongoing)

- Add new datasets through abstract RAG pipeline (no re-ingestion of full corpus)
- User feedback loop → flag bad citations → feed into evaluation harness
- Fine-tune domain-specific embeddings when query volume is sufficient
- Layer 2 image descriptions (multimodal ingestion-time descriptions)
- Multimodal search for ECG / anatomy diagrams
- API access tier for developers
- Mobile app (React Native)
