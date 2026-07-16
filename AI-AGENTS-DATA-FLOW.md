# Edraak AI Agents: Data Inputs, Outputs, and Responsibilities

There are **four main LLM agents**, but Transaction Intelligence performs two separate AI tasks. Therefore, the system makes five kinds of Gemini calls.

The central architecture principle is:

> **Python calculates the financial truth. AI interprets messy data and explains the result.**

The JSON below is simplified and illustrative, but matches the implemented schemas.

## 1. Data Sufficiency Agent

**Purpose:** Decide whether the connected accounts appear to represent the customer's complete financial life.

### Input

The agent receives aggregates and up to 25 recent transactions—not unrestricted access to the database.

```json
{
  "declared_salary": 14500,
  "connected_banks_ar": [
    "مصرف الإنماء"
  ],
  "history_months": 6,
  "transactions_count": 124,
  "avg_monthly_income_visible": 14500,
  "avg_monthly_expense_visible": 4200,
  "top_expense_signals": [
    {
      "merchant_or_description": "Tamimi Markets",
      "avg_monthly_amount": 1300
    },
    {
      "merchant_or_description": "Transfer Out",
      "avg_monthly_amount": 1800
    }
  ],
  "visible_loans_count": 1,
  "visible_loan_installments": 2200,
  "total_visible_balance": 7200,
  "recent_transactions_sample": [
    {
      "date": "2026-07-12",
      "amount": -1800,
      "merchant": null,
      "description": "MONTHLY TRANSFER",
      "channel": "online"
    }
  ]
}
```

### Output

```json
{
  "looks_complete": false,
  "confidence": 0.88,
  "findings_ar": [
    "يظهر الراتب، لكن تكاليف السكن والفواتير الأساسية غير واضحة.",
    "توجد تحويلات شهرية قد تشير إلى استخدام حساب آخر غير مرتبط."
  ],
  "trace_message_ar": "تم تقييم مدى اكتمال الصورة المالية من البيانات المرتبطة."
}
```

### What it really does

It recognizes patterns that are difficult to express as simple rules, such as:

- Salary exists, but no rent, utilities, or normal living expenses appear.
- Significant spending exists, but income appears incomplete.
- Regular transfers may indicate another unlinked account.

It is **advisory only**. It cannot block the customer. Deterministic Python rules handle blocking cases such as a completely missing salary.

---

## 2. Transaction Intelligence: Recurring Obligations

**Purpose:** Understand what a recurring transaction represents.

Python first detects that transactions repeat with a similar amount and date. The agent only labels the meaning.

### Input

```json
{
  "customer_id": "CUST001",
  "groups": [
    {
      "group_id": "GRP-001",
      "sample_descriptions": [
        "TABBY INST 2 OF 4",
        "TABBY PAYMENT"
      ],
      "sample_merchants": [
        "Tabby"
      ],
      "sample_channels": [
        "card"
      ],
      "monthly_amount": 450,
      "day_of_month": 15,
      "months_seen": 3,
      "occurrences": 3
    },
    {
      "group_id": "GRP-002",
      "sample_descriptions": [
        "TRANSFER TO AHMED FAMILY"
      ],
      "sample_merchants": [],
      "sample_channels": [
        "online"
      ],
      "monthly_amount": 1000,
      "day_of_month": 27,
      "months_seen": 6,
      "occurrences": 6
    }
  ]
}
```

### Output

```json
{
  "labels": [
    {
      "group_id": "GRP-001",
      "obligation_type": "bnpl_installment",
      "counterparty": "Tabby",
      "label_ar": "أقساط تابي",
      "is_committed": true,
      "remaining_months": 2,
      "confidence": 0.97
    },
    {
      "group_id": "GRP-002",
      "obligation_type": "family_support",
      "counterparty": "دعم عائلي",
      "label_ar": "تحويل عائلي شهري",
      "is_committed": true,
      "remaining_months": null,
      "confidence": 0.84
    }
  ],
  "trace_message_ar": "تم تفسير أنماط المعاملات المتكررة."
}
```

### What it really does

The agent answers:

- Is this BNPL, rent, a subscription, a jamiya, or family support?
- Is it a committed obligation?
- Does the description show a remaining-payment countdown?

