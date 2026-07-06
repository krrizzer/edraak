# Edraak Cloud Run App

Edraak is a Cloud Run-ready FastAPI + React prototype for an Agentic AI CFO / Financial Seatbelt. It helps a banking customer test whether a major financial commitment is safe before taking action.

The app runs in production-style mode only: it reads customer data from BigQuery and uses Gemini 2.5 Flash-Lite through Vertex AI. It does not fall back to local mock data or static agent responses.

## Flow

```text
login
-> identify customer
-> collect customer data from customers, transactions, loans
-> read derived user_profiles
-> run deterministic financial tools
-> build strict AgentContext
-> run agents sequentially
-> save decision and recommendation if BigQuery is enabled
-> return stable response to UI
```

The user logs in with an English username such as `fahad`, `sara`, or `khalid`, then enters only the financial goal details.

## Data Model

Source banking tables:

- `customers`
- `transactions`
- `loans`

Derived analytical table:

- `user_profiles`

`user_profiles` is not an original bank table. It is generated from real BigQuery `customers`, `transactions`, and `loans`, then stored in BigQuery. If the row is missing during analysis, the backend generates it on demand, saves it to `user_profiles`, then continues the agent flow.

The production loader is:

```text
app/functions/profile_loader.py
```

It reads real BigQuery `customers`, `transactions`, and `loans`, calculates the derived profile, then inserts into `user_profiles`. The normal app flow can call the same calculation automatically when a profile is missing.

## Agents

Agents live under `app/agents/`:

- `schemas.py`: shared context and strict agent output schemas
- `gemini_client.py`: Vertex AI Gemini JSON helper with strict schema validation
- `root_agent.py`: explicit orchestration
- `data_validation_agent.py`
- `profile_agent.py`
- `risk_agent.py`
- `alternatives_agent.py`
- `recommendation_agent.py`
- `tools.py`

The sequence is fixed:

1. Data validation agent
2. Profile agent
3. Risk agent
4. Alternatives agent
5. Recommendation agent

Each agent returns a Pydantic-validated schema. If Gemini is disabled, misconfigured, fails, or returns invalid JSON, the request fails. The app does not return deterministic/static agent text in production mode.

## Calculations

Python tools run before the agents:

- obligation ratio before
- obligation ratio after
- monthly buffer after
- risk score
- safety score
- deterministic recommendation

Gemini is not trusted for calculations or data retrieval. It only writes Arabic summaries, explanations, risks, alternatives, readiness steps, and recommendation wording based on calculated values.

## BigQuery

`USE_BIGQUERY=true` is required. The app reads:

- `customers`
- `transactions`
- `loans`
- `user_profiles`

The app writes only:

- `decision_requests`
- `recommendations`

`decision_requests` and `recommendations` are storage-only tables. They are not read back into the agent flow.

If BigQuery is unavailable, misconfigured, or fails to write, the request fails.

## Logs

When running locally, logs appear in the backend terminal running `python -m uvicorn app.main:app --reload --port 8080`.

The main log categories are:

- `edraak.api`: login, customer endpoints, analysis start/end, persistence
- `edraak.bigquery`: BigQuery table reads/writes and row counts
- `edraak.agents`: agent flow, tool outputs, validation status
- `edraak.gemini`: Vertex AI Gemini calls, model/location, response preview, schema validation

In Cloud Run, the same logs appear in the service logs.

## Vertex AI Gemini

Use Vertex AI only:

```text
USE_GEMINI=true
GCP_PROJECT_ID=YOUR_PROJECT_ID
VERTEX_LOCATION=global
GEMINI_MODEL=gemini-2.5-flash-lite
```

The app uses `google-genai` with `vertexai=True`. Do not use a Gemini API key path.

## Run Locally On Windows

Open VS Code at:

```text
C:\Users\yasse\Documents\github\edraak\cloud-run\edrak
```

### 1. Check Node.js And npm

In a new VS Code terminal, run:

```powershell
node -v
npm -v
```

If either command is not recognized, install Node.js LTS:

```powershell
winget install OpenJS.NodeJS.LTS
```

After installation, close VS Code completely, reopen it, and test again:

```powershell
node -v
npm -v
```

### 2. Run Backend Locally

```bash
cd cloud-run/edrak
pip install -r app/requirements.txt
python -m uvicorn app.main:app --reload --port 8080
```

Health check:

```bash
curl http://localhost:8080/api/health
```

For Vertex AI Gemini local mode:

```powershell
$env:USE_BIGQUERY="true"
$env:USE_GEMINI="true"
$env:GCP_PROJECT_ID="YOUR_PROJECT_ID"
$env:VERTEX_LOCATION="global"
$env:GEMINI_MODEL="gemini-2.5-flash-lite"
python -m uvicorn app.main:app --reload --port 8080
```

Keep this backend terminal running.

Optional: pre-load derived user profiles before analysis:

```powershell
curl.exe -X POST http://localhost:8080/api/admin/load-user-profiles
```

Optional: pre-load one customer profile only:

```powershell
curl.exe -X POST http://localhost:8080/api/admin/load-user-profiles -H "Content-Type: application/json" -d "{\"customer_id\":\"CUST002\"}"
```

### 3. Run UI Locally

Open a second VS Code terminal:

```bash
cd C:\Users\yasse\Documents\github\edraak\cloud-run\edrak\ui
npm install
npm run dev
```

Open the URL printed by Vite, usually:

```text
http://localhost:5173
```

Login with:

```text
fahad
sara
khalid
```

The Vite UI calls `http://localhost:8080` when running on port `5173`. In Docker and Cloud Run, API calls use same-origin requests.

## API

- `GET /api/health`
- `POST /api/login`
- `POST /api/admin/load-user-profiles`
- `GET /api/customer/{customer_id}`
- `GET /api/customer/{customer_id}/profile`
- `GET /api/customer/{customer_id}/transactions`
- `GET /api/customer/{customer_id}/loans`
- `POST /api/analyze`

## Build With Docker

```bash
cd cloud-run/edrak
docker build -t edraak-app .
docker run -p 8080:8080 edraak-app
```

Open:

```bash
http://localhost:8080
```

## Deploy to Cloud Run

```bash
cd cloud-run/edrak

gcloud run deploy edraak-app \
  --source . \
  --region me-central2 \
  --allow-unauthenticated \
  --set-env-vars USE_BIGQUERY=true,USE_GEMINI=true,GCP_PROJECT_ID=YOUR_PROJECT_ID,VERTEX_LOCATION=global,GEMINI_MODEL=gemini-2.5-flash-lite,BQ_DATASET=edraak_finance
```

Or use:

```bash
GCP_PROJECT_ID=YOUR_PROJECT_ID ./deploy.sh
```

## Environment Variables

```text
PORT=8080
USE_BIGQUERY=true
USE_GEMINI=true
GCP_PROJECT_ID=
VERTEX_LOCATION=global
GEMINI_MODEL=gemini-2.5-flash-lite
BQ_DATASET=edraak_finance
BQ_CUSTOMERS_TABLE=customers
BQ_TRANSACTIONS_TABLE=transactions
BQ_LOANS_TABLE=loans
BQ_USER_PROFILES_TABLE=user_profiles
BQ_DECISION_REQUESTS_TABLE=decision_requests
BQ_RECOMMENDATIONS_TABLE=recommendations
VITE_API_BASE_URL=
```

The application path expects real BigQuery table data. Synthetic SQL files can still be used to seed a demo dataset, but the running app does not use in-code mock data.
