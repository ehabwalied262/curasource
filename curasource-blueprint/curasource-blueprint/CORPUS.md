# CORPUS.md — Dataset Inventory & Management

---

## Dataset Overview

~130 PDFs | ~2GB | Covering medical references, fitness certifications, and training programs.

---

## Categorized Inventory

### Medical Reference Textbooks
| Title | Edition | Year | Est. Size | Priority |
|-------|---------|------|-----------|----------|
| Harrison's Principles of Internal Medicine | 21st | 2022 | 317MB | 🔴 Critical |
| Davidson's Principles and Practice of Medicine | 24th | 2022 | Large | 🔴 Critical |
| Davidson's Essentials of Medicine | Latest | — | Medium | 🟡 Check for dupe |
| Kumar & Clark's Clinical Medicine | Latest | — | Large | 🔴 Critical |
| Oxford Handbook of Clinical Medicine | Latest | — | Medium | 🟠 High |
| Oxford Handbook of Emergency Medicine | Latest | — | Medium | 🟠 High |

### Cardiology / ECG
| Title | Edition | Year | Notes |
|-------|---------|------|-------|
| Goldberger's Clinical Electrocardiography | Latest | — | Heavy image content |
| Hampton's 150 ECG Cases | Latest | — | Case-based, image-heavy |

### Pharmacology
| Title | Edition | Year | Notes |
|-------|---------|------|-------|
| Oxford Handbook of Practical Drug Therapy | Latest | — | Tables critical |
| BNF / Drug reference (if any) | — | — | Verify licensing |

### Fitness Certifications
| Title | Edition | Year | Domain |
|-------|---------|------|--------|
| NASM Essentials of Personal Fitness Training | 7th | 2021 | 💪 Fitness |
| ACE Personal Trainer Manual | 6th | 2020 | 💪 Fitness |
| ACSM's Guidelines for Exercise Testing | 11th | 2021 | 💪 Fitness |
| NSCA Essentials of Strength & Conditioning | 4th | 2016 | 💪 Fitness |
| NSCA Essentials of Strength & Conditioning | 3rd | 2008 | 💪 ⚠️ Older edition |
| ISSA Certified Personal Trainer | Latest | — | 💪 Likely scanned |

### Evidence-Based Training Programs
| Title | Author | Notes |
|-------|--------|-------|
| PPL Hypertrophy Program | Jeff Nippard | Tables: sets/reps/rest |
| Scientific Principles of Hypertrophy | Dr. Mike Israetel | Dense text + tables |
| The Muscle and Strength Pyramids | Eric Helms | Structured programs |
| Rapid Fat Loss Handbook | Lyle McDonald | ⚠️ Check for duplicate |
| Stubborn Fat Solution | Lyle McDonald | ⚠️ Check for duplicate |
| Ultimate Diet 2.0 | Lyle McDonald | — |

---

## Known Duplicate Risk (Resolve Before Ingestion)

| File A | File B | Resolution |
|--------|--------|-----------|
| `Medical Textbooks/Davidson's Essentials.pdf` | `others (medicide)/Davidson's Essentials.pdf` | Hash comparison → keep one |
| `Harrison's Manual of Medicine.pdf` | `Harrison's 21st Edition.pdf` | Different books (Manual ≠ Full) — KEEP BOTH |
| `NSCA 3rd Edition.pdf` | `NSCA 4th Edition.pdf` | Different editions — KEEP BOTH, prefer 4th in retrieval |
| `Rapid Fat Loss Handbook.pdf` (location 1) | `Rapid Fat Loss Handbook.pdf` (location 2) | Hash comparison → keep one |

**Resolution command:**
```bash
# Find exact duplicates by content hash
python ingestion/scripts/find_duplicates.py --corpus-dir /data/corpus

# Output:
# DUPLICATE: Davidson's Essentials (Medical Textbooks/) == Davidson's Essentials (others/)
# Hash: abc123...
# Action: Keep Medical Textbooks/ version, delete others/ version
```

---

## Metadata Standards

Every source file gets this metadata before ingestion begins:

