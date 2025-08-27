#!/bin/bash

# Protectogram Health Check Script

set -e

# Default values
APP_URL="${APP_URL:-https://protectogram-staging.fly.dev}"
TIMEOUT=10

echo "🏥 Checking Protectogram health at $APP_URL"

# Function to check endpoint
check_endpoint() {
    local endpoint=$1
    local name=$2
    local url="$APP_URL$endpoint"

    echo -n "Checking $name... "

    if curl -f -s --max-time $TIMEOUT "$url" > /dev/null; then
        echo "✅ OK"
        return 0
    else
        echo "❌ FAILED"
        return 1
    fi
}

# Check all endpoints
failed=0

check_endpoint "/health/live" "Liveness" || failed=1
check_endpoint "/health/ready" "Readiness" || failed=1
check_endpoint "/metrics" "Metrics" || failed=1

# Check specific metrics if available
echo -n "Checking metrics content... "
if curl -s --max-time $TIMEOUT "$APP_URL/metrics" | grep -q "panic_"; then
    echo "✅ Metrics available"
else
    echo "⚠️  No panic metrics found"
fi

# Summary
echo ""
if [ $failed -eq 0 ]; then
    echo "🎉 All health checks passed!"
    exit 0
else
    echo "💥 Some health checks failed!"
    exit 1
fi
