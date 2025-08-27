"""Application metrics."""

from prometheus_client import Counter, Histogram

# Scheduler metrics
scheduler_job_lag = Histogram(
    "scheduler_job_lag_seconds",
    "Scheduler job execution lag in seconds",
    ["job_type"],
)

# Panic metrics
panic_incidents_started = Counter(
    "panic_incidents_started_total",
    "Total number of panic incidents started",
)

panic_acknowledged = Counter(
    "panic_acknowledged_total",
    "Total number of panic incidents acknowledged",
)

panic_canceled = Counter(
    "panic_canceled_total",
    "Total number of panic incidents canceled",
)

# Call metrics
call_attempts_total = Counter(
    "call_attempts_total",
    "Total number of call attempts",
    ["result"],
)

# Telegram metrics
telegram_messages_sent = Counter(
    "telegram_messages_sent_total",
    "Total number of Telegram messages sent",
    ["message_type"],
)
