project_id        = "YOUR_PROJECT_ID"
region            = "me-central2"
bigquery_location = "me-central2"

service_name                   = "edraak-app"
cloud_run_service_account_name = "edraak-cloud-run-sa"

dataset_id                  = "edraak_finance"
artifact_registry_repo_name = "edraak"

create_cloud_run_service = true
allow_unauthenticated    = true
create_secrets           = false

labels = {
  project = "edraak"
  env     = "hackathon"
  owner   = "yasser"
}
