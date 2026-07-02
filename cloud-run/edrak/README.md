# Edraak

Edraak is an Agentic AI CFO / Financial Seatbelt prototype for major financial commitments. It helps a user test decisions such as car financing, housing commitments, weddings, travel, debt payoff, emergency financing, and other large commitments before taking action.

The current version uses only synthetic data and mock agent logic. It is safe for prototype and hackathon demos, and it does not connect to real BigQuery, Gemini, Vertex AI, or banking systems yet.

## Folder Structure

```text
cloud-run/edrak/
  README.md
  Dockerfile
  .dockerignore
  deploy.sh
  app/
    main.py
    requirements.txt
    functions/
      __init__.py
      mock_data.py
      bigquery_data.py
      financial_tools.py
    agents/
      __init__.py
      root_agent.py
      profile_agent.py
      risk_agent.py
      alternatives_agent.py
      recommendation_agent.py
      tools.py
  ui/
    package.json
    index.html
    src/
      main.jsx
      App.jsx
      styles.css
```

## Why These Folders Exist

`app/` contains the FastAPI backend and Cloud Run entry point.

`ui/` contains the minimal Vite + React frontend. The Docker build compiles it and copies the static files into `app/static`.

`agents/` contains the mock agent orchestration that will later map to Google ADK agents and tools. The app works locally today without requiring ADK, Gemini, or Vertex AI configuration.

## Run Backend Locally

```bash
cd cloud-run/edrak
pip install -r app/requirements.txt
uvicorn app.main:app --reload --port 8080
```

Health check:

```bash
curl http://localhost:8080/api/health
```

## Run UI Locally

```bash
cd cloud-run/edrak/ui
npm install
npm run dev
```

During local UI development, the frontend calls `http://localhost:8080` when Vite is running on port `5173`. In Docker and Cloud Run, the UI uses same-origin API calls. You can override the API URL with `VITE_API_BASE_URL`.

## Build and Run With Docker

```bash
cd cloud-run/edrak
docker build -t edraak-app .
docker run -p 8080:8080 edraak-app
```

Then open:

```bash
http://localhost:8080
```

## Deploy to Cloud Run

```bash
cd cloud-run/edrak
chmod +x deploy.sh
./deploy.sh
```

The script deploys the service as `edraak-app` to `me-central2` by default. Override the region with:

```bash
REGION=me-central2 ./deploy.sh
```

## Environment Variables

```text
PORT=8080
USE_ADK=false
USE_GEMINI=false
GCP_PROJECT_ID=
BQ_DATASET=
BQ_PROFILES_TABLE=
BQ_TRANSACTIONS_TABLE=
BQ_RECOMMENDATIONS_TABLE=
```

## BigQuery Integration

Future BigQuery work belongs in `app/functions/bigquery_data.py`. The placeholder functions already show where to load customer profiles, load transactions, and save recommendations.

## ADK and Gemini Integration

Future Google ADK orchestration belongs in `app/agents/root_agent.py`. Agent-facing tools are collected in `app/agents/tools.py`, so they can later become real ADK tools without changing the API contract.

## Current API

- `GET /api/health`
- `GET /api/profiles`
- `GET /api/transactions/{user_id}`
- `POST /api/analyze`

All calculations are intentionally simple, readable, and mock-based so a developer can understand the full project quickly and replace pieces with production integrations later.
