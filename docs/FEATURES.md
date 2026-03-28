# Feature Specifications

## F1: Document Storage & Management

### F1.1 Upload & AI Enrichment
Upload any supported format → auto-classify, summarize, extract entities → write metadata back to FormKiQ → index vectors → emit events. Tiered: LIGHT (0.5cr, bulk import), STANDARD (2.5cr, on-access), DEEP (5cr, on-demand).

### F1.2 Version Control
FormKiQ native versioning. Upload new version → previous version archived but accessible. API returns latest approved version by default. Full version history via GET /documents/{id}/versions. ISO 9001 compliant: only latest approved version in active circulation.

### F1.3 Access Control
Per-document role-based permissions: read, write, admin. Enforced at API middleware before any operation. Roles assigned per user per document or per document type. Tenant-level admin can configure default permissions per doc_type. Access changes logged to audit trail.

### F1.4 File Format Support
| Tier | Formats | AI Processing |
|------|---------|--------------|
| Tier 1 (Full AI) | PDF, DOCX, XLSX, PPTX, TXT, CSV, MD, HTML, JPG, PNG | Classification, extraction, Q&A, graph |
| Tier 2 (Store + OCR) | Scanned PDFs, TIFF, BMP | OCR → text → then Tier 1 processing |
| Tier 3 (Store only) | DWG, DXF, ZIP, MP4, CAD | Storage + manual tagging. No AI enrichment |
File size: 100MB per file (Lambda). 1GB via multipart upload (S3 direct).

### F1.5 OCR Engine
Phase 1: AWS Textract (pay-per-page, high accuracy, runs in customer AWS). Phase 3: Claude Vision for complex layouts with tables, handwriting, forms. Both accessible via LLMProvider interface.

### F1.6 Data Migration
POST /migration/bulk-upload: accept ZIP, queue for sequential LIGHT enrichment. POST /migration/import-metadata: CSV mapping filename → existing tags. Migration credits at $0.05/cr. POST /export/full: documents as ZIP + metadata CSV + graph JSON-LD.

## F2: Event Bus & Integration

### F2.1 Event Bus
Every state-changing action emits a typed event. In-process async dispatch. Events: document.uploaded, document.classified, document.enriched, document.indexed, document.searched, document.answered, review.requested, review.completed, metadata.updated, workflow.triggered, workflow.completed, plugin.executed, graph.entity_created, graph.relationship_created, graph.entity_merged, usage.threshold_reached.

### F2.2 Webhook System
Register URLs via POST /webhooks with event_type filter. HMAC-SHA256 signed payloads. Retry: 3 attempts, exponential backoff (10s/30s/90s). Delivery history queryable. Connects n8n, Zapier, Power Automate, or any HTTP endpoint.

### F2.3 Plugin SDK
Three types: EnrichmentPlugin (add tags after AI), ActionPlugin (side effects), IntegrationPlugin (bidirectional sync). Python base classes with DocumentContext. Register via config. Emit plugin.executed events.

### F2.4 YAML Document Workflows
Define document-specific workflows in YAML: extract → validate → classify → notify → tag → review. Pre-built templates: supplier_cert_review, sop_update_check. Pre-execution credit estimation. Partial execution if credits insufficient.

## F3: Knowledge Graph

### F3.1 Auto-Generated Entity Graph (Phase 2-3)
AI extracts entities during enrichment → stored as Neo4j nodes. Relationships discovered across documents (DEEP enrichment). Entity resolution merges duplicates (embedding similarity > 0.85). Graph events emitted for downstream workflows.

### F3.2 User-Defined Entity Patterns (Phase 3-4)
Users define extraction patterns per tenant: regex (PF-\d{3} = Part Number) or AI prompt ('extract equipment references'). Vertical packs ship defaults. New patterns retroactively apply to existing documents. Configurable via POST /graph/patterns.

### F3.3 Visual Graph Explorer (Phase 4)
Interactive force-directed graph (Cytoscape.js). Click entity → see connected documents. Filter by type, date, compliance status. 2-hop traversal for local neighborhood. Color-coded by entity type. Time slider for graph evolution.

### F3.4 Graph-Powered Retrieval (Phase 3)
Graph traversal added as third source in hybrid retrieval (keyword + vector + graph → RRF fusion). Enables multi-hop reasoning: "Show me all documents affected if we change the spec on Part PF-300."

