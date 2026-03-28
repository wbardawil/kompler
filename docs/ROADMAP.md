# Development Roadmap

## Phase Overview

| Phase | Timeline | Focus | Exit Criteria |
|-------|----------|-------|---------------|
| 0 | Wk 1-2 | Validate | 10 discovery calls completed. Pricing + vertical confirmed or pivoted. |
| 1 | Wk 3-6 | Foundation | Upload 1,000 docs → classified → events firing → webhooks received → credits tracked |
| 2 | Wk 7-12 | Intelligence | Question → cited answer. Graph nodes auto-created. Cache working. First paying customer. |
| 3 | Wk 13-20 | Differentiation | Graph in retrieval. Compliance reports. n8n guide. Next.js MVP. 3-5 customers. |
| 4 | Mo 6-12 | Scale | Full frontend. Multi-tenant. Camunda. Vertical packs. >$10K MRR. |

## Phase 0: Validation (Weeks 1-2)

| Deliverable | Description |
|-------------|-------------|
| 10 discovery calls | Manufacturing quality managers from CSTO network |
| Validation script | 30 min, 6 phases, 19 questions (including views/reporting/graph) |
| Pricing validation | Van Westendorp on $199/$499/$1,499 tiers vs per-seat |
| Assumption check | Kill assumptions that 7/10 buyers contradict |
| Go/no-go decision | Adjust pricing, features, vertical. Then Phase 1. |

## Phase 1: Foundation (Weeks 3-6)

### Core Platform
| File | Description |
|------|-------------|
| src/core/config.py | Settings: all layers including metering, cache, graph, security |
| src/core/schemas.py | ALL models: Document, Event, Webhook, Plugin, Workflow, Graph, Cache, Report, Subscription |
| src/core/exceptions.py | Full hierarchy: FormKiQ, AI, Retrieval, Agent, EventBus, Plugin, Workflow, Metering, Graph, Cache, Auth |
| src/core/interfaces.py | DocumentStore, LLMProvider, VectorStore, GraphStore abstractions |
| src/core/telemetry.py | Structlog + Sentry integration |
| src/formkiq/client.py | Implements DocumentStore. 7 endpoints. Retry logic. Version support. |

### Ingestion + Enrichment
| File | Description |
|------|-------------|
| src/ingestion/pipeline.py | Upload → OCR → enrich → index → emit events. Credit check before Claude. LIGHT/STANDARD tiers. |
| src/ingestion/enrichment.py | Claude classification + extraction. Bilingual (EN/ES). prompt_version tracking. |
| src/ingestion/migration.py | Bulk upload ZIP. CSV metadata import. Migration credit type. |
| src/prompts/enrichment.py | Few-shot prompts for manufacturing doc types |
| src/retrieval/vector.py | OpenSearch indexing (embed + store) |

### Event Bus + Webhooks
| File | Description |
|------|-------------|
| src/events/bus.py | In-process async emitter. Subscriber registry. |
| src/events/webhooks.py | HTTP POST delivery. HMAC signing. Retry. |
| src/events/subscribers.py | audit_logger, webhook_dispatcher, credit_meter, plugin_trigger |

### Metering
| File | Description |
|------|-------------|
| src/metering/tracker.py | Credit tracking per tenant. Credit types (standard/bulk/cached). |
| src/metering/limits.py | Spending caps. Graceful degradation. |
| src/metering/storage.py | Per-tenant storage tracking. |
| src/metering/dashboard.py | Usage aggregation for API. |

### Cache (Phase 1 = content hash only)
| File | Description |
|------|-------------|
| src/cache/content_hash.py | SHA-256 dedup. Skip re-classification on duplicate uploads. |

### API
| File | Description |
|------|-------------|
| src/api/app.py | FastAPI factory. Event bus + metering init on startup. Sentry. |
| src/api/middleware.py | API key auth. Tenant injection. Rate limiting per tier. CORS. Access control check. |
| src/api/routes/health.py | GET /health |
| src/api/routes/documents.py | Upload, get, list, versions, access control |
| src/api/routes/webhooks.py | CRUD webhook subscriptions |
| src/api/routes/usage.py | Real-time credit balance + consumption |
| src/api/routes/migration.py | Bulk upload + CSV import |

