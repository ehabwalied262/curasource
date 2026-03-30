FROM python:3.11-slim

# System deps needed by sentence-transformers / numpy
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the BGE embedding model into the image.
# This prevents a cold-start timeout on Koyeb — the model
# (~1.3 GB) is baked in at build time, not fetched at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-en-v1.5')"

# Copy application code
COPY backend/ ./backend/

EXPOSE 8001

CMD ["python", "-m", "backend.main"]
