"""Prometheus metrics configuration."""

from prometheus_client import Counter, Gauge

# Scheduler metrics
scheduler_job_lag_seconds = Gauge(
    name="scheduler_job_lag_seconds",
    documentation="Scheduler job execution lag in seconds",
)

# Health check metrics
health_ready_checks_total = Counter(
    name="health_ready_checks_total",
    documentation="Total number of readiness checks",
    labelnames=["result", "reason"],
)

# Inbound events metrics
inbound_events_total = Counter(
    name="inbound_events_total",
    documentation="Inbound events by provider/type",
    labelnames=["provider", "type"],
)

# Duplicate events metrics
duplicate_inbox_dropped_total = Counter(
    name="duplicate_inbox_dropped_total",
    documentation="Duplicates dropped",
    labelnames=["provider"],
)

# Outbox metrics
outbox_sent_total = Counter(
    name="outbox_sent_total",
    documentation="Outbox messages sent",
    labelnames=["channel"],
)

outbox_errors_total = Counter(
    name="outbox_errors_total",
    documentation="Outbox errors",
    labelnames=["channel"],
)
