# API_SPEC.md — CuraSource API Specification

Base URL: `https://api.curasource.com/v1`
All requests require: `Authorization: Bearer <clerk_jwt>`
All responses: `Content-Type: application/json`

---

## POST /query

Submit a question. Returns a streamed or non-streamed response with citations.

### Request
```json
{
  "query": "What is the first-line treatment for type 2 diabetes?",
  "domain": ["medical"],
  "session_id": "sess_abc123",
  "stream": true
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| query | string | ✅ | — | 3–1000 chars |
| domain | array[string] | ❌ | ["medical","fitness"] | Values: "medical", "fitness" |
| session_id | string | ❌ | null | Creates new session if null |
| stream | boolean | ❌ | true | — |

### Response (non-streamed)
```json
{
  "query_id": "qry_xyz789",
  "session_id": "sess_abc123",
  "response_text": "The first-line pharmacological treatment for type 2 diabetes mellitus is metformin [1], unless contraindicated by renal impairment [2].",
  "citations": [
    {
      "index": 1,
      "source_title": "Harrison's Principles of Internal Medicine",
      "edition": "21st",
      "chapter": "Chapter 396: Diabetes Mellitus",
      "page_number": 2855,
      "excerpt": "Metformin is the preferred initial pharmacologic agent for most patients with type 2 diabetes...",
      "verification_status": "verified",
      "verification_score": 0.94,
      "content_type": "prose",
      "image_path": null
    },
    {
      "index": 2,
      "source_title": "Davidson's Principles and Practice of Medicine",
      "edition": "24th",
      "chapter": "Chapter 21: Diabetes Mellitus",
      "page_number": 712,
      "excerpt": "Dose reduction is required when eGFR falls below 45 mL/min...",
      "verification_status": "low_confidence",
      "verification_score": 0.62,
      "content_type": "prose",
      "image_path": null
    }
  ],
  "domain_tags_used": ["medical"],
  "chunks_retrieved": 5,
  "latency_ms": 1840,
  "out_of_scope": false
}
```

### Streamed Response (SSE)
```
event: delta
data: {"text": "The first-line "}

event: delta
data: {"text": "pharmacological treatment "}

event: citation_found
data: {"index": 1, "source_title": "Harrison's...", "page_number": 2855}

event: delta
data: {"text": "for type 2 diabetes "}

event: done
data: {"query_id": "qry_xyz789", "citations": [...], "latency_ms": 1840}
```

### Error Responses
```json
// 400 — Invalid request
{"error": "validation_error", "detail": "query must be at least 3 characters"}

// 401 — Unauthenticated
{"error": "unauthorized", "detail": "Invalid or expired token"}

// 422 — Out of scope
{"error": "out_of_scope", "detail": "Query not covered by available sources", "closest_match": "..."}

// 429 — Rate limited
{"error": "rate_limit_exceeded", "detail": "Free tier: 10 queries/day. Resets at midnight UTC.", "reset_at": "2025-01-15T00:00:00Z"}

// 503 — Retrieval unavailable
{"error": "retrieval_failed", "detail": "Search temporarily unavailable. Please try again."}
```

---

## GET /sessions

List user's chat sessions.

### Response
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "title": "What is the first-line treatment for T2DM?",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:45:00Z",
      "query_count": 5
    }
  ],
  "total": 12,
  "page": 1
}
```

---

## GET /sessions/{session_id}

Get full session history with all queries and responses.

### Response
```json
{
  "session_id": "sess_abc123",
  "created_at": "2025-01-15T10:30:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What is the first-line treatment for T2DM?",
      "timestamp": "2025-01-15T10:30:05Z"
    },
    {
      "role": "assistant",
      "query_id": "qry_xyz789",
      "content": "The first-line pharmacological treatment...",
      "citations": [...],
      "timestamp": "2025-01-15T10:30:07Z"
    }
  ]
}
```

---

## DELETE /sessions/{session_id}

Delete a session and all its queries.

### Response
```json
{"deleted": true, "session_id": "sess_abc123"}
```

---

## GET /sources

Browse available corpus sources.

### Query Params
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| domain | string | all | Filter: "medical" or "fitness" |
| page | int | 1 | Pagination |
| per_page | int | 20 | Max 50 |

### Response
```json
{
  "sources": [
    {
      "source_id": "src_harrison21",
      "title": "Harrison's Principles of Internal Medicine",
      "edition": "21st",
      "publication_year": 2022,
      "authors": ["Loscalzo J", "Fauci AS"],
      "domain": "medical",
      "subdomain": "internal_medicine",
      "chunk_count": 40234,
      "has_tables": true,
      "has_figures": true
    }
  ],
  "total": 47,
  "page": 1
}
```

---

## GET /sources/{source_id}/chunks

Get chunks from a specific source (for source browser).

### Query Params
| Param | Type | Description |
|-------|------|-------------|
| page_number | int | Filter by PDF page |
| content_type | string | Filter: "prose", "table", "figure_reference" |
| search | string | Search within this source |

---

## POST /feedback

Submit feedback on a query response.

### Request
```json
{
  "query_id": "qry_xyz789",
  "rating": "down",
  "reason": "bad_citation",
  "flagged_citation_indices": [2],
  "comment": "Citation 2 doesn't actually support the claim about renal dosing."
}
```

| Field | Type | Values |
|-------|------|--------|
| rating | string | "up", "down" |
| reason | string | "wrong_info", "bad_citation", "incomplete", "out_of_scope", "other" |
| flagged_citation_indices | array[int] | Citation indices the user is flagging |
| comment | string | Optional free text |

### Response
```json
{"feedback_id": "fb_abc", "received": true}
```

---

## GET /usage

Get current user's usage stats.

### Response
```json
{
  "tier": "free",
  "queries_today": 7,
  "queries_limit_daily": 10,
  "queries_remaining_today": 3,
  "reset_at": "2025-01-16T00:00:00Z",
  "total_queries_all_time": 143
}
```

---

## Webhook Events (from Clerk)

CuraSource listens to Clerk webhooks at `POST /webhooks/clerk`:

| Event | Action |
|-------|--------|
| `user.created` | Create user record in PostgreSQL |
| `user.deleted` | Soft-delete user + anonymize query logs |
| `session.ended` | Log session end time |
