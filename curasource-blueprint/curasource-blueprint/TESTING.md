# TESTING.md — CuraSource Test Strategy & Scenarios

---

## Testing Philosophy

CuraSource is a medical-adjacent product. **A wrong citation is worse than no citation.** The testing strategy prioritizes:

1. **Citation accuracy** — the system must not lie about what sources say
2. **Retrieval quality** — the right chunks must surface for the right queries
3. **Hallucination detection** — the verifier must catch ungrounded claims
4. **Regression prevention** — pipeline changes must not degrade quality

---

## Test Pyramid

```
         ┌────────────────────────────┐
         │    E2E Tests (Playwright)  │  ~20 flows
         │  Full user journey tests   │
         ├────────────────────────────┤
         │   Integration Tests        │  ~80 tests
         │  Pipeline + API endpoints  │
         ├────────────────────────────┤
         │      Unit Tests            │  ~200 tests
         │  Pure logic, parsers,      │
         │  chunkers, verifier        │
         └────────────────────────────┘
```

---

## Unit Tests

### 1. Chunker Tests
```python
# tests/unit/test_chunker.py

class TestStructureAwareChunker:
    
    def test_prose_respects_max_tokens(self):
        """Prose chunks never exceed MAX_CHUNK_TOKENS (400)"""
        chunker = StructureAwareChunker()
        long_prose = "word " * 1000
        chunks = chunker.chunk_prose(long_prose)
        for chunk in chunks:
            assert count_tokens(chunk.content) <= 400
    
    def test_table_is_never_split(self):
        """A single table becomes exactly one chunk, regardless of size"""
        large_table = generate_markdown_table(rows=50, cols=6)  # ~800 tokens
        chunker = StructureAwareChunker()
        chunks = chunker.chunk_element(PageElement(type="table", content=large_table))
        assert len(chunks) == 1
        assert chunks[0].content_type == "table"
    
    def test_table_chunk_preserves_headers(self):
        """Table chunks include the header row"""
        table = "| Drug | Dose | Frequency |\n|---|---|---|\n| Metformin | 500mg | BID |"
        chunker = StructureAwareChunker()
        chunk = chunker.chunk_element(PageElement(type="table", content=table))
        assert "Drug" in chunk.content
        assert "Dose" in chunk.content
    
    def test_chunk_never_crosses_heading_boundary(self):
        """Prose chunks don't span across H2 headings"""
        doc_with_sections = """
        ## Section A
        Paragraph about section A. More text here...
        ## Section B  
        Paragraph about section B. Different content.
        """
        chunks = StructureAwareChunker().chunk(parse(doc_with_sections))
        for chunk in chunks:
            assert "Section A" not in chunk.content or "Section B" not in chunk.content
    
    def test_figure_includes_caption(self):
        """Figure chunks always include caption text"""
        figure = PageElement(type="figure", caption="Figure 7.3: ST elevation in STEMI", image_path="fig.png")
        chunk = StructureAwareChunker().chunk_figure(figure, surrounding_text="See figure below.")
        assert "ST elevation" in chunk.content
        assert chunk.content_type == "figure_reference"
    
    def test_overlap_in_prose_chunks(self):
        """Adjacent prose chunks share OVERLAP_TOKENS tokens"""
        text = "sentence one. " * 200
        chunks = StructureAwareChunker().chunk_prose(text)
        if len(chunks) > 1:
            # Last 50 tokens of chunk N should appear in chunk N+1
            end_of_first = chunks[0].content[-200:]
            start_of_second = chunks[1].content[:200:]
            assert any(word in start_of_second for word in end_of_first.split()[-20:])
    
    def test_algorithm_block_kept_intact(self):
        """Clinical algorithm blocks are never split"""
        algorithm = generate_clinical_algorithm()  # Decision tree structure
        chunks = StructureAwareChunker().chunk_element(PageElement(type="algorithm", content=algorithm))
        assert len(chunks) == 1
        assert chunks[0].content_type == "algorithm"
```

### 2. Metadata Tests
```python
class TestMetadataTagger:
    
    def test_all_required_fields_present(self):
        """Every chunk must have all required metadata fields"""
        required = ["chunk_id", "source_file", "domain", "page_number", 
                    "content_type", "chunk_hash", "edition", "publication_year"]
        chunk = create_test_chunk()
        tagger = MetadataTagger()
        tagged = tagger.tag(chunk, source_metadata=create_test_source_metadata())
        for field in required:
            assert getattr(tagged.metadata, field) is not None, f"Missing: {field}"
    
    def test_domain_classification_medical(self):
        """Harrison's PDF correctly classified as medical"""
        tagger = MetadataTagger()
        source = SourceMetadata(source_file="Harrisons_21st_Ed.pdf", ...)
        assert tagger.infer_domain(source) == "medical"
    
    def test_domain_classification_fitness(self):
        """NASM textbook correctly classified as fitness"""
        tagger = MetadataTagger()
        source = SourceMetadata(source_file="NASM_Essentials_7th.pdf", ...)
        assert tagger.infer_domain(source) == "fitness"
    
    def test_chunk_hash_is_deterministic(self):
        """Same content always produces same hash"""
        content = "Metformin is the preferred initial agent for T2DM."
        hash1 = compute_chunk_hash(content)
        hash2 = compute_chunk_hash(content)
        assert hash1 == hash2
    
    def test_chunk_hash_differs_for_different_content(self):
        """Different content produces different hash"""
        hash1 = compute_chunk_hash("content A")
        hash2 = compute_chunk_hash("content B")
        assert hash1 != hash2
```

### 3. Citation Verifier Tests
```python
class TestNLIVerifier:
    
    def test_verifies_directly_stated_claim(self):
        """Claim directly stated in source → entailed"""
        verifier = DeBERTaVerifier(model_path)
        source = "Metformin is the first-line treatment for type 2 diabetes mellitus."
        claim = "Metformin is recommended as initial therapy for T2DM."
        result = verifier.verify(claim, source)
        assert result.status == "verified"
        assert result.score > 0.75
    
    def test_rejects_contradicted_claim(self):
        """Claim contradicts source → not entailed"""
        verifier = DeBERTaVerifier(model_path)
        source = "Metformin is contraindicated in severe renal impairment (eGFR < 30)."
        claim = "Metformin can be safely used in all stages of renal disease."
        result = verifier.verify(claim, source)
        assert result.status in ["low_confidence", "failed"]
        assert result.score < 0.50
    
    def test_flags_hallucinated_specifics(self):
        """Hallucinated specific numbers not in source → flagged"""
        verifier = DeBERTaVerifier(model_path)
        source = "Blood pressure targets should be individualized based on patient factors."
        claim = "Blood pressure target for most patients is below 120/80 mmHg."
        result = verifier.verify(claim, source)
        # Source doesn't mention specific numbers — should not be verified
        assert result.score < 0.75
    
    def test_batch_verification_matches_individual(self):
        """Batch verification produces same results as individual calls"""
        verifier = DeBERTaVerifier(model_path)
        pairs = [(claim1, source1), (claim2, source2), (claim3, source3)]
        
        individual_results = [verifier.verify(c, s) for c, s in pairs]
        batch_results = verifier.verify_batch(pairs)
        
        for ind, batch in zip(individual_results, batch_results):
            assert abs(ind.score - batch.score) < 0.01
    
    def test_verifier_latency_under_500ms(self):
        """5-citation batch verification completes under 500ms"""
        verifier = DeBERTaVerifier(model_path)
        pairs = [(f"claim {i}", f"source {i}") for i in range(5)]
        
        start = time.time()
        verifier.verify_batch(pairs)
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 500, f"Verification took {elapsed}ms"
```

### 4. Domain Router Tests
```python
class TestDomainRouter:
    
    @pytest.mark.parametrize("query,expected", [
        ("What is the first-line treatment for hypertensive urgency?", ["medical"]),
        ("Best rep range for hypertrophy?", ["fitness"]),
        ("Can a diabetic patient do high-intensity interval training?", ["medical", "fitness"]),
        ("Harrison's chapter on nephrology", ["medical"]),
        ("Jeff Nippard PPL program", ["fitness"]),
        ("metformin and exercise interaction", ["medical", "fitness"]),
    ])
    def test_domain_classification(self, query, expected):
        router = DomainRouter()
        result = router.classify(query)
        assert sorted(result) == sorted(expected)
```

---

## Integration Tests

