import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from huggingface_hub import InferenceClient
from loguru import logger
from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# --------------- Configuration ---------------
HF_TOKEN = os.getenv("HF_TOKEN")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "curasource_chunks")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
PORT = int(os.getenv("PORT", "8001"))

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
