project_id        = "project-53540efb-1397-45cd-9d9"
region            = "us-central1"
bigquery_location = "us-central1"

service_name                   = "edraak-app"
cloud_run_service_account_name = "edraak-cloud-run-sa"

dataset_id                  = "edraak_finance"
artifact_registry_repo_name = "edraak"

create_cloud_run_service = false
allow_unauthenticated    = true
create_secrets           = false

labels = {
  project = "edraak"
  env     = "hackathon"
  owner   = "yasser"
}