### 5. Retrieval Pipeline Tests
```python
class TestHybridRetrieval:
    """Tests against a test Qdrant instance with known chunks"""
    
    async def test_medical_query_returns_medical_chunks_only(self):
        """Domain filter works correctly"""
        retriever = HybridRetriever(test_qdrant_client, test_bm25_index)
        chunks = await retriever.retrieve(
            query="metformin dosing in renal impairment",
            domain=["medical"],
            top_k=5
        )
        for chunk in chunks:
            assert chunk.metadata.domain == "medical"
    
    async def test_known_query_returns_expected_source(self):
        """Specific query retrieves the known correct source"""
        # This test uses a curated Q→source mapping
        retriever = HybridRetriever(test_qdrant_client, test_bm25_index)
        chunks = await retriever.retrieve(
            query="ST elevation criteria for STEMI diagnosis",
            domain=["medical"],
            top_k=5
        )
        source_files = [c.metadata.source_file for c in chunks]
        assert any("Harrison" in f or "Goldberger" in f for f in source_files)
    
    async def test_reranker_improves_ordering(self):
        """Reranked results are more relevant than pre-rerank ordering"""
        # Run retrieval with and without reranker, evaluate relevance
        retriever_without_rerank = HybridRetriever(..., reranker=None)
        retriever_with_rerank = HybridRetriever(..., reranker=CohereReranker(...))
        
        query = "atrial fibrillation management in elderly patients"
        results_without = await retriever_without_rerank.retrieve(query, ["medical"], 5)
        results_with = await retriever_with_rerank.retrieve(query, ["medical"], 5)
        
        # Top result should be more relevant with reranking
        # (Evaluated by checking if known-relevant chunk ranks higher)
        ...
    
    async def test_retrieval_latency_under_800ms(self):
        """Full hybrid retrieval completes under 800ms P95"""
        retriever = HybridRetriever(...)
        latencies = []
        
        for query in BENCHMARK_QUERIES[:20]:
            start = time.time()
            await retriever.retrieve(query, ["medical", "fitness"], 20)
            latencies.append((time.time() - start) * 1000)
        
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 800, f"P95 retrieval latency: {p95}ms"
```

### 6. API Endpoint Tests
```python
class TestQueryEndpoint:
    
    async def test_query_returns_valid_response(self, test_client):
        response = await test_client.post("/api/query", json={
            "query": "What is metformin?",
            "domain": ["medical"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "response_text" in data
        assert "citations" in data
        assert isinstance(data["citations"], list)
    
    async def test_citations_have_required_fields(self, test_client):
        response = await test_client.post("/api/query", json={
            "query": "STEMI treatment protocol",
            "domain": ["medical"]
        })
        for citation in response.json()["citations"]:
            assert "source_title" in citation
            assert "page_number" in citation
            assert "verification_status" in citation
            assert citation["verification_status"] in ["verified", "low_confidence"]
    
    async def test_rate_limit_enforced(self, test_client, free_user_token):
        """Free tier: blocked after 10 queries"""
        for i in range(10):
            r = await test_client.post("/api/query", 
                json={"query": f"query {i}", "domain": ["medical"]},
                headers={"Authorization": f"Bearer {free_user_token}"}
            )
            assert r.status_code == 200
        
        # 11th query should be rate-limited
        r = await test_client.post("/api/query",
            json={"query": "one more query", "domain": ["medical"]},
            headers={"Authorization": f"Bearer {free_user_token}"}
        )
        assert r.status_code == 429
    
    async def test_unauthenticated_request_rejected(self, test_client):
        response = await test_client.post("/api/query", 
            json={"query": "test", "domain": ["medical"]}
        )
        assert response.status_code == 401
```

---

## Evaluation Harness

### 7. RAG Quality Evaluation (Not pytest — separate evaluation scripts)

```python
# evaluation/run_eval.py
# Run periodically as retrieval/generation parameters change

EVALUATION_SET = [
    # Format: (query, domain, expected_source_contains, expected_answer_contains)
    ("First-line treatment for T2DM", ["medical"], "Harrison", "metformin"),
    ("STEMI diagnostic criteria", ["medical"], ["Harrison", "Goldberger"], "ST elevation"),
    ("Optimal protein intake for hypertrophy", ["fitness"], ["NSCA", "ISSN"], "1.6"),
    ("Progressive overload definition", ["fitness"], ["NASM", "NSCA"], "progressive"),
    ("Metformin contraindications", ["medical"], "Harrison", "renal"),
    ("RPE scale in training", ["fitness"], ["Nippard", "Israetel"], "Rate of Perceived"),
    ("Hypertensive urgency management", ["medical"], ["Harrison", "Davidson"], "labetalol"),
    ("Sets and reps for strength", ["fitness"], ["NSCA", "NASM"], None),
    ("Can diabetics do HIIT?", ["medical", "fitness"], None, None),  # Cross-domain
    ("ECG findings in atrial fibrillation", ["medical"], ["Goldberger", "Hampton"], "irregularly"),
    # ... 90 more entries
]

def evaluate():
    results = []
    for query, domain, expected_source, expected_answer in EVALUATION_SET:
        chunks = retriever.retrieve(query, domain, top_k=5)
        response = generator.generate(query, chunks)
        
        # Metric 1: Source Recall — did expected source appear in top-5?
        source_recall = check_source_recall(chunks, expected_source)
        
        # Metric 2: Answer Quality — does response contain expected content?
        answer_quality = check_answer_contains(response, expected_answer) if expected_answer else None
        
        # Metric 3: Citation verification pass rate
        verification_rate = len([c for c in response.citations if c.status == "verified"]) / len(response.citations)
        
        results.append({
            "query": query,
            "source_recall": source_recall,
            "answer_quality": answer_quality,
            "verification_rate": verification_rate,
            "latency_ms": response.latency_ms,
        })
    
    # Print summary
    print(f"Source Recall@5: {mean(r['source_recall'] for r in results):.1%}")
    print(f"Answer Quality: {mean(r['answer_quality'] for r in results if r['answer_quality'] is not None):.1%}")
    print(f"Avg Verification Rate: {mean(r['verification_rate'] for r in results):.1%}")
    print(f"P95 Latency: {sorted(r['latency_ms'] for r in results)[int(len(results)*0.95)]}ms")
```

---

## E2E Tests (Playwright)

```typescript
// tests/e2e/chat.spec.ts

test("user can ask a medical question and see citations", async ({ page }) => {
  await page.goto("/chat");
  await page.fill('[data-testid="query-input"]', "What is metformin?");
  await page.click('[data-testid="send-button"]');
  
  // Wait for streaming to complete
  await page.waitForSelector('[data-testid="citation-card"]', { timeout: 15000 });
  
  const citations = await page.locator('[data-testid="citation-card"]').count();
  expect(citations).toBeGreaterThan(0);
  
  // Citations have required content
  const firstCitation = page.locator('[data-testid="citation-card"]').first();
  await expect(firstCitation).toContainText("Edition");
  await expect(firstCitation).toContainText("Page");
});

test("clicking citation opens source panel", async ({ page }) => {
  await page.goto("/chat");
  // ... ask question ...
  await page.click('[data-testid="citation-badge-1"]');
  await expect(page.locator('[data-testid="source-panel"]')).toBeVisible();
  await expect(page.locator('[data-testid="pdf-viewer"]')).toBeVisible();
});

test("domain filter changes retrieval scope", async ({ page }) => {
  await page.goto("/chat");
  await page.click('[data-testid="domain-filter-fitness"]');
  await page.fill('[data-testid="query-input"]', "progressive overload");
  await page.click('[data-testid="send-button"]');
  await page.waitForSelector('[data-testid="citation-card"]');
  
  // All citations should be from fitness sources
  const sources = await page.locator('[data-testid="citation-source-title"]').allTextContents();
  for (const source of sources) {
    expect(["NASM", "ACE", "ACSM", "NSCA", "Nippard", "Israetel"].some(s => source.includes(s))).toBe(true);
  }
});
```

---

## Quality Gates (CI must pass all)

| Gate | Threshold | Blocks Deploy? |
|------|-----------|---------------|
| Unit test pass rate | 100% | ✅ Yes |
| Integration test pass rate | 100% | ✅ Yes |
| E2E test pass rate | 95%+ | ✅ Yes |
| Retrieval Recall@5 (eval harness) | > 85% | ✅ Yes |
| Hallucination rate (manual spot-check) | < 5% | Manual review |
| P95 end-to-end latency | < 3000ms | ⚠️ Warning |
| Code coverage (backend) | > 80% | ⚠️ Warning |