### Infrastructure
| File | Description |
|------|-------------|
| tests/eval/ | Golden dataset (10 entries) + accuracy runner |
| CloudWatch | Dashboards: API latency, error rate, webhook delivery, credit consumption |
| Sentry | Error tracking (free tier) |

## Phase 2: Intelligence (Weeks 7-12)

### Retrieval + Agent
| File | Description |
|------|-------------|
| src/retrieval/keyword.py | FormKiQ search wrapper |
| src/retrieval/vector.py | Add kNN query |
| src/retrieval/hybrid.py | 2-source RRF (keyword + vector). Graph added Phase 3. |
| src/retrieval/reranker.py | Claude reranking. Credit-optional (skip when low). |
| src/agents/state.py | LangGraph state with cache fields |
| src/agents/nodes.py | 8 nodes including cache_check and cache_store |
| src/agents/graph.py | StateGraph with credit estimation |
| src/api/routes/chat.py | POST /chat with SSE. cache_hit + credits_consumed in response. |

### Knowledge Graph (basic)
| File | Description |
|------|-------------|
| src/retrieval/graph_store.py | Neo4j GraphStore implementation |
| src/graph/resolution.py | Entity resolution (embedding similarity) |
| docker-compose.yml | Neo4j added to dev environment |

### Cache (full)
| File | Description |
|------|-------------|
| src/cache/semantic.py | Semantic Q&A cache (cosine > 0.90) |
| src/cache/response.py | Exact match cache (hash lookup) |

### Workflows + Plugins
| File | Description |
|------|-------------|
| src/workflows/parser.py + runner.py | YAML workflow execution with credit estimation |
| src/plugins/registry.py + sdk.py | Plugin loading + execution |
| src/plugins/builtin/expiry_checker.py | Reference implementation |

### Frontend (prototype)
| File | Description |
|------|-------------|
| Streamlit app | Chat + document list. Validate UX before investing in Next.js. |

### Analytics
| File | Description |
|------|-------------|
| src/api/routes/analytics.py | Customer health metrics |
| src/api/routes/billing.py | Billing history |

## Phase 3: Differentiation (Weeks 13-20)

| Deliverable | Description |
|-------------|-------------|
| Graph in hybrid retrieval | 3-source RRF (keyword + vector + graph). Multi-hop reasoning. |
| DEEP enrichment | Cross-document relationship discovery (5 credits) |
| User-defined patterns | POST /graph/patterns. Regex + AI prompt per tenant. |
| Compliance reports | Document control status, audit trail, entity compliance, retention |
| src/api/routes/reports.py | Report generation + PDF/Excel export |
| src/api/routes/graph.py | Entity traversal + search + patterns API |
| n8n integration guide | docs/N8N_GUIDE.md + 3 example workflow JSONs |
| Next.js MVP | Chat + document list + basic viewer (react-pdf) |
| Version control API | GET /documents/{id}/versions |
| src/core/audit.py | Full audit trail implementation |
| Channel partner recruitment | 5 conversations, first agreement |

## Phase 4: Scale (Months 6-12)

| Deliverable | Description |
|-------------|-------------|
| Full Next.js frontend | Graph explorer, admin console, embeddable widget |
| Multi-tenant | tenant_id isolation in FormKiQ + OpenSearch + Neo4j |
| Camunda connector | BPMN integration for enterprise workflows |
| Community detection | Graph clustering (Enterprise tier) |
| Executive reports | ROI dashboard, adoption metrics, BI tool API |
| AI-enhanced viewer | Entity highlights, in-context Q&A |
| Plugin SDK docs | Developer guide for building custom plugins |
| App marketplace | Vertical packs, connectors, agent templates (free + paid) |
| Vertical packs | ISO 9001, IATF 16949, IMMEX, HIPAA, CFDI/SAT |
| AWS Marketplace listing | AMI/container, EULA, pricing config |
| SSO (SAML 2.0) | Enterprise authentication |
| Email ingestion | SES → Lambda → FormKiQ auto-classify |
