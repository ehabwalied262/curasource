# 1. Use an official Python base image
FROM python:3.11-slim

# 2. Install SYSTEM-LEVEL dependencies (The stuff pip can't do)
# This installs Tesseract OCR, Poppler (for PDFs), and Graphics libraries
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libmagic1 \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy your requirements file first (for faster caching)
COPY requirements.txt .

# 5. Install Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your project code
COPY . .

# 7. Expose the ports for your API (Search=8000, Chat=8001)
EXPOSE 8000
EXPOSE 8001

# 8. Start the Chat API by default
CMD ["python", "-m", "backend.main"]