# CLAUDE.md — Kompler Project Instructions

## What This Project Is

Kompler is an AI document intelligence **platform** that makes business documents work for you. Instead of replacing existing storage, Kompler adds an intelligence layer — classifying documents, extracting entities, building a knowledge graph, and proactively alerting users to compliance gaps, expiring certifications, and contradictions.

**Intelligence layer, not storage.** Phase 1-2 uses own S3 for document storage. Phase 3+ adds connectors to SharePoint, Google Drive, Dropbox — documents stay where they are, we add the brains.

**Multi-tenant SaaS.** Single deployment, all customers share infrastructure. PostgreSQL RLS for data isolation.

**GHL-inspired model.** Unlimited users, usage-based pricing, potential white-label channel for ISO consultants (Phase 3).

## Architecture (6 Layers)

```
L6: Frontend (Next.js + shadcn/ui)
L5: API + Auth + Metering (FastAPI + Stripe)
L4: Agentic Layer (LangGraph — proactive alerts, compliance scanning)
L3: Knowledge Graph + Search (PostgreSQL: pgvector + tsvector + RLS)
L2: AI Processing (Claude API — Haiku classify, Sonnet extract/Q&A)
L1: Document Sources (Phase 1-2: own S3 | Phase 3+: connectors)
```

## Tech Stack

- **Language:** Python 3.12+
- **API:** FastAPI + Pydantic v2
- **Database:** PostgreSQL 16 (pgvector, tsvector, RLS)
- **AI:** anthropic SDK (Haiku for classification, Sonnet for extraction/Q&A)
- **Agents:** LangGraph (proactive compliance scanning)
- **Cache/Queue:** Redis + ARQ
- **Storage:** S3 (boto3 direct)
- **Frontend:** Next.js 14 + shadcn/ui
- **Payments:** Stripe
- **Observability:** structlog + Sentry
- **ORM:** SQLAlchemy 2.0 (async) + Alembic migrations

## Database: PostgreSQL Does Everything

ONE database replaces what was previously 3 systems:
- **pgvector** → vector similarity search (was OpenSearch)
- **tsvector** → full-text keyword search (was OpenSearch)
- **Adjacency tables** → knowledge graph (was Neo4j; Apache AGE in Phase 2+)
- **RLS policies** → multi-tenant data isolation
- **Standard tables** → metadata, metering, audit (was DynamoDB)

## Abstraction Interfaces (src/core/interfaces.py)

ALL external dependencies accessed through abstract interfaces:
- DocumentSource → S3 (Phase 1-2), SharePoint/GDrive connectors (Phase 3+)
- LLMProvider → Claude API
- SearchEngine → PostgreSQL (pgvector + tsvector hybrid)
- GraphStore → PostgreSQL adjacency tables (Phase 1), Apache AGE (Phase 2+)

## Pricing Tiers

| Tier | Monthly | AI Enrichments | Q&A | Connectors |
|------|---------|---------------|-----|------------|
| Starter | $99 | 2,000/mo | Unlimited | 1 source |
| Pro | $299 | 10,000/mo | Unlimited | 3 sources |
| Business | $699 | 50,000/mo | Unlimited | Unlimited |
| Enterprise | Custom | Unlimited | Unlimited | White-label |

- Q&A is always FREE (this is how users experience value daily)
- Only enrichment (classify, extract, graph build) consumes credits
- No per-seat licensing — unlimited users at every tier

## Enrichment Tiers

- LIGHT (0.5cr): classify + summarize. Haiku model. Default on upload.
- STANDARD (2.5cr): + entity extraction + graph nodes. Sonnet model. On demand.
- DEEP (5cr): + cross-doc relationship discovery. Sonnet model. Phase 2.

## Security

- Prompt injection defense: sanitize document text before Claude calls.
- HMAC webhook signing. Tenant isolation via RLS.
- Rate limiting per tier: Starter 60/min, Pro 300/min, Business 1000/min.
- Sentry error tracking. AI disclaimer on every response.

## Coding Standards

- All external calls async (httpx, asyncpg, aioboto3).
- All deps via abstract interfaces.
- structlog with correlation IDs and tenant_id.
- Pydantic v2 for all data contracts.
- Type hints everywhere.
- SQLAlchemy 2.0 async patterns (async_sessionmaker, AsyncSession).
- Tests mock all externals. Sentry captures unhandled exceptions.
- tenant_id on EVERY database query — enforced by RLS + application layer.

## Phase Boundaries

- Phase 1 (Wk 1-4): Core — S3 upload, enrichment pipeline, PostgreSQL schema, basic API, Q&A with RAG.
- Phase 2 (Wk 5-8): Intelligence — graph viz, proactive alerts, semantic cache, Stripe billing, Next.js dashboard.
- Phase 3 (Wk 9-14): Connectors — SharePoint, Google Drive, white-label, compliance reports, workflows.
- Phase 4 (Mo 4-8): Scale — full frontend, marketplace, vertical packs, advanced graph analytics.

## What NOT to Do

- Do NOT reference FormKiQ, OpenSearch, Neo4j, or DynamoDB — these are removed.
- Do NOT build customer-deployed infrastructure — this is multi-tenant SaaS.
- Do NOT gate Q&A behind credits — it's always free.
- Do NOT add per-seat licensing logic.
- Do NOT use synchronous database calls — everything is async.
