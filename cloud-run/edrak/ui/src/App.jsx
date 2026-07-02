import { useState } from "react";

const apiBase =
  import.meta.env.VITE_API_BASE_URL ||
  (window.location.port === "5173" ? "http://localhost:8080" : "");

const goalTypes = [
  ["car", "تمويل سيارة"],
  ["home", "التزام سكني"],
  ["wedding", "مصاريف زواج"],
  ["travel", "سفر"],
  ["debt", "سداد دين"],
  ["emergency", "تمويل طارئ"],
];

const urgencyOptions = [
  ["low", "منخفضة"],
  ["medium", "متوسطة"],
  ["high", "عالية"],
];

export default function App() {
  const [username, setUsername] = useState("");
  const [customer, setCustomer] = useState(null);
  const [form, setForm] = useState({
    goal_type: "car",
    goal_amount: 120000,
    monthly_installment: 2500,
    duration_months: 48,
    down_payment: 10000,
    urgency: "medium",
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: ["goal_type", "urgency"].includes(field) ? value : Number(value),
    }));
  }

  async function login(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiBase}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
      });

      if (!response.ok) throw new Error("login failed");
      setCustomer(await response.json());
      setResult(null);
    } catch {
      setError("لم يتم العثور على المستخدم. جرّب fahad أو sara أو khalid.");
    } finally {
      setLoading(false);
    }
  }

  async function analyzeDecision(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${apiBase}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customer.customer_id, ...form }),
      });

      if (!response.ok) throw new Error("analysis failed");
      setResult(await response.json());
    } catch {
      setError("تعذر تحليل القرار. تأكد من تشغيل الـ API.");
    } finally {
      setLoading(false);
    }
  }

  if (!customer) {
    return (
      <main className="login-page" dir="rtl">
        <section className="login-panel">
          <p className="eyebrow">Agentic AI CFO</p>
          <h1>إدراك</h1>
          <h2>حزام الأمان المالي قبل الالتزامات الكبيرة</h2>
          <form onSubmit={login}>
            <label>
              اسم المستخدم بالإنجليزية
              <input
                autoFocus
                dir="ltr"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="fahad"
              />
            </label>
            <button className="primary-action" type="submit" disabled={loading || !username.trim()}>
              {loading ? "جاري الدخول..." : "دخول"}
            </button>
            <p className="helper">جرّب: fahad أو sara أو khalid</p>
            {error && <p className="error">{error}</p>}
          </form>
        </section>
      </main>
    );
  }

  return (
    <main dir="rtl">
      <header className="topbar">
        <div>
          <p className="eyebrow">إدراك</p>
          <h1>مرحبًا، {customer.ar_name}</h1>
          <p>أدخل تفاصيل القرار المالي وسنحلل أثره بناء على بياناتك البنكية التجريبية.</p>
        </div>
        <button className="secondary-action" onClick={() => setCustomer(null)}>
          تغيير المستخدم
        </button>
      </header>

      <section className="workspace">
        <form className="decision-form" onSubmit={analyzeDecision}>
          <h2>تفاصيل القرار</h2>
          <label>
            نوع الهدف
            <select value={form.goal_type} onChange={(event) => updateField("goal_type", event.target.value)}>
              {goalTypes.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            مبلغ الهدف
            <input type="number" value={form.goal_amount} onChange={(event) => updateField("goal_amount", event.target.value)} />
          </label>
          <label>
            القسط الشهري المتوقع
            <input type="number" value={form.monthly_installment} onChange={(event) => updateField("monthly_installment", event.target.value)} />
          </label>
          <label>
            مدة الالتزام بالأشهر
            <input type="number" value={form.duration_months} onChange={(event) => updateField("duration_months", event.target.value)} />
          </label>
          <label>
            الدفعة المقدمة
            <input type="number" value={form.down_payment} onChange={(event) => updateField("down_payment", event.target.value)} />
          </label>
          <label>
            درجة الاستعجال
            <select value={form.urgency} onChange={(event) => updateField("urgency", event.target.value)}>
              {urgencyOptions.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button className="primary-action" type="submit" disabled={loading}>
            {loading ? "جاري التحليل..." : "حلّل القرار"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>

        <section className="results">
          {!result && <p className="empty-state">ابدأ التحليل لعرض التوصية ومسار الوكلاء.</p>}
          {result && <Results result={result} />}
        </section>
      </section>
    </main>
  );
}

function Results({ result }) {
  const profile = result.generated_profile;

  return (
    <>
      <article className="result-panel">
        <div className="result-head">
          <span className="badge">{result.recommendation}</span>
          <Metric label="المخاطر" value={result.risk_score} />
          <Metric label="الأمان" value={result.safety_score} />
          <Metric label="الثقة" value={result.confidence} />
        </div>
        <div className="metrics">
          <span>حزام الأمان: {result.financial_seatbelt_status}</span>
          <span>قبل القرار: {result.obligation_ratio_before}%</span>
          <span>بعد القرار: {result.obligation_ratio_after}%</span>
          <span>الفائض المتوقع: {result.monthly_buffer_after.toLocaleString()} ر.س</span>
        </div>
        <p className="explanation">{result.explanation_ar}</p>
      </article>

      <article className="summary-panel">
        <h2>الملف المالي المشتق</h2>
        <div className="summary-grid">
          <Metric label="الراتب" value={`${profile.salary.toLocaleString()} ر.س`} />
          <Metric label="أقساط القروض" value={`${profile.monthly_loan_installments.toLocaleString()} ر.س`} />
          <Metric label="الإنفاق المرن" value={`${profile.avg_flexible_spending.toLocaleString()} ر.س`} />
          <Metric label="الالتزامات" value={`${profile.recurring_obligations.toLocaleString()} ر.س`} />
          <Metric label="القروض النشطة" value={profile.active_loans_count} />
          <Metric label="المتبقي من القروض" value={`${profile.total_remaining_loans.toLocaleString()} ر.س`} />
        </div>
        <p>{profile.spending_behavior_summary_ar}</p>
      </article>

      {result.validation_warnings_ar.length > 0 && (
        <List title="تنبيهات التحقق" items={result.validation_warnings_ar} />
      )}
      <List title="عوامل المخاطر" items={result.risk_factors_ar} />
      <List title="بدائل أكثر أمانًا" items={result.safer_options_ar} />
      <ReadinessPath path={result.readiness_path_ar} />
      <AgentTrace items={result.agent_trace_ar} />
    </>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <small>{label}</small>
    </div>
  );
}

function List({ title, items }) {
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

function ReadinessPath({ path }) {
  return (
    <article className="simple-panel">
      <h2>مسار الجاهزية</h2>
      <div className="path-grid">
        {Object.entries(path).map(([period, items]) => (
          <div className="path-card" key={period}>
            <strong>{period.replace("_days", " يوم")}</strong>
            <ul>
              {items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </article>
  );
}

function AgentTrace({ items }) {
  return (
    <article className="simple-panel">
      <h2>مسار الوكلاء</h2>
      <div className="trace-grid">
        {items.map((item) => (
          <div className="trace-card" key={item.agent}>
            <span>{item.status}</span>
            <h3>{item.agent}</h3>
            <p>{item.message}</p>
          </div>
        ))}
      </div>
    </article>
  );
}
