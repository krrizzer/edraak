locals {
  required_apis = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "aiplatform.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
  ])

  secret_ids = toset([
    "edraak-gemini-api-key",
    "edraak-config",
  ])
}

resource "google_project_service" "required" {
  for_each = local.required_apis

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "cloud_run_service_account" {
  source = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/iam-service-account?ref=master&depth=1"

  project_id   = var.project_id
  name         = var.cloud_run_service_account_name
  display_name = "Edraak Cloud Run service account"
  description  = "Runtime identity for the Edraak Cloud Run application."

  iam_project_roles = {
    (var.project_id) = concat(
      [
        "roles/bigquery.jobUser",
        "roles/aiplatform.user",
        "roles/logging.logWriter",
      ],
      var.create_secrets ? ["roles/secretmanager.secretAccessor"] : []
    )
  }

  depends_on = [
    google_project_service.required["iam.googleapis.com"],
  ]
}

resource "google_bigquery_dataset" "edraak" {
  project                    = var.project_id
  dataset_id                 = var.dataset_id
  location                   = var.bigquery_location
  description                = "Synthetic prototype finance data for Edraak."
  labels                     = var.labels
  delete_contents_on_destroy = true

  depends_on = [
    google_project_service.required["bigquery.googleapis.com"],
  ]
}

resource "google_bigquery_dataset_iam_member" "cloud_run_data_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.edraak.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = module.cloud_run_service_account.iam_email
}

# The mock banks' own database: a SEPARATE dataset the gateway serves from,
# simulating that a real bank API has a core system behind it. Edraak's app
# only ever receives this data through the consented gateway API.
resource "google_bigquery_dataset" "bank_cores" {
  project                    = var.project_id
  dataset_id                 = var.bank_cores_dataset_id
  location                   = var.bigquery_location
  description                = "Simulated core-banking data behind the mock KSAOB gateway."
  labels                     = var.labels
  delete_contents_on_destroy = true

  depends_on = [
    google_project_service.required["bigquery.googleapis.com"],
  ]
}

# The Edraak service account seeds the cores (the daily auto-seed) and the
# gateway reads them. Kept to one SA for demo simplicity.
resource "google_bigquery_dataset_iam_member" "bank_cores_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.bank_cores.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = module.cloud_run_service_account.iam_email
}

resource "google_bigquery_table" "core_accounts" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.bank_cores.dataset_id
  table_id            = "accounts"
  deletion_protection = false
  schema              = google_bigquery_table.accounts.schema
}

resource "google_bigquery_table" "core_transactions" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.bank_cores.dataset_id
  table_id            = "transactions"
  deletion_protection = false
  schema              = google_bigquery_table.transactions.schema
}

resource "google_bigquery_table" "core_loans" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.bank_cores.dataset_id
  table_id            = "loans"
  deletion_protection = false
  schema              = google_bigquery_table.loans.schema
}

