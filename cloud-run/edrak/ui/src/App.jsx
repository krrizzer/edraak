import { useEffect, useMemo, useState } from "react";

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

const architectureCards = [
  ["Cloud Run", "تشغيل التطبيق والـ API"],
  ["BigQuery", "تخزين وتحليل البيانات المالية"],
  ["Vertex AI / Gemini", "تشغيل وكيل الذكاء الاصطناعي لاحقًا"],
  ["ADK Agents", "تنظيم الوكلاء والأدوات"],
  ["IAM / Secret Manager", "تأمين الوصول"],
  ["Cloud Logging", "مراقبة النظام"],
];

export default function App() {
  const [profiles, setProfiles] = useState([]);
  const [selectedUser, setSelectedUser] = useState("stable");
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

  useEffect(() => {
    fetch(`${apiBase}/api/profiles`)
      .then((response) => response.json())
      .then((data) => {
        setProfiles(data);
        if (data[0]?.user_id) setSelectedUser(data[0].user_id);
      })
      .catch(() => setError("تعذر تحميل الملفات المالية التجريبية."));
  }, []);

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.user_id === selectedUser),
    [profiles, selectedUser]
  );

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: ["goal_type", "urgency"].includes(field) ? value : Number(value),
    }));
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
        body: JSON.stringify({ user_id: selectedUser, ...form }),
      });

      if (!response.ok) throw new Error("bad response");
      setResult(await response.json());
    } catch {
      setError("تعذر تحليل القرار. تأكد من تشغيل الـ API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">Agentic AI CFO</p>
          <h1>إدراك</h1>
          <h2>حزام الأمان المالي للقرارات الكبيرة</h2>
          <p>
            إدراك يحلل أثر القروض والالتزامات قبل اتخاذ القرار، ويقترح بدائل
            أكثر أمانًا ومسارًا واضحًا للوصول إلى الجاهزية المالية.
          </p>
        </div>
        <div className="seatbelt-panel">
          <span>حزام الأمان المالي</span>
          <strong>{result?.financial_seatbelt_status || "جاهز"}</strong>
          <small>تحليل مبني على بيانات صناعية آمنة للعرض التجريبي</small>
        </div>
      </section>

      <section>
        <div className="section-title">
          <h2>اختر الملف المالي</h2>
          <p>ثلاث شخصيات صناعية لاختبار السيناريو بسرعة.</p>
        </div>
        <div className="profile-grid">
          {profiles.map((profile) => (
            <button
              className={`profile-card ${selectedUser === profile.user_id ? "active" : ""}`}
              key={profile.user_id}
              onClick={() => setSelectedUser(profile.user_id)}
            >
              <strong>{profile.name_ar}</strong>
              <span>{profile.behavior_summary_ar}</span>
              <dl>
                <div>
                  <dt>الدخل</dt>
                  <dd>{profile.monthly_income.toLocaleString()} ر.س</dd>
                </div>
                <div>
                  <dt>الالتزامات</dt>
                  <dd>{profile.monthly_obligations.toLocaleString()} ر.س</dd>
                </div>
              </dl>
            </button>
          ))}
        </div>
      </section>

      <section className="workspace">
        <form className="decision-form" onSubmit={analyzeDecision}>
          <h2>تفاصيل القرار</h2>
          <label>
            نوع الهدف
            <select value={form.goal_type} onChange={(event) => updateField("goal_type", event.target.value)}>
              {goalTypes.map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
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
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </label>
          <button className="primary-action" type="submit" disabled={loading || !selectedProfile}>
            {loading ? "جاري التحليل..." : "حلّل القرار"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>

        <div className="results">
          <h2>مسار الوكلاء</h2>
          <div className="trace-grid">
            {(result?.agent_trace_ar || []).map((item) => (
              <article className="trace-card" key={item.agent}>
                <span>{item.status}</span>
                <h3>{item.agent}</h3>
                <p>{item.message}</p>
              </article>
            ))}
            {!result && <p className="empty-state">ابدأ التحليل لعرض خطوات الوكلاء.</p>}
          </div>

          {result && (
            <article className="result-panel">
              <div className="result-head">
                <span className="badge">{result.recommendation}</span>
                <div>
                  <strong>{result.risk_score}</strong>
                  <small>درجة المخاطر</small>
                </div>
                <div>
                  <strong>{result.safety_score}</strong>
                  <small>درجة الأمان</small>
                </div>
              </div>
              <div className="metrics">
                <span>قبل القرار: {result.obligation_ratio_before}%</span>
                <span>بعد القرار: {result.obligation_ratio_after}%</span>
                <span>الفائض: {result.monthly_buffer_after.toLocaleString()} ر.س</span>
              </div>
              <p className="explanation">{result.explanation_ar}</p>
              <List title="عوامل المخاطر" items={result.risk_factors_ar} />
              <List title="بدائل أكثر أمانًا" items={result.safer_options_ar} />
              <div>
                <h3>مسار الجاهزية</h3>
                <div className="path-grid">
                  {Object.entries(result.readiness_path_ar).map(([period, items]) => (
                    <div className="path-card" key={period}>
                      <strong>{period.replace("_days", " يوم")}</strong>
                      <ul>
                        {items.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            </article>
          )}
        </div>
      </section>

      <section>
        <div className="section-title">
          <h2>معمارية Google Cloud</h2>
          <p>جاهزة للتوسع من النموذج التجريبي إلى تكامل فعلي.</p>
        </div>
        <div className="architecture-grid">
          {architectureCards.map(([title, text]) => (
            <article className="architecture-card" key={title}>
              <strong>{title}</strong>
              <span>{text}</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function List({ title, items }) {
  return (
    <div>
      <h3>{title}</h3>
      <ul>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}
