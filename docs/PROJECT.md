# Project Context

## Positioning

"AI-powered document intelligence for regulated industries — unlimited users, usage-based pricing, deployed in your AWS, with an auto-generated knowledge graph that shows how all your documents connect."

## Target Verticals (Priority Order)

1. **Manufacturing** (beachhead): ISO 9001, IATF 16949, IMMEX. SOPs, quality records, supplier certs.
2. **Healthcare**: HIPAA, 21 CFR Part 11. Clinical protocols, patient records.
3. **Tax/Accounting**: CFDI/SAT, SOX. Invoices, tax returns, audit workpapers.
4. **Legal**: Contracts, briefs, discovery. Highest product maturity required — enter last.

## Pricing — Hybrid: Platform Fee + AI Credits

| Tier | Platform Fee | Users | Monthly Credits | Migration Credits | Storage |
|------|-------------|-------|----------------|-------------------|---------|
| Starter | $199/mo | Unlimited | 500 | 5,000 (one-time) | 50 GB |
| Professional | $499/mo | Unlimited | 5,000 | 50,000 (one-time) | 500 GB |
| Enterprise | $1,499/mo | Unlimited | 25,000 | 200,000 (one-time) | 2 TB |
| Enterprise+ | Custom | Unlimited | Committed | Unlimited | Unlimited |

Credit costs: LIGHT 0.5cr, STANDARD 2.5cr, DEEP 5cr, simple Q&A 1cr, agentic Q&A 3cr. Search/browse/graph/reporting = FREE. Extra credits: $0.25/$0.15/$0.08/negotiated per tier. Migration credits at $0.05/cr.

Regional: LATAM 65%, APAC 70%, DACH 105% of US list.
All pricing draft — pending Phase 0 validation.

## Competitive Advantage

We beat M-Files on: cost (82% cheaper at 200 users), unlimited users (no per-seat), AI depth (agentic RAG + reflection + semantic cache), auto-generated knowledge graph (visual explorer), multilingual native processing, data sovereignty (your AWS), open extensibility (event bus + 400 connectors via n8n + plugin SDK).

They beat us on: workflow maturity (built-in engine vs integration), compliance certifications (FDA, GxP), 15 years of enterprise polish, dedicated support, established channel.

Our strategy: integrate their workflow strengths (via n8n/Camunda) while owning AI intelligence + knowledge graph as our moat.

## ICP

50-500 employees, $10M-$500M revenue, manufacturing (Phase 1), ISO-certified or pursuing, 2+ languages, cloud-friendly (AWS or open), 1-3 IT people (not a department), quality manager or ops director as champion, $15K-$100K/year budget authority, simple-moderate workflow needs.

## Anti-ICP

Complex BPM buyers (12-step BPMN), 1000+ user enterprise expecting turnkey, compliance-deadline buyers needing certification NOW, strict Microsoft-only shops (exceptions with Power Automate bridge), personal/micro (<5 users), air-gapped/no-cloud, high-volume IDP (50K invoices/day), panic-deadline (30-day full production).
