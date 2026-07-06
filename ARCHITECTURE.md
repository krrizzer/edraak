# Edraak Architecture Design

This document shows the production-style architecture for Edraak: a Cloud Run FastAPI + React app that retrieves real BigQuery banking data, generates a derived customer profile when needed, runs an agentic financial decision workflow through Vertex AI Gemini, and stores the request/recommendation outputs.

## 1. System Architecture

```mermaid
flowchart LR
    User["Customer / Demo User"] --> Browser["React UI<br/>localhost:5173 or Cloud Run static UI"]
    Browser --> API["FastAPI Backend<br/>Cloud Run service"]

    API --> AuthFlow["Login Flow<br/>username_en -> customer_id"]
    API --> AnalysisFlow["Financial Decision Flow"]
    API --> AdminFlow["Optional Admin Profile Loader"]

    AuthFlow --> BQCustomers[("BigQuery<br/>customers")]

    AnalysisFlow --> BQCustomers
    AnalysisFlow --> BQTransactions[("BigQuery<br/>transactions")]
    AnalysisFlow --> BQLoans[("BigQuery<br/>loans")]
    AnalysisFlow --> BQProfiles[("BigQuery<br/>user_profiles")]

    AdminFlow --> BQCustomers
    AdminFlow --> BQTransactions
    AdminFlow --> BQLoans
    AdminFlow --> BQProfiles

    AnalysisFlow --> Tools["Deterministic Python Tools<br/>ratios, buffer, risk score"]
    Tools --> Agents["Agentic Workflow<br/>strict schemas"]
    Agents --> Vertex["Vertex AI Gemini<br/>gemini-2.5-flash-lite"]
    Vertex --> Agents

    AnalysisFlow --> BQRequests[("BigQuery<br/>decision_requests<br/>storage only")]
    AnalysisFlow --> BQRecommendations[("BigQuery<br/>recommendations<br/>storage only")]
    AnalysisFlow --> Browser

    Terraform["Terraform Infra"] -. creates/configures .-> API
    Terraform -. creates/configures .-> BQCustomers
    Terraform -. creates/configures .-> BQTransactions
    Terraform -. creates/configures .-> BQLoans
    Terraform -. creates/configures .-> BQProfiles
    Terraform -. creates/configures .-> BQRequests
    Terraform -. creates/configures .-> BQRecommendations
```

## 2. User Workflow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as React UI
    participant API as FastAPI Backend
    participant BQ as BigQuery
    participant Tools as Python Tools
    participant Agents as Agent Pipeline
    participant Gemini as Vertex AI Gemini

    U->>UI: Enter English username
    UI->>API: POST /api/login
    API->>BQ: Query customers by username_en
    BQ-->>API: Customer row
    API-->>UI: customer_id + display names

    U->>UI: Enter goal / loan details
    UI->>API: POST /api/analyze

    API->>BQ: Read customers
    API->>BQ: Read transactions
    API->>BQ: Read active loans
    API->>BQ: Read user_profiles

    alt user_profiles row is missing
        API->>API: Generate profile from real customers + transactions + loans
        API->>BQ: Insert generated row into user_profiles
    end

    API->>Tools: Calculate obligation ratios, monthly buffer, risk score
    Tools-->>API: Calculated metrics

    API->>Agents: Build strict AgentContext
    Agents->>Gemini: Data validation agent
    Gemini-->>Agents: Validated JSON schema
    Agents->>Gemini: Profile agent
    Gemini-->>Agents: Validated JSON schema
    Agents->>Gemini: Risk agent
    Gemini-->>Agents: Validated JSON schema
    Agents->>Gemini: Alternatives agent
    Gemini-->>Agents: Validated JSON schema
    Agents->>Gemini: Recommendation agent
    Gemini-->>Agents: Validated JSON schema

    API->>BQ: Insert decision_requests
    API->>BQ: Insert recommendations
    API-->>UI: Recommendation, explanation, risks, alternatives, trace
    UI-->>U: Show result
