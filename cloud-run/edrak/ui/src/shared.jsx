// Small shared building blocks used by both modes.

export const BANK_NAMES_AR = {
  ALRAJHI: "مصرف الراجحي",
  SNB: "البنك الأهلي السعودي",
  RIYAD: "بنك الرياض",
  SAB: "البنك السعودي الأول",
  UNKNOWN: "بنك غير محدد",
};

export const OBLIGATION_BADGES = {
  bnpl_installment: "أقساط BNPL",
  jamiya: "جمعية",
  family_support: "حوالة عائلية",
  rent: "إيجار",
  subscription: "اشتراك",
  loan_installment_other_bank: "قرض بنك آخر",
};

export const STEP_NAMES_AR = {
  validator: "التحقق من البيانات",
  recurrence_detector: "كشف الالتزامات المتكررة",
  transaction_intelligence: "تصنيف الالتزامات",
  forecast_engine: "محرك التوقعات",
  risk_model: "نموذج المخاطر",
  verdict_rules: "قواعد القرار",
  decision_advisor: "المستشار المالي",
  radar_detector: "كاشف الرادار",
  intervention_agent: "وكيل التدخل",
};

// Maps each verdict to a badge colour class (green safe -> red not-suitable).
const VERDICT_CLASSES = {
  "قرار آمن": "verdict-safe",
  "مقبول بحذر": "verdict-caution",
  "الأفضل تأجيله": "verdict-delay",
  "غير مناسب": "verdict-avoid",
};

export function verdictClass(verdict) {
  return VERDICT_CLASSES[verdict] || "verdict-caution";
}

export function sar(value) {
  if (value === null || value === undefined) return "-";
  return `${Math.round(value).toLocaleString("en-US")} ر.س`;
}

export function Spinner({ size = "small" }) {
  return <span className={`spinner spinner-${size}`} aria-hidden="true" />;
}

export function InlineLoading({ title, detail }) {
  return (
    <div className="inline-loading">
      <Spinner />
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
    </div>
  );
}

export function LoadingPanel({ title, steps }) {
  return (
    <article className="loading-panel" aria-live="polite">
      <div className="loading-hero">
        <Spinner size="large" />
        <div>
          <h2>{title}</h2>
          <p>الطلب يعمل الآن، وستظهر النتيجة هنا مباشرة عند اكتمال التحليل.</p>
        </div>
      </div>
      <div className="loading-steps">
        {steps.map((step, index) => (
          <div className="loading-step" style={{ "--delay": `${index * 0.35}s` }} key={step}>
            <span className="loading-dot" />
            <strong>{step}</strong>
          </div>
        ))}
      </div>
      <div className="loading-bar" />
    </article>
  );
}

export function Metric({ label, value }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <small>{label}</small>
    </div>
  );
}

export function List({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <article className="simple-panel">
      <h2>{title}</h2>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  );
}

// The honest step trace: deterministic steps and LLM steps are labeled apart.
export function StepTrace({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <article className="simple-panel">
      <h2>مسار المعالجة</h2>
      <div className="trace-grid">
        {items.map((item) => (
          <div className="trace-card" key={item.step}>
            <span className={item.kind === "llm" ? "kind-llm" : "kind-det"}>
              {item.kind === "llm" ? "ذكاء اصطناعي" : "حتمي"}
            </span>
            <h3>{STEP_NAMES_AR[item.step] || item.step}</h3>
            <p>{item.message_ar}</p>
            <small>{item.elapsed_ms} م.ث</small>
          </div>
        ))}
      </div>
    </article>
  );
}
