#!/bin/bash
set -euo pipefail

REPO_DIR="$HOME/PROJECTS/barbs-digital-twin"
S3_PATH="s3://sensemaking-ai/digital-twin-logs/latest.json"
LOCAL_PATH="$REPO_DIR/latest.json"

cd "$REPO_DIR"

echo "Pulling latest Digital Twin log from S3..."
aws s3 cp "$S3_PATH" "$LOCAL_PATH" --profile sensemaking

echo "Done. Local file updated:"
ls -lh "$LOCAL_PATH"
