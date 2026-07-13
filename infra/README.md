# Edraak Infrastructure

This folder contains a small Terraform layer for the Edraak hackathon prototype. It creates the baseline Google Cloud resources needed by the Cloud Run app in `../cloud-run/edrak`.

## What This Creates

- Required Google Cloud APIs for Cloud Run, Cloud Build, Artifact Registry, BigQuery, Vertex AI, IAM, Secret Manager, and Logging
- A Cloud Run runtime service account
- Minimal project IAM for that service account
- One BigQuery dataset named `edraak_finance` by default
- Nine BigQuery tables: `customers`, `accounts`, `transactions`, `loans`,
  `user_profiles`, `detected_obligations`, `decision_requests`,
  `recommendations`, and `alerts`
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
do ```bash
Download the Google Cloud CLI Installer from google 
```

if doesnt work in vs code do : 


```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
then try 
```bash
gcloud --version
```
do
```bash
gcloud auth login
```
then do
```bash
gcloud auth application-default login
```
then do
```bash
gcloud auth application-default set-quota-project project-53540efb-1397-45cd-9d9
```
then do 
```bash
gcloud config set project project-53540efb-1397-45cd-9d9
```

then confirm project: 
```bash
gcloud config get-value project
```


- Correct Google Cloud project selected
- Billing enabled on the project
- Terraform installed, version `1.5` or newer

### Install Terraform On Windows

1. Download the Terraform executable.

Go to the official [Terraform Download Page](https://developer.hashicorp.com/terraform/install).

Under the Windows tab, download the `amd64` version. It will download a `.zip` file. Extract it, and you will see one file named:

```text
terraform.exe
```

2. Move Terraform to a permanent folder.

Do not leave it in your Downloads folder. Create a permanent folder, for example:

```text
C:\terraform
```

Move `terraform.exe` into that `C:\terraform` folder.

3. Add Terraform to your Windows PATH.

Press the Windows key, type `env`, and select **Edit the system environment variables**.

Click **Environment Variables...** at the bottom right.

Under **System variables**, find `Path` and double-click it.

Click **New** and add:

```text
C:\terraform
```

Click **OK** on all open windows to save.

4. Restart VS Code and test.

Close VS Code completely, then open it again. Open a new terminal and run:

```powershell
terraform --version
```

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
terraform apply -var-file="terraform.tfvars"
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

That command replaces the placeholder Cloud Run sample container with the real Edraak FastAPI + Flutter application. Deploy the mock gateway (`cloud-run/mock-bank`) as a second Cloud Run service and set `OPENBANKING_GATEWAY_URL` on the app.

If Terraform created the placeholder Cloud Run service, a future `terraform apply` may try to return it to the sample image. For a hackathon flow, use Terraform for baseline infra and use `gcloud run deploy` for app releases, or later add a real image variable to Terraform when you want Terraform to manage releases too.

## Notes

All BigQuery reads and writes live in `../cloud-run/edrak/app/data/bigquery_client.py`.

Vertex AI Gemini calls live in `../cloud-run/edrak/app/agents/gemini_client.py`.

After `terraform apply`, load the demo data with
`python -m app.data.seed.load_seed_data` from `../cloud-run/edrak`.

Do not put real secret values in Terraform. If `create_secrets = true`, Terraform creates empty secret containers only. Add real values manually or through CI/CD.
