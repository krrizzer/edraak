param(
    [string]$ProjectId = "project-53540efb-1397-45cd-9d9",
    [string]$Region = "us-central1",
    [string]$DemoResetToken = "edraak-demo-reset",
    [switch]$AutoApprove,
    [switch]$SkipInfrastructure
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$serviceAccount = "edraak-cloud-run-sa@$ProjectId.iam.gserviceaccount.com"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI (gcloud) is not installed or not on PATH."
}
if (-not $SkipInfrastructure) {
    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        throw "Terraform 1.5+ is not installed or not on PATH."
    }
    if (-not (Get-Command bq -ErrorAction SilentlyContinue)) {
        throw "The BigQuery CLI (bq) is not installed or not on PATH. Install it with the Google Cloud CLI."
    }
}
$activeAccount = (& gcloud auth list --filter="status:ACTIVE" --format="value(account)").Trim()
if (-not $activeAccount) {
    throw "No active gcloud account. Run: gcloud auth login"
}
& gcloud auth application-default print-access-token --quiet *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Application Default Credentials are missing. Run: gcloud auth application-default login"
}

Write-Host "Deploying as $activeAccount to $ProjectId ($Region)..."

function Import-ExistingBigQueryTableIfNeeded {
    param(
        [Parameter(Mandatory = $true)][string]$TerraformAddress,
        [Parameter(Mandatory = $true)][string]$DatasetId,
        [Parameter(Mandatory = $true)][string]$TableId
    )

    $stateAddresses = @(& terraform state list)
    if ($LASTEXITCODE -ne 0) { throw "terraform state list failed" }
    if ($stateAddresses -contains $TerraformAddress) {
        return
    }

    # The backend creates additive runtime tables when an older environment is
    # missing them. Adopt those tables into Terraform instead of failing with a
    # 409 or deleting/recreating data that already exists.
    $tableReference = "${ProjectId}:${DatasetId}.${TableId}"
    & bq show --project_id=$ProjectId --format=none $tableReference *> $null
    if ($LASTEXITCODE -ne 0) {
        return
    }

    Write-Host "Adopting existing BigQuery table $tableReference into Terraform state..."
    $importId = "projects/$ProjectId/datasets/$DatasetId/tables/$TableId"
    $importArgs = @(
        "import",
        "-var-file=terraform.tfvars",
        "-var=project_id=$ProjectId",
        "-var=region=$Region",
        "-var=bigquery_location=$Region",
        $TerraformAddress,
        $importId
    )
    & terraform @importArgs
    if ($LASTEXITCODE -ne 0) {
        throw "terraform import failed for $TerraformAddress"
    }
}

if ($SkipInfrastructure) {
    Write-Host "1/3 Skipping infrastructure; redeploying Cloud Run services only..."
} else {
    Write-Host "1/3 Provisioning BigQuery, IAM, and Artifact Registry..."
    Push-Location (Join-Path $root "infra")
    try {
        & terraform init
        if ($LASTEXITCODE -ne 0) { throw "terraform init failed" }

        Import-ExistingBigQueryTableIfNeeded `
            -TerraformAddress "google_bigquery_table.core_consents" `
            -DatasetId "bank_cores" `
            -TableId "consents"
        Import-ExistingBigQueryTableIfNeeded `
            -TerraformAddress "google_bigquery_table.transaction_classifications" `
            -DatasetId "edraak_finance" `
            -TableId "transaction_classifications"

        $applyArgs = @(
            "apply",
            "-var-file=terraform.tfvars",
            "-var=project_id=$ProjectId",
            "-var=region=$Region",
            "-var=bigquery_location=$Region"
        )
        if ($AutoApprove) { $applyArgs += "-auto-approve" }
        & terraform @applyArgs
        if ($LASTEXITCODE -ne 0) { throw "terraform apply failed" }
    } finally {
        Pop-Location
    }
}

Write-Host "2/3 Deploying the mock banking gateway..."
Push-Location (Join-Path $root "cloud-run/mock-bank")
try {
    & gcloud run deploy ksaob-mock-gateway `
        --source . `
        --project $ProjectId `
        --region $Region `
        --service-account $serviceAccount `
        --max-instances 1 `
        --allow-unauthenticated `
        --set-env-vars "GCP_PROJECT_ID=$ProjectId,BANK_CORES_DATASET=bank_cores,DEMO_RESET_TOKEN=$DemoResetToken" `
        --quiet
    if ($LASTEXITCODE -ne 0) { throw "gateway deployment failed" }
} finally {
    Pop-Location
}

$gatewayUrl = (& gcloud run services describe ksaob-mock-gateway `
    --project $ProjectId --region $Region --format="value(status.url)").Trim()
if (-not $gatewayUrl) { throw "Could not discover the gateway URL" }

Write-Host "3/3 Deploying Edraak with automatic startup seeding..."
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
        --set-env-vars "USE_BIGQUERY=true,USE_GEMINI=true,GCP_PROJECT_ID=$ProjectId,VERTEX_LOCATION=global,GEMINI_MODEL=gemini-2.5-flash-lite,BQ_DATASET=edraak_finance,BANK_CORES_DATASET=bank_cores,AUTO_SEED=true,DEMO_RESET_TOKEN=$DemoResetToken,OPENBANKING_GATEWAY_URL=$gatewayUrl" `
        --quiet
    if ($LASTEXITCODE -ne 0) { throw "Edraak deployment failed" }
} finally {
    Pop-Location
}

$appUrl = (& gcloud run services describe edraak-app `
    --project $ProjectId --region $Region --format="value(status.url)").Trim()
Write-Host ""
Write-Host "Edraak is ready: $appUrl" -ForegroundColor Green
Write-Host "Gateway API: $gatewayUrl/docs"
Write-Host "The first Edraak cold start automatically refreshes today's synthetic demo data."
