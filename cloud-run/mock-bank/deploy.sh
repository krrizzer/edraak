#!/bin/bash
set -e

SERVICE_NAME="ksaob-mock-gateway"
REGION="${REGION:-me-central2}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"
BANK_CORES_DATASET="${BANK_CORES_DATASET:-bank_cores}"
# The gateway reads its bank cores from BigQuery; run it as the Edraak SA (or any
# SA with dataViewer on the bank_cores dataset).
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-}"

EXTRA_ARGS=""
if [ -n "$SERVICE_ACCOUNT" ]; then
  EXTRA_ARGS="--service-account $SERVICE_ACCOUNT"
fi

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,BANK_CORES_DATASET=$BANK_CORES_DATASET" \
  $EXTRA_ARGS

echo
echo "Gateway deployed. Set OPENBANKING_GATEWAY_URL on the edraak-app service to this URL,"
echo "and set OPENBANKING_GATEWAY_URL / API base for the Flutter app accordingly."
