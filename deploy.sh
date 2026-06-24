#!/usr/bin/env bash
# Deploy VibeCI to Google Cloud Run — demo-only (no GEMINI_API_KEY is shipped).
#
# One-time prerequisites (your account / project):
#   ./gcloud.sh auth login                            # e.g. daniel@cmoconfessions.com
#   ./gcloud.sh config set project YOUR_PROJECT_ID    # billing must be enabled
#
# Then deploy with:  ./deploy.sh
#
# Builds from the Dockerfile via Cloud Build (no local Docker needed), then deploys.
# To enable Live mode, append:  --set-env-vars GEMINI_API_KEY=<quota-enabled-key>
set -euo pipefail
cd "$(dirname "$0")"

REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-vibeci}"

# --max-instances 1: job state is in-memory, so the SSE stream must stay on one process.
./gcloud.sh run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances 1
