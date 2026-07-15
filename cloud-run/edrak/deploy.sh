#!/bin/bash
set -e

SERVICE_NAME="edraak-app"
REGION="${REGION:-us-central1}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-edraak-cloud-run-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com}"
USE_BIGQUERY="${USE_BIGQUERY:-true}"
USE_GEMINI="${USE_GEMINI:-true}"
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash-lite}"
BQ_DATASET="${BQ_DATASET:-edraak_finance}"
BANK_CORES_DATASET="${BANK_CORES_DATASET:-bank_cores}"
AUTO_SEED="${AUTO_SEED:-true}"
DEMO_RESET_TOKEN="${DEMO_RESET_TOKEN:-edraak-demo-reset}"
# URL of the deployed ksaob-mock-gateway service (deploy that first, then set this).
OPENBANKING_GATEWAY_URL="${OPENBANKING_GATEWAY_URL:-}"

if [ "$GCP_PROJECT_ID" = "YOUR_PROJECT_ID" ]; then
  echo "Set GCP_PROJECT_ID before deploying."
  exit 1
fi

if [ -z "$OPENBANKING_GATEWAY_URL" ]; then
  OPENBANKING_GATEWAY_URL="$(gcloud run services describe ksaob-mock-gateway \
    --project "$GCP_PROJECT_ID" --region "$REGION" --format='value(status.url)' 2>/dev/null || true)"
fi
if [ -z "$OPENBANKING_GATEWAY_URL" ]; then
  echo "Deploy cloud-run/mock-bank first, or set OPENBANKING_GATEWAY_URL."
  exit 1
fi

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$GCP_PROJECT_ID" \
  --region "$REGION" \
  --service-account "$SERVICE_ACCOUNT" \
  --timeout 300 \
  --max-instances 1 \
  --allow-unauthenticated \
  --set-env-vars "USE_BIGQUERY=$USE_BIGQUERY,USE_GEMINI=$USE_GEMINI,GCP_PROJECT_ID=$GCP_PROJECT_ID,VERTEX_LOCATION=$VERTEX_LOCATION,GEMINI_MODEL=$GEMINI_MODEL,BQ_DATASET=$BQ_DATASET,BANK_CORES_DATASET=$BANK_CORES_DATASET,AUTO_SEED=$AUTO_SEED,DEMO_RESET_TOKEN=$DEMO_RESET_TOKEN,OPENBANKING_GATEWAY_URL=$OPENBANKING_GATEWAY_URL"
