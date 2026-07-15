variable "project_id" {
  description = "Google Cloud project ID where Edraak infrastructure will be created."
  type        = string
}

variable "region" {
  description = "Google Cloud region for regional resources."
  type        = string
  default     = "me-central2"
}

variable "bigquery_location" {
  description = "BigQuery dataset location."
  type        = string
  default     = "me-central2"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "edraak-app"
}

variable "cloud_run_service_account_name" {
  description = "Service account name used by the Cloud Run application."
  type        = string
  default     = "edraak-cloud-run-sa"
}

variable "dataset_id" {
  description = "BigQuery dataset ID for Edraak prototype data."
  type        = string
  default     = "edraak_finance"
}

variable "bank_cores_dataset_id" {
  description = "BigQuery dataset ID for the simulated core-banking data behind the mock gateway."
  type        = string
  default     = "bank_cores"
}

variable "artifact_registry_repo_name" {
  description = "Artifact Registry Docker repository name."
  type        = string
  default     = "edraak"
}

variable "create_cloud_run_service" {
  description = "Whether Terraform should create the placeholder Cloud Run service."
  type        = bool
  default     = true
}

variable "allow_unauthenticated" {
  description = "Whether to allow public unauthenticated access to the Cloud Run service."
  type        = bool
  default     = true
}

variable "create_secrets" {
  description = "Whether to create placeholder Secret Manager secret containers."
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels applied to supported resources."
  type        = map(string)
  default = {
    project = "edraak"
    env     = "hackathon"
  }
}
