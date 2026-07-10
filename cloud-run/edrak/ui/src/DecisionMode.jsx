// Mode A — the Decision Seatbelt: goal form, 12-month forecast, verdict, and advice.
import { useState } from "react";
import { postJson } from "./api";
import BankPanel from "./BankPanel";
import ForecastChart from "./ForecastChart";
import { List, LoadingPanel, Metric, Spinner, StepTrace, sar, verdictClass } from "./shared";

const goalTypes = [
  ["car", "تمويل سيارة"],
  ["home", "التزام سكني"],
  ["wedding", "مصاريف زواج"],
  ["travel", "سفر"],
  ["debt", "سداد دين"],
  ["emergency", "تمويل طارئ"],
];

const analysisSteps = [
  "التحقق من البيانات عبر البنوك",
  "كشف الالتزامات المتكررة وتصنيفها",
  "محاكاة التدفق النقدي 12 شهرًا",
  "تطبيق قواعد القرار وتقدير المخاطر",
  "كتابة التوصية والبدائل",
];

export default function DecisionMode({ customer }) {
  const [form, setForm] = useState({
    goal_type: "car",
    goal_amount: 120000,
    monthly_installment: 2500,
    duration_months: 48,
    down_payment: 10000,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: field === "goal_type" ? value : Number(value),
    }));
  }

  async function analyzeDecision(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await postJson("/api/analyze", { customer_id: customer.customer_id, ...form }, "فشل تحليل القرار."));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="workspace">
      <form className="decision-form" onSubmit={analyzeDecision}>
        <h2>تفاصيل القرار</h2>
        <label>
          نوع الهدف
          <select value={form.goal_type} onChange={(e) => updateField("goal_type", e.target.value)} disabled={loading}>
            {goalTypes.map(([value, label]) => (
              <option value={value} key={value}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          مبلغ الهدف
          <input type="number" value={form.goal_amount} onChange={(e) => updateField("goal_amount", e.target.value)} disabled={loading} />
        </label>
        <label>
          القسط الشهري المتوقع
          <input type="number" value={form.monthly_installment} onChange={(e) => updateField("monthly_installment", e.target.value)} disabled={loading} />
        </label>
        <label>
          مدة الالتزام بالأشهر
          <input type="number" value={form.duration_months} onChange={(e) => updateField("duration_months", e.target.value)} disabled={loading} />
        </label>
        <label>
          الدفعة المقدمة
          <input type="number" value={form.down_payment} onChange={(e) => updateField("down_payment", e.target.value)} disabled={loading} />
        </label>
        <button className="primary-action" type="submit" disabled={loading}>
          {loading ? (
            <span className="button-loading">
              <Spinner />
              جاري التحليل...
            </span>
          ) : (
            "حلّل القرار"
          )}
        </button>
        {error && <p className="error">{error}</p>}
      </form>

      <section className="results">
        {loading && <LoadingPanel title="جاري تحليل القرار عبر بنوكك" steps={analysisSteps} />}
        {!loading && !result && <p className="empty-state">ابدأ التحليل لعرض التوقعات الشهرية والتوصية.</p>}
        {!loading && result && <Results result={result} />}
      </section>
    </section>
  );
}

function Results({ result }) {
  const forecast = result.forecast;
  const readiness =
    result.ready_in_months != null
      ? `بعد ${result.ready_in_months} شهر`
      : result.recommendation === "غير مناسب"
      ? "غير قابل للتأجيل"
      : "الآن";
  return (
    <>
      <article className="result-panel">
        <div className="result-head">
          <span className={`badge ${verdictClass(result.recommendation)}`}>{result.recommendation}</span>
          <Metric label="احتمالية التعثر" value={`${Math.round(result.risk_probability * 100)}%`} />
          <Metric label="أدنى فائض شهري" value={sar(forecast.min_buffer_value)} />
          <Metric label="الجاهزية" value={readiness} />
        </div>
        <p className="explanation">{result.explanation_ar}</p>
      </article>

      <ForecastChart forecast={forecast} />
      <BankPanel obligationsByBank={result.detected_obligations_by_bank} />

      <article className="summary-panel">
        <h2>ملفك المالي عبر البنوك</h2>
        <div className="summary-grid">
          <Metric label="الراتب" value={sar(result.profile.salary)} />
          <Metric label="إجمالي الأرصدة" value={sar(result.profile.total_balance)} />
          <Metric label="عدد البنوك" value={result.profile.banks_count} />
          <Metric label="أقساط القروض" value={sar(result.profile.monthly_loan_installments)} />
          <Metric label="متوسط الصرف الشهري" value={sar(result.profile.avg_monthly_spending)} />
          <Metric label="الإنفاق المرن" value={sar(result.profile.avg_flexible_spending)} />
        </div>
      </article>

      {result.validation_warnings_ar.length > 0 && (
        <List title="تنبيهات التحقق" items={result.validation_warnings_ar} />
      )}
      <List title="عوامل المخاطر" items={result.risk_factors_ar} />
      <List title="بدائل أكثر أمانًا" items={result.safer_options_ar} />
      <StepTrace items={result.step_trace} />
    </>
  );
}
