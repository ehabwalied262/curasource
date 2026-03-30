# CuraSource — Project Blueprint

> **A production-grade RAG (Retrieval-Augmented Generation) platform for trusted medical and fitness knowledge, powered by a ~130-PDF corpus with citation-verified responses.**

---

## What Is CuraSource?

CuraSource is an AI-powered knowledge assistant that answers medical and fitness questions by retrieving information directly from authoritative textbooks and evidence-based training resources. Every answer is grounded in a specific source, chapter, and page — no hallucinations, no unverified claims.

**The core promise:** Users get expert-level answers with traceable, verifiable citations from real textbooks.

---

## Blueprint File Index

| File | Purpose |
|------|---------|
| `README.md` | This file — project overview & navigation |
| `PLAN.md` | Phased implementation roadmap (5 phases, 14 weeks) |
| `ARCHITECTURE.md` | System architecture, data flow, component breakdown |
| `TECH_STACK.md` | Full technology decisions with rationale |
| `FEATURES.md` | Complete feature list (MVP → V2 → V3) |
| `DATA_PIPELINE.md` | Ingestion, parsing, chunking, embedding strategy |
| `UI_UX.md` | Design system, component specs, user flows |
| `API_SPEC.md` | All API endpoints, request/response contracts |
| `CODE_STANDARDS.md` | Coding conventions, SOLID principles, patterns |
| `TESTING.md` | Test strategy, scenarios, evaluation harness |
| `SECURITY.md` | Auth, data protection, medical liability considerations |
| `DEPLOYMENT.md` | Infrastructure, CI/CD, monitoring |
| `CORPUS.md` | Dataset inventory, categorization, dedup strategy |

---

## Quick Summary

- **Frontend:** Next.js 14 (App Router) + TypeScript
- **Backend:** FastAPI (Python 3.11+)
- **Vector DB:** Qdrant
- **LLM:** Claude API (claude-sonnet-4-20250514)
- **Embeddings:** OpenAI text-embedding-3-large
- **Reranker:** Cohere Rerank v3
- **Retrieval:** Hybrid BM25 + Vector + Reranker
- **Verification:** NLI-based citation entailment (DeBERTa-v3)
- **Database:** PostgreSQL (users, sessions, feedback)
- **Cache:** Redis
- **Deployment:** Vercel (frontend) + Koyeb (backend) + Qdrant Cloud

---

## The One Thing To Internalize

> **The ingestion pipeline is the product. The LLM is just the interface.**
>
> If chunks are wrong, metadata is wrong, or parsing is broken — no amount of prompt engineering will save the product. 40% of total effort goes to Phase 1 (Parsing & Ingestion).

---

## Domain Coverage

| Domain | Sources |
|--------|---------|
| Medical Reference | Harrison's, Davidson's, Kumar & Clark, Oxford Handbooks |
| Emergency Medicine | Oxford Handbook of Emergency Medicine |
| Cardiology | Goldberger's ECG, Hampton's 150 ECG Cases |
| Pharmacology | Oxford Handbook of Practical Drug Therapy |
| Fitness & Strength | NASM, ACE, ACSM, NSCA (3rd & 4th ed.) |
| Training Programs | Jeff Nippard, Dr. Mike Israetel, Lyle McDonald |
| Sports Nutrition | ISSA, various evidence-based resources |
