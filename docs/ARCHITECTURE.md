# Architecture

## Design Principle

DocuVault AI is a platform with 8 layers. The core handles document intelligence. Everything else plugs in via events, APIs, webhooks, and plugins. We write ~20% of code. The rest is proven infrastructure.

## 8-Layer Architecture

```
L8 Frontend ──── Next.js + react-pdf + Cytoscape.js + Recharts + shadcn/ui
L7 Reporting ─── Operational dashboards + Compliance reports + AI quality + Executive ROI
L6 Metering ──── Credit tracker + Spending caps + Usage dashboard + Storage metering
L5 Workflows ─── n8n (visual 400+ connectors) + Camunda (BPMN) + YAML agent workflows
L4 Integration ─ Event bus + Webhooks + REST API + Plugin SDK + MCP Server
   Verticals ─── ISO 9001 + HIPAA + CFDI (schemas + prompts + patterns + workflows)
L3 Graph+Cache ─ Neo4j graph + Entity resolution + Semantic cache + Content hash
L2 AI+Retrieval  Claude enrichment + 3-source RRF + LangGraph agent + Reranker
L1 Storage ───── FormKiQ (S3+DDB+Lambda) + OpenSearch + Versioning + ACL + OCR
```

## Event Flow

```
User uploads document
  → FormKiQ stores in S3 → emit document.uploaded
  → Content hash check (duplicate? → skip classification, 0 credits)
  → OCR if scanned (Textract/Vision)
  → Claude classifies + summarizes (LIGHT: 0.5cr)
  → emit document.classified
  → [On first access] Claude extracts entities (STANDARD: 2.5cr)
  → Entity resolution against graph (merge or create new)
  → Write graph nodes → emit graph.entity_created
  → emit document.enriched
  → Plugins execute (matching triggers)
  → Webhook dispatcher sends to all subscribers
  → [On demand] DEEP enrichment: cross-doc relationships (5cr)
  → emit graph.relationship_created
```

## Q&A Pipeline

```
User asks question
  → Exact cache check (hash match? → return, 0cr)
  → Semantic cache check (cosine > 0.90? → return, 0cr)
  → Credit estimation (simple: 1cr, agentic: 3cr)
  → Query rewrite (Claude)
  → Hybrid retrieval: keyword (FormKiQ) + vector (OpenSearch) + graph (Neo4j)
  → RRF fusion (weights: keyword 0.3, vector 0.4, graph 0.3)
  → Claude reranking (optional, credit-dependent)
  → Claude generation with citations
  → Reflection check (grounded? retry if not, max 2)
  → Store in semantic cache + exact cache
  → emit document.answered
  → If confidence < threshold → emit review.requested
```

## Infrastructure Costs Per Tenant

| Resource | Monthly Cost | Notes |
|----------|-------------|-------|
| S3 (50GB) | $1.15 | Negligible. Scales linearly. |
| DynamoDB | <$1 | Pay per request. Negligible at our scale. |
| Lambda | <$1 | Serverless. Near-zero idle. |
| OpenSearch | $50-200 | Semi-fixed. Shared across tenants. |
| Neo4j Community | $0 | Free. Self-hosted in Docker. |
| Claude API | $10-280 | Primary variable cost. Scales with credits consumed. |
| Sentry | $0 | Free tier: 5K events/mo. |

## Why Assemble, Don't Build

| | Build Own | Assemble OSS |
|---|---|---|
| Document storage | 6+ months | FormKiQ: 1 day |
| AI enrichment | 3+ months | Claude API: 1 week |
| Workflow engine | 12+ months | n8n: 2-3 days (webhooks) |
| Knowledge graph | 6+ months | Neo4j Community: 1 day |
| Semantic cache | 2+ months | OpenSearch + embeddings: 1 week |
| Our focus | Diluted | 100% on intelligence layer |
