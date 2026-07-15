# Running Edraak locally, then on Cloud Run

Edraak is **two backend services + a Flutter app**:

| Piece | Folder | Port (local) | Talks to |
|---|---|---|---|
| Mock KSAOB gateway (the banks) | `cloud-run/mock-bank` | 8091 | `bank_cores` BigQuery dataset only |
| Edraak backend | `cloud-run/edrak` | 8080 | both BigQuery datasets, Vertex AI, the gateway |
| Flutter app | `cloud-run/edrak/ui` | 5xxxx (Chrome) | the backend + the gateway |

## Prerequisites

- Python 3.11+
- Flutter SDK — https://docs.flutter.dev/get-started/install (`flutter --version` to check)
- A Google Cloud project with BigQuery + Vertex AI, and `gcloud auth application-default login`
- BigQuery tables created (`terraform apply` in `infra/`, or run `bigquery/02_create_tables.sql`)

## 1. Start the Edraak backend (Terminal 1) — start this FIRST

```powershell
cd cloud-run/edrak
pip install -r app/requirements.txt
python -m app.functions.risk_model                 # trains + saves the risk model once

$env:GCP_PROJECT_ID="project-53540efb-1397-45cd-9d9"
$env:OPENBANKING_GATEWAY_URL="http://localhost:8091"

python -m uvicorn app.main:app --reload --port 8080
```

**No manual seeding anymore.** On startup the backend checks `bank_cores.seed_meta`
and, if the demo world isn't anchored to *today* or uses an older seed-layout
version, regenerates everything
automatically: the banks' cores into the **`bank_cores` dataset** (all banks) and
first-party data into `edraak_finance` (host bank only). On demo day the Cloud Run
cold start does this by itself. To force a reseed manually:
`python -m app.data.seed.load_seed_data` (or set `AUTO_SEED=false` to disable).

Schema readiness is checked separately from seed freshness. Additive runtime
support tables such as `transaction_classifications` are created automatically
on startup even when today's seed is already fresh, so a code update never
requires reseeding customer data.

After a generated-core refresh, the backend also invalidates the separate
gateway's in-memory snapshot. The next bank API request therefore reads the new
BigQuery rows immediately instead of serving the previous layout for five minutes.

## 2. Start the mock gateway (Terminal 2)

```powershell
cd cloud-run/mock-bank
pip install -r requirements.txt

$env:GCP_PROJECT_ID="project-53540efb-1397-45cd-9d9"   # reads the bank_cores dataset

python -m uvicorn main:app --port 8091
```

- Landing page: http://localhost:8091/
- **API page (Swagger):** http://localhost:8091/docs

The gateway serves from its own database — the `bank_cores` BigQuery dataset —
exactly like a real bank API has a core system behind it. It caches rows in
memory for 5 minutes. For this hackathon demo both Cloud Run services use the
same runtime service account; the application boundary is enforced in code and
by using separate datasets, not by separate IAM identities.

Bank-side consent state is append-only in `bank_cores.consents`, so approvals
survive Cloud Run restarts. The demo deploy keeps one warm gateway instance so
the in-memory read cache remains predictable.

## 3. Run the Flutter app (Terminal 3)

