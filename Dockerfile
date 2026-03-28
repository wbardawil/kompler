FROM python:3.13-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir pdfplumber python-docx openpyxl psycopg-binary psycopg

# Copy remaining files
COPY alembic/ alembic/
COPY alembic.ini ./
COPY scripts/ scripts/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
