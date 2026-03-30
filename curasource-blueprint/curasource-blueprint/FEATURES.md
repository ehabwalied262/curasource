# FEATURES.md — CuraSource Feature Specification

---

## MVP Features (Launch)

### F1 — Conversational Query Interface
**What:** A chat-style interface where users type questions and receive AI-generated answers grounded in the corpus.

**Behavior:**
- User types a question in natural language
- System streams the response in real-time (SSE)
- Response includes inline citation markers `[1]`, `[2]`
- Citations panel below response shows full source details
- Each citation shows: Title, Edition, Chapter, Page Number, relevant excerpt

**Edge Cases:**
- Query outside corpus scope → "This topic isn't covered in the available sources. Here's what's closest..."
- No relevant chunks found → "I couldn't find reliable information on this in the sources. Please consult a medical professional."
- Conflicting information across editions → "Note: Harrison's 21st Ed recommends X, while the 19th Ed recommends Y. The 21st Ed is more recent."

---

### F2 — Citation Verification Indicators
**What:** Visual trust signals on every citation showing verification status.

**States:**
- ✅ **Verified** — NLI entailment score > 0.75. Shown normally.
- ⚠️ **Low Confidence** — Score 0.50–0.75. Yellow indicator + tooltip: "This citation matched with lower confidence. Verify manually."
- ❌ **Unverified** — Score < 0.50. Dropped from response entirely. Not shown.

**UI:** Small colored dot/badge next to each citation number.

---

### F3 — Source Viewer
**What:** Click any citation to open the source — shows the exact page from the original PDF (or table/figure if applicable).

**Behavior:**
- Click `[1]` → slide-in panel (or modal) showing:
  - PDF rendered at the cited page (via react-pdf)
  - Highlighted section if possible
  - Full source metadata: Title, Authors, Edition, Year
  - "View full source" button → source browser
- For tables: render the extracted markdown table, not the PDF
- For figure references: show the figure image + caption

---

### F4 — Domain Filtering
**What:** Let users scope queries to a specific domain before asking.

**Options:**
- 🏥 Medical (default: all medical sources)
- 💪 Fitness & Training (certification textbooks + programs)
- 🔀 Both (cross-domain, e.g., "Can a diabetic do HIIT?")

**UI:** Toggle group above the chat input. Persists per session.

---

### F5 — Session History
**What:** Users can access previous conversations.

**Behavior:**
- Sidebar lists past sessions (title = first query, truncated)
- Click to restore full conversation with all citations
- Sessions tied to user account
- Delete session option

---

### F6 — Corpus Browser
**What:** Browse all available sources without querying — explore what's in the system.

**UI:**
- Grid of source cards, filterable by domain
- Each card: Title, Authors, Edition, Year, Domain tag, Chunk count
- Click → source detail page with table of contents (if extractable)
- Search within corpus metadata (not full-text)

---

### F7 — User Authentication
**What:** Account system for session persistence and rate limiting.

**Features:**
- Email/password registration + login
- Google OAuth
- Password reset flow
- Account page (usage stats, session history)

**Tiers (MVP):**
- Free: 10 queries/day
- Pro: 100 queries/day (future)

---

### F8 — Query Feedback
**What:** Users can rate responses and flag problematic citations.

**UI:**
- 👍 / 👎 below every response
- On 👎: dropdown — "Wrong information", "Bad citation", "Incomplete", "Other" + optional text
- Flag individual citations: small flag icon per citation → "This citation doesn't support the claim"
- Feedback stored in PostgreSQL for evaluation harness

---

## V2 Features (Post-Launch)

### F9 — Multi-Turn Medical Context
**What:** System remembers clinical context within a session.

**Example:**
- User: "What's the first-line treatment for T2DM?"
- User: "What about if the patient also has CKD stage 3?"
- System understands "the patient" and "T2DM" from context and adjusts answer accordingly.

---

### F10 — Figure & Image Search
**What:** Search specifically for clinical images, ECG strips, diagrams.

**Example:**
- "Show me ECG examples of atrial fibrillation"
- Returns: figure references with images from Goldberger's, Hampton's
- Images shown with caption, page reference, and textual description

---

### F11 — Comparison Mode
**What:** Side-by-side comparison of what different sources say about the same topic.

**Example:**
- "Compare NASM vs ACE on progressive overload principles"
- Two-column layout: NASM excerpt | ACE excerpt | key differences highlighted

---

### F12 — Abstract RAG (New Source Ingestion)
**What:** Add new documents to the corpus without re-ingesting everything.

**For operators:**
- Upload PDF → automatic domain tagging suggestion → manual confirm → ingest
- New chunks added to Qdrant and BM25 index incrementally
- No downtime

---

### F13 — Drug Interaction Checker
**What:** Structured tool for checking drug interactions, powered by pharmacy tables in corpus.

**Example:**
- Input: Drug A + Drug B → System queries pharmacy table chunks → Returns interaction severity + recommendation + citation

---

## V3 Features (Long-Term)

### F14 — Mobile App
- React Native (Expo)
- Same feature set as web
- Offline: cache last 5 sessions

### F15 — API Access
- REST API for developers
- Use CuraSource retrieval + citation in their own applications
- API key management, usage tracking, billing

### F16 — Professional Mode
- Verified medical professional accounts (credential upload)
- Unlocked: prescription dosing details, full clinical algorithms
- Enhanced rate limits

### F17 — Fine-Tuned Domain Embeddings
- Once enough query data is collected (10k+ queries per domain)
- Fine-tune embedding model on domain-specific query-document pairs
- Expected: 5–15% retrieval quality improvement

### F18 — Multimodal ECG Interpretation
- During ingestion: feed ECG images to vision model, generate clinical descriptions
- At query time: ECG images are searchable by clinical findings
- Tagged as AI-generated, not author-written
