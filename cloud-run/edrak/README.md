# Edraak Cloud Run App

Edraak is a Cloud Run-ready FastAPI + React prototype for a cross-bank
financial seatbelt on simulated SAMA Open Banking data. It sees the customer's
accounts, loans, and raw transactions across ALL of their banks, simulates the
next 12 months of cash flow, and communicates the result in Arabic.

The app runs in production-style mode only: it reads from BigQuery and uses
Gemini 2.5 Flash-Lite through Vertex AI. There is no mock mode and no static
fallback text.

**Architecture principle:** the LLM understands messy data and communicates;
deterministic Python computes every number. The LLM never invents or overrides
a number.

## Two Modes

### Mode A — Decision Seatbelt (`POST /api/analyze`)

```text
login
-> load customers, accounts, transactions, loans across all banks
-> validator                  (deterministic)
-> transaction intelligence   (LLM, or fresh detected_obligations cache)
-> profile builder            (deterministic, cross-bank aggregates)
-> forecast engine            (deterministic, 12 months, remaining_months aware)
-> risk model                 (scikit-learn, P(missed payment))
-> verdict rules              (deterministic, curve rules + ready_in_months)
-> decision advisor           (LLM, must echo the verdict exactly)
-> store decision_requests + recommendations (storage only)
-> respond with forecast rows, obligations by bank, advice, honest trace
```

### Mode B — Financial Radar (`POST /api/radar/trigger`)

```text
radar detector (deterministic):
  month-to-date pace per category vs trailing 3-month same-day-window baseline
  projected balance at every upcoming committed payment date this month
  gap -> amount, date, cause category (biggest positive deviation)
-> intervention agent (LLM): ONE short actionable Arabic alert
-> store in alerts (storage only) and return with the trajectory numbers
```

In production the radar trigger would be a Cloud Scheduler job; the UI button
simulates it.

## Project Layout

```text
app/
  main.py                  # FastAPI routes only, thin
  config.py                # env, table names, model path
  pipeline.py              # step orchestration for both modes + honest trace
  data/
    bigquery_client.py     # ALL BigQuery reads/writes
    seed/                  # demo data generator + loader (dates relative to today)
  functions/               # deterministic layer, unit-tested
    validator.py           # completeness/consistency checks (plain Python)
    profile_builder.py     # cross-bank user_profiles row
    forecast_engine.py     # 12-month projection (the brain)
    verdict_rules.py       # curve rules; thresholds in one dict at the top
    radar.py               # current-month gap detection
    risk_model.py          # sklearn logistic regression; synthetic training data
  agents/                  # the only LLM code
    gemini_client.py       # Vertex AI calls + strict schema validation + number audit
    schemas.py             # all Pydantic response schemas
    transaction_intelligence.py
    decision_advisor.py
    intervention.py
ui/                        # Vite + React (Arabic, RTL): mode select, chart, radar
tests/                     # forecast/verdict/radar unit tests
```

## Data Rules

- Source tables: `customers`, `accounts`, `transactions` (with the messy
  `raw_description` the agent reads), `loans` (with `remaining_months`).
- Derived: `user_profiles` (cross-bank aggregates), `detected_obligations`
  (cache of agent output, reused while fresh — see
  `OBLIGATION_CACHE_MAX_AGE_HOURS`).
- Storage-only, never read by agents: `decision_requests`, `recommendations`,
  `alerts`.
- The Transaction Intelligence Agent must cite supporting transaction ids;
  Python recomputes amount/day/banks from those rows and replaces any amount
  off by more than 15%.
- The Decision Advisor must return `recommendation` equal to the deterministic
  verdict or the request fails with HTTP 502.

## Run Locally

```bash
pip install -r app/requirements.txt
python -m app.functions.risk_model      # trains + saves the placeholder model
export GCP_PROJECT_ID=your-project      # BigQuery + Vertex AI credentials required
uvicorn app.main:app --reload --port 8080
```

UI:

```bash
cd ui
npm install
npm run dev
```

Seed the demo data (dates are relative to the run day — reseed near demo day):

```bash
GCP_PROJECT_ID=your-project python -m app.data.seed.load_seed_data
```

Tests:

```bash
pip install -r ../requirements-dev.txt   # or: pip install pytest
python -m pytest tests/
```

## Demo Users

| user | story | expected outcome |
|---|---|---|
| `fahad` | healthy at Al Rajhi; SNB loan with 2 months left + 3 BNPL stacks + جمعية + family transfer at other banks | Mode A on 2,500/mo car → الأفضل تأجيله, ready in ~2 months |
| `sara` | strong salary, one car loan, no BNPL | Mode A → قرار آمن |
| `khalid` | salary day 1, cafe spending accelerating, 3,100 installment day 27 | Mode B radar → gap ≈ 340 SAR |
| `noura` | 9,500 salary, rent + loan + 3 BNPL stacks, thin savings | Mode A → غير مناسب |

Note: the radar demo needs the seed to be loaded before khalid's installment
day (day 27 of the month); seeding on day 27+ shows the "belt secure" state.

## API

- `GET /api/health`
- `POST /api/login` — `{"username": "fahad"}`
- `POST /api/analyze` — Mode A decision input
- `POST /api/radar/trigger` — `{"customer_id": "CUST003"}`
- `GET /api/alerts/{customer_id}`

## Deploy

```bash
GCP_PROJECT_ID=your-project ./deploy.sh    # Cloud Run, me-central2 by default
```

## Environment Variables

```text
PORT=8080
USE_BIGQUERY=true
USE_GEMINI=true
GCP_PROJECT_ID=
BQ_DATASET=edraak_finance
VERTEX_LOCATION=global
GEMINI_MODEL=gemini-2.5-flash-lite
RISK_MODEL_PATH=                    # optional; default app/functions/models/risk_model.joblib
OBLIGATION_CACHE_MAX_AGE_HOURS=24
VITE_API_BASE_URL=                  # optional UI override
```
