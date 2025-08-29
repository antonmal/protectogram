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

# Domain metrics (declared but not used yet)
duplicate_inbox_dropped_total = Counter(
    name="duplicate_inbox_dropped_total",
    documentation="Total number of duplicate inbox messages dropped",
)
