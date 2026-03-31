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
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

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
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=2000)
    domain: Optional[Literal["medical", "fitness", "nutrition"]] = None

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

# --------------- Search Logic ---------------
def embed(text: str) -> list:
    """Embed text via HF Inference API using the same BGE model used during ingestion."""
    response = hf_client.feature_extraction(text, model="BAAI/bge-large-en-v1.5")
    # feature_extraction returns a nested list — flatten to 1D
    vector = response[0] if isinstance(response[0], list) else response
    return vector if isinstance(vector, list) else vector.tolist()


def search_qdrant(text: str, domain_filter: Optional[str] = None, limit: int = 3) -> list:
    """Search the Qdrant vector database and return matching chunks."""
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
    for hit in search_response.points:
        results.append({
            "score": round(hit.score, 3),
            "text": hit.payload.get("text_content", ""),
            "source": hit.payload.get("source_file", "Unknown"),
            "page": hit.payload.get("page_number", 0),
            "chapter": hit.payload.get("chapter", ""),
            "domain": hit.payload.get("domain", ""),
        })
    return results

# --------------- Endpoints ---------------
@app.post("/chat")
def chat(req: ChatRequest):
    logger.info(f"Chat request: '{req.message}' [domain={req.domain}]")

    # 1. RETRIEVE from Qdrant
    try:
        search_results = search_qdrant(req.message, domain_filter=req.domain, limit=3)
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        raise HTTPException(status_code=503, detail="Vector database unavailable. Is Qdrant running?")

    # 2. BUILD context for the LLM
    context_text = ""
    for idx, res in enumerate(search_results):
        context_text += f"\n--- Source {idx+1} (File: {res['source']}, Page: {res['page']}) ---\n"
        context_text += res["text"] + "\n"

    system_prompt = (
        "You are CuraSource, a professional Medical and Fitness Assistant. "
        "Use ONLY the provided context below to answer the user's question. "
        "If the answer isn't in the context, say you don't know based on the current library. "
        "Always cite your sources (File Name and Page Number)."
    )
    user_prompt = f"CONTEXT FROM LIBRARY:\n{context_text}\n\nUSER QUESTION: {req.message}"

    # 3. GENERATE via Llama 3
    logger.info("Generating response from Llama 3...")
    response_text = ""
    try:
        for message in hf_client.chat_completion(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
            stream=True,
        ):
            if message.choices and len(message.choices) > 0:
                token = message.choices[0].delta.content
                if token:
                    response_text += token
    except Exception as e:
        logger.error(f"Llama 3 generation failed: {e}")
        raise HTTPException(status_code=502, detail="LLM generation failed. Check HF quota or model access.")

    # 4. FORMAT citations for the frontend
    citations = []
    sources_used = []
    for idx, res in enumerate(search_results):
        citations.append(CitationDetail(
            index=idx + 1,
            source_title=res["source"],
            edition="",
            chapter=res.get("chapter", ""),
            page_number=res.get("page", 0),
            excerpt=res["text"][:300],
            verification_status="verified" if res["score"] > 0.7 else "low_confidence",
            verification_score=res["score"],
        ))
        sources_used.append({"file": res["source"], "page": res.get("page", 0)})

    return {
        "response_text": response_text,
        "citations": [c.model_dump() for c in citations],
        "answer": response_text,
        "sources_used": sources_used,
    }


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Streaming endpoint — sends tokens via SSE as they arrive from Llama 3."""
    logger.info(f"Stream request: '{req.message}' [domain={req.domain}]")

    # 1. RETRIEVE
    try:
        search_results = search_qdrant(req.message, domain_filter=req.domain, limit=3)
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        raise HTTPException(status_code=503, detail="Vector database unavailable.")

    # 2. BUILD context
    context_text = ""
    for idx, res in enumerate(search_results):
        context_text += f"\n--- Source {idx+1} (File: {res['source']}, Page: {res['page']}) ---\n"
        context_text += res["text"] + "\n"

    system_prompt = (
        "You are CuraSource, a professional Medical and Fitness Assistant. "
        "Use ONLY the provided context below to answer the user's question. "
        "If the answer isn't in the context, say you don't know based on the current library. "
        "Always cite your sources (File Name and Page Number)."
    )
    user_prompt = f"CONTEXT FROM LIBRARY:\n{context_text}\n\nUSER QUESTION: {req.message}"

    # 3. Build citations upfront (sent at end)
    citations = []
    for idx, res in enumerate(search_results):
        citations.append(CitationDetail(
            index=idx + 1,
            source_title=res["source"],
            edition="",
            chapter=res.get("chapter", ""),
            page_number=res.get("page", 0),
            excerpt=res["text"][:300],
            verification_status="verified" if res["score"] > 0.7 else "low_confidence",
            verification_score=res["score"],
        ))

    def token_generator():
        try:
            for message in hf_client.chat_completion(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
                stream=True,
            ):
                if message.choices and message.choices[0].delta.content:
                    token = message.choices[0].delta.content
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # Final event with citations
            yield f"data: {json.dumps({'done': True, 'citations': [c.model_dump() for c in citations]})}\n\n"

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
                "Authorization": f"Bearer {ELEVENLABS_API_KEY}",
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
