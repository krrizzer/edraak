# Edraak Cloud Run App

Edraak is a Cloud Run-ready FastAPI + React prototype for testing large financial commitments before a customer takes action.

The current app uses synthetic banking data and mock sequential agents. It does not require BigQuery, Gemini, Vertex AI, or Google ADK to run locally.

## Current Flow

```text
login
-> identify customer
-> collect customer data from source tables
-> generate derived financial profile
-> validate data
-> run agents sequentially
-> return recommendation
-> show result in UI
```

The user no longer selects a fake profile. They log in with an English username such as `fahad`, `sara`, or `khalid`, then enter only the financial goal details.

## Data Model

Source banking tables:

- `customers`: customer identity, Arabic/English names, salary, balance, birthday, and national ID placeholder.
- `transactions`: customer spending and income history linked by `customer_id`.
- `loans`: active and closed loan commitments linked by `customer_id`.

Derived analytical table/object:

- `user_profiles`: generated from `customers`, `transactions`, and `loans`.

The bank does not originally own a user profile table. Edraak derives it through `app/functions/load_user_profiles.py`.

## Project Structure

```text
cloud-run/edrak/
  README.md
  Dockerfile
  deploy.sh
  app/
    main.py
    requirements.txt
    functions/
      mock_data.py
      bigquery_data.py
      load_user_profiles.py
      tools/
        calculate_obligation_ratio.py
        calculate_monthly_buffer.py
        calculate_risk_score.py
        detect_recurring_obligations.py
        categorize_spending.py
    agents/
      root_agent.py
      data_validation_agent.py
      profile_agent.py
      risk_agent.py
      alternatives_agent.py
      recommendation_agent.py
      tools.py
  ui/
    src/
      App.jsx
      styles.css
```

## Agents

Agents run only after the API has collected customer, transaction, loan, and derived profile data.

Order:

1. `data_validation_agent.py`
2. `profile_agent.py`
3. `risk_agent.py`
4. `alternatives_agent.py`
5. `recommendation_agent.py`

`root_agent.py` coordinates the sequence. `agents/tools.py` keeps small ADK-ready wrappers around the calculation functions.

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

Generate derived user profiles manually:

```bash
curl -X POST http://localhost:8080/api/admin/load-user-profiles
```

You can also run:

```bash
python -m app.functions.load_user_profiles
```

## Run UI Locally

```bash
cd cloud-run/edrak/ui
npm install
npm run dev
```

The Vite UI calls `http://localhost:8080` when running on port `5173`. In Docker and Cloud Run, API calls use same-origin requests. Override with `VITE_API_BASE_URL` if needed.

## API

- `GET /api/health`
- `POST /api/login`
- `POST /api/admin/load-user-profiles`
- `GET /api/customer/{customer_id}`
- `GET /api/customer/{customer_id}/profile`
- `GET /api/customer/{customer_id}/transactions`
- `GET /api/customer/{customer_id}/loans`
- `POST /api/analyze`

## BigQuery Placeholder

`app/functions/bigquery_data.py` mirrors the future BigQuery tables:

- `customers`
- `transactions`
- `loans`
- `user_profiles`
- `decision_requests`
- `recommendations`

For now, these functions call mock data so local running is not blocked by BigQuery setup.

## Build and Run With Docker

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
chmod +x deploy.sh
./deploy.sh
```

The script deploys `edraak-app` to `me-central2` by default. Override the region with:

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
BQ_CUSTOMERS_TABLE=customers
BQ_TRANSACTIONS_TABLE=transactions
BQ_LOANS_TABLE=loans
BQ_USER_PROFILES_TABLE=user_profiles
BQ_DECISION_REQUESTS_TABLE=decision_requests
BQ_RECOMMENDATIONS_TABLE=recommendations
VITE_API_BASE_URL=
```

All data is synthetic and safe for prototype or hackathon demos.
