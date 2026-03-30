import uuid
import os
from typing import List
from loguru import logger
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

load_dotenv()

# Import our Chunk model from the chunker we built
from ingestion.chunkers.structure_chunker import Chunk

_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
_QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
_DEFAULT_COLLECTION = os.getenv("COLLECTION_NAME", "curasource_chunks")

class QdrantEmbedder:
    def __init__(self, collection_name: str = _DEFAULT_COLLECTION):
        self.collection_name = collection_name
        self.qdrant = QdrantClient(url=_QDRANT_URL, api_key=_QDRANT_API_KEY)
        
        logger.info("Loading BAAI/bge-large-en-v1.5 model into memory...")
        logger.info("(This might take a minute on the first run as it downloads the model weights)")
        self.model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        
        self._ensure_collection()

    def _ensure_collection(self):
        """Creates the Qdrant collection if it doesn't already exist."""
        if not self.qdrant.collection_exists(self.collection_name):
            logger.info(f"Creating new Qdrant collection: {self.collection_name}")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1024,  # BGE-large outputs exactly 1024 dimensions
                    distance=Distance.COSINE # Best practice for text similarity
                )
            )
        else:
            logger.info(f"Connected to existing collection: {self.collection_name}")

    def embed_and_upload(self, chunks: List[Chunk], batch_size: int = 50):
        """Converts chunks into math vectors and saves them to Qdrant."""
        if not chunks:
            logger.warning("No chunks provided to embedder.")
            return

        logger.info(f"Embedding and uploading {len(chunks)} chunks to Qdrant...")
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            
            # 1. Extract the text content for the model to read
            texts = [chunk.content for chunk in batch]
            
            # 2. Generate the embeddings using BGE
            embeddings = self.model.encode(texts, show_progress_bar=False)
            
            # 3. Prepare the data payload for Qdrant
            points = []
            for chunk, emb in zip(batch, embeddings):
                # Generate a unique, deterministic ID based on the chunk's content hash
                # This ensures if we run the script twice, it overwrites rather than duplicates
                chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.metadata.chunk_hash))
                
                # --- NEW FIX: Combine metadata and actual text into the payload ---
                payload_data = chunk.metadata.model_dump()
                payload_data["text_content"] = chunk.content 
                
                points.append(PointStruct(
                    id=chunk_uuid,
                    vector=emb.tolist(),
                    payload=payload_data  # <-- We now upload the merged data
                ))
            
            # 4. Fire it into the database
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Uploaded batch {i // batch_size + 1} ({len(batch)} chunks)")
            
        logger.success(f"Successfully secured {len(chunks)} chunks in Qdrant!")