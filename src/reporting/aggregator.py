# MIT License — DocuVault AI
"""Event counting and time-series aggregation for dashboards.

Layer: Reporting
Every action is an event. Reporting = counting and grouping events.
Provides data for operational dashboards: volume, accuracy, usage, workflows.

Phase 2-3 deliverable. All reports are FREE (0 credits).
"""
# TODO: Implement ReportAggregator with:
# - count_events(tenant_id, event_type, date_range) → int
# - time_series(tenant_id, event_type, interval='day', date_range) → list[{date, count}]
# - group_by(tenant_id, event_type, field, date_range) → dict[field_value, count]
# - Sources: event bus history (DynamoDB), metering data, audit log
