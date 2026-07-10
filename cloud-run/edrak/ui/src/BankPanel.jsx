// "ما لا يراه بنكك": detected obligations grouped by bank — the cross-bank money shot.
import { BANK_NAMES_AR, OBLIGATION_BADGES, sar } from "./shared";

export default function BankPanel({ obligationsByBank }) {
  const banks = Object.entries(obligationsByBank || {});
  if (banks.length === 0) return null;

  return (
    <article className="bank-panel">
      <h2>ما لا يراه بنكك</h2>
      <p className="helper">
        التزامات رصدها الذكاء الاصطناعي من أوصاف المعاملات الخام عبر جميع بنوكك — هذا ما لا يظهر في فحص المديونية التقليدي لبنك واحد.
      </p>
      <div className="bank-grid">
        {banks.map(([bankCode, items]) => (
          <div className="bank-card" key={bankCode}>
            <h3>{BANK_NAMES_AR[bankCode] || bankCode}</h3>
            <ul className="obligation-list">
              {items.map((item) => (
                <li key={`${bankCode}-${item.counterparty}-${item.monthly_amount}`}>
                  <span className={`type-badge type-${item.obligation_type}`}>
                    {OBLIGATION_BADGES[item.obligation_type] || item.obligation_type}
                  </span>
                  <strong>{item.label_ar || item.counterparty}</strong>
                  <span className="obligation-amount">{sar(item.monthly_amount)} شهريًا</span>
                  <small>
                    يوم {item.day_of_month}
                    {item.remaining_months != null ? ` · متبقٍ ${item.remaining_months} شهر` : " · مستمر"}
                    {` · ثقة ${Math.round((item.confidence || 0) * 100)}%`}
                  </small>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </article>
  );
}
