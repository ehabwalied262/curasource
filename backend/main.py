import re
import uvicorn
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal, AsyncGenerator
from huggingface_hub import InferenceClient
from loguru import logger
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

# Load the .env file
load_dotenv()

# --------------- Configuration ---------------
# .strip() guards against trailing newlines when secrets are pasted in HF Spaces UI
HF_TOKEN = (os.getenv("HF_TOKEN") or "").strip()
QDRANT_URL = (os.getenv("QDRANT_URL") or "http://localhost:6333").strip()
QDRANT_API_KEY = (os.getenv("QDRANT_API_KEY") or "").strip() or None
COLLECTION_NAME = (os.getenv("COLLECTION_NAME") or "curasource_chunks").strip()
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")]
PORT = int((os.getenv("PORT") or "8001").strip())
ELEVENLABS_API_KEY = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah - Mature, Reassuring
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_ANON_KEY = (os.getenv("SUPABASE_ANON_KEY") or "").strip()

if not HF_TOKEN:
    logger.error("HF_TOKEN not found! Make sure it is set in your .env file.")

# --------------- Rate Limiter ---------------
limiter = Limiter(key_func=get_remote_address)

# --------------- Prompt injection guard ---------------
_INJECTION_PATTERNS = re.compile(
    r"ignore (previous|all|prior|above) (instructions?|rules?|prompt)|"
    r"disregard (your|all|the) (instructions?|rules?|constraints?)|"
    r"you are now|act as (an? )?(un|evil|jailbreak)|"
    r"do anything now|dan mode|developer mode|jailbreak|"
    r"system prompt:|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]",
    re.IGNORECASE,
)

MAX_MESSAGE_LENGTH = 1500  # hard cap below the Pydantic max_length

def check_input(text: str) -> str:
    """Raise 400 if the input looks like a prompt injection attempt."""
    if len(text) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail="Message too long.")
    if _INJECTION_PATTERNS.search(text):
        raise HTTPException(status_code=400, detail="Input contains disallowed content.")
    return text

# --------------- Analytics / Query Logging ---------------
import httpx as _httpx

def log_query(query: str, domain: Optional[str], response_length: int, citation_count: int, endpoint: str) -> None:
    """Fire-and-forget insert into Supabase query_logs table.
    Truncates the query to 500 chars so we capture intent without storing PII walls of text."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return
    try:
        _httpx.post(
            f"{SUPABASE_URL}/rest/v1/query_logs",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={
                "query": query[:500],
                "domain": domain,
                "response_length": response_length,
                "citation_count": citation_count,
                "endpoint": endpoint,
            },
            timeout=3,
        )
    except Exception as exc:
        logger.warning(f"Query log failed (non-fatal): {exc}")

# --------------- ML Models ---------------
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Both embeddings and LLM go through HF Inference API —
# no local model downloads, no torch, tiny Docker image.
logger.info("Connecting to HF Inference API (embeddings + LLM)...")
hf_client = InferenceClient(token=HF_TOKEN)

# --------------- Pydantic Models ---------------
class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=2000)
    domain: Optional[Literal["medical", "fitness", "nutrition"]] = None
    history: List[HistoryMessage] = Field(default_factory=list)

class CitationDetail(BaseModel):
    index: int
    source_title: str
    edition: str
    chapter: str
    page_number: int
    excerpt: str
    verification_status: Literal["verified", "low_confidence", "failed"] = "verified"
    verification_score: float = 0.0

class ChatResponse(BaseModel):
    response_text: str
    citations: List[CitationDetail]
    # Keep legacy fields for backwards compat with any direct API consumers
    answer: str
    sources_used: List[dict]

# --------------- App ---------------
app = FastAPI(
    title="CuraSource API",
    description="Medical & Fitness RAG Backend",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)

# --------------- Domain Prompts ---------------
# Each domain has a gatekeeper persona. These are used as the base system prompt.
DOMAIN_SYSTEM_PROMPTS = {
    "medical": (
        "You are CuraSource Medical — an experienced attending physician and clinical educator. "
        "You speak like a trusted colleague: direct, confident, and practical. Never textbook-dry.\n\n"

        "PERSONA: You have seen thousands of cases. You know what matters clinically. "
        "You cut through complexity and get to what the clinician actually needs to know right now.\n\n"

        "STYLE RULES:\n"
        "- Open with the most important clinical point first — the diagnosis, the first-line drug, the immediate action.\n"
        "- Use **bold** for drug names, thresholds, and key clinical terms.\n"
        "- Short paragraphs (2-3 sentences). Bullet points for 3+ item lists (drugs, steps, signs).\n"
        "- Do NOT use markdown headers (###). Flow naturally between points.\n"
        "- Do NOT include a Sources section — citations are handled separately by the app.\n"
        "- Reference facts inline as [Source N] matching the source numbers in the context.\n\n"

        "CONTENT RULES:\n"
        "- Only use information from the provided context. Never invent facts or drug doses.\n"
        "- If the context lacks key information, say so: 'From what I have in the library...'\n"
        "- For management questions: cover (1) Classification/Assessment, (2) First-line treatment with targets, "
        "(3) Escalation/alternatives, (4) Monitoring parameters. Include specific thresholds (MAP ≥65, lactate, SpO₂, etc.).\n"
        "- For simple factual questions: 150-250 words. For management/protocol questions: 300-500 words. "
        "Let clinical completeness — not a word count — determine length.\n"
        "- End with a brief clinical pearl or safety note when appropriate."
    ),

    "fitness": (
        "You are CuraSource Fitness — a certified strength & conditioning coach and exercise scientist. "
        "You speak like a knowledgeable coach who genuinely cares about the client's progress and safety.\n\n"

        "PERSONA: You have trained athletes, beginners, and everyone in between. "
        "You give precise, actionable guidance — not generic advice.\n\n"

        "STYLE RULES:\n"
        "- Open with the core recommendation immediately — exercise selection, training principle, or answer.\n"
        "- Use **bold** for exercise names, key principles, and numbers (sets, reps, loads).\n"
        "- Short paragraphs (2-3 sentences). Bullet points for exercise lists or step-by-step progressions.\n"
        "- Do NOT use markdown headers (###). Flow naturally between points.\n"
        "- Do NOT include a Sources section — citations are handled separately by the app.\n"
        "- Reference facts inline as [Source N] matching the source numbers in the context.\n\n"

        "CONTENT RULES:\n"
        "- Only use information from the provided context. Never invent protocols or numbers.\n"
        "- For program design: cover (1) Exercise Selection, (2) Sets/Reps/Load, (3) Progression strategy, "
        "(4) Safety cues or contraindications.\n"
        "- Always mention modifications for beginners or those with limitations when relevant.\n"
        "- 150-350 words. Include specific numbers (sets, reps, rest periods, percentages) whenever the context provides them.\n"
        "- End with a practical coaching tip."
    ),

    "nutrition": (
        "You are CuraSource Nutrition — a registered clinical dietitian with expertise in both sports nutrition "
        "and medical nutrition therapy. You speak with warmth and clarity.\n\n"

        "PERSONA: You translate nutritional science into practical, livable advice. "
        "You balance evidence with real-world feasibility.\n\n"

        "STYLE RULES:\n"
        "- Open with the core nutritional recommendation or answer immediately.\n"
        "- Use **bold** for key nutrients, foods, quantities, and clinical terms.\n"
        "- Short paragraphs (2-3 sentences). Bullet points for food lists or multi-step plans.\n"
        "- Do NOT use markdown headers (###). Flow naturally between points.\n"
        "- Do NOT include a Sources section — citations are handled separately by the app.\n"
        "- Reference facts inline as [Source N] matching the source numbers in the context.\n\n"

        "CONTENT RULES:\n"
        "- Only use information from the provided context. Never invent quantities or protocols.\n"
        "- For dietary recommendations: cover (1) Core Recommendation, (2) Rationale, "
        "(3) Practical Implementation with food examples, (4) Monitoring or adjustment signals.\n"
        "- Always mention interactions with medical conditions (diabetes, CKD, etc.) when relevant.\n"
        "- 150-350 words. Include specific quantities and food sources whenever the context provides them.\n"
        "- End with a practical tip for adherence."
    ),

    "default": (
        "You are CuraSource — a knowledgeable Medical and Fitness AI assistant. "
        "You speak like a brilliant colleague: warm, clear, and conversational. Never textbook-dry.\n\n"

        "STYLE RULES:\n"
        "- Start with a direct answer in 1-2 sentences.\n"
        "- Use **bold** for important terms. Short paragraphs. Bullets for 3+ item lists.\n"
        "- Do NOT use markdown headers. Do NOT include a Sources section.\n"
        "- Reference facts inline as [Source N] matching the source numbers in the context.\n\n"

        "CONTENT RULES:\n"
        "- Only use information from the provided context. Never invent facts.\n"
        "- If context is insufficient, say: 'From what I have in the library...'\n"
        "- 150-400 words depending on complexity.\n"
        "- End with a brief closing thought or clinical pearl."
    ),
}

# --------------- Helpers ---------------
def get_system_prompt(domain: Optional[str]) -> str:
    return DOMAIN_SYSTEM_PROMPTS.get(domain or "default", DOMAIN_SYSTEM_PROMPTS["default"])

def build_context_text(search_results: list) -> str:
    context = ""
    for idx, res in enumerate(search_results):
        context += f"\n--- Source {idx+1} (File: {res['source']}, Page: {res['page']}) ---\n"
        context += res["text"] + "\n"
    return context

def build_citations(search_results: list) -> List[CitationDetail]:
    citations = []
    for idx, res in enumerate(search_results):
        citations.append(CitationDetail(
            index=idx + 1,
            source_title=res["source"],
            edition="",
            chapter=res.get("chapter", ""),
            page_number=res.get("page", 0),
            excerpt=res["text"],
            verification_status="verified" if res["score"] > 0.7 else "low_confidence",
            verification_score=res["score"],
        ))
    return citations

def truncate_history(history: List[HistoryMessage], max_tokens: int = 1500) -> List[dict]:
    """Keep the most recent messages that fit within the token budget.
    Always keeps at least the last 4 messages (2 exchanges).
    Approximate: 1 token ≈ 0.75 words."""
    if not history:
        return []

    formatted = [{"role": m.role, "content": m.content} for m in history]
    # Always keep last 4 messages minimum
    minimum = formatted[-4:] if len(formatted) >= 4 else formatted

    # Walk backwards and accumulate within budget
    token_count = 0
    cutoff = len(formatted)
    for i in range(len(formatted) - 1, -1, -1):
        approx_tokens = len(formatted[i]["content"].split()) * 1.4
        if token_count + approx_tokens > max_tokens and i < len(formatted) - 4:
            cutoff = i + 1
            break
        token_count += approx_tokens

    return formatted[cutoff:]


# --------------- Search Logic ---------------
def embed(text: str) -> list:
    """Embed text via HF Inference API using the same BGE model used during ingestion."""
    response = hf_client.feature_extraction(text, model="BAAI/bge-large-en-v1.5")
    # feature_extraction returns a nested list — flatten to 1D
    vector = response[0] if isinstance(response[0], list) else response
    return vector if isinstance(vector, list) else vector.tolist()


def search_qdrant(text: str, domain_filter: Optional[str] = None, limit: int = 10) -> list:
    """Search the Qdrant vector database and return matching chunks.
    Fetches up to `limit` results. If all results are from the same subdomain,
    does a second diversity pass to broaden coverage."""
    vector = embed(text)

    query_filter = None
    if domain_filter:
        query_filter = qdrant_models.Filter(
            must=[qdrant_models.FieldCondition(
                key="domain",
                match=qdrant_models.MatchValue(value=domain_filter),
            )]
        )

    search_response = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=query_filter,
        limit=limit,
    )

    results = []
    seen_hashes = set()
    for hit in search_response.points:
        chunk_hash = hit.payload.get("chunk_hash", str(hit.id))
        if chunk_hash in seen_hashes:
            continue
        seen_hashes.add(chunk_hash)
        results.append({
            "score": round(hit.score, 3),
            "text": hit.payload.get("text_content", ""),
            "source": hit.payload.get("source_file", "Unknown"),
            "page": hit.payload.get("page_number", 0),
            "chapter": hit.payload.get("chapter", ""),
            "domain": hit.payload.get("domain", ""),
            "subdomain": hit.payload.get("subdomain", ""),
        })

    # Diversity check: if all results share the same subdomain, do a second pass
    # with that subdomain excluded to surface broader context (e.g. classification frameworks)
    if results and len(results) >= 3:
        subdomains = [r["subdomain"] for r in results if r["subdomain"]]
        if subdomains and len(set(subdomains)) == 1:
            dominant_subdomain = subdomains[0]
            logger.info(f"All results from subdomain '{dominant_subdomain}' — running diversity pass")
            diversity_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="domain",
                        match=qdrant_models.MatchValue(value=domain_filter),
                    )
                ] if domain_filter else [],
                must_not=[
                    qdrant_models.FieldCondition(
                        key="subdomain",
                        match=qdrant_models.MatchValue(value=dominant_subdomain),
                    )
                ],
            )
            diversity_response = qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=vector,
                query_filter=diversity_filter,
                limit=3,
            )
            for hit in diversity_response.points:
                chunk_hash = hit.payload.get("chunk_hash", str(hit.id))
                if chunk_hash not in seen_hashes:
                    seen_hashes.add(chunk_hash)
                    results.append({
                        "score": round(hit.score, 3),
                        "text": hit.payload.get("text_content", ""),
                        "source": hit.payload.get("source_file", "Unknown"),
                        "page": hit.payload.get("page_number", 0),
                        "chapter": hit.payload.get("chapter", ""),
                        "domain": hit.payload.get("domain", ""),
                        "subdomain": hit.payload.get("subdomain", ""),
                    })

    # Return top 7 by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:7]


# --------------- Endpoints ---------------
@app.post("/chat")
@limiter.limit("10/minute")
def chat(request: Request, req: ChatRequest):
    check_input(req.message)
    logger.info(f"Chat request: '{req.message[:80]}' [domain={req.domain}]")
    history = truncate_history(req.history)

    # 1. RETRIEVE from Qdrant
    try:
        search_results = search_qdrant(req.message, domain_filter=req.domain)
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        raise HTTPException(status_code=503, detail="Vector database unavailable. Is Qdrant running?")

    # 2. BUILD context
    context_text = build_context_text(search_results)
    system_prompt = get_system_prompt(req.domain)
    user_prompt = f"CONTEXT FROM LIBRARY:\n{context_text}\n\nUSER QUESTION: {req.message}"

    # 3. BUILD full message list with truncated history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    # 4. GENERATE via Llama 3
    logger.info("Generating response from Llama 3...")
    response_text = ""
    try:
        for message in hf_client.chat_completion(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=messages,
            max_tokens=800,
            stream=True,
        ):
            if message.choices and len(message.choices) > 0:
                token = message.choices[0].delta.content
                if token:
                    response_text += token
    except Exception as e:
        logger.error(f"Llama 3 generation failed: {e}")
        raise HTTPException(status_code=502, detail="LLM generation failed. Check HF quota or model access.")

    citations = build_citations(search_results)
    sources_used = [{"file": r["source"], "page": r.get("page", 0)} for r in search_results]

    log_query(req.message, req.domain, len(response_text), len(citations), "chat")

    return {
        "response_text": response_text,
        "citations": [c.model_dump() for c in citations],
        "answer": response_text,
        "sources_used": sources_used,
        "response_type": "answer",
    }


@app.post("/chat/stream")
@limiter.limit("10/minute")
def chat_stream(request: Request, req: ChatRequest):
    """Streaming endpoint — sends tokens via SSE as they arrive from Llama 3."""
    check_input(req.message)
    logger.info(f"Stream request: '{req.message[:80]}' [domain={req.domain}]")
    history = truncate_history(req.history)

    # RAG search + full answer
    try:
        search_results = search_qdrant(req.message, domain_filter=req.domain)
        logger.info(f"Qdrant returned {len(search_results)} results")
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        raise HTTPException(status_code=503, detail="Vector database unavailable.")

    context_text = build_context_text(search_results)
    system_prompt = get_system_prompt(req.domain)
    user_prompt = f"CONTEXT FROM LIBRARY:\n{context_text}\n\nUSER QUESTION: {req.message}"

    # Full message list with conversation history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    citations = build_citations(search_results)

    def token_generator():
        total_chars = 0
        try:
            for message in hf_client.chat_completion(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                messages=messages,
                max_tokens=800,
                stream=True,
            ):
                if message.choices and message.choices[0].delta.content:
                    token = message.choices[0].delta.content
                    total_chars += len(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # Final event with citations
            yield f"data: {json.dumps({'done': True, 'citations': [c.model_dump() for c in citations], 'response_type': 'answer'})}\n\n"
            log_query(req.message, req.domain, total_chars, len(citations), "stream")

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000)

@app.post("/tts")
@limiter.limit("5/minute")
def tts(request: Request, req: TTSRequest):
    """Proxy TTS request to ElevenLabs — keeps API key server-side."""
    if not ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_API_KEY is not set")
        raise HTTPException(status_code=503, detail="TTS not configured")

    import httpx
    logger.info(f"TTS request ({len(req.text)} chars), key starts with: {ELEVENLABS_API_KEY[:8]}...")
    try:
        resp = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": req.text[:2500],
                "model_id": "eleven_flash_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30,
        )
        logger.info(f"ElevenLabs responded with status {resp.status_code}")
        if resp.status_code == 401:
            logger.warning("ElevenLabs 401 — free tier blocked from this IP (proxy/VPN flag). TTS unavailable.")
            raise HTTPException(status_code=503, detail="TTS unavailable: ElevenLabs free tier is blocked on this deployment. Upgrade to a paid plan.")
        if resp.status_code != 200:
            logger.error(f"ElevenLabs error {resp.status_code}: {resp.text[:500]}")
            raise HTTPException(status_code=502, detail=f"TTS failed: {resp.status_code}")

        return StreamingResponse(
            iter([resp.content]),
            media_type="audio/mpeg",
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="TTS request timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    """Health check for deployment platforms."""
    qdrant_ok = False
    try:
        qdrant.get_collections()  # just a ping
        qdrant_ok = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "vector_db": "connected" if qdrant_ok else "disconnected",
        "llm": "meta-llama/Meta-Llama-3-8B-Instruct",
    }


if __name__ == "__main__":
    logger.info(f"CuraSource API starting on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
