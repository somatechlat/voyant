#!/bin/bash
set -e

# Voyant Real Infrastructure Integration Test Runner
# Targets the standalone Docker stack on localhost ports (45xxx)

echo "⚡ Preparing Environment for Real-Infra Integration Tests..."

# 1. Export Environment Variables for Localhost Ports
export DATABASE_URL=postgresql://voyant:voyant@localhost:45432/voyant
export REDIS_URL=redis://:voyant@localhost:45379/0
export KAFKA_BOOTSTRAP_SERVERS=localhost:45092
export TEMPORAL_HOST=localhost:45233
export VOYANT_MCP_API_URL=http://localhost:45000
export VOYANT_ENV=production

# 2. Check Dependencies
echo "🔍 Verifying services are reachable..."
if ! curl -s http://localhost:45000/health > /dev/null; then
    echo "❌ voyant_api is not reachable at localhost:45000. Is the stack running?"
    exit 1
fi

echo "✅ voyant_api is reachable."

# 3. Run Pytest
echo "🚀 Running Pytest (Integration Scope)..."
# We exclude 'unit' markers if they exist, or just run everything that hits the DB/API
# Assuming standard pytest discovery
python -m pytest tests/ -v -s

echo "✨ Tests Completed."
