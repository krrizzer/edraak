output "project_id" {
  description = "Google Cloud project ID."
  value       = var.project_id
}

output "region" {
  description = "Google Cloud region used for regional resources."
  value       = var.region
}

output "cloud_run_service_name" {
  description = "Cloud Run service name, if created."
  value       = var.create_cloud_run_service ? google_cloud_run_v2_service.edraak[0].name : null
}

output "cloud_run_service_url" {
  description = "Cloud Run service URL, if created."
  value       = var.create_cloud_run_service ? google_cloud_run_v2_service.edraak[0].uri : null
}

output "cloud_run_service_account_email" {
  description = "Runtime service account email for the Cloud Run app."
  value       = module.cloud_run_service_account.email
}

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID."
  value       = google_bigquery_dataset.edraak.dataset_id
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository URL."
  value       = module.artifact_registry.url
}

output "enabled_apis" {
  description = "Google Cloud APIs enabled by this Terraform layer."
  value       = sort([for api in google_project_service.required : api.service])
}