# One-row bookkeeping table: which day the synthetic world is anchored to.
# The backend re-seeds automatically when this is not today's date.
resource "google_bigquery_table" "core_seed_meta" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.bank_cores.dataset_id
  table_id            = "seed_meta"
  deletion_protection = false

  schema = jsonencode([
    { name = "anchor_date", type = "DATE", mode = "REQUIRED" },
    { name = "seeded_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "customers" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "customers"
  deletion_protection = false

  # current_balance was removed: balances now live per bank in the accounts table.
  schema = jsonencode([
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "username_en", type = "STRING", mode = "REQUIRED" },
    { name = "ar_name", type = "STRING", mode = "NULLABLE" },
    { name = "en_name", type = "STRING", mode = "NULLABLE" },
    { name = "national_id", type = "STRING", mode = "NULLABLE" },
    { name = "birthday", type = "DATE", mode = "NULLABLE" },
    { name = "salary", type = "FLOAT", mode = "NULLABLE" },
    { name = "city", type = "STRING", mode = "NULLABLE" },
    { name = "employment_sector", type = "STRING", mode = "NULLABLE" },
    { name = "employer_name", type = "STRING", mode = "NULLABLE" },
    { name = "account_open_date", type = "DATE", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

# Cross-bank accounts: one row per bank account the customer holds anywhere.
# This table is what makes Edraak an Open Banking product instead of a single-bank tool.
resource "google_bigquery_table" "accounts" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "accounts"
  deletion_protection = false

  schema = jsonencode([
    { name = "account_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "bank_code", type = "STRING", mode = "NULLABLE" },
    { name = "bank_name_ar", type = "STRING", mode = "NULLABLE" },
    { name = "account_type", type = "STRING", mode = "NULLABLE" },
    { name = "iban", type = "STRING", mode = "NULLABLE" },
    { name = "balance", type = "FLOAT", mode = "NULLABLE" },
    { name = "is_primary", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "transactions" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "transactions"
  deletion_protection = false

  # raw_description is the messy bank narrative string the Transaction Intelligence
  # Agent reads. category stays but is intentionally unreliable/partial, like real
  # cross-bank data. is_recurring was removed: recurrence is detected, not seeded.
  schema = jsonencode([
    { name = "transaction_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "account_id", type = "STRING", mode = "NULLABLE" },
    { name = "bank_code", type = "STRING", mode = "NULLABLE" },
    { name = "transaction_date", type = "DATE", mode = "NULLABLE" },
    { name = "merchant", type = "STRING", mode = "NULLABLE" },
    { name = "category", type = "STRING", mode = "NULLABLE" },
    { name = "raw_description", type = "STRING", mode = "NULLABLE" },
    { name = "amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "transaction_type", type = "STRING", mode = "NULLABLE" },
    { name = "channel", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "loans" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "loans"
  deletion_protection = false

  # bank_code: loans can exist at OTHER banks (the cross-bank story).
  # remaining_months: critical for the forecast — a loan with remaining_months=1
  # drops off the projection from month 2 onward.
  schema = jsonencode([
    { name = "loan_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "bank_code", type = "STRING", mode = "NULLABLE" },
    { name = "loan_type", type = "STRING", mode = "NULLABLE" },
    { name = "loan_total_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "total_profit_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "total_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "remaining_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "monthly_installment", type = "FLOAT", mode = "NULLABLE" },
    { name = "remaining_months", type = "INTEGER", mode = "NULLABLE" },
    { name = "first_installment_date", type = "DATE", mode = "NULLABLE" },
    { name = "start_date", type = "DATE", mode = "NULLABLE" },
    { name = "end_date", type = "DATE", mode = "NULLABLE" },
    { name = "status", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

# Cache of Transaction Intelligence Agent output. Reused on analyze when fresh
# so the demo does not re-run LLM classification on every request.
resource "google_bigquery_table" "detected_obligations" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "detected_obligations"
  deletion_protection = false

  schema = jsonencode([
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "obligation_type", type = "STRING", mode = "NULLABLE" },
    { name = "counterparty", type = "STRING", mode = "NULLABLE" },
    { name = "monthly_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "day_of_month", type = "INTEGER", mode = "NULLABLE" },
    { name = "remaining_months", type = "INTEGER", mode = "NULLABLE" },
    { name = "confidence", type = "FLOAT", mode = "NULLABLE" },
    { name = "is_committed", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "source_bank_codes", type = "STRING", mode = "REPEATED" },
    { name = "detected_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

# TPP-side consent ledger: Edraak's own record of every consent it holds, so
# every ingested row traces back to a consent id. The bank keeps its own copy.
resource "google_bigquery_table" "ob_consents" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "ob_consents"
  deletion_protection = false

  schema = jsonencode([
    { name = "consent_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "bank_code", type = "STRING", mode = "NULLABLE" },
    { name = "status", type = "STRING", mode = "NULLABLE" },
    { name = "permissions", type = "STRING", mode = "REPEATED" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "expires_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "revoked_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

# Bronze layer: the raw KSAOB JSON exactly as pulled from a bank gateway, kept
# as proof of what arrived before any normalization.
resource "google_bigquery_table" "ob_raw_payloads" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "ob_raw_payloads"
  deletion_protection = false

  schema = jsonencode([
    { name = "payload_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "bank_code", type = "STRING", mode = "NULLABLE" },
    { name = "consent_id", type = "STRING", mode = "NULLABLE" },
    { name = "resource", type = "STRING", mode = "NULLABLE" },
    { name = "account_id", type = "STRING", mode = "NULLABLE" },
    { name = "page", type = "INTEGER", mode = "NULLABLE" },
    { name = "raw_json", type = "STRING", mode = "NULLABLE" },
    { name = "fetched_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

# Storage-only radar alerts. Agents never read this table.
resource "google_bigquery_table" "alerts" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "alerts"
  deletion_protection = false

  schema = jsonencode([
    { name = "alert_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "alert_type", type = "STRING", mode = "NULLABLE" },
    { name = "gap_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "gap_date", type = "DATE", mode = "NULLABLE" },
    { name = "cause_category", type = "STRING", mode = "NULLABLE" },
    { name = "message_ar", type = "STRING", mode = "NULLABLE" },
    { name = "trajectory_json", type = "STRING", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "user_profiles" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "user_profiles"
  deletion_protection = false

  # Cross-bank aggregates: totals span every account/loan the customer holds
  # at any bank. Old single-bank prose fields were removed with the 5-agent flow.
  schema = jsonencode([
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "ar_name", type = "STRING", mode = "NULLABLE" },
    { name = "en_name", type = "STRING", mode = "NULLABLE" },
    { name = "salary", type = "FLOAT", mode = "NULLABLE" },
    { name = "salary_day", type = "INTEGER", mode = "NULLABLE" },
    { name = "salary_timing_variance_days", type = "FLOAT", mode = "NULLABLE" },
    { name = "total_balance", type = "FLOAT", mode = "NULLABLE" },
    { name = "banks_count", type = "INTEGER", mode = "NULLABLE" },
    { name = "active_loans_count", type = "INTEGER", mode = "NULLABLE" },
    { name = "total_remaining_loans", type = "FLOAT", mode = "NULLABLE" },
    { name = "monthly_loan_installments", type = "FLOAT", mode = "NULLABLE" },
    { name = "avg_monthly_spending", type = "FLOAT", mode = "NULLABLE" },
    { name = "avg_flexible_spending", type = "FLOAT", mode = "NULLABLE" },
    { name = "monthly_spending_std", type = "FLOAT", mode = "NULLABLE" },
    { name = "profile_generated_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "decision_requests" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "decision_requests"
  deletion_protection = false

  schema = jsonencode([
    { name = "request_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "goal_type", type = "STRING", mode = "NULLABLE" },
    { name = "goal_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "monthly_installment", type = "FLOAT", mode = "NULLABLE" },
    { name = "duration_months", type = "INTEGER", mode = "NULLABLE" },
    { name = "down_payment", type = "FLOAT", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "recommendations" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "recommendations"
  deletion_protection = false

  # Snapshot columns replaced by forecast-curve columns after the reshape.
  schema = jsonencode([
    { name = "recommendation_id", type = "STRING", mode = "REQUIRED" },
    { name = "request_id", type = "STRING", mode = "NULLABLE" },
    { name = "customer_id", type = "STRING", mode = "NULLABLE" },
    { name = "recommendation", type = "STRING", mode = "NULLABLE" },
    { name = "ready_in_months", type = "INTEGER", mode = "NULLABLE" },
    { name = "risk_probability", type = "FLOAT", mode = "NULLABLE" },
    { name = "obligation_ratio_now", type = "FLOAT", mode = "NULLABLE" },
    { name = "obligation_ratio_peak", type = "FLOAT", mode = "NULLABLE" },
    { name = "first_shortfall_month", type = "INTEGER", mode = "NULLABLE" },
    { name = "first_shortfall_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "min_buffer_value", type = "FLOAT", mode = "NULLABLE" },
    { name = "months_of_savings_cover", type = "FLOAT", mode = "NULLABLE" },
    { name = "forecast_json", type = "STRING", mode = "NULLABLE" },
    { name = "validation_warnings_json", type = "STRING", mode = "NULLABLE" },
    { name = "explanation_ar", type = "STRING", mode = "NULLABLE" },
    { name = "risk_factors_json", type = "STRING", mode = "NULLABLE" },
    { name = "safer_options_json", type = "STRING", mode = "NULLABLE" },
    { name = "step_trace_json", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

module "artifact_registry" {
  source = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/artifact-registry?ref=master&depth=1"

  project_id  = var.project_id
  location    = var.region
  name        = var.artifact_registry_repo_name
  description = "Docker images for the Edraak Cloud Run application."
  labels      = var.labels

  format = {
    docker = {
      standard = {}
    }
  }

  depends_on = [
    google_project_service.required["artifactregistry.googleapis.com"],
  ]
}

resource "google_cloud_run_v2_service" "edraak" {
  count = var.create_cloud_run_service ? 1 : 0

  project             = var.project_id
  name                = var.service_name
  location            = var.region
  labels              = var.labels
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = module.cloud_run_service_account.email
    timeout         = "300s"

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      env {
        name  = "USE_BIGQUERY"
        value = "true"
      }

      env {
        name  = "USE_GEMINI"
        value = "true"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "BQ_DATASET"
        value = var.dataset_id
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.required["run.googleapis.com"],
    module.cloud_run_service_account,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.create_cloud_run_service && var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.edraak[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_secret_manager_secret" "placeholders" {
  for_each = var.create_secrets ? local.secret_ids : toset([])

  project   = var.project_id
  secret_id = each.value
  labels    = var.labels

  replication {
    auto {}
  }

  depends_on = [
    google_project_service.required["secretmanager.googleapis.com"],
  ]
}