It **cannot change**:

- Monthly amount
- Payment date
- Source bank
- Number of transactions

Python takes those values from the original transaction group when merging the AI label.

---

## 3. Transaction Intelligence: Spending Categorization

**Purpose:** Categorize raw bank descriptions for the Financial Radar.

This is a separate Gemini call under the Transaction Intelligence module.

### Input

```json
{
  "customer_id": "CUST003",
  "patterns": [
    {
      "pattern_id": "PAT-001",
      "merchants": [
        "Starbucks"
      ],
      "sample_descriptions": [
        "POS STARBUCKS RIYADH",
        "CARD PURCHASE STARBUCKS"
      ],
      "channel": "pos",
      "direction": "debit",
      "occurrences": 9
    },
    {
      "pattern_id": "PAT-002",
      "merchants": [
        "HungerStation"
      ],
      "sample_descriptions": [
        "ONLINE HUNGERSTATION"
      ],
      "channel": "online",
      "direction": "debit",
      "occurrences": 7
    }
  ]
}
```

Notice that the agent does not need the customer's balance or transaction amounts for this classification.

### Output

```json
{
  "labels": [
    {
      "pattern_id": "PAT-001",
      "category": "cafes",
      "confidence": 0.99
    },
    {
      "pattern_id": "PAT-002",
      "category": "restaurants",
      "confidence": 0.96
    }
  ],
  "trace_message_ar": "تم تصنيف أنماط الإنفاق من التاجر ووصف المعاملة."
}
```

### What it really does

It converts messy descriptions such as `POS STARBUCKS RUH 1043` into stable categories:

- Cafés
- Restaurants
- Groceries
- Shopping
- Fuel
- Transport
- Bills
- Healthcare
- Transfers
- Other

Python then calculates whether spending in that category is accelerating. The agent does not calculate the percentage or financial gap.

---

## 4. Decision Advisor Agent

**Purpose:** Explain a decision that Python has already made.

This is the largest payload because it receives the deterministic analysis result.

### Input

```json
{
  "customer": {
    "customer_id": "CUST001",
    "ar_name": "فهد",
    "en_name": "Fahad"
  },
  "decision_input": {
    "customer_id": "CUST001",
    "monthly_installment": 2500,
    "duration_months": 36,
    "down_payment": 10000
  },
  "verdict": {
    "verdict": "الأفضل تأجيله",
    "ready_in_months": 2,
    "reason_tags": [
      "temporary_overlap",
      "bnpl_stacking"
    ]
  },
  "risk_probability": 0.42,
  "forecast": {
    "first_shortfall_month": 1,
    "first_shortfall_amount": 900,
    "min_buffer_month": 1,
    "min_buffer_value": -900,
    "obligation_ratio_peak": 0.61,
    "months": [
      {
        "month": 1,
        "income": 14500,
        "committed": 5900,
        "new_commitment": 2500,
        "flexible": 7000,
        "buffer": -900,
        "events": []
      },
      {
        "month": 3,
        "income": 14500,
        "committed": 3900,
        "new_commitment": 2500,
        "flexible": 7000,
        "buffer": 1100,
        "events": [
          {
            "type": "obligation_released",
            "label": "Tabby",
            "amount": 450,
            "kind": "bnpl_installment"
          }
        ]
      }
    ],
    "stress_events": [
      {
        "month": 1,
        "cause": "temporary_overlap",
        "gap": 900,
        "ending_soon": [
          "Tabby",
          "car_loan@ALRAJHI"
        ]
      }
    ]
  },
  "detected_obligations": [
    {
      "obligation_type": "bnpl_installment",
      "counterparty": "Tabby",
      "monthly_amount": 450,
      "remaining_months": 2,
      "source_bank_codes": [
        "ALRAJHI"
      ]
    }
  ],
  "profile": {
    "salary": 14500,
    "total_balance": 7200,
    "banks_count": 2,
    "monthly_loan_installments": 4100,
    "avg_flexible_spending": 7000
  },
  "validation_warnings_ar": []
}
```

### Output

