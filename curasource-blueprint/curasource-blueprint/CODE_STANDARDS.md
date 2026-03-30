# CODE_STANDARDS.md — CuraSource Coding Conventions & Principles

---

## Core Philosophy

Write code that is **readable first, clever never**. CuraSource is a medical-adjacent product — ambiguous code is a liability. Every function should be obvious in intent, every module obvious in responsibility.

---

## SOLID Principles Applied

### S — Single Responsibility Principle
Each class/module does ONE thing.

```python
# ✅ GOOD — each class has one job
class PDFParser:
    def parse(self, filepath: str) -> ParsedDocument: ...

class StructureChunker:
    def chunk(self, document: ParsedDocument) -> list[Chunk]: ...

class ChunkEmbedder:
    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...

class QdrantUploader:
    async def upload(self, chunks: list[EmbeddedChunk]) -> None: ...

# ❌ BAD — one class doing everything
class IngestionManager:
    def parse_and_chunk_and_embed_and_upload(self, filepath): ...
```

### O — Open/Closed Principle
Open for extension, closed for modification. Use ABCs for parsers, chunkers, retrievers.

```python
# ✅ GOOD — add new parsers without changing existing code
from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, filepath: str) -> ParsedDocument:
        pass
    
    @abstractmethod
    def can_handle(self, filepath: str) -> bool:
        pass

class PyMuPDFParser(BaseParser):
    def parse(self, filepath: str) -> ParsedDocument: ...
    def can_handle(self, filepath: str) -> bool:
        return not self._is_scanned(filepath)

class TesseractParser(BaseParser):
    def parse(self, filepath: str) -> ParsedDocument: ...
    def can_handle(self, filepath: str) -> bool:
        return self._is_scanned(filepath)

# Add LlamaParse: extend, don't modify PyMuPDFParser
class LlamaParseParser(BaseParser): ...
```

### L — Liskov Substitution Principle
Subclasses must honor the contract of their base class.

```python
# ✅ GOOD — any retriever can substitute another
class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: str, domain: list[str], top_k: int) -> list[Chunk]:
        pass

class HybridRetriever(BaseRetriever):
    async def retrieve(self, query: str, domain: list[str], top_k: int) -> list[Chunk]:
        # Always returns list[Chunk] — honors the contract
        ...

class VectorOnlyRetriever(BaseRetriever):
    async def retrieve(self, query: str, domain: list[str], top_k: int) -> list[Chunk]:
        # Test/fallback retriever — same interface
        ...
```

### I — Interface Segregation Principle
Don't force classes to implement interfaces they don't use.

```python
# ✅ GOOD — separate interfaces for different capabilities
class Embeddable(Protocol):
    async def embed(self, text: str) -> list[float]: ...

class Reranker(Protocol):
    async def rerank(self, query: str, documents: list[str]) -> list[float]: ...

class CitationVerifier(Protocol):
    async def verify(self, claim: str, source: str) -> VerificationResult: ...

# CohereClient only implements what it supports
class CohereClient(Reranker):
    async def rerank(self, query: str, documents: list[str]) -> list[float]: ...
    # Not forced to implement Embeddable or CitationVerifier
```

### D — Dependency Inversion Principle
Depend on abstractions, not concretions.

```python
# ✅ GOOD — QueryOrchestrator depends on interfaces, not implementations
class QueryOrchestrator:
    def __init__(
        self,
        retriever: BaseRetriever,       # Interface
        reranker: Reranker,             # Protocol
        generator: BaseGenerator,       # Interface
        verifier: CitationVerifier,     # Protocol
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator
        self.verifier = verifier

# In tests, inject mocks:
orchestrator = QueryOrchestrator(
    retriever=MockRetriever(),
    reranker=MockReranker(),
    generator=MockGenerator(),
    verifier=MockVerifier(),
)

# In production, inject real implementations:
orchestrator = QueryOrchestrator(
    retriever=HybridRetriever(qdrant_client, bm25_index),
    reranker=CohereReranker(api_key),
    generator=ClaudeGenerator(anthropic_client),
    verifier=DeBERTaVerifier(model_path),
)
```

---

## Python Backend Standards

### File Structure
```
backend/
├── api/
│   ├── routes/
│   │   ├── query.py          # /api/query endpoints
│   │   ├── sources.py        # /api/sources endpoints
│   │   └── feedback.py       # /api/feedback endpoints
│   ├── middleware/
│   │   ├── auth.py           # Clerk JWT verification
│   │   ├── rate_limiter.py   # Redis-based rate limiting
│   │   └── request_logger.py
│   └── dependencies.py       # FastAPI dependency injection
├── pipeline/
│   ├── domain_router.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── generator.py
│   └── verifier.py
├── models/
│   ├── chunk.py              # Pydantic + SQLAlchemy models
│   ├── query.py
│   ├── source.py
│   └── feedback.py
├── db/
│   ├── postgres.py           # Async SQLAlchemy session
│   ├── qdrant.py             # Qdrant client setup
│   └── redis.py              # Redis client setup
├── config.py                 # Pydantic Settings
└── main.py                   # FastAPI app init
```

### Naming Conventions
```python
# Variables and functions: snake_case
chunk_metadata = get_chunk_metadata(chunk_id)
async def retrieve_top_chunks(query: str) -> list[Chunk]: ...

# Classes: PascalCase
class StructureAwareChunker: ...
class CitationVerificationResult: ...

# Constants: UPPER_SNAKE_CASE
MAX_CHUNK_TOKENS = 400
DEFAULT_TOP_K = 5
VERIFICATION_THRESHOLD = 0.75

# Private methods: _single_underscore
class Retriever:
    def _apply_domain_filter(self, domain: list[str]) -> Filter: ...

# Type aliases: PascalCase
ChunkId = str
DomainTag = Literal["medical", "fitness"]
```