```powershell
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
3. **Link Al Rajhi once.** اربط حساباتك → ربط مصرف الراجحي → a **new tab
   opens on the gateway's domain** with the bank's own approval screen → السماح
   → the app pulls every external demo account, transaction, and loan through
   the API. Other banks remain visible but contain no demo database rows.
4. **Prove it with the API page.** On http://localhost:8091/docs, call
   `GET .../transactions` with no consent → **403**. Approve a consent, retry
   with the `x-consent-id` → **200 + data**. Bonus: an Al Rajhi consent cannot read
   Alinma's endpoints (403) — consent is per-bank.
5. **Re-analyze.** The external loan tail + BNPL stacks surface in "ما لا يراه بنكك"
   and the verdict flips to **الأفضل تأجيله — جاهز بعد شهرين**.
6. **Radar:** log in as `khalid` → الرادار → محاكاة فحص نهاية الشهر → the
   ~340 SAR gap alert before the day-27 installment (works before any linking —
   his car loan is at the host bank).

Transaction rows contain no trusted category. On the first radar run, the agent
classifies spending from merchant, raw description, channel, and repetition;
the result is cached separately. Every displayed balance is then computed by
deterministic code and the visible equation must add exactly.

Alternative logins for different demo stories: `sara` is the disciplined safe
case; `noura` is the low-reserve debt-stress case; and `abdullah` has strong
assets but high mortgage, car, nursery, family-support, and jamiya commitments.
For every user, Alinma is the host bank and **Al Rajhi is the only external bank
that contains seeded data**.

### Reset between demonstrations

On the home screen, **long-press the Edraak logo**, then confirm. This hidden
control revokes the current user's bank-side consents, removes their imported
external-bank data and stored results, and restores the generated Alinma-only
starting state. It does not require rerunning a seed command or restarting a
service.

## Deploy to Cloud Run

### First-time GCP checklist

1. Create or select a billing-enabled GCP project. For the simplest demo setup,
   use a Google account with Project Owner access.
2. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) and
   Terraform 1.5 or newer.
3. Authenticate both the Cloud CLI and Terraform from PowerShell:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project "YOUR_PROJECT_ID"
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project "YOUR_PROJECT_ID"
```

4. From the repository root, deploy the entire system:

```powershell
cd C:\path\to\edraak
.\deploy-demo.ps1 -ProjectId "YOUR_PROJECT_ID" -Region "us-central1"
```

The script applies Terraform, deploys the gateway, discovers its URL, and then
deploys the Flutter + FastAPI app with automatic startup seeding. Terraform will
show its plan and ask for `yes`; add `-AutoApprove` only when you intentionally
want to skip that confirmation. Flutter is built remotely inside the Docker
build, so a local Flutter installation is not required for deployment.

The wrapper is safe to rerun. If the application previously created an
additive runtime table (`bank_cores.consents` or
`edraak_finance.transaction_classifications`) before Terraform knew about it,
the wrapper adopts that existing table into Terraform state and continues. It
does not delete or recreate the table's data.

After infrastructure has succeeded once, an application-only redeploy can skip
Terraform entirely:

```powershell
.\deploy-demo.ps1 -SkipInfrastructure -AutoApprove
```

5. The script prints both final URLs:

```text
Edraak is ready: https://...
Gateway API: https://.../docs
```

6. Open the Edraak URL. No manual seed command is required. If reusing a project
   where you already ran a demo, log in as the intended user and long-press the
   Edraak logo once to restore that user's clean Alinma-only starting state.

To target another project or region, use for example:

```powershell
.\deploy-demo.ps1 -ProjectId "my-project" -Region "us-central1"
```

The individual Bash scripts remain available if you prefer manual deployment:

```bash
# 1) gateway (uses the shared demo runtime SA by default)
cd cloud-run/mock-bank
GCP_PROJECT_ID=your-project ./deploy.sh

# 2) backend (auto-discovers the gateway in the same project and region)
cd ../edrak
GCP_PROJECT_ID=your-project ./deploy.sh
```

Terraform creates `bank_cores` and `edraak_finance`, including durable gateway
consents. On demo day nothing else is needed: the backend's first cold start
re-anchors the synthetic bank cores and host-bank rows to that day automatically.

The Edraak Dockerfile builds the Flutter web app and serves it from FastAPI, so
the deployed app is same-origin for the API and reads the gateway URL at runtime
from `/api/ui-config` — no rebuild needed to change environments.

Terraform and both deployment scripts default to `us-central1`, matching the
current `terraform.tfvars` and avoiding cross-region BigQuery surprises.
