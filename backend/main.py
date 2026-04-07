import uvicorn
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, AsyncGenerator
from huggingface_hub import InferenceClient
from loguru import logger
from dotenv import load_dotenv
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

if not HF_TOKEN:
    logger.error("HF_TOKEN not found! Make sure it is set in your .env file.")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Triage system prompt — used for the first quick LLM call to decide: ask or search?
TRIAGE_PROMPTS = {
    "medical": (
        "You are a medical triage assistant. Your ONLY job: decide to ask ALL missing questions at once, or search.\n\n"

        "OUTPUT FORMAT — output EXACTLY one of these two options. No preamble, no reasoning, no explanation:\n\n"

        "Option 1 — To search the database:\n"
        "[SEARCH_RAG]\n"
        "<expanded search query>\n\n"

        "Option 2 — Ask ALL missing questions in ONE message:\n"
        "<questions only — start directly with 'Before I search' or 'Quick questions:'>\n\n"

        "STEP 1 — Read the question carefully and note what is ALREADY provided:\n"
        "- Diagnosis or condition type already named? → do NOT ask for it\n"
        "- Vitals or measurements already given (BP, HR, SpO₂, size, weight)? → do NOT ask for them\n"
        "- Treatments already mentioned (drugs given, creams tried, procedures done)? → do NOT ask for them\n"
        "- Patient demographics already given (age, sex, comorbidities)? → do NOT ask for them\n\n"

        "STEP 2 — Decide:\n"
        "- If ALL key context is already in the question → Option 1 (search)\n"
        "- If SOME context is missing AND it would change management → Option 2 (ask ONLY for what is missing)\n"
        "- ONLY on FIRST turn. History has ANY assistant message → ALWAYS Option 1.\n\n"

        "EXAMPLES:\n"
        "'How do I treat a dark pimple?' → missing: skin type, size, prior treatment "
        "→ ask: 'Before I search — what skin type (oily, dry, sensitive), how large, and has anything been tried?'\n\n"

        "'How do I treat a dark pimple on sensitive skin?' → skin type already given "
        "→ ask: 'Before I search — how large is it, and has anything been tried already?'\n\n"

        "'Manage hypotension in a septic patient, BP 80/50, already on fluids' → shock type + BP + prior tx all given "
        "→ [SEARCH_RAG]\nmanage septic shock hypotension BP 80/50 refractory to fluids\n\n"

        "'Manage hypotension in ICU' → nothing given "
        "→ ask: 'Before I search — what type of shock (septic, cardiogenic, hypovolemic), current BP, and what has been given?'\n\n"

        "'What is the mechanism of metformin?' → educational, no context needed "
        "→ [SEARCH_RAG]\nmechanism of metformin\n\n"

        "CRITICAL: Ask ONLY what is relevant to THIS topic. "
        "Do NOT ask about shock/BP for non-cardiovascular questions. "
        "Do NOT re-ask anything the user already provided. "
        "Do NOT output any reasoning or preamble — just the questions or [SEARCH_RAG]."
    ),

    "fitness": (
        "You are a fitness triage assistant. Decide: ask ALL missing questions at once, or search.\n\n"

        "OUTPUT FORMAT — no preamble, no reasoning:\n"
        "Option 1 — Search: [SEARCH_RAG]\n<query>\n"
        "Option 2 — Ask ONLY the missing questions in ONE message\n\n"

        "STEP 1 — Read the question and note what is ALREADY provided:\n"
        "- Experience level already stated (beginner, advanced)? → do NOT ask\n"
        "- Goal already stated (fat loss, hypertrophy, strength)? → do NOT ask\n"
        "- Injuries or limitations already mentioned? → do NOT ask\n"
        "- Equipment or schedule already given? → do NOT ask\n\n"

        "STEP 2 — Decide:\n"
        "- All key context given → Option 1 (search)\n"
        "- Some context missing AND it changes the program → Option 2 (ask ONLY what is missing)\n"
        "- History has ANY assistant message → ALWAYS Option 1\n\n"

        "EXAMPLES:\n"
        "'Design me a workout program' → missing all context "
        "→ ask: 'Quick questions: experience level (beginner/intermediate/advanced), "
        "main goal (strength, hypertrophy, fat loss), and any injuries or limitations?'\n\n"

        "'Design a hypertrophy program for an intermediate lifter' → goal + level given "
        "→ ask: 'Any injuries or limitations I should work around?'\n\n"

        "'Design a hypertrophy program for an intermediate lifter, no injuries' → all context given "
        "→ [SEARCH_RAG]\nhypertrophy program intermediate lifter\n\n"

        "Educational/conceptual questions → always [SEARCH_RAG]. "
        "Do NOT re-ask anything the user already provided."
    ),

    "nutrition": (
        "You are a nutrition triage assistant. Decide: ask ALL missing questions at once, or search.\n\n"

        "OUTPUT FORMAT — no preamble, no reasoning:\n"
        "Option 1 — Search: [SEARCH_RAG]\n<query>\n"
        "Option 2 — Ask ONLY the missing questions in ONE message\n\n"

        "STEP 1 — Read the question and note what is ALREADY provided:\n"
        "- Medical condition already stated (diabetes, CKD, hypertension)? → do NOT ask\n"
        "- Goal already stated (weight loss, muscle gain, managing condition)? → do NOT ask\n"
        "- Allergies or intolerances already mentioned? → do NOT ask\n\n"

        "STEP 2 — Decide:\n"
        "- All key context given → Option 1 (search)\n"
        "- Some context missing AND it changes the recommendation → Option 2 (ask ONLY what is missing)\n"
        "- History has ANY assistant message → ALWAYS Option 1\n\n"

        "EXAMPLES:\n"
        "'How should I improve my diet?' → missing all context "
        "→ ask: 'A couple of quick questions: any medical conditions (diabetes, high cholesterol), "
        "food allergies, and your main goal (weight loss, muscle gain, managing a condition)?'\n\n"

        "'How should a diabetic improve their diet for weight loss?' → condition + goal given "
        "→ ask: 'Any food allergies or intolerances I should know about?'\n\n"

        "'Nutrition plan for a diabetic trying to lose weight, no allergies' → all context given "
        "→ [SEARCH_RAG]\ndiabetic weight loss nutrition plan\n\n"

        "Educational/conceptual questions → always [SEARCH_RAG]. "
        "Do NOT re-ask anything the user already provided."
    ),

    "default": (
        "You are a triage assistant. Your ONLY job is to decide whether to search the database or ask a question.\n\n"
        "DECISION A — Search: Output [SEARCH_RAG] on line 1, then a search query on line 2.\n"
        "DECISION B — Clarify: Ask 1-2 focused questions if critical context is missing.\n"
        "Default to DECISION A when unsure."
    ),
}