```json
{
  "recommendation": "الأفضل تأجيله",
  "explanation_ar": "يظهر عجز بقيمة 900 ريال في الشهر الأول بسبب تداخل الالتزام الجديد مع الأقساط الحالية. بعد شهرين تنتهي بعض الالتزامات المؤقتة ويتحسن الهامش الشهري.",
  "risk_factors_ar": [
    "تداخل عدة التزامات خلال الفترة الأولى.",
    "ارتفاع نسبة الالتزامات في أكثر أشهر التوقع ضغطاً."
  ],
  "safer_options_ar": [
    "الانتظار شهرين قبل بدء الالتزام الجديد.",
    "زيادة الدفعة المقدمة لتخفيف الالتزام الشهري."
  ],
  "trace_message_ar": "تم تحويل نتيجة المحاكاة إلى تفسير مالي واضح."
}
```

### What it really does

It turns numbers into an understandable Arabic story.

It **does not decide** whether the application is safe. The verdict comes from Python rules. If the agent returns a different recommendation, the application rejects its response.

It also cannot silently change or round financial figures. Numbers appearing in its response are audited against the input payload.

---

## 5. Intervention Agent

**Purpose:** Provide one short, human action for the Financial Radar.

Python has already calculated the balance, gap, date, cause, and suggested spending reductions.

### Input

```json
{
  "customer": {
    "customer_id": "CUST003",
    "ar_name": "خالد",
    "en_name": "Khalid"
  },
  "has_gap": true,
  "alert_type": "installment_gap",
  "gap_amount": 340,
  "gap_date": "2026-07-27",
  "cause_category": {
    "category": "cafes",
    "label_ar": "المقاهي",
    "mtd": 760,
    "baseline_mtd": 420,
    "deviation_pct": 81
  },
  "trajectory": {
    "balance_now": 2800,
    "savings_reserve": 5000,
    "daily_flexible_pace": 145,
    "upcoming_commitments_total": 2200,
    "projected_eom_balance": -340,
    "suggested_cuts": [
      {
        "category": "cafes",
        "label_ar": "المقاهي",
        "recoverable": 360
      }
    ]
  }
}
```

### Output

```json
{
  "guidance_ar": "خفّض إنفاق المقاهي مؤقتاً حتى يمر الالتزام القادم بأمان.",
  "trace_message_ar": "تم اختيار الإجراء الأكثر ارتباطاً بسبب ارتفاع الإنفاق."
}
```

### What it really does

It phrases the best action without shaming the customer.

It is explicitly prohibited from writing:

- Numbers
- Dates
- Percentages
- Financial equations
- Suggestions to borrow more money

Python renders the factual message separately, such as the current balance, upcoming commitments, and projected ending balance. If the AI guidance contains digits, the application removes it.

---

## What Is Not an LLM Agent?

The Risk Model is machine learning, but it is not a Gemini agent. It receives six numeric features:

```json
{
  "obligation_ratio_peak": 0.61,
  "min_buffer_over_income": -0.06,
  "salary_timing_variance_days": 1.8,
  "bnpl_count": 3,
  "savings_cover_months": 0.7,
  "banks_with_obligations": 2
}
```

It returns a missed-payment probability. Deterministic verdict rules then combine that probability with the 12-month forecast to produce:

```json
{
  "verdict": "الأفضل تأجيله",
  "ready_in_months": 2,
  "reason_tags": [
    "temporary_overlap"
  ]
}
```

## Responsibility Chain

```text
Bank data
  → Python detects and calculates facts
  → AI understands transaction meaning
  → Python simulates and makes the verdict
  → AI explains the verdict
```

## Relevant Implementation Files

- Response schemas: `cloud-run/edrak/app/agents/schemas.py`
- Data Sufficiency Agent: `cloud-run/edrak/app/agents/data_sufficiency.py`
- Transaction Intelligence: `cloud-run/edrak/app/agents/transaction_intelligence.py`
- Decision Advisor: `cloud-run/edrak/app/agents/decision_advisor.py`
- Intervention Agent: `cloud-run/edrak/app/agents/intervention.py`
- Gemini client and schema validation: `cloud-run/edrak/app/agents/gemini_client.py`
- Pipeline orchestration: `cloud-run/edrak/app/pipeline.py`
