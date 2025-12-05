#!/bin/bash
set -e

REMOTE_HOST="hetzner"
REMOTE_PATH="~/stephan-matching-api"
SERVICE_URL="https://matching-api.quietloop.dev"

echo "=== Deploying stephan-matching-api ==="

# Test SSH connection
if ! ssh "$REMOTE_HOST" "echo 'Connection OK'" > /dev/null 2>&1; then
    echo "SSH connection failed"
    exit 1
fi

# Sync project files
echo "Syncing files..."
rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='*.pyc' \
    --exclude='data/' \
    ./ "$REMOTE_HOST:$REMOTE_PATH/"

# Remote build and deploy
echo "Building container (this takes a while for ML deps)..."
ssh -t "$REMOTE_HOST" "cd $REMOTE_PATH && \
    docker network create quietloop-network 2>/dev/null || true && \
    docker compose down || true && \
    docker compose build --progress=plain 2>&1 | grep -E '^\#|Downloading|Installing|Collecting|Successfully' && \
    echo '--- Starting container ---' && \
    docker compose up -d"

# Wait for health check
echo "Waiting for service to be healthy..."
sleep 10
for i in {1..12}; do
    if ssh "$REMOTE_HOST" "curl -sf http://localhost:3008/health" > /dev/null 2>&1; then
        echo "Service is healthy!"
        echo "URL: $SERVICE_URL"
        exit 0
    fi
    echo "  Attempt $i/12..."
    sleep 5
done

echo "Service failed to become healthy"
ssh "$REMOTE_HOST" "cd $REMOTE_PATH && docker compose logs --tail=50"
exit 1