# --------------- Helpers ---------------
def get_system_prompt(domain: Optional[str]) -> str:
    return DOMAIN_SYSTEM_PROMPTS.get(domain or "default", DOMAIN_SYSTEM_PROMPTS["default"])

def get_triage_prompt(domain: Optional[str]) -> str:
    return TRIAGE_PROMPTS.get(domain or "default", TRIAGE_PROMPTS["default"])

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

def count_clarification_rounds(history: List[dict]) -> int:
    """Count how many assistant clarifying turns have already happened."""
    return sum(1 for m in history if m["role"] == "assistant")


def extract_and_calculate_map(text: str) -> Optional[str]:
    """Detect BP values like '90/40' or '120/80' and calculate MAP."""
    import re
    match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})', text)
    if match:
        sbp, dbp = int(match.group(1)), int(match.group(2))
        if 40 <= sbp <= 250 and 20 <= dbp <= 150:
            map_val = round(dbp + (sbp - dbp) / 3)
            return f"(MAP ~{map_val} mmHg)"
    return None


def strip_cot_preamble(text: str) -> str:
    """Remove chain-of-thought reasoning lines that Llama 8B sometimes leaks before its answer.
    Keeps only the lines that form the actual question or [SEARCH_RAG] output."""
    import re
    cot_starters = (
        r"^since this is",
        r"^this is (a|the) first",
        r"^i('ll| will) ask",
        r"^i('m| am) going to",
        r"^let me",
        r"^i need to",
        r"^based on",
        r"^the question (is|asks)",
        r"^it('s| is) a management",
        r"^i'll search",
        r"^i will search",
    )
    pattern = re.compile("|".join(cot_starters), re.IGNORECASE)
    lines = text.split("\n")
    filtered = [line for line in lines if not pattern.match(line.strip())]
    result = "\n".join(filtered).strip()
    return result if result else text


