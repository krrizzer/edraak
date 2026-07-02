#!/bin/bash
set -e

SERVICE_NAME="edraak-app"
REGION="${REGION:-me-central2}"

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated
