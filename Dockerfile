FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000
ENV USE_BEDROCK_MOCK=true

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
