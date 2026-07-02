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

resource "google_bigquery_table" "customer_profiles" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "customer_profiles"
  deletion_protection = false

  schema = jsonencode([
    { name = "user_id", type = "STRING", mode = "REQUIRED" },
    { name = "name_ar", type = "STRING", mode = "NULLABLE" },
    { name = "monthly_income", type = "FLOAT", mode = "NULLABLE" },
    { name = "current_balance", type = "FLOAT", mode = "NULLABLE" },
    { name = "savings", type = "FLOAT", mode = "NULLABLE" },
    { name = "monthly_obligations", type = "FLOAT", mode = "NULLABLE" },
    { name = "risk_preference_ar", type = "STRING", mode = "NULLABLE" },
    { name = "behavior_summary_ar", type = "STRING", mode = "NULLABLE" },
    { name = "avg_flexible_spending", type = "FLOAT", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "transactions" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "transactions"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  schema = jsonencode([
    { name = "transaction_id", type = "STRING", mode = "REQUIRED" },
    { name = "user_id", type = "STRING", mode = "REQUIRED" },
    { name = "transaction_date", type = "DATE", mode = "NULLABLE" },
    { name = "merchant", type = "STRING", mode = "NULLABLE" },
    { name = "category", type = "STRING", mode = "NULLABLE" },
    { name = "amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "transaction_type", type = "STRING", mode = "NULLABLE" },
    { name = "is_recurring", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "decision_requests" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "decision_requests"
  deletion_protection = false

  schema = jsonencode([
    { name = "request_id", type = "STRING", mode = "REQUIRED" },
    { name = "user_id", type = "STRING", mode = "REQUIRED" },
    { name = "goal_type", type = "STRING", mode = "NULLABLE" },
    { name = "goal_amount", type = "FLOAT", mode = "NULLABLE" },
    { name = "monthly_installment", type = "FLOAT", mode = "NULLABLE" },
    { name = "duration_months", type = "INTEGER", mode = "NULLABLE" },
    { name = "down_payment", type = "FLOAT", mode = "NULLABLE" },
    { name = "urgency", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "recommendations" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.edraak.dataset_id
  table_id            = "recommendations"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  schema = jsonencode([
    { name = "recommendation_id", type = "STRING", mode = "REQUIRED" },
    { name = "request_id", type = "STRING", mode = "NULLABLE" },
    { name = "user_id", type = "STRING", mode = "NULLABLE" },
    { name = "recommendation", type = "STRING", mode = "NULLABLE" },
    { name = "risk_score", type = "FLOAT", mode = "NULLABLE" },
    { name = "safety_score", type = "FLOAT", mode = "NULLABLE" },
    { name = "explanation_ar", type = "STRING", mode = "NULLABLE" },
    { name = "safer_options_json", type = "STRING", mode = "NULLABLE" },
    { name = "readiness_path_json", type = "STRING", mode = "NULLABLE" },
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
        name  = "USE_ADK"
        value = "false"
      }

      env {
        name  = "USE_GEMINI"
        value = "false"
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
