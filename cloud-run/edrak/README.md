# Edraak Cloud Run App

Edraak is a Cloud Run-ready FastAPI + Flutter prototype for a cross-bank
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
-> data sufficiency            (LLM, advisory preflight; deterministic fallback)
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
  AI-derived category pace vs trailing 3-month same-day-window baseline
  projected balance at every upcoming committed payment date this month
  gap -> amount, date, cause category (biggest positive deviation)
-> intervention agent (LLM): number-free Arabic guidance only
-> deterministic renderer: exact balance equation + numeric message
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
    completeness.py        # deterministic data-coverage check
    recurrence.py          # deterministic recurring-obligation grouping
  data/
    bigquery_client.py     # ALL BigQuery reads/writes
    ingestion.py           # consent → gateway pull → bronze → silver
    seed/                  # first-party seed generator + loader
  agents/                  # the only LLM code
    gemini_client.py       # Vertex AI calls + strict schema validation + number audit
    schemas.py             # all Pydantic response schemas
    transaction_intelligence.py
    data_sufficiency.py
    decision_advisor.py
    intervention.py
ui/                        # Flutter web app (Arabic, RTL): login, link banks, chart, radar
tests/                     # forecast/verdict/radar/recurrence/validator unit tests
```

## Data Rules

- Source tables: `customers`, `accounts`, `transactions` (merchant,
  `raw_description`, channel — deliberately no category), `loans` (with
  `remaining_months`).
- Derived: `user_profiles` (cross-bank aggregates), `detected_obligations`
  (cache of agent output, reused while fresh — see
  `OBLIGATION_CACHE_MAX_AGE_HOURS`), and `transaction_classifications` (AI labels
  inferred from the raw transaction signals).
- Storage-only, never read by agents: `decision_requests`, `recommendations`,
  `alerts`.
- Deterministic recurrence detection owns amounts, days, and bank codes. The
  Transaction Intelligence Agent only labels the fixed groups.
- The Decision Advisor must return `recommendation` equal to the deterministic
  verdict or the request fails with HTTP 502.

## Run Locally

```bash
pip install -r app/requirements.txt
python -m app.functions.risk_model      # trains + saves the placeholder model
export GCP_PROJECT_ID=your-project      # BigQuery + Vertex AI credentials required
uvicorn app.main:app --reload --port 8080
```

UI (Flutter web — needs the Flutter SDK) and the mock gateway both run as
separate processes. See [../../RUNNING.md](../../RUNNING.md) for the full
three-terminal guide. In brief:

```bash
cd ui
flutter pub get
flutter run -d chrome --dart-define=API_BASE=http://localhost:8080 --dart-define=GATEWAY_BASE=http://localhost:8081
```

Startup automatically refreshes stale seed data. Manual loading is only a recovery option:

```bash
GCP_PROJECT_ID=your-project python -m app.data.seed.load_seed_data
```

Startup also ensures additive derived/cache tables exist independently of the
seed date. Updating the app therefore does not require reseeding merely to add
`transaction_classifications`.

Tests:

```bash
pip install -r ../requirements-dev.txt   # or: pip install pytest
python -m pytest tests/
```

## Demo Users

| user | story | expected outcome |
|---|---|---|
| `fahad` | healthy inside Alinma; one Al Rajhi link reveals the consolidated external loan + 3 BNPL stacks + جمعية + family transfer | Mode A on 2,500/mo car → الأفضل تأجيله, ready in ~2 months |
| `sara` | 22,000 government salary, rent + modest car loan, disciplined spending, 63,000 savings | Mode A → قرار آمن |
| `khalid` | 14,500 salary, rent + car loan, cafe/restaurant spending accelerating | Mode B radar → gap ≈ 340 SAR |
| `noura` | 10,200 salary, shared rent + personal loan + BNPL stacks, minimal reserve | Mode A → غير مناسب |
| `abdullah` | 26,000 salary and strong savings, but mortgage + external car loan + family/nursery commitments | Mode A → acceptable with caution |

Note: the radar demo needs the seed to be loaded before khalid's installment
day (day 27 of the month); seeding on day 27+ shows the "belt secure" state.

## API

- `GET /api/health`
- `POST /api/login` — `{"username": "fahad"}`
- `POST /api/analyze` — Mode A decision input
- `POST /api/radar/trigger` — `{"customer_id": "CUST003"}`
- `GET /api/alerts/{customer_id}`
- `POST /api/demo/reset` — hidden presentation reset for one demo customer

## Deploy

```powershell
# From the repository root: provisions and deploys both services in us-central1
.\deploy-demo.ps1
```

During a presentation, long-press the home-screen logo and confirm to revoke
linked-bank consents and restore that user to the clean Alinma-only state.

## Environment Variables

```text
PORT=8080
USE_BIGQUERY=true
USE_GEMINI=true
GCP_PROJECT_ID=
BQ_DATASET=edraak_finance
BANK_CORES_DATASET=bank_cores
AUTO_SEED=true
OPENBANKING_GATEWAY_URL=
DEMO_RESET_TOKEN=edraak-demo-reset
VERTEX_LOCATION=global
GEMINI_MODEL=gemini-2.5-flash-lite
RISK_MODEL_PATH=                    # optional; default app/functions/models/risk_model.joblib
OBLIGATION_CACHE_MAX_AGE_HOURS=24
```
