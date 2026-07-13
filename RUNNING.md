# Running Edraak locally, then on Cloud Run

Edraak is **two backend services + a Flutter app**:

| Piece | Folder | Port (local) | Talks to |
|---|---|---|---|
| Mock KSAOB gateway (the banks) | `cloud-run/mock-bank` | 8081 | nothing (data in RAM) |
| Edraak backend | `cloud-run/edrak` | 8080 | BigQuery, Vertex AI, the gateway |
| Flutter app | `cloud-run/edrak/ui` | 5xxxx (Chrome) | the backend + the gateway |

## Prerequisites

- Python 3.11+
- Flutter SDK — https://docs.flutter.dev/get-started/install (`flutter --version` to check)
- A Google Cloud project with BigQuery + Vertex AI, and `gcloud auth application-default login`
- BigQuery tables created (`terraform apply` in `infra/`, or run `bigquery/02_create_tables.sql`)

## 1. Start the Edraak backend (Terminal 1) — start this FIRST

```bash
cd cloud-run/edrak
pip install -r app/requirements.txt
python -m app.functions.risk_model                 # trains + saves the risk model once

$env:GCP_PROJECT_ID="project-53540efb-1397-45cd-9d9"
$env:OPENBANKING_GATEWAY_URL="http://localhost:8091"

python -m uvicorn app.main:app --reload --port 8080
```

**No manual seeding anymore.** On startup the backend checks `bank_cores.seed_meta`
and, if the demo world isn't anchored to *today*, regenerates everything
automatically: the banks' cores into the **`bank_cores` dataset** (all banks) and
first-party data into `edraak_finance` (host bank only). On demo day the Cloud Run
cold start does this by itself. To force a reseed manually:
`python -m app.data.seed.load_seed_data` (or set `AUTO_SEED=false` to disable).

## 2. Start the mock gateway (Terminal 2)

```bash
cd cloud-run/mock-bank
pip install -r requirements.txt

$env:GCP_PROJECT_ID="project-53540efb-1397-45cd-9d9"   # reads the bank_cores dataset

python -m uvicorn main:app --port 8091
```

- Landing page: http://localhost:8091/
- **API page (Swagger):** http://localhost:8091/docs

The gateway serves from its own database — the `bank_cores` BigQuery dataset —
exactly like a real bank API has a core system behind it. It caches rows in
memory for 5 minutes, and it has no access to `edraak_finance`.

## 3. Run the Flutter app (Terminal 3)

```bash
cd cloud-run/edrak/ui
flutter pub get
flutter run -d chrome --dart-define=API_BASE=http://localhost:8080 --dart-define=GATEWAY_BASE=http://localhost:8091
```

> The `--dart-define`s are required locally because the Flutter dev server is not
> the backend. In production (served by FastAPI) they're not needed — the app uses
> the same origin for the API and fetches the gateway URL from `/api/ui-config`.

Icons (all optional, graceful placeholders until added) go in
`cloud-run/edrak/ui/assets/icons/`: **`Amad.png`** (app logo) plus bank logos
named by bank code — `ALINMA.png`, `ALRAJHI.png`, `SNB.png`, `RIYAD.png`,
`SAB.png`. Restart `flutter run` after adding files.

## The demo flow (what to show)

The host bank is **مصرف الإنماء (ALINMA)** — Edraak runs inside it, so it's
always connected. Everything else arrives via open banking.

1. **Log in** as `fahad`. Only Alinma data is visible.
2. **Analyze first** (حزام الأمان → حلّل القرار). The **smart validator** fires
   before the analysis: deterministic logic + the Data Sufficiency Agent (LLM)
   inspect the visible picture, and a dismissible dialog says what looks like it
   is happening at unlinked banks — "هل تود المتابعة؟". Proceed → **مقبول بحذر**;
   he looks manageable when you can only see his salary bank.
3. **Link the two main banks.** اربط حساباتك → ربط البنك الأهلي → a **new tab
   opens on the gateway's domain** with the bank's own approval screen → السماح
   → the app pulls accounts, transactions **and the SNB loan** through the API.
   Repeat for بنك الرياض. (Al Rajhi/SAB hold only noise — linking them adds
   almost nothing, which is itself realistic.)
4. **Prove it with the API page.** On http://localhost:8091/docs, call
   `GET .../transactions` with no consent → **403**. Approve a consent, retry
   with the `x-consent-id` → **200 + data**. Bonus: an SNB consent cannot read
   Alinma's endpoints (403) — consent is per-bank.
5. **Re-analyze.** The SNB loan tail + BNPL stacks surface in "ما لا يراه بنكك"
   and the verdict flips to **الأفضل تأجيله — جاهز بعد شهرين**.
6. **Radar:** log in as `khalid` → الرادار → محاكاة فحص نهاية الشهر → the
   ~340 SAR gap alert before the day-27 installment (works before any linking —
   his car loan is at the host bank).

> Tip: run the gateway WITHOUT `--reload` during the actual demo. Consents now
> survive restarts (persisted to `consents_store.json`), but fewer moving parts
> is still better on stage.

## Deploy to Cloud Run

Deploy the gateway first, then point Edraak at it:

```bash
# 1) gateway (needs read access to bank_cores: pass the Edraak SA or any SA
#    with BigQuery dataViewer on that dataset)
cd cloud-run/mock-bank
GCP_PROJECT_ID=your-project \
SERVICE_ACCOUNT=edraak-cloud-run-sa@your-project.iam.gserviceaccount.com \
./deploy.sh                       # note the printed https://ksaob-mock-gateway-....run.app URL

# 2) backend (set the gateway URL so the app + ingestion can reach it)
cd ../edrak
GCP_PROJECT_ID=your-project \
OPENBANKING_GATEWAY_URL=https://ksaob-mock-gateway-....run.app \
./deploy.sh
```

Run `terraform apply` once before deploying — it creates the new `bank_cores`
dataset + tables. On demo day nothing else is needed: the backend's first cold
start re-anchors the whole demo world to that day automatically.

The Edraak Dockerfile builds the Flutter web app and serves it from FastAPI, so
the deployed app is same-origin for the API and reads the gateway URL at runtime
from `/api/ui-config` — no rebuild needed to change environments.

> Region note: `terraform.tfvars` uses `us-central1` but `deploy.sh` defaults to
> `me-central2`. Match them — deploy with `REGION=us-central1 ./deploy.sh` if your
> BigQuery dataset is in `us-central1`.
