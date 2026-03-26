#!/bin/bash
# Deploy Pulse to AWS EC2
# Usage: ./deploy-aws.sh <ec2-host>
#
# Prerequisites:
#   - EC2 instance with Docker + Docker Compose installed
#   - SSH key configured
#   - Security group allows outbound HTTPS (443)

set -e

HOST="${1:?Usage: ./deploy-aws.sh <ec2-user@ec2-host>}"
REMOTE_DIR="/opt/pulse"

echo "🚀 Deploying Pulse to $HOST..."

# Create remote directory
ssh "$HOST" "sudo mkdir -p $REMOTE_DIR && sudo chown \$(whoami) $REMOTE_DIR"

# Sync code
rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' \
    --exclude 'realtime/.env' \
    ./ "$HOST:$REMOTE_DIR/"

# Copy env file
scp realtime/.env "$HOST:$REMOTE_DIR/realtime/.env"

# Build and run
ssh "$HOST" "cd $REMOTE_DIR && docker compose up -d --build"

echo ""
echo "✅ Pulse deployed. Check logs:"
echo "   ssh $HOST 'docker compose -f $REMOTE_DIR/docker-compose.yml logs -f'"
