# Setup Guide

## Prerequisites

- Python 3.12+
- AWS account with FormKiQ Core deployed
- Anthropic API key
- Docker + Docker Compose (for local Neo4j + OpenSearch)

## Installation

```bash
git clone https://github.com/your-org/docuvault-ai.git
cd docuvault-ai
cp .env.example .env    # Edit with your values
pip install -e ".[dev]"
make test               # Verify setup
make run                # Start API server
```

## Environment Variables

See `.env.example` for all variables with descriptions.

Required: `FORMKIQ_API_URL`, `FORMKIQ_API_KEY`, `ANTHROPIC_API_KEY`

## Verification

```bash
# FormKiQ connection
curl -H "Authorization: $FORMKIQ_API_KEY" $FORMKIQ_API_URL/documents?limit=1

# API health
curl http://localhost:8000/health

# Upload test document
curl -X POST http://localhost:8000/documents/upload -F "file=@test.pdf" -H "X-API-Key: dev-key-1"
```