```

## 3. Agentic Workflow

```mermaid
flowchart TD
    Context["AgentContext<br/>customer + transactions + loans + user_profile + decision_input + tool_outputs"]

    Tools["Deterministic Tools<br/>- obligation_ratio_before<br/>- obligation_ratio_after<br/>- monthly_buffer_after<br/>- risk_score<br/>- safety_score<br/>- deterministic_recommendation"]

    Validation["1. Data Validation Agent<br/>checks missing/mismatched data"]
    Profile["2. Profile Agent<br/>explains derived financial profile"]
    Risk["3. Risk Agent<br/>explains commitment risk"]
    Alternatives["4. Alternatives Agent<br/>safer options + 30/60/90 path"]
    Recommendation["5. Recommendation Agent<br/>final Arabic recommendation"]

    Response["Stable API Response<br/>recommendation + scores + explanation + agent_trace"]

    Context --> Tools
    Tools --> Validation
    Validation --> Profile
    Profile --> Risk
    Risk --> Alternatives
    Alternatives --> Recommendation
    Recommendation --> Response

    Validation -. "Vertex AI Gemini<br/>strict JSON schema" .-> Gemini["gemini-2.5-flash-lite"]
    Profile -. "Vertex AI Gemini<br/>strict JSON schema" .-> Gemini
    Risk -. "Vertex AI Gemini<br/>strict JSON schema" .-> Gemini
    Alternatives -. "Vertex AI Gemini<br/>strict JSON schema" .-> Gemini
    Recommendation -. "Vertex AI Gemini<br/>strict JSON schema" .-> Gemini
```

## 4. BigQuery Table Usage

```mermaid
flowchart LR
    Customers[("customers<br/>source table")]
    Transactions[("transactions<br/>source table")]
    Loans[("loans<br/>source table")]
    Profiles[("user_profiles<br/>derived analytical table")]
    Requests[("decision_requests<br/>write-only storage")]
    Recommendations[("recommendations<br/>write-only storage")]

    Customers --> ProfileLoader["Profile Loader<br/>on-demand or admin preload"]
    Transactions --> ProfileLoader
    Loans --> ProfileLoader
    ProfileLoader --> Profiles

    Customers --> Analysis["Analyze Flow"]
    Transactions --> Analysis
    Loans --> Analysis
    Profiles --> Analysis

    Analysis --> Requests
    Analysis --> Recommendations

    Requests -. "not read by agents" .-> StorageNote["Storage only"]
    Recommendations -. "not read by agents" .-> StorageNote
```

## 5. Service Responsibilities

| Area | Responsibility |
| --- | --- |
| React UI | Login screen, goal/loan form, loading states, result view, agent trace display |
| FastAPI Backend | API routes, BigQuery retrieval, on-demand profile generation, agent orchestration, response shaping |
| BigQuery Source Tables | `customers`, `transactions`, `loans` contain original banking data |
| BigQuery Derived Table | `user_profiles` is calculated from source tables and reused by analysis |
| BigQuery Storage Tables | `decision_requests` and `recommendations` store outputs only; they are not analysis inputs |
| Python Tools | Deterministic calculations that Gemini is not allowed to invent or change |
| Agents | Structured reasoning and Arabic explanations using strict Pydantic schemas |
| Vertex AI Gemini | LLM execution using `gemini-2.5-flash-lite` through Vertex AI only |
| Terraform | Infra setup for Cloud Run, BigQuery, IAM, and deployment configuration |

## 6. Runtime Log Timeline

The backend logs are designed to read like the workflow:

```text
flow.login.submitted
flow.login.success
flow.analysis.clicked
flow.analysis.data_collection.start
flow.analysis.data_collection.customer
flow.analysis.data_collection.transactions
flow.analysis.data_collection.loans
flow.analysis.data_collection.profile
flow.analysis.profile_generate_on_demand.start
flow.analysis.profile_generate_on_demand.completed
flow.tools.start
flow.tools.completed
flow.agent.validation.start
flow.agent.validation.completed
flow.agent.profile.start
flow.agent.profile.completed
flow.agent.risk.start
flow.agent.risk.completed
flow.agent.alternatives.start
flow.agent.alternatives.completed
flow.agent.recommendation.start
flow.agent.recommendation.completed
flow.analysis.storage.start
flow.analysis.storage.completed
flow.analysis.completed
```

## 7. Production Rules

- The app uses BigQuery source data, not in-code mock data.
- `user_profiles` can be generated on demand, but only from real BigQuery `customers`, `transactions`, and `loans`.
- Gemini must run through Vertex AI using `gemini-2.5-flash-lite`.
- Gemini responses must pass strict Pydantic schema validation.
- Deterministic Python tools own numeric calculations.
- `decision_requests` and `recommendations` are storage-only tables and must not be reused as agent input.
