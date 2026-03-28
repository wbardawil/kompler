FROM python:3.13-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps WITHOUT sentence-transformers/torch (too big for Railway)
# Embeddings will use the API instead of local model in production
COPY pyproject.toml README.md ./
COPY src/ src/

# Install with minimal deps, skip heavy ML packages
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] python-multipart sse-starlette \
    anthropic pydantic pydantic-settings \
    sqlalchemy[asyncio] asyncpg pgvector alembic \
    redis arq httpx \
    structlog sentry-sdk[fastapi] \
    slowapi python-jose[cryptography] passlib[bcrypt] \
    stripe python-dotenv pyyaml \
    psycopg psycopg-binary \
    pdfplumber python-docx openpyxl \
    langgraph langchain-core \
    boto3

# Copy remaining files
COPY alembic/ alembic/
COPY alembic.ini ./
COPY scripts/ scripts/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