def looks_like_follow_up_answer(message: str) -> bool:
    """Return True if the message reads like an answer to a prior clarification
    rather than a new standalone question.

    A standalone question typically starts with a question word or ends with '?'.
    A follow-up answer is descriptive (e.g. 'sensitive, medium, no creams').
    """
    msg = message.strip().lower()
    question_starters = (
        "how", "what", "when", "why", "which", "who",
        "should", "can ", "could", "does", "is ", "are ",
        "do ", "will ", "would ", "please", "explain",
    )
    has_question_mark = "?" in message
    starts_with_question = any(msg.startswith(q) for q in question_starters)
    return not has_question_mark and not starts_with_question


def build_search_query_from_history(history: List[dict], message: str) -> str:
    """Synthesize a focused search query anchored to the original question.

    Uses the first user message as the core topic, then appends only
    meaningful clinical context (filters out 'I don't know' etc.).
    """
    skip_phrases = ["i don't know", "i dont know", "not sure", "no idea",
                    "you tell me", "just answer", "skip", "i don't", "idk"]

    user_messages = [m["content"] for m in history if m["role"] == "user"]
    user_messages.append(message)

    # First user message = original question (anchor)
    original_question = user_messages[0] if user_messages else message

    # Subsequent messages = clinical context gathered (skip non-answers)
    clinical_context = []
    for msg in user_messages[1:]:
        if not any(phrase in msg.lower() for phrase in skip_phrases) and len(msg.strip()) > 2:
            clinical_context.append(msg.strip())

    # Auto-calculate MAP from any BP values in the conversation
    all_text = " ".join(user_messages)
    map_annotation = extract_and_calculate_map(all_text)

    if clinical_context:
        query = f"{original_question} {' '.join(clinical_context)}"
        if map_annotation:
            query += f" {map_annotation}"
    else:
        query = original_question

    return query[:400]


