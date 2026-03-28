FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ src/

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

COPY alembic/ alembic/
COPY alembic.ini ./
COPY scripts/ scripts/

CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