## F4: AI & Retrieval

### F4.1 Hybrid Retrieval
3-source RRF fusion: keyword (FormKiQ) + vector (OpenSearch kNN) + graph (Neo4j traversal). Configurable weights (default: keyword 0.3, vector 0.4, graph 0.3).

### F4.2 Self-Correcting Agent (LangGraph)
8 nodes: cache_check → rewrite → retrieve → rerank → generate → reflect → cache_store → writeback. Credit estimation before execution. Graceful degradation to simple retrieval when credits low. Reflection retries max 2 times before human review flag.

### F4.3 Semantic Q&A Cache (Phase 2)
Embed queries. Before Claude, check for similar previous query (cosine > 0.90). Hit = instant, 0 credits. Miss = generate + store. TTL 7 days. Invalidate on source doc update. 60-80% hit rate in enterprise Q&A.

### F4.4 Confidence & Human Review
Every AI response includes confidence score (0.0-1.0). Below threshold (default 0.6) → auto-route to human review queue. Reviewer approves/edits/rejects. Approved answers cached. Reasoning trace shows exactly why AI is uncertain.

## F5: Metering & Billing

### F5.1 Credit System
1 credit ≈ 1 AI action. FREE: search, browse, graph traversal, visualization, reporting, webhooks. PAID: classification (0.5-1cr), extraction (2-2.5cr), Q&A (1-3cr), DEEP enrichment (5cr), AI-based plugins (0.5cr).

### F5.2 Spending Caps
Customer-configurable monthly max. When exceeded: AI features pause, search continues, queued enrichment processes when credits replenished. Real-time dashboard with alerts at 50/80/95%.

### F5.3 Migration Credits
One-time credits included per tier (Starter 5K, Professional 50K, Enterprise 200K). Applied automatically on bulk upload endpoint. LIGHT enrichment rate ($0.05/cr).

## F6: Reporting & Analytics (ALL FREE)

### F6.1 Operational Dashboards (Phase 2-3)
Document volume, classification accuracy, search/Q&A analytics, usage/credit dashboard, workflow activity.

### F6.2 Compliance Reports (Phase 3)
Document control status, audit trail (full chain of custody), entity compliance (graph-powered), retention compliance, supplier cert status, training record traceability. Export: PDF, Excel.

### F6.3 AI Quality Reports (Phase 3)
Classification accuracy trends, confidence distribution, human override analysis, cache efficiency, graph growth.

### F6.4 Executive Reports (Phase 4)
ROI dashboard (time saved, cost per document), adoption metrics, knowledge coverage. Enterprise tier: custom report builder + BI tool API (Power BI, Tableau).

## F7: Frontend & Viewing

### F7.1 Document Explorer (Phase 2)
Table/grid view. Filters: doc_type, date, language, compliance tags, enrichment status. Search integrated. Thumbnail previews.

### F7.2 Document Viewer (Phase 2-3)
In-browser PDF (react-pdf). Metadata sidebar. Entity highlights → graph links. Version history. Download original. In-context Q&A. Related documents panel.

### F7.3 Chat Interface (Phase 2)
SSE streaming. Inline citations. Confidence indicator. Reasoning trace (expandable). Cache indicator. Conversation history. Scope selector (all docs / folder / doc type / entity).

### F7.4 Knowledge Graph Explorer (Phase 4)
Cytoscape.js. Force-directed layout. Click navigation. Filter + zoom. Color-coded. Time slider.

### F7.5 Admin Console (Phase 4)
Users + roles + SSO. API keys. Usage dashboard. Billing. Entity patterns. Compliance packs. Webhook management. Audit log viewer.

### F7.6 Embeddable Widget (Phase 4)
JavaScript snippet. Modes: search (free), Q&A (credits), preview (free). Themeable. API key auth.

## F8: Security & Compliance

### F8.1 Authentication
Phase 1-2: API key with tenant identification. Phase 3: OIDC (Okta, Azure AD, Google via Cognito). Phase 4: SAML 2.0 for enterprise.

### F8.2 Audit Trail
Every action logged: who, what, when, from where. Full chain of custody per document. AI decisions logged with input hash + output. Immutable event store.

### F8.3 AI Safety
Disclaimer on every response. Confidence scoring. Human review queue. Prompt injection defense. Version-aware retrieval (prefer latest revision, note discrepancies).
