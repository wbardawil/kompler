# Security Architecture

## Threat Model

### 1. Prompt Injection via Document Content
Malicious text in uploaded documents could manipulate Claude during classification/Q&A.
**Mitigation**: Sanitize document text before Claude calls. Strip known injection patterns. Limit input length. System prompts treat document content as DATA, not instructions. Log input hash for traceability.

### 2. Webhook Endpoint Abuse (SSRF)
Attacker registers webhook URL pointing to internal services.
**Mitigation**: Validate URLs against allowlist. Block private IPs (10.x, 172.16-31.x, 192.168.x). Rate-limit registrations. HMAC-sign payloads.

### 3. Tenant Data Leakage
Tenant A's documents returned in Tenant B's queries.
**Mitigation**: tenant_id filter on EVERY query (FormKiQ, OpenSearch, Neo4j). API middleware injects tenant_id from auth token, never from user input. Integration tests verify isolation.

### 4. Document-Level Access Violation
User accesses a document they shouldn't see.
**Mitigation**: Per-document permissions checked at API middleware BEFORE any read/write. Roles: read, write, admin. Default permissions configurable per doc_type per tenant.

### 5. API Key Exposure
Keys leaked in logs, error messages, or client code.
**Mitigation**: Never log API keys. Mask in errors. Rotation via API. Scoped keys (read-only, upload-only, admin).

### 6. Claude API Data Handling
Document content sent to Claude could be retained.
**Mitigation**: Anthropic API zero data retention by default. Verify via DPA. Document for customers. Never send to other LLM APIs without consent.

### 7. Credit Manipulation
Bypass credit checks for free AI processing.
**Mitigation**: Credit checks server-side before every Claude call. Rate limiting per tenant per tier. Anomaly detection on sudden spikes.

### 8. Version Control Bypass
User accesses archived/superseded document version.
**Mitigation**: API returns latest approved version by default. Archived versions accessible only with explicit version_id parameter. Access logged.

## Encryption

| Layer | Method |
|-------|--------|
| At rest (S3) | SSE-KMS with customer-managed keys |
| At rest (DynamoDB) | AWS-managed encryption |
| At rest (OpenSearch) | Node-to-node TLS + encryption at rest |
| At rest (Neo4j) | Encrypted volume (EBS) |
| In transit | TLS 1.3 on all endpoints |
| API keys | Hashed with bcrypt |

## Access Control

- **Tenant level**: API key → tenant_id. All queries filtered by tenant.
- **Document level**: role-based (read/write/admin) per document or doc_type.
- **API level**: Rate limiting per tier (Starter 60/min, Pro 300/min, Enterprise 1000/min).
- **Network level**: VPC isolation for OpenSearch and Neo4j. Private subnets.

## AI Safety

- Disclaimer on every AI response (AgentResponse.disclaimer field).
- Confidence scores on all classifications and answers.
- Human review queue for low-confidence results.
- Version-aware retrieval: prefer latest revision, flag discrepancies.
- Prompt version stored with every enrichment result for traceability.
- Audit trail logs every AI decision with input hash + output.

## Incident Response

1. **Detection**: Sentry alerts, CloudWatch alarms (error rate > 5%, latency > 5s, unauthorized access, credit anomalies)
2. **Containment**: Disable affected API keys, block webhook URLs, isolate tenant
3. **Communication**: Notify affected customers within 24 hours
4. **Recovery**: Rotate credentials, review audit logs, patch
5. **Post-mortem**: Document, update threat model, add detection