```python
SOURCE_REGISTRY = {
    "Harrisons_21st_Edition.pdf": {
        "title": "Harrison's Principles of Internal Medicine",
        "edition": "21st",
        "publication_year": 2022,
        "authors": ["Loscalzo J", "Fauci AS", "Kasper DL", "Hauser SL", "Longo DL", "Jameson JL"],
        "publisher": "McGraw-Hill",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "is_scanned": False,
        "has_tables": True,
        "has_images": True,
        "parser_recommendation": "llamaparse",  # Multi-column, complex
        "notes": "Multi-column layout, heavy tables, 317MB"
    },
    "NASM_Essentials_7th.pdf": {
        "title": "NASM Essentials of Personal Fitness Training",
        "edition": "7th",
        "publication_year": 2021,
        "authors": ["Clark M", "Lucett S", "Sutton B"],
        "publisher": "Jones & Bartlett",
        "domain": "fitness",
        "subdomain": "personal_training",
        "is_scanned": False,
        "has_tables": True,
        "has_images": True,
        "parser_recommendation": "pymupdf",
        "notes": ""
    },
    # ... all 130 files registered here before ingestion
}
```

---

## Edition Priority Rules

When multiple editions of the same textbook exist, apply these rules at retrieval time:

```python
EDITION_PREFERENCES = {
    "NSCA Essentials of Strength & Conditioning": "4th",  # Prefer over 3rd
    # Add others as needed
}

def prefer_newer_edition(chunks: list[Chunk]) -> list[Chunk]:
    """
    When chunks from multiple editions of the same title appear,
    boost newer edition chunks in ranking.
    Applied as a post-reranking adjustment.
    """
    ...
```

**Metadata display rule:** When citing an older edition, always note it:
> "According to NSCA 3rd Edition (2008)... Note: a newer 4th Edition (2016) is also available in the corpus."

---

## Content Type Distribution (Expected)

After ingestion, run this to verify corpus health:

```python
def corpus_health_report(qdrant_client):
    stats = {}
    
    for domain in ["medical", "fitness"]:
        for content_type in ["prose", "table", "figure_reference", "algorithm"]:
            count = count_chunks(domain=domain, content_type=content_type)
            stats[f"{domain}.{content_type}"] = count
    
    # Expected distribution (rough):
    # medical.prose:            ~60,000
    # medical.table:            ~8,000   ← critical to get right
    # medical.figure_reference: ~5,000
    # medical.algorithm:        ~2,000
    # fitness.prose:            ~18,000
    # fitness.table:            ~3,000   ← training program tables
    # fitness.figure_reference: ~1,500
    
    return stats
```

---

## Adding New Sources (Post-Launch)

New sources go through the abstract RAG pipeline:

1. **Upload PDF** to Cloudflare R2 at `pdfs/pending/{filename}`
2. **Register metadata** in `SOURCE_REGISTRY` with all required fields
3. **Run single-file ingestion:**
   ```bash
   python ingestion/pipeline.py --file "Harrisons_22nd_Edition.pdf" --mode single
   ```
4. **Validate output:** Sample 20 chunks, verify metadata
5. **Promote to active:** Update R2 path to `pdfs/active/`
6. **No downtime:** Qdrant upserts are non-blocking

---

## Copyright Notes

| Source | Publisher | Copyright Status | Notes |
|--------|-----------|-----------------|-------|
| Harrison's | McGraw-Hill | Copyrighted | Fair use as educational excerpts |
| Davidson's | Elsevier | Copyrighted | Elsevier has strict AI policies — legal review needed |
| Oxford Handbooks | Oxford UP | Copyrighted | Review OUP AI policy |
| NASM/ACE | Jones & Bartlett / ACE | Copyrighted | Certification bodies may have specific policies |
| Nippard/Israetel Programs | Individual authors | Copyrighted | Contact authors for commercial use |

> ⚠️ Consult copyright attorney before commercial launch. The critical question is whether RAG retrieval of excerpt-length chunks constitutes transformative fair use in an educational context.
