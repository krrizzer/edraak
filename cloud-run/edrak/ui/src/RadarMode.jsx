// Mode B — the Financial Radar: simulate the scheduled check, show the alert or the secure state.
import { useEffect, useState } from "react";
import { getJson, postJson } from "./api";
import { LoadingPanel, Spinner, StepTrace, sar } from "./shared";

const radarSteps = [
  "قراءة أرصدة وحركات الشهر الحالي",
  "مقارنة وتيرة الصرف بخط الأساس",
  "إسقاط الرصيد حتى مواعيد الأقساط",
  "صياغة التنبيه",
];

export default function RadarMode({ customer }) {
  const [result, setResult] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson(`/api/alerts/${customer.customer_id}`, "تعذر تحميل التنبيهات السابقة.")
      .then(setAlerts)
      .catch(() => setAlerts([]));
  }, [customer.customer_id, result]);

  async function triggerRadar() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await postJson("/api/radar/trigger", { customer_id: customer.customer_id }, "فشل فحص الرادار."));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="radar-layout">
      <article className="simple-panel radar-trigger">
        <h2>الرادار المالي</h2>
        <p>
          يراقب الرادار وتيرة صرفك الحالية عبر جميع بنوكك ويتوقع فجوات السداد قبل حدوثها.
        </p>
        <button className="primary-action" onClick={triggerRadar} disabled={loading}>
          {loading ? (
            <span className="button-loading">
              <Spinner />
              جاري الفحص...
            </span>
          ) : (
            "محاكاة فحص نهاية الشهر"
          )}
        </button>
        <small className="helper">
          في الإنتاج يعمل هذا الفحص تلقائيًا عبر Cloud Scheduler — الزر هنا يحاكي التشغيل المجدول.
        </small>
        {error && <p className="error">{error}</p>}
      </article>

      {loading && <LoadingPanel title="جاري فحص مسار الشهر الحالي" steps={radarSteps} />}
      {!loading && result && <RadarResult result={result} />}

      <PastAlerts alerts={alerts} />
    </section>
  );
}

function RadarResult({ result }) {
  return (
    <>
      <article className={result.has_gap ? "alert-card alert-danger" : "alert-card alert-safe"}>
        <h2>{result.title_ar}</h2>
        <p className="alert-message">{result.message_ar}</p>
        {result.has_gap && (
          <div className="metrics">
            <span className="warn-chip">الفجوة المتوقعة: {sar(result.gap_amount)}</span>
            <span className="warn-chip">التاريخ: {result.gap_date}</span>
            {result.cause_category && (
              <span className="warn-chip">
                السبب: {result.cause_category.label_ar} ‏(+{result.cause_category.deviation_pct}% عن المعتاد)
              </span>
            )}
          </div>
        )}
        {!result.has_gap && (
          <div className="metrics">
            <span>الحزام مثبّت — الرصيد المتوقع نهاية الشهر: {sar(result.trajectory.projected_eom_balance)}</span>
          </div>
        )}
      </article>

      <Trajectory trajectory={result.trajectory} />
      <StepTrace items={result.step_trace} />
    </>
  );
}

function Trajectory({ trajectory }) {
  return (
    <article className="simple-panel">
      <h2>الأرقام خلف النتيجة</h2>
      <div className="metrics">
        <span>الرصيد الحالي: {sar(trajectory.balance_now)}</span>
        <span>وتيرة الصرف اليومية: {sar(trajectory.daily_flexible_pace)}</span>
        <span>الرصيد المتوقع نهاية الشهر: {sar(trajectory.projected_eom_balance)}</span>
        {trajectory.expected_salary_day && <span>الراتب متوقع يوم {trajectory.expected_salary_day}</span>}
      </div>

      <h3>وتيرة الصرف حسب الفئة (مقارنة بنفس الأيام من الأشهر الماضية)</h3>
      <table className="pace-table">
        <thead>
          <tr>
            <th>الفئة</th>
            <th>هذا الشهر</th>
            <th>المعتاد</th>
            <th>الانحراف</th>
          </tr>
        </thead>
        <tbody>
          {trajectory.categories.map((row) => (
            <tr key={row.category}>
              <td>{row.label_ar}</td>
              <td>{sar(row.mtd)}</td>
              <td>{sar(row.baseline_mtd)}</td>
              <td className={row.deviation_pct > 20 ? "dev-up" : row.deviation_pct < -20 ? "dev-down" : ""}>
                {row.deviation_pct > 0 ? "+" : ""}{row.deviation_pct}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {trajectory.upcoming_payments.length > 0 && (
        <>
          <h3>الالتزامات القادمة هذا الشهر</h3>
          <ul>
            {trajectory.upcoming_payments.map((p) => (
              <li key={`${p.label}-${p.day}`}>
                يوم {p.day}: {p.label} — {sar(p.amount)}
              </li>
            ))}
          </ul>
        </>
      )}
    </article>
  );
}

function PastAlerts({ alerts }) {
  if (!alerts || alerts.length === 0) return null;
  return (
    <article className="simple-panel">
      <h2>تنبيهات سابقة</h2>
      <div className="past-alerts">
        {alerts.map((alert) => (
          <div className="past-alert" key={alert.alert_id}>
            <div className="past-alert-head">
              <strong>{sar(alert.gap_amount)}</strong>
              <small>{String(alert.created_at).slice(0, 10)} · قسط يوم {String(alert.gap_date).slice(8, 10)}</small>
            </div>
            <p>{alert.message_ar}</p>
          </div>
        ))}
      </div>
    </article>
  );
}
