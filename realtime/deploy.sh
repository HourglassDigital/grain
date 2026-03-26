#!/bin/bash
# Deploy Pulse realtime bot to AWS EC2
# Prerequisites: Docker installed on EC2, SSH access configured

set -e

REMOTE_HOST="${1:?Usage: ./deploy.sh <ec2-host>}"
REMOTE_DIR="/opt/pulse-realtime"

echo "Deploying Pulse realtime bot to $REMOTE_HOST..."

# Build Docker image locally
docker build -t pulse-realtime -f realtime/Dockerfile .

# Save and transfer
docker save pulse-realtime | gzip > /tmp/pulse-realtime.tar.gz
scp /tmp/pulse-realtime.tar.gz "$REMOTE_HOST:$REMOTE_DIR/"
scp realtime/.env "$REMOTE_HOST:$REMOTE_DIR/.env"

# Load and run on remote
ssh "$REMOTE_HOST" << 'EOF'
cd /opt/pulse-realtime
docker load < pulse-realtime.tar.gz
docker stop pulse-realtime 2>/dev/null || true
docker rm pulse-realtime 2>/dev/null || true
docker run -d \
    --name pulse-realtime \
    --restart unless-stopped \
    --env-file .env \
    pulse-realtime
echo "Pulse realtime bot is running"
docker logs --tail 20 pulse-realtime
EOF

rm /tmp/pulse-realtime.tar.gz
echo "Deploy complete."
