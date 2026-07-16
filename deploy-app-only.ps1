param(
    [string]$ProjectId,
    [string]$Region = "us-central1",
    [string]$DemoResetToken = "edraak-demo-reset"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI (gcloud) is not installed or not on PATH."
}

if (-not $ProjectId) {
    $ProjectId = (& gcloud config get-value project 2>$null).Trim()
}
if (-not $ProjectId -or $ProjectId -eq "(unset)") {
    throw 'No Google Cloud project is configured. Pass -ProjectId "YOUR_PROJECT_ID" or run: gcloud config set project "YOUR_PROJECT_ID"'
}

$activeAccount = (& gcloud auth list --filter="status:ACTIVE" --format="value(account)").Trim()
if (-not $activeAccount) {
    throw "No active gcloud account. Run: gcloud auth login"
}

$serviceAccount = "edraak-cloud-run-sa@$ProjectId.iam.gserviceaccount.com"
$gatewayUrl = (& gcloud run services describe ksaob-mock-gateway `
    --project $ProjectId `
    --region $Region `
    --format="value(status.url)").Trim()

if ($LASTEXITCODE -ne 0 -or -not $gatewayUrl) {
    throw "Could not find ksaob-mock-gateway in project $ProjectId and region $Region. Deploy the gateway first or check the project and region."
}

Write-Host "Deploying edraak-app only as $activeAccount..."
Write-Host "Project: $ProjectId"
Write-Host "Region:  $Region"
Write-Host "Gateway: $gatewayUrl"

Push-Location (Join-Path $root "cloud-run/edrak")
try {
    & gcloud run deploy edraak-app `
        --source . `
        --project $ProjectId `
        --region $Region `
        --service-account $serviceAccount `
        --timeout 300 `
        --max-instances 1 `
        --allow-unauthenticated `
        --set-env-vars "USE_BIGQUERY=true,USE_GEMINI=true,GCP_PROJECT_ID=$ProjectId,VERTEX_LOCATION=global,GEMINI_MODEL=gemini-2.5-flash-lite,BQ_DATASET=edraak_finance,BANK_CORES_DATASET=bank_cores,AUTO_SEED=true,DEMO_RESET_TOKEN=$DemoResetToken,OPENBANKING_GATEWAY_URL=$gatewayUrl"

    if ($LASTEXITCODE -ne 0) {
        throw "edraak-app deployment failed."
    }
} finally {
    Pop-Location
}

$appUrl = (& gcloud run services describe edraak-app `
    --project $ProjectId `
    --region $Region `
    --format="value(status.url)").Trim()

if ($LASTEXITCODE -ne 0 -or -not $appUrl) {
    throw "Deployment completed, but the edraak-app URL could not be retrieved."
}

Write-Host ""
Write-Host "Edraak app deployed: $appUrl" -ForegroundColor Green
