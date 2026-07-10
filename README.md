# Edraak

Edraak is a hackathon prototype for a **cross-bank financial seatbelt** built on
simulated SAMA Open Banking data. It sees a customer's accounts, loans, BNPL
stacks, and informal obligations across ALL of their banks, simulates the next
12 months of cash flow month by month, and warns them — in Arabic — before a
commitment or a spending pace gets them into trouble.

Two modes after login:

- **حزام الأمان المالي (Decision Seatbelt):** test a commitment before signing.
  The forecast knows that a loan with 2 installments left stops costing money in
  month 3 — so instead of a blanket "no" it can say
  "ليس الآن — لكن بعد شهرين يصبح القرار آمنًا، وهذا هو السبب".
- **الرادار المالي (Financial Radar):** current-month monitoring that projects
  the balance at every upcoming installment date and fires one actionable alert:
  "بناءً على وتيرة صرفك الحالية، ستنقصك 340 ريال عن قسط يوم 27 — تقليل مصروف
  المقاهي هذا الأسبوع يغطي الفجوة."

**Architecture principle:** the LLM understands messy data and communicates;
deterministic Python computes every number. The LLM never invents or overrides
a number.

## What Is In This Repository

```text
.
|-- cloud-run/
|   `-- edrak/
|       |-- app/              # FastAPI backend
|       |   |-- main.py       #   thin routes
|       |   |-- pipeline.py   #   Mode A / Mode B orchestration + honest trace
|       |   |-- functions/    #   deterministic: forecast, verdict, radar, risk model
|       |   |-- agents/       #   3 LLM agents on Vertex AI Gemini
|       |   `-- data/         #   BigQuery client + seed generator
|       |-- ui/               # Vite + React frontend (Arabic, RTL)
|       |-- tests/            # unit tests for the deterministic layer
|       |-- Dockerfile        # builds UI, trains risk model, serves from FastAPI
|       `-- deploy.sh         # source deploy to Google Cloud Run
|-- bigquery/                 # manual SQL setup (alternative to Terraform)
`-- infra/                    # Terraform: BigQuery, Cloud Run SA, Artifact Registry
```

## The Pipeline (Mode A)

`validator → recurrence_detector (deterministic) → transaction_intelligence
(LLM) → forecast_engine → risk_model → verdict_rules (deterministic) →
decision_advisor (LLM)`

- **Recurrence Detector** (deterministic Python) finds *what* recurs — groups
  of transactions with a consistent amount on a consistent day across months,
  kept when they're isolated by amount (a rent nobody else matches) or carry a
  real provider signal (`TABBY`, `SADAD`, `NETFLIX`).
- **Transaction Intelligence Agent** only labels *what each group is* (جمعية vs
  family transfer vs BNPL vs rent) from the messy narrative strings ("تمارا -
  قسط 2 من 4", "POS TABBY* PAYMENT RUH"). Python owns every amount, day, and
  bank, so the LLM can't invent a number; results are cached in
  `detected_obligations`.
- **Forecast Engine** projects income, committed outflow, buffer, obligation
  ratio, and savings for the next 12 months, respecting `remaining_months` on
  every loan and BNPL stack.
- **Verdict Rules** decide قرار آمن / مقبول بحذر / الأفضل تأجيله / غير مناسب over
  the curve, including `ready_in_months` when waiting fixes a temporary overlap.
- **Risk Model** (scikit-learn, trained on synthetic data at build time) adds a
  displayed `P(missed payment)` — it never decides the verdict.
- **Decision Advisor Agent** writes the Arabic result and must echo the
  deterministic verdict exactly, or the backend rejects it.

See [ARCHITECTURE.md](ARCHITECTURE.md) for diagrams and details.

## Run Locally

Run the backend (BigQuery + Vertex AI credentials required — one mode, no mocks):

```bash
cd cloud-run/edrak
pip install -r app/requirements.txt
python -m app.functions.risk_model          # train the placeholder risk model once
export GCP_PROJECT_ID=your-project
uvicorn app.main:app --reload --port 8080
```

Run the UI in another terminal:

```bash
cd cloud-run/edrak/ui
npm install
npm run dev
```

The local Vite UI calls `http://localhost:8080` by default when running on port
`5173`. In Docker and Cloud Run, API calls use the same origin.

Run the tests:

```bash
cd cloud-run/edrak
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Seed The Demo Data

Seed dates are generated relative to the day you run the loader — that is what
keeps the radar demo alive:

```bash
cd cloud-run/edrak
GCP_PROJECT_ID=your-project python -m app.data.seed.load_seed_data
```

Demo users: `fahad` (the cross-bank hero → الأفضل تأجيله), `sara` (healthy →
قرار آمن), `khalid` (radar customer → gap ≈ 340 SAR before the day-27
installment), `noura` (overstretched → غير مناسب).

## API Endpoints

- `GET /api/health`
- `POST /api/login` — `{"username": "fahad"}`
- `POST /api/analyze` — Mode A (body below)
- `POST /api/radar/trigger` — Mode B — `{"customer_id": "CUST003"}`
- `GET /api/alerts/{customer_id}` — stored radar alerts

The request body for `POST /api/analyze`:

```json
{
  "customer_id": "CUST001",
  "goal_type": "car",
  "goal_amount": 120000,
  "monthly_installment": 2500,
  "duration_months": 48,
  "down_payment": 10000
}
```

The response includes the verdict, the 12 forecast rows with an uncertainty
band (for the chart), first-shortfall info, the obligation-ratio curve summary,
`risk_probability`, `ready_in_months`, detected obligations grouped by bank (the
"ما لا يراه بنكك" panel), the Arabic explanation, risk factors and safer
alternatives, validation warnings, and the honest step trace.

## Build With Docker

```bash
cd cloud-run/edrak
docker build -t edraak-app .
docker run -p 8080:8080 -e GCP_PROJECT_ID=your-project edraak-app
```

## Deploy The App

```bash
cd cloud-run/edrak
GCP_PROJECT_ID=your-project ./deploy.sh
```

By default, it deploys the service as `edraak-app` in `me-central2`.

## Provision Google Cloud Infrastructure

```bash
cd infra
terraform init
terraform apply -var-file=terraform.tfvars
```

Terraform creates the BigQuery dataset and tables (`customers`, `accounts`,
`transactions`, `loans`, `user_profiles`, `detected_obligations`,
`decision_requests`, `recommendations`, `alerts`), the Cloud Run service
account with minimal IAM, and the Artifact Registry repository. See
`infra/README.md`.

## Environment Variables

```text
PORT=8080
USE_BIGQUERY=true
USE_GEMINI=true
GCP_PROJECT_ID=
BQ_DATASET=edraak_finance
VERTEX_LOCATION=global
GEMINI_MODEL=gemini-2.5-flash-lite
RISK_MODEL_PATH=            # optional; defaults to app/functions/models/risk_model.joblib
VITE_API_BASE_URL=          # optional UI override
```
