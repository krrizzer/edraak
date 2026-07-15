#!/bin/bash
set -e

SERVICE_NAME="ksaob-mock-gateway"
REGION="${REGION:-us-central1}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"
BANK_CORES_DATASET="${BANK_CORES_DATASET:-bank_cores}"
DEMO_RESET_TOKEN="${DEMO_RESET_TOKEN:-edraak-demo-reset}"
# Demo choice: gateway and backend share the Edraak runtime SA. The gateway reads
# bank rows and appends consent state only inside the bank_cores dataset.
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-edraak-cloud-run-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com}"

if [ "$GCP_PROJECT_ID" = "YOUR_PROJECT_ID" ]; then
  echo "Set GCP_PROJECT_ID before deploying."
  exit 1
fi

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$GCP_PROJECT_ID" \
  --region "$REGION" \
  --service-account "$SERVICE_ACCOUNT" \
  --max-instances 1 \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,BANK_CORES_DATASET=$BANK_CORES_DATASET,DEMO_RESET_TOKEN=$DEMO_RESET_TOKEN"

echo
echo "Gateway deployed. Set OPENBANKING_GATEWAY_URL on the edraak-app service to this URL,"
echo "and set OPENBANKING_GATEWAY_URL / API base for the Flutter app accordingly."