### Pydantic Models (All I/O)
```python
from pydantic import BaseModel, Field
from datetime import datetime

# ALL request/response objects must be Pydantic models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    domain: list[DomainTag] = Field(default=["medical", "fitness"])
    session_id: str | None = None

class CitationDetail(BaseModel):
    index: int
    source_title: str
    edition: str
    chapter: str
    page_number: int
    excerpt: str
    verification_status: Literal["verified", "low_confidence"]
    verification_score: float

class QueryResponse(BaseModel):
    response_text: str
    citations: list[CitationDetail]
    domain_tags_used: list[str]
    latency_ms: int
    query_id: str
```

### Error Handling
```python
# Custom exception hierarchy
class CuraSourceError(Exception):
    """Base exception"""
    pass

class RetrievalError(CuraSourceError):
    """Qdrant or BM25 retrieval failed"""
    pass

class GenerationError(CuraSourceError):
    """Claude API call failed"""
    pass

class VerificationError(CuraSourceError):
    """NLI model inference failed"""
    pass

# FastAPI exception handlers
@app.exception_handler(RetrievalError)
async def retrieval_error_handler(request, exc):
    logger.error(f"Retrieval failed: {exc}", exc_info=True)
    return JSONResponse(status_code=503, content={"error": "retrieval_failed", "message": "Search temporarily unavailable"})

# Never expose internal errors to clients
# Never swallow exceptions silently
```

### Async Patterns
```python
# ✅ GOOD — parallel I/O operations
async def hybrid_retrieve(query: str, domain: list[str]) -> list[Chunk]:
    bm25_task = asyncio.create_task(bm25_search(query, domain))
    vector_task = asyncio.create_task(vector_search(query, domain))
    
    bm25_results, vector_results = await asyncio.gather(bm25_task, vector_task)
    return reciprocal_rank_fusion([bm25_results, vector_results])

# ❌ BAD — sequential when parallel is possible
async def hybrid_retrieve(query: str, domain: list[str]) -> list[Chunk]:
    bm25_results = await bm25_search(query, domain)     # Wait...
    vector_results = await vector_search(query, domain)  # Then wait again
    return reciprocal_rank_fusion([bm25_results, vector_results])
```

### Logging
```python
from loguru import logger

# Structured logging — always include context
logger.info("Query processed", 
    query_id=query_id,
    domain=domain,
    chunks_retrieved=len(chunks),
    verification_passed=len(verified),
    latency_ms=elapsed
)

# Never log PII
logger.info("User authenticated", user_id=user.id)  # ✅
logger.info("User authenticated", email=user.email)  # ❌ PII
```

---

## TypeScript Frontend Standards

### File Structure
```
frontend/
├── app/                      # Next.js App Router
├── components/
│   ├── chat/
│   │   ├── ChatInterface.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── CitationBadge.tsx
│   │   ├── CitationCard.tsx
│   │   └── QueryInput.tsx
│   ├── sources/
│   │   ├── SourcePanel.tsx
│   │   ├── SourceCard.tsx
│   │   └── PDFViewer.tsx
│   └── ui/                   # shadcn/ui components
├── hooks/
│   ├── useChat.ts
│   ├── useSession.ts
│   └── useSourcePanel.ts
├── stores/
│   └── chatStore.ts          # Zustand
├── types/
│   ├── api.ts                # API request/response types
│   ├── chat.ts               # Chat domain types
│   └── source.ts             # Source domain types
└── lib/
    ├── api.ts                # API client
    └── utils.ts
```

### TypeScript Rules
```typescript
// ✅ Always type function parameters and return types
async function fetchQuery(request: QueryRequest): Promise<QueryResponse> { ... }

// ✅ Use discriminated unions for state
type CitationStatus = 
  | { status: "verified"; score: number }
  | { status: "low_confidence"; score: number; warning: string }

// ✅ Prefer interfaces for objects, types for unions/aliases
interface Citation {
  index: number;
  sourceTitle: string;
  edition: string;
  chapter: string;
  pageNumber: number;
  excerpt: string;
  verification: CitationStatus;
}

// ❌ Never use `any`
const data: any = await fetch(...);  // ❌
const data: QueryResponse = await fetch(...);  // ✅

// ❌ Never non-null assert unless truly impossible to be null
const el = document.getElementById("root")!;  // ❌ fragile
const el = document.getElementById("root");
if (!el) throw new Error("Root element not found");  // ✅
```

### Component Standards
```tsx
// ✅ Props interfaces always defined separately
interface CitationCardProps {
  citation: Citation;
  onViewSource: (citation: Citation) => void;
}

// ✅ Components are pure and predictable
export function CitationCard({ citation, onViewSource }: CitationCardProps) {
  return (
    <div className="citation-card" role="article" aria-label={`Citation ${citation.index}`}>
      {/* ... */}
    </div>
  );
}

// ✅ Loading states always handled
function ChatMessage({ isStreaming }: { isStreaming: boolean }) {
  if (isStreaming) return <StreamingIndicator />;
  // ...
}
```

---

## Git Conventions

### Branch Naming
```
feature/ingestion-table-chunker
fix/citation-badge-accessibility  
chore/upgrade-qdrant-client
docs/update-architecture
```

### Commit Messages (Conventional Commits)
```
feat(pipeline): add structure-aware table chunker
fix(verifier): batch NLI calls to reduce latency
docs(api): add citation endpoint spec
chore(deps): upgrade anthropic SDK to 0.25.0
test(retriever): add domain filter integration tests
refactor(generator): extract prompt templates to config
```

### PR Rules
- No PR merges without passing CI
- No PR merges without at least 1 review (when team > 1)
- PR description must link to the feature/bug it addresses
- All new features must include tests
