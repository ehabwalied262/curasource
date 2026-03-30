# DATA_PIPELINE.md — Ingestion, Parsing & Chunking Strategy

---

## Overview

The ingestion pipeline converts raw PDFs into searchable, citable chunks stored in Qdrant. This is the foundation of the entire product — a flawed pipeline means flawed citations, which destroys user trust.

**Rule #1: Never split a table.**
**Rule #2: Every chunk must have complete metadata.**
**Rule #3: Deduplicate before embedding.**

---

## File Categories & Parser Assignment

| Category | Example Files | Primary Parser | Fallback |
|----------|------------|---------------|----------|
| Dense medical reference | Harrison's, Davidson's, Kumar & Clark | LlamaParse | PyMuPDF |
| Oxford Handbooks | Emergency Medicine, Drug Therapy | LlamaParse | PyMuPDF |
| Fitness certifications | ACE, ACSM, NASM, NSCA | PyMuPDF | LlamaParse |
| Scanned textbooks | ISSA (likely scanned) | Tesseract OCR | LlamaParse OCR |
| Training programs | Nippard, Israetel, McDonald | PyMuPDF | LlamaParse |
| ECG / Cardiology | Goldberger's, Hampton's | LlamaParse | PyMuPDF + Vision |

---

## Step 1 — Dataset Deduplication

Before parsing anything, deduplicate the file list.

**Known duplicate pairs to resolve:**
```
Medical Textbooks/Davidson's Essentials.pdf  
↕ Duplicate?  
others (medicide)/Davidson's Essentials.pdf

Medical Textbooks/Harrison's Manual of Medicine.pdf  
↕ Version check  
Medical Textbooks/Harrison's 21st Edition.pdf

Lyle McDonald/Rapid Fat Loss Handbook.pdf  
↕ Duplicate?  
others/Rapid Fat Loss Handbook.pdf
```

**Dedup strategy:**
```python
import hashlib

def file_hash(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

# Build hash map, keep one per hash (prefer richer metadata version)
seen_hashes = {}
for file in all_files:
    h = file_hash(file)
    if h not in seen_hashes:
        seen_hashes[h] = file
    else:
        # Log duplicate, keep the one with better metadata
        resolve_duplicate(file, seen_hashes[h])
```

---

## Step 2 — Parsing

### Parser Decision Tree
```
Is file scanned (image-only PDF)?
  YES → Tesseract OCR → output raw text with approximate page numbers
  NO  → Has complex layout (multi-column, heavy tables)?
          YES → LlamaParse → structured markdown output
          NO  → PyMuPDF → fast native text extraction
```

### Parser Outputs (Normalized Format)
All parsers output the same normalized structure:
```python
@dataclass
class ParsedDocument:
    source_file: str
    metadata: DocumentMetadata
    pages: list[ParsedPage]

@dataclass
class ParsedPage:
    page_number: int
    elements: list[PageElement]  # ordered list of content elements

@dataclass  
class PageElement:
    element_type: Literal["heading", "paragraph", "table", "figure", "list", "algorithm"]
    content: str          # text content or markdown table
    level: int | None     # for headings: 1/2/3
    image_path: str | None  # for figures: path to extracted image
    caption: str | None     # for figures/tables
    raw_html: str | None    # preserve for complex elements
```

---

## Step 3 — Structure-Aware Chunking

### Chunking Rules by Content Type

**Prose (paragraphs):**
```python
MAX_TOKENS = 400
OVERLAP_TOKENS = 50
BOUNDARY = "heading"  # Never chunk across heading boundaries

# Algorithm:
# 1. Group content by H2/H3 heading sections
# 2. Within each section, split prose into 300-400 token chunks
# 3. Add 50-token overlap from previous chunk
# 4. Tag with heading path: "Chapter 7 > Cardiovascular Disorders > Acute MI"
```

**Tables (CRITICAL — never split):**
```python
# Rule: one table = one chunk, regardless of token count
# Even a 1000-token table stays intact

def chunk_table(element: PageElement) -> Chunk:
    return Chunk(
        content=element.content,  # Full markdown table
        content_type="table",
        token_count=count_tokens(element.content),  # Can exceed 400
        caption=element.caption,
        page_number=element.page_number,
    )
```

**Figure References:**
```python
def chunk_figure(element: PageElement, surrounding_text: str) -> Chunk:
    # Combine: caption + 1 paragraph before + 1 paragraph after
    content = f"{surrounding_text}\n\nFigure: {element.caption}"
    return Chunk(
        content=content,
        content_type="figure_reference",
        image_path=element.image_path,  # Stored in R2
        caption=element.caption,
        page_number=element.page_number,
    )
```

**Clinical Algorithms / Decision Trees:**
```python
# Detect by: boxed content, indented decision branches, "if/then" patterns
# Rule: keep entire algorithm as one chunk

def chunk_algorithm(elements: list[PageElement]) -> Chunk:
    combined = "\n".join(e.content for e in elements)
    return Chunk(
        content=combined,
        content_type="algorithm",
        # Tag with medical specialty for filtering
    )
```

---

## Step 4 — Metadata Attachment

Every chunk gets this complete metadata payload:

