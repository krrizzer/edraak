## 1. System Architecture

```mermaid
flowchart LR
    User["Customer / Demo User"] --> Browser["Flutter app<br/>Link banks · Seatbelt · Radar"]
    Browser --> API["FastAPI Backend<br/>Cloud Run service"]

    API --> AuthFlow["Login Flow<br/>username_en -> customer_id"]
    API --> AnalysisFlow["Mode A: Decision Seatbelt<br/>POST /api/analyze"]
    API --> RadarFlow["Mode B: Financial Radar<br/>POST /api/radar/trigger"]

    AuthFlow --> BQCustomers[("BigQuery<br/>customers")]

    AnalysisFlow --> BQCustomers
    AnalysisFlow --> BQAccounts[("BigQuery<br/>accounts<br/>all banks")]
    AnalysisFlow --> BQTransactions[("BigQuery<br/>transactions<br/>raw_description")]
    AnalysisFlow --> BQLoans[("BigQuery<br/>loans<br/>remaining_months")]
    AnalysisFlow --> BQObligations[("BigQuery<br/>detected_obligations<br/>LLM cache")]
    RadarFlow --> BQClassifications[("BigQuery<br/>transaction_classifications<br/>AI-derived cache")]

    RadarFlow --> BQAccounts
    RadarFlow --> BQTransactions
    RadarFlow --> BQLoans
    RadarFlow --> BQObligations

    AnalysisFlow --> Deterministic["Deterministic Python<br/>validator, forecast engine,<br/>verdict rules, risk model"]
    RadarFlow --> RadarDet["Deterministic Python<br/>pace math, gap detection"]

    AnalysisFlow --> Agents["LLM Agents<br/>strict Pydantic schemas"]
    RadarFlow --> Agents
    Agents --> Vertex["Vertex AI Gemini<br/>gemini-2.5-flash-lite"]
    Vertex --> Agents

    AnalysisFlow --> BQRequests[("BigQuery<br/>decision_requests<br/>storage only")]
    AnalysisFlow --> BQRecommendations[("BigQuery<br/>recommendations<br/>storage only")]
    RadarFlow --> BQAlerts[("BigQuery<br/>alerts<br/>storage only")]

    AnalysisFlow --> Browser
    RadarFlow --> Browser

    Terraform["Terraform Infra"] -. creates/configures .-> API
    Terraform -. creates/configures .-> BQCustomers
    Terraform -. creates/configures .-> BQAccounts
    Terraform -. creates/configures .-> BQTransactions
    Terraform -. creates/configures .-> BQLoans
    Terraform -. creates/configures .-> BQObligations
    Terraform -. creates/configures .-> BQClassifications
    Terraform -. creates/configures .-> BQAlerts
```

The principle: the LLM understands messy data and communicates; deterministic
Python computes every number. The LLM never invents or overrides a number.

## Open Banking retrieval — two services, one consent gate

Data from other banks only reaches the Edraak warehouse through a consented API
pull. The mock gateway is a separate Cloud Run service backed by the separate
`bank_cores` BigQuery dataset. For demo simplicity both services share one
runtime service account; separation here is by dataset and application path,
not a production-grade IAM boundary.

```mermaid
flowchart LR
    subgraph GW["Cloud Run #2: mock KSAOB gateway"]
      Cores[("bank_cores BigQuery<br/>accounts · transactions · loans")]
      BankConsents[("bank_cores.consents<br/>durable append-only state")]
      Consent["Consent gate<br/>403 without an Authorised consent"]
      Cores --> Consent
      BankConsents --> Consent
    end

    subgraph APP["Cloud Run #1: Edraak"]
      Flutter["Flutter app"]
      Ingest["Ingestion pipeline"]
      Flutter -- "1. create + approve consent" --> Consent
      Flutter -- "2. POST /api/ingest" --> Ingest
      Ingest -- "3. consented pull (x-consent-id)" --> Consent
      Ingest --> Bronze[("BRONZE<br/>ob_raw_payloads")]
      Ingest --> Silver[("SILVER<br/>accounts / transactions / loans")]
      Ingest --> Ledger[("ob_consents<br/>TPP ledger")]
      Silver --> Gold["GOLD (derived)<br/>profile · obligations · classifications · forecast"]
    end

    Seeder["Daily automatic demo seed"] --> Cores
    Seeder --> FirstParty[("First-party state<br/>customers · Alinma rows")]
    FirstParty --> Silver
```

The startup seeder writes the full synthetic banking world to `bank_cores` and
only each customer's Alinma rows to `edraak_finance`. External accounts,
transactions, and loans are consolidated under Al Rajhi for the demo and arrive
through one consented gateway pull. The other bank choices remain visible but
have no seeded rows. Loans use a
demo-only product-data extension alongside the simulated AIS endpoints.

Source transactions intentionally contain no category. Transaction meaning is
derived from merchant, raw description, channel, and repeated patterns, then
stored separately in `transaction_classifications`.

Long-pressing the home-screen logo invokes the hidden reset flow: bank-side
consents are revoked, that customer's external warehouse rows and stored outputs
are deleted, and their generated Alinma-only rows are restored.
