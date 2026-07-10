// App shell: login → mode selection → Decision Seatbelt (Mode A) or Financial Radar (Mode B).
import { useState } from "react";
import { postJson } from "./api";
import DecisionMode from "./DecisionMode";
import RadarMode from "./RadarMode";
import { InlineLoading, Spinner } from "./shared";

export default function App() {
  const [username, setUsername] = useState("");
  const [customer, setCustomer] = useState(null);
  const [mode, setMode] = useState(null); // null → mode selection, "decision" | "radar"
  const [loginLoading, setLoginLoading] = useState(false);
  const [error, setError] = useState("");

  async function login(event) {
    event.preventDefault();
    setLoginLoading(true);
    setError("");
    try {
      setCustomer(await postJson("/api/login", { username }, "فشل تسجيل الدخول."));
      setMode(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoginLoading(false);
    }
  }

  function logout() {
    setCustomer(null);
    setMode(null);
    setError("");
  }

  if (!customer) {
    return (
      <main className="login-page" dir="rtl">
        <section className="login-panel">
          <p className="eyebrow">حزام الأمان المالي عبر البنوك</p>
          <h1>إدراك</h1>
          <h2>يرى كل بنوكك، ويحسب أشهرك القادمة قبل أن تلتزم</h2>
          <form onSubmit={login}>
            <label>
              اسم المستخدم بالإنجليزية
              <input
                autoFocus
                dir="ltr"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="fahad"
                disabled={loginLoading}
              />
            </label>
            <button className="primary-action" type="submit" disabled={loginLoading || !username.trim()}>
              {loginLoading ? (
                <span className="button-loading">
                  <Spinner />
                  جاري الدخول...
                </span>
              ) : (
                "دخول"
              )}
            </button>
            <p className="helper">جرّب: fahad أو sara أو khalid أو noura</p>
            {loginLoading && <InlineLoading title="جاري التحقق من المستخدم" detail="نبحث عن بيانات العميل الأساسية." />}
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
          <p>رؤية موحدة عبر جميع بنوكك: افحص قرارًا قبل اتخاذه، أو راقب مسار شهرك الحالي.</p>
        </div>
        <div className="topbar-actions">
          {mode && (
            <button className="secondary-action" onClick={() => setMode(null)}>
              تغيير الوضع
            </button>
          )}
          <button className="secondary-action" onClick={logout}>
            تغيير المستخدم
          </button>
        </div>
      </header>

      {!mode && <ModeSelect onSelect={setMode} />}
      {mode === "decision" && <DecisionMode customer={customer} />}
      {mode === "radar" && <RadarMode customer={customer} />}
    </main>
  );
}

function ModeSelect({ onSelect }) {
  return (
    <section className="mode-select">
      <button className="mode-card" onClick={() => onSelect("decision")}>
        <span className="mode-icon">🛡️</span>
        <h2>حزام الأمان المالي</h2>
        <p>افحص قرارًا قبل اتخاذه: نحاكي أشهرك الاثني عشر القادمة عبر كل بنوكك ونخبرك متى وأين ستتعثر — ومتى تصبح جاهزًا.</p>
        <span className="mode-cta">افحص قرارًا ←</span>
      </button>
      <button className="mode-card" onClick={() => onSelect("radar")}>
        <span className="mode-icon">📡</span>
        <h2>الرادار المالي</h2>
        <p>تنبيهات استباقية: نراقب وتيرة صرفك هذا الشهر ونحذرك قبل أن ينقصك المبلغ عن قسط قادم — مع الحل الأسرع للفجوة.</p>
        <span className="mode-cta">افتح الرادار ←</span>
      </button>
    </section>
  );
}
