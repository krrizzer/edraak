## 3. Agentic Workflow

Exactly three LLM agents remain after the reshape — each does work that
actually requires an LLM. Everything else is deterministic Python and is shown
in the trace as such (that is the auditability pitch, not a weakness).

### Mode A — Decision Seatbelt

```mermaid
flowchart TD
    A["Cross-bank data<br/>customers + accounts + transactions + loans"]
    V["Validator<br/>(deterministic)"]
    RD["Recurrence Detector<br/>(deterministic: finds WHAT recurs)"]
    TI["Transaction Intelligence Agent<br/>(LLM: labels WHAT each group IS)"]
    Cache[("detected_obligations<br/>cache")]
    PB["Profile Builder<br/>(deterministic)"]
    FE["Forecast Engine<br/>(deterministic, 12 months)"]
    RM["Risk Model<br/>(scikit-learn, P(missed payment))"]
    VR["Verdict Rules<br/>(deterministic, over the curve)"]
    DA["Decision Advisor Agent<br/>(LLM: Arabic explanation)"]
    R["API Response"]
    L["Vertex AI Gemini 2.5 Flash Lite"]

    A --> V --> RD --> TI
    TI <--> Cache
    TI --> PB --> FE --> VR
    FE --> RM --> VR
    VR --> DA --> R

    TI -. strict JSON call .-> L
    DA -. strict JSON call .-> L
    L -. validated response .-> TI
    L -. validated response .-> DA
```

### Mode B — Financial Radar

```mermaid
flowchart TD
    A2["Current month data<br/>balances + MTD transactions"]
    RD["Radar Detector<br/>(deterministic: pace vs baseline,<br/>projected balance at payment dates)"]
    IA["Intervention Agent<br/>(LLM: one actionable Arabic alert)"]
    AL[("alerts<br/>storage only")]
    R2["API Response"]
    L2["Vertex AI Gemini 2.5 Flash Lite"]

    A2 --> RD --> IA --> R2
    IA --> AL
    IA -. strict JSON call .-> L2
    L2 -. validated response .-> IA
```

### Guardrails

- Strict Pydantic schema validation on every Gemini call; invalid output fails
  the request with a clear error — no silent degradation.
- Deterministic Python groups the recurring transactions first (by consistent
  amount, day, and isolation/provider signal). The agent only *labels* each
  group, so it never sets an amount, day, or bank — the old amount-echo check
  is no longer needed because the LLM can't touch a number.
- The Decision Advisor must echo the deterministic verdict exactly; the backend
  rejects the response if it differs.
- A number audit logs any figure in agent prose that does not exist in the
  agent's input payload.
