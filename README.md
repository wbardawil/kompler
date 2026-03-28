# Kompler

**AI document intelligence — make your business documents work for you.**

Upload documents → AI classifies and extracts entities → knowledge graph auto-discovers relationships → ask questions in plain language → get proactive compliance alerts.

Unlimited users. Usage-based pricing. Q&A is always free.

## Architecture

```
Frontend     Next.js + shadcn/ui
API          FastAPI + Stripe + Auth + Metering
Agents       LangGraph (proactive alerts, compliance scanning)
Data         PostgreSQL (pgvector + tsvector + RLS)
AI           Claude API (Haiku classify, Sonnet extract/Q&A)
Storage      S3 (Phase 1-2) → Connectors (Phase 3+)
```

## Quickstart

```bash
# 1. Start database
docker compose up -d

# 2. Install dependencies
pip install -e ".[dev]"
pip install pdfplumber python-docx openpyxl

# 3. Set up database
cp .env.example .env   # Add your ANTHROPIC_API_KEY
alembic upgrade head
python scripts/seed.py

# 4. Start API
make run               # http://localhost:8000/health

# 5. Start frontend
cd frontend && npm install && npm run dev   # http://localhost:3000
```

## API Examples

```bash
# Health check
curl http://localhost:8000/health

# List documents
curl -H 'X-Api-Key: dev-key-1' http://localhost:8000/api/v1/documents

# Upload a document
curl -H 'X-Api-Key: dev-key-1' -F 'file=@my-document.pdf' http://localhost:8000/api/v1/documents

# Ask a question (FREE — 0 credits)
curl -H 'X-Api-Key: dev-key-1' -H 'Content-Type: application/json' \
  -d '{"question": "Which supplier certificates expire this quarter?"}' \
  http://localhost:8000/api/v1/chat

# Check usage
curl -H 'X-Api-Key: dev-key-1' http://localhost:8000/api/v1/usage
```

## Pricing

| Tier | Monthly | AI Enrichments | Q&A | Connectors |
|------|---------|---------------|-----|------------|
| Starter | $99 | 2,000/mo | Unlimited | 1 source |
| Pro | $299 | 10,000/mo | Unlimited | 3 sources |
| Business | $699 | 50,000/mo | Unlimited | Unlimited |

## License
MIT