```python
@dataclass
class ChunkMetadata:
    # Identity
    chunk_id: str                    # UUID v4
    chunk_hash: str                  # SHA-256 of content (for dedup)
    
    # Source
    source_file: str                 # "Harrisons_21st_Edition.pdf"
    title: str                       # "Harrison's Principles of Internal Medicine"
    authors: list[str]
    edition: str                     # "21st"
    publication_year: int            # 2022
    publisher: str
    
    # Location
    page_number: int
    chapter: str                     # "Chapter 7"
    section_heading: str             # "Cardiovascular Disorders"
    subsection: str                  # "Acute MI Management"
    heading_path: str                # "Ch7 > Cardiovascular > Acute MI"
    
    # Content
    domain: Literal["medical", "fitness"]
    subdomain: str                   # "cardiology", "strength_training", etc.
    content_type: Literal["prose", "table", "figure_reference", "algorithm", "list"]
    
    # Special flags
    is_scanned: bool                 # Was this parsed via OCR?
    generated_description: bool      # Was content AI-generated (for images)?
    has_image: bool
    image_path: str | None           # R2 URL if has_image
    
    # Ingestion
    ingested_at: datetime
    parser_used: str                 # "pymupdf" | "llamaparse" | "tesseract"
```

---

## Step 5 — Chunk Deduplication

Before embedding, deduplicate chunks:

```python
def is_duplicate(chunk: Chunk, qdrant_client) -> bool:
    # Check if chunk_hash already exists in Qdrant payload
    results = qdrant_client.scroll(
        collection_name="curasource_chunks",
        scroll_filter=Filter(
            must=[FieldCondition(key="chunk_hash", match=MatchValue(value=chunk.chunk_hash))]
        ),
        limit=1
    )
    return len(results[0]) > 0
```

---

## Step 6 — Embedding

```python
from openai import AsyncOpenAI

async def embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    client = AsyncOpenAI()
    
    # Batch in groups of 100 (API limit)
    all_embeddings = []
    for batch in batched(chunks, 100):
        response = await client.embeddings.create(
            model="text-embedding-3-large",
            input=[c.content for c in batch],
            dimensions=1536  # Truncate from 3072 for cost savings
        )
        all_embeddings.extend([r.embedding for r in response.data])
    
    return all_embeddings
```

---

## Step 7 — Qdrant Upload

```python
from qdrant_client.models import PointStruct

async def upload_to_qdrant(chunks: list[Chunk], embeddings: list[list[float]]):
    points = [
        PointStruct(
            id=chunk.chunk_id,
            vector=embedding,
            payload=asdict(chunk.metadata)
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]
    
    qdrant_client.upsert(
        collection_name="curasource_chunks",
        points=points,
        wait=True
    )
```

---

## Step 8 — BM25 Index Build

```python
from rank_bm25 import BM25Okapi

def build_bm25_index(chunks: list[Chunk]) -> BM25Okapi:
    tokenized = [chunk.content.lower().split() for chunk in chunks]
    return BM25Okapi(tokenized)

# Persist index to disk (pickle for dev, Redis serialization for prod)
```

---

## Validation Checklist (Run After Full Ingestion)

```python
def validate_corpus(qdrant_client):
    results = []
    
    # 1. Check for split tables
    table_chunks = get_chunks_by_type("table")
    for chunk in table_chunks:
        if not chunk.content.startswith("|") and "---" not in chunk.content:
            results.append(f"WARN: Possible split table in {chunk.source_file} p{chunk.page_number}")
    
    # 2. Check for missing page numbers
    missing_pages = get_chunks_where(page_number=None)
    results.append(f"Chunks missing page numbers: {len(missing_pages)}")
    
    # 3. Check domain coverage
    for domain in ["medical", "fitness"]:
        count = count_chunks_by_domain(domain)
        results.append(f"{domain}: {count} chunks")
    
    # 4. Sample 50 random chunks for manual review
    sample = random_sample(50)
    export_to_csv(sample, "validation_sample.csv")
    
    return results
```

---

## Corpus Statistics (Expected)

| Domain | Sources | Est. Chunks |
|--------|---------|-------------|
| Medical Reference | Harrison's, Davidson's, Kumar & Clark | ~40,000 |
| Emergency/Handbooks | Oxford Handbooks | ~8,000 |
| Cardiology/ECG | Goldberger's, Hampton's | ~5,000 |
| Pharmacology | Oxford Drug Therapy | ~6,000 |
| Fitness Certs | NASM, ACE, ACSM, NSCA | ~15,000 |
| Training Programs | Nippard, Israetel, McDonald | ~5,000 |
| **Total** | ~130 PDFs | **~79,000 chunks** |

---

## Image Handling Strategy

### Layer 1 (Implement Now)
Extract caption + surrounding context → store as `figure_reference` chunk.
Images stored in R2 at path: `pdfs/{source_slug}/figures/page_{n}_fig_{i}.png`

### Layer 2 (Phase 5)
```python
async def generate_image_description(image_path: str, caption: str) -> str:
    """Use Claude vision to generate clinical description of medical image."""
    response = await anthropic.messages.create(
        model="claude-opus-4-20250514",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": image_path}},
                {"type": "text", "text": f"Caption: {caption}\n\nDescribe exactly what this medical image shows in precise clinical terms. Include all labels, anatomical structures, pathological findings, and measurements visible."}
            ]
        }]
    )
    return response.content[0].text
    # Tag resulting chunk: generated_description=True
```
