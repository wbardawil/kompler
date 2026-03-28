# Operations Runbook

## Purpose
Enables any competent developer to keep DocuVault AI running for 30 days. Bus factor = 1 mitigation.

## Credential Locations
All in [PASSWORD MANAGER — configure before launch]:
AWS root + IAM, Anthropic API key, FormKiQ API key, domain registrar, GitHub, OpenSearch, Neo4j, Sentry, Stripe.
**Backup access person**: [DESIGNATE BEFORE LAUNCH]

## Error Tracking
Sentry (free tier: 5K events/mo). All unhandled exceptions captured automatically.
Dashboard: [SENTRY_URL]. Alerts: Slack or email on new error types.

## Monitoring (CloudWatch)

### Dashboards
- API: request count, error rate, P50/P95/P99 latency
- AI: Claude API call count, error rate, token usage, cost
- Metering: credits consumed by tenant, storage utilization
- Webhooks: delivery success rate, retry count, latency

### Alarms
- API error rate > 5% sustained 5 min → alert
- API latency P95 > 5s sustained 5 min → alert
- Webhook delivery failure > 10% → alert
- Claude API error rate > 5% → alert
- Credit consumption spike > 3x normal for any tenant → alert

## Daily Checklist
- [ ] Sentry: any new unresolved errors?
- [ ] CloudWatch: all alarms green?
- [ ] Review items in human review queue

## Weekly Checklist
- [ ] Credit consumption trends per tenant
- [ ] Dependency security updates: pip audit
- [ ] Backup verification (see below)
- [ ] Audit log review for anomalies

## Backup & Disaster Recovery

| Resource | Backup Method | RPO | RTO |
|----------|-------------|-----|-----|
| S3 (documents) | Versioning + cross-region replication | 0 (realtime) | <1 hour |
| DynamoDB (metadata) | Point-in-time recovery enabled | 5 min | <1 hour |
| OpenSearch (vectors) | Automated snapshots to S3 (hourly) | 1 hour | 2-4 hours |
| Neo4j (graph) | Daily cypher-shell dump to S3 | 24 hours | 2-4 hours |
| Sentry (errors) | SaaS-managed | N/A | N/A |

### Restore procedures
- S3: restore from versioned object or cross-region replica
- DynamoDB: restore to point-in-time via AWS console
- OpenSearch: restore from S3 snapshot
- Neo4j: load from dump file

## Deployment

```bash
# Standard (CI/CD on push to main)
git push origin main  # GitHub Actions: lint → test → build → deploy

# Manual (emergency)
docker build -t docuvault-ai .
docker push [ECR_REPO]:latest
aws ecs update-service --cluster docuvault --service api --force-new-deployment

# Rollback
aws ecs update-service --cluster docuvault --service api \
  --task-definition docuvault-api:[PREVIOUS_REVISION]
```

## Scaling Triggers
- API latency > 5s sustained → check Lambda concurrency
- OpenSearch CPU > 80% → scale instance
- Neo4j memory > 80% → upgrade instance or shard
- Credit consumption spike → investigate (growth or abuse?)

## Rate Limits Per Tier
- Starter: 60 req/min
- Professional: 300 req/min
- Enterprise: 1000 req/min
- Configured in src/api/middleware.py via SlowAPI

## Scheduled Tasks (AWS EventBridge)
- Daily: retention policy check (flag expired docs)
- Daily: certificate expiry scan (flag within 30 days)
- Daily: stale SOP detection (no review in 12+ months)
- Hourly: storage usage refresh per tenant
- Weekly: graph health check (orphan entities, disconnected nodes)
