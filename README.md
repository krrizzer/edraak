# Edraak

Edraak is a hackathon prototype for an agentic AI CFO: a "financial seatbelt" that helps people test large financial commitments before they make them. It currently focuses on decisions such as car financing, housing commitments, wedding costs, travel, debt payoff, and emergency financing.

The project is intentionally safe for demos. The current application uses synthetic profiles, synthetic transactions, and readable mock agent logic. It does not connect to real banking data, Gemini, Vertex AI, ADK orchestration, or live BigQuery tables yet, but the codebase is structured so those integrations can be added later.

## What Is In This Repository

```text
.
|-- cloud-run/
|   `-- edrak/
|       |-- app/              # FastAPI backend, mock data, financial tools, agent orchestration
|       |-- ui/               # Vite + React frontend
|       |-- Dockerfile        # Builds the React UI and serves it from FastAPI
|       |-- deploy.sh         # Source deploy to Google Cloud Run
|       `-- README.md         # App-specific setup and API notes
`-- infra/
    |-- main.tf               # Google Cloud baseline infrastructure
    |-- variables.tf          # Terraform configuration variables
    |-- outputs.tf            # Terraform outputs
    |-- versions.tf           # Terraform and provider constraints
    `-- README.md             # Infrastructure-specific setup notes
```

## Product Flow

1. A user selects one of the synthetic financial profiles.
2. The user enters a proposed commitment: goal type, goal amount, monthly installment, duration, down payment, and urgency.
3. The backend calculates financial pressure signals such as obligation ratio, projected monthly buffer, risk score, and safety score.
4. Mock specialist agents generate a profile summary, risk factors, safer alternatives, and a 30/60/90-day readiness path.
5. The frontend presents the recommendation in Arabic with an agent trace and decision metrics.

## Architecture

- **Frontend:** Vite + React single-page app in `cloud-run/edrak/ui`.
- **Backend:** FastAPI app in `cloud-run/edrak/app`.
- **Mock data:** Synthetic customer profiles and transactions in `app/functions/mock_data.py`.
- **Financial logic:** Obligation ratio, monthly buffer, risk score, recommendations, safer options, and readiness paths in `app/functions/financial_tools.py`.
- **Agent layer:** Mock root orchestration and specialist agents in `app/agents`.
- **Cloud runtime:** Docker builds the UI, copies the static output into FastAPI, and serves both the API and frontend on port `8080`.
- **Infrastructure:** Terraform creates a small Google Cloud baseline for Cloud Run, Artifact Registry, BigQuery, Vertex AI readiness, IAM, Secret Manager placeholders, and logging.

## Run Locally

Run the backend:

```bash
cd cloud-run/edrak
pip install -r app/requirements.txt
uvicorn app.main:app --reload --port 8080
```

Run the UI in another terminal:

```bash
cd cloud-run/edrak/ui
npm install
npm run dev
```

The local Vite UI calls `http://localhost:8080` by default when running on port `5173`. In Docker and Cloud Run, API calls use the same origin.

## Build With Docker

```bash
cd cloud-run/edrak
docker build -t edraak-app .
docker run -p 8080:8080 edraak-app
```

Then open `http://localhost:8080`.

## API Endpoints

- `GET /api/health`
- `GET /api/profiles`
- `GET /api/transactions/{user_id}`
- `POST /api/analyze`

The request body for `POST /api/analyze` includes:

```json
{
  "user_id": "stable",
  "goal_type": "car",
  "goal_amount": 120000,
  "monthly_installment": 2500,
  "duration_months": 48,
  "down_payment": 10000,
  "urgency": "medium"
}
```

## Deploy The App

The application folder includes a Cloud Run source deployment script:

```bash
cd cloud-run/edrak
chmod +x deploy.sh
./deploy.sh
```

By default, it deploys the service as `edraak-app` in `me-central2`. Override the region with:

```bash
REGION=me-central2 ./deploy.sh
```

## Provision Google Cloud Infrastructure

The Terraform layer in `infra/` creates the baseline resources the prototype is designed to use:

- Required Google Cloud APIs
- Cloud Run runtime service account
- Minimal IAM permissions
- BigQuery dataset and tables for profiles, transactions, decision requests, and recommendations
- Artifact Registry Docker repository
- Optional placeholder Cloud Run service
- Optional Secret Manager secret containers

Apply it with:

```bash
cd infra
terraform init
terraform apply -var-file=terraform.tfvars
```

See `infra/README.md` for the full infrastructure notes and cost-conscious defaults.

## Environment Variables

The app works in mock mode without setting these values, but they define the future integration points:

```text
PORT=8080
USE_ADK=false
USE_GEMINI=false
GCP_PROJECT_ID=
BQ_DATASET=
BQ_PROFILES_TABLE=
BQ_TRANSACTIONS_TABLE=
BQ_RECOMMENDATIONS_TABLE=
VITE_API_BASE_URL=
```

## Current Status

Edraak is a prototype, not a production financial advisor. The current version is best used to demonstrate the decision flow, agent experience, Google Cloud architecture, and integration plan. Production readiness would require real data pipelines, authentication, authorization, privacy controls, auditable recommendations, tested ADK/Gemini orchestration, robust error handling, and formal financial compliance review.

## Next Integration Points

- Replace mock profiles and transactions with BigQuery reads in `app/functions/bigquery_data.py`.
- Persist decision requests and recommendations to BigQuery.
- Replace the mock root orchestration in `app/agents/root_agent.py` with real ADK agent orchestration.
- Enable Gemini or Vertex AI for generated explanations and recommendation review.
- Add authentication before connecting any real user or financial data.
