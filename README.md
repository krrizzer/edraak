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
|   |-- edrak/                # THE PRODUCT (Cloud Run service #1)
|   |   |-- app/              #   FastAPI backend
|   |   |   |-- main.py       #     thin routes
|   |   |   |-- pipeline.py   #     Mode A / Mode B orchestration + honest trace
|   |   |   |-- functions/    #     deterministic: forecast, verdict, radar, risk, completeness
|   |   |   |-- agents/       #     3 LLM agents on Vertex AI Gemini
|   |   |   `-- data/         #     BigQuery client, ingestion pipeline, seed generator
|   |   |-- ui/               #   Flutter web app (Arabic, RTL, Alinma-inspired)
|   |   |-- tests/            #   unit tests for the deterministic layer
|   |   |-- Dockerfile        #   builds Flutter web, trains risk model, serves from FastAPI
|   |   `-- deploy.sh         #   source deploy to Google Cloud Run
|   `-- mock-bank/            # MOCK KSAOB GATEWAY (Cloud Run service #2)
|       |-- main.py           #   consent-gated AIS API + bank-side approval screen
|       |-- bank_cores.py     #   the banks' data, in RAM (never BigQuery)
|       `-- generate_seed_data.py  # shared generator (kept in sync with edrak's)
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

The system is **two backend services + a Flutter app**, so a full local run uses
three terminals. See [RUNNING.md](RUNNING.md) for the complete guide; the short
version:

**Terminal 1 — the mock KSAOB gateway** (plays the banks; no BigQuery):

```bash
cd cloud-run/mock-bank
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8081
# Swagger (the API page): http://localhost:8081/docs
```

**Terminal 2 — the Edraak backend** (BigQuery + Vertex AI credentials required):

```bash
cd cloud-run/edrak
pip install -r app/requirements.txt
python -m app.functions.risk_model                 # train the placeholder risk model once
export GCP_PROJECT_ID=your-project
export OPENBANKING_GATEWAY_URL=http://localhost:8081
python -m app.data.seed.load_seed_data             # seed FIRST-PARTY data only
python -m uvicorn app.main:app --reload --port 8080
```

**Terminal 3 — the Flutter app** (needs the Flutter SDK: https://docs.flutter.dev/get-started/install):

```bash
cd cloud-run/edrak/ui
flutter pub get
flutter run -d chrome \
  --dart-define=API_BASE=http://localhost:8080 \
  --dart-define=GATEWAY_BASE=http://localhost:8081
```

Run the tests:

```bash
cd cloud-run/edrak
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Seed The Demo Data

The seeder loads **only first-party data** into BigQuery — each customer's home
bank, plus `customers` and `loans` (a bureau-style feed). Every *other* bank's
accounts and transactions live in the gateway's memory until the in-app consent
flow pulls them. Seed dates are relative to the run day (keeps the radar alive):

```bash
cd cloud-run/edrak
GCP_PROJECT_ID=your-project python -m app.data.seed.load_seed_data
```

Demo users: `fahad` (the cross-bank hero → الأفضل تأجيله after linking his other
banks), `sara` (healthy → قرار آمن), `khalid` (radar customer → gap ≈ 340 SAR
before the day-27 installment), `noura` (overstretched → غير مناسب).

The strongest demo beat: analyze `fahad` **before** linking — he looks healthy at
Al Rajhi. Then link SNB + Riyad through the consent flow (the coverage card even
tells you SNB is missing, from the bureau loan) and re-analyze — the hidden BNPL
stacks and other-bank loan surface, and the verdict flips.

## API Endpoints

Edraak backend:

- `GET /api/health`
- `GET /api/ui-config` — runtime config for the app (the gateway URL)
- `POST /api/login` — `{"username": "fahad"}`
- `GET /api/coverage/{customer_id}` — is the linked data enough? which banks to add?
- `POST /api/ingest` — `{"customer_id","bank_code","consent_id"}` — pull a consented bank
- `GET /api/consents/{customer_id}` — linked-account consents
- `POST /api/analyze` — Mode A (body below)
- `POST /api/radar/trigger` — Mode B — `{"customer_id": "CUST003"}`
- `GET /api/alerts/{customer_id}` — stored radar alerts

Mock KSAOB gateway (separate service, port 8081):

- `GET /docs` — the interactive API page (Swagger)
- `POST /{bank}/open-banking/v1/consents` → `GET/POST /{bank}/authorize` (approval)
- `GET /{bank}/open-banking/v1/accounts | .../balances | .../transactions` (consent-gated)
- `DELETE /{bank}/open-banking/v1/consents/{id}` — revoke

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
