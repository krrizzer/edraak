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
    Terraform -. creates/configures .-> BQAlerts
```

The principle: the LLM understands messy data and communicates; deterministic
Python computes every number. The LLM never invents or overrides a number.

## Open Banking retrieval — two services, one consent gate

Data from other banks only reaches the warehouse through a consented API pull.
The mock gateway is a **separate Cloud Run service** with no BigQuery access, so
the wall between "the banks" and "our warehouse" is physical, not narrative.

```mermaid
flowchart LR
    subgraph GW["Cloud Run #2: mock KSAOB gateway (no BigQuery)"]
      Cores[("Bank cores<br/>in RAM, per bank")]
      Consent["Consent gate<br/>403 without an Authorised consent"]
      Cores --> Consent
    end

    subgraph APP["Cloud Run #1: Edraak"]
      Flutter["Flutter app"]
      Ingest["Ingestion pipeline"]
      Flutter -- "1. create + approve consent" --> Consent
      Flutter -- "2. POST /api/ingest" --> Ingest
      Ingest -- "3. consented pull (x-consent-id)" --> Consent
      Ingest --> Bronze[("BRONZE<br/>ob_raw_payloads")]
      Ingest --> Silver[("SILVER<br/>accounts / transactions")]
      Ingest --> Ledger[("ob_consents<br/>TPP ledger")]
      Silver --> Gold["GOLD (derived)<br/>profile · obligations · forecast"]
    end

    FirstParty[("First-party seed<br/>customers · loans · host bank")] --> Silver
```

First-party data (the host bank, `customers`, `loans` as a bureau feed) is seeded
straight into BigQuery; every other bank stays in the gateway's RAM until the
customer links it. Loans arrive via the bureau feed (SIMAH-style), not AIS.
