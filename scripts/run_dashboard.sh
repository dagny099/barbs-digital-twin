#!/bin/bash
set -euo pipefail

REPO_DIR="$HOME/PROJECTS/barbs-digital-twin"

cd "$REPO_DIR"

# Pull freshest log before launch
./scripts/pull_latest_log.sh

# Activate your environment if needed
# source .venv/bin/activate

# Launch dashboard
PYTHONPATH=. streamlit run dashboard/app.py
#streamlit run dashboard/app.py