def triage_request(
    domain: Optional[str],
    history: List[dict],
    message: str,
) -> tuple[bool, str]:
    """
    Call the LLM with the triage prompt to decide: search or clarify?
    Returns (should_search: bool, search_query_or_clarification: str)

    Hard limit: after 2 clarification rounds, always search.
    Also forces search if user says 'I don't know' or similar.
    """
    # Hard limit: max 1 clarifying turn, then always search
    # (triage prompts now ask all questions at once in the first turn)
    clarification_rounds = count_clarification_rounds(history)
    if clarification_rounds >= 1:
        query = build_search_query_from_history(history, message)
        logger.info(f"Triage → FORCE SEARCH (limit reached) | Query: {query[:80]}")
        return True, query

    # If history is missing (e.g. lost on reconnect) but the message reads like
    # a follow-up answer (no "?", no question word), search with it as context.
    if not history and looks_like_follow_up_answer(message):
        query = message
        logger.info(f"Triage → FORCE SEARCH (looks like follow-up with no history) | Query: {query[:80]}")
        return True, query

    # If user says they don't know, proceed with what we have
    dont_know_phrases = ["i don't know", "i dont know", "not sure", "no idea", "you tell me", "just answer", "skip"]
    if any(phrase in message.lower() for phrase in dont_know_phrases):
        query = build_search_query_from_history(history, message)
        logger.info(f"Triage → FORCE SEARCH (user unsure) | Query: {query[:80]}")
        return True, query

    triage_prompt = get_triage_prompt(domain)

    # Inject the original question as context so the model can ask topic-relevant questions.
    # When there's history, the original question is the first user message.
    original_question = history[0]["content"] if history else message
    triage_context = triage_prompt
    if history:
        triage_context += (
            f"\n\nThe original question being discussed is: \"{original_question}\". "
            "Ask ONLY questions directly relevant to that specific topic."
        )

    messages = [{"role": "system", "content": triage_context}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        response = hf_client.chat_completion(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=messages,
            max_tokens=120,
            stream=False,
        )
        text = response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Triage call failed ({e}), defaulting to search")
        return True, message  # safe default: search with original message

    # Llama 3 sometimes adds preamble before the tag — search anywhere in the response
    if "[SEARCH_RAG]" in text:
        # Extract query: everything after the [SEARCH_RAG] tag on the next line
        after_tag = text.split("[SEARCH_RAG]", 1)[1].strip()
        # Take the first non-empty line as the query
        query_lines = [l.strip() for l in after_tag.split("\n") if l.strip()]
        # Strip surrounding quotes if present
        query = query_lines[0].strip('"\'') if query_lines else message
        logger.info(f"Triage → SEARCH | Query: {query}")
        return True, query

    # Strip any chain-of-thought preamble the model leaked before the actual question
    cleaned = strip_cot_preamble(text)
    logger.info(f"Triage → CLARIFY | Response: {cleaned[:80]}...")
    return False, cleaned


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
def chat(req: ChatRequest):
    logger.info(f"Chat request: '{req.message}' [domain={req.domain}]")
    history = truncate_history(req.history)

    # Triage: decide whether to search or clarify
    should_search, query_or_clarification = triage_request(req.domain, history, req.message)

    if not should_search:
        # Return the clarifying question directly — no RAG needed
        return {
            "response_text": query_or_clarification,
            "citations": [],
            "answer": query_or_clarification,
            "sources_used": [],
            "response_type": "clarification",
        }

    # 1. RETRIEVE from Qdrant using the rewritten query
    try:
        search_results = search_qdrant(query_or_clarification, domain_filter=req.domain)
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

    return {
        "response_text": response_text,
        "citations": [c.model_dump() for c in citations],
        "answer": response_text,
        "sources_used": sources_used,
        "response_type": "answer",
    }


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Streaming endpoint — sends tokens via SSE as they arrive from Llama 3."""
    logger.info(f"Stream request: '{req.message}' [domain={req.domain}]")
    history = truncate_history(req.history)

    # Phase A: Triage — decide whether to search or ask a clarifying question
    should_search, query_or_clarification = triage_request(req.domain, history, req.message)

    if not should_search:
        # Stream the clarifying question directly — no RAG, no embedding
        def clarification_generator():
            # Stream word by word so the typing animation works
            words = query_or_clarification.split(" ")
            for i, word in enumerate(words):
                token = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True, 'citations': [], 'response_type': 'clarification'})}\n\n"

        return StreamingResponse(clarification_generator(), media_type="text/event-stream")

    # Phase B: RAG search + full answer
    try:
        search_results = search_qdrant(query_or_clarification, domain_filter=req.domain)
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
        try:
            for message in hf_client.chat_completion(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                messages=messages,
                max_tokens=800,
                stream=True,
            ):
                if message.choices and message.choices[0].delta.content:
                    token = message.choices[0].delta.content
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # Final event with citations
            yield f"data: {json.dumps({'done': True, 'citations': [c.model_dump() for c in citations], 'response_type': 'answer'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000)

@app.post("/tts")
def tts(req: TTSRequest):
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
