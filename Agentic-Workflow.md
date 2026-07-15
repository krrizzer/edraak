## 3. Agentic Workflow

Exactly four focused LLM agents remain after the reshape — each does work that
requires language judgment. Everything else is deterministic Python and is
shown in the trace as such (that is the auditability pitch, not a weakness).

Before Mode A begins, the **Data Sufficiency Agent** reviews deterministic
coverage evidence and warns when the linked accounts look like only part of the
customer's financial life. It is advisory: deterministic critical findings can
block analysis, while this agent can only warn.

### Mode A — Decision Seatbelt

```mermaid
flowchart TD
    A["Cross-bank data<br/>customers + accounts + transactions + loans"]
    DS["Data Sufficiency Agent<br/>(LLM: advisory completeness judgment)"]
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

    A --> DS --> V --> RD --> TI
    TI <--> Cache
    TI --> PB --> FE --> VR
    FE --> RM --> VR
    VR --> DA --> R

    TI -. strict JSON call .-> L
    DS -. strict JSON call .-> L
    DA -. strict JSON call .-> L
    L -. validated response .-> TI
    L -. validated response .-> DS
    L -. validated response .-> DA
```

### Mode B — Financial Radar

```mermaid
flowchart TD
    A2["Current month data<br/>balances + MTD transactions"]
    TC["Transaction Intelligence Agent<br/>(LLM: classifies merchant + raw narrative)"]
    CC[("transaction_classifications<br/>derived cache")]
    RD["Radar Detector<br/>(deterministic: pace vs baseline,<br/>projected balance at payment dates)"]
    IA["Intervention Agent<br/>(LLM: number-free Arabic guidance)"]
    AL[("alerts<br/>storage only")]
    R2["API Response"]
    L2["Vertex AI Gemini 2.5 Flash Lite"]

    A2 --> TC --> CC --> RD --> IA --> R2
    IA --> AL
    IA -. strict JSON call .-> L2
    TC -. strict JSON call .-> L2
    L2 -. validated response .-> IA
    L2 -. validated response .-> TC
```

### Guardrails

- Strict Pydantic schema validation applies to every Gemini call. The three
  pipeline agents fail the request clearly on invalid output. The advisory Data
  Sufficiency Agent alone degrades to deterministic coverage with an explicit
  notice so it cannot lock the customer out.
- Deterministic Python groups the recurring transactions first (by consistent
  amount, day, and isolation/provider signal). The agent only *labels* each
  group, so it never sets an amount, day, or bank — the old amount-echo check
  is no longer needed because the LLM can't touch a number.
- Source transactions contain no category. The agent classifies spending from
  merchant, raw description, channel, and pattern evidence into a separate cache.
- Radar renders the balance equation and every numeric sentence in deterministic
  Python. The Intervention Agent can add guidance but is forbidden from writing
  numbers or dates.
- The Decision Advisor must echo the deterministic verdict exactly; the backend
  rejects the response if it differs.
- A number audit logs any figure in agent prose that does not exist in the
  agent's input payload.
