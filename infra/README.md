# Edraak Infrastructure

This folder contains a small Terraform layer for the Edraak hackathon prototype. It creates the baseline Google Cloud resources needed by the Cloud Run app in `../cloud-run/edrak`.

## What This Creates

- Required Google Cloud APIs for Cloud Run, Cloud Build, Artifact Registry, BigQuery, Vertex AI, IAM, Secret Manager, and Logging
- A Cloud Run runtime service account
- Minimal project IAM for that service account
- One BigQuery dataset named `edraak_finance` by default
- Four BigQuery tables for profiles, transactions, decision requests, and recommendations
- One Docker Artifact Registry repository
- An optional placeholder Cloud Run service using a public sample image
- Optional Secret Manager secret containers with no real secret values

This project uses Google Cloud Foundation Fabric modules where they keep the code shorter and cleaner:

https://github.com/GoogleCloudPlatform/cloud-foundation-fabric

The full FAST landing-zone structure is intentionally not used. Edraak is a lightweight hackathon prototype, not an enterprise landing zone.

## What This Does Not Create

To avoid unexpected cost, this layer does not create GKE, GPUs, VPC, NAT, load balancers, Cloud SQL, Memorystore, scheduled jobs, logging sinks, always-on instances, or production-scale storage.

The Cloud Run service uses min instances `0`, BigQuery is limited to a small dataset and tables, Secret Manager is optional, and Artifact Registry is a single Docker repository.

## Prerequisites

- `gcloud` authenticated
- Correct Google Cloud project selected
- Billing enabled on the project
- Terraform installed, version `1.5` or newer

## Configure

Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:

```hcl
project_id = "YOUR_REAL_PROJECT_ID"
```

Adjust region, dataset name, Cloud Run public access, or optional secrets only if needed.

## Apply

```bash
terraform init
terraform apply -var-file=terraform.tfvars
```

## Destroy

```bash
terraform destroy -var-file=terraform.tfvars
```

## Deploy The Real App Later

Terraform creates the baseline infrastructure. The actual app deployment can happen separately from the Cloud Run app folder:

```bash
gcloud run deploy edraak-app --source ../cloud-run/edrak --region me-central2
```

That command replaces the placeholder Cloud Run sample container with the real Edraak FastAPI + React application.

If Terraform created the placeholder Cloud Run service, a future `terraform apply` may try to return it to the sample image. For a hackathon flow, use Terraform for baseline infra and use `gcloud run deploy` for app releases, or later add a real image variable to Terraform when you want Terraform to manage releases too.

## Notes

BigQuery integration should be added later in `../cloud-run/edrak/app/functions/bigquery_data.py`.

ADK and Gemini integration should be added later in `../cloud-run/edrak/app/agents/root_agent.py` and `../cloud-run/edrak/app/agents/tools.py`.

Do not put real secret values in Terraform. If `create_secrets = true`, Terraform creates empty secret containers only. Add real values manually or through CI/CD.
