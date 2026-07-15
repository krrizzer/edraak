# Edraak Architecture

Edraak is a cross-bank financial seatbelt built on simulated SAMA Open Banking
data: a FastAPI backend + Flutter app on Cloud Run that reads a customer's accounts,
loans, and raw transactions across ALL of their banks from BigQuery, simulates
the next 12 months of cash flow, and communicates the result in Arabic through
Vertex AI Gemini agents.

**The architecture principle:** the LLM understands messy data and
communicates; deterministic Python computes every number. The LLM never invents
or overrides a number.

The system has two modes after login:

- **Mode A — Decision Seatbelt (pre-loan):** month-by-month 12-month cash-flow
  simulation for a proposed commitment, with a rules-based verdict
  (قرار آمن / مقبول بحذر / الأفضل تأجيله / غير مناسب) and a computed "ready in N months".
- **Mode B — Financial Radar (post-loan):** current-month trajectory monitoring
  that projects the balance at every upcoming committed payment date and fires
  one actionable Arabic alert when a gap is coming.

The detailed diagrams live in their own documents:

1. [System Architecture](System-Architecture.md) — components and data flow.
2. [User Workflow](User-Workflow.md) — sequence diagrams for both modes.
3. [Agentic Workflow](Agentic-Workflow.md) — the 4 focused LLM agents, the
   deterministic steps between them, and the guardrails.
4. [BigQuery Design](BigQuery-design.md) — table roles and the seed data story.

Key modules:

| Layer | Location | Role |
|---|---|---|
| Routes | `cloud-run/edrak/app/main.py` | Thin FastAPI endpoints |
| Orchestration | `cloud-run/edrak/app/pipeline.py` | Mode A / Mode B step sequencing + honest trace |
| Deterministic | `cloud-run/edrak/app/functions/` | validator, profile_builder, forecast_engine, verdict_rules, radar, risk_model |
| Agents | `cloud-run/edrak/app/agents/` | data_sufficiency, transaction_intelligence, decision_advisor, intervention (+ gemini_client, schemas) |
| Data | `cloud-run/edrak/app/data/` | bigquery_client (all reads/writes), seed generator/loader |
| UI | `cloud-run/edrak/ui/` | Flutter web: login, bank-linking, forecast chart, bank panel, radar |
| Gateway | `cloud-run/mock-bank/` | Separate service: consent-gated mock KSAOB Open Banking API |
| Pipeline | `cloud-run/edrak/app/data/ingestion.py` | Consent → gateway pull → bronze → silver |
| Infra | `infra/` | Terraform: BigQuery tables, Cloud Run SA, Artifact Registry |
