-- BigQuery Standard SQL
-- Edraak development and testing queries (cross-bank reshape).

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

-- Use this value in the examples below when testing one customer.
DECLARE selected_customer_id STRING DEFAULT 'CUST001';
DECLARE selected_username STRING DEFAULT 'fahad';

-- 1. Find the customer by English username, same as the login flow.
SELECT customer_id, username_en, ar_name, en_name, salary
FROM `YOUR_PROJECT_ID.edraak_finance.customers`
WHERE username_en = selected_username;

-- 2. Cross-bank visibility: every account the customer holds at every bank.
SELECT account_id, bank_code, bank_name_ar, account_type, iban, balance, is_primary
FROM `YOUR_PROJECT_ID.edraak_finance.accounts`
WHERE customer_id = selected_customer_id
ORDER BY is_primary DESC, bank_code;

-- 3. The messy narrative strings the Transaction Intelligence Agent reads.
SELECT transaction_date, bank_code, amount, raw_description, category
FROM `YOUR_PROJECT_ID.edraak_finance.transactions`
WHERE customer_id = selected_customer_id
ORDER BY transaction_date DESC
LIMIT 50;

-- 4. Loans across all banks with the months they have left.
SELECT loan_id, bank_code, loan_type, monthly_installment, remaining_months,
       remaining_amount, first_installment_date, status
FROM `YOUR_PROJECT_ID.edraak_finance.loans`
WHERE customer_id = selected_customer_id
  AND status = 'active'
ORDER BY remaining_months;

-- 5. What the LLM detected across banks (cache of Agent 1 output).
SELECT obligation_type, counterparty, monthly_amount, day_of_month,
       remaining_months, confidence, is_committed, source_bank_codes, detected_at
FROM `YOUR_PROJECT_ID.edraak_finance.detected_obligations`
WHERE customer_id = selected_customer_id
ORDER BY monthly_amount DESC;

-- 6. The derived cross-bank profile used by the forecast engine.
SELECT customer_id, salary, salary_day, salary_timing_variance_days,
       total_balance, banks_count, active_loans_count,
       monthly_loan_installments, avg_monthly_spending, avg_flexible_spending
FROM `YOUR_PROJECT_ID.edraak_finance.user_profiles`
WHERE customer_id = selected_customer_id
ORDER BY profile_generated_at DESC
LIMIT 1;

-- 7. Latest decision requests (storage-only table).
SELECT request_id, customer_id, goal_type, goal_amount, monthly_installment,
       duration_months, down_payment, created_at
FROM `YOUR_PROJECT_ID.edraak_finance.decision_requests`
ORDER BY created_at DESC
LIMIT 20;

-- 8. Recommendations with the forecast-curve summary columns.
SELECT recommendation_id, customer_id, recommendation, ready_in_months,
       risk_probability, obligation_ratio_now, obligation_ratio_peak,
       first_shortfall_month, min_buffer_value, months_of_savings_cover, created_at
FROM `YOUR_PROJECT_ID.edraak_finance.recommendations`
ORDER BY created_at DESC
LIMIT 20;

-- 9. Radar alerts fired for a customer (storage-only table).
SELECT alert_id, created_at, alert_type, gap_amount, gap_date,
       cause_category, message_ar
FROM `YOUR_PROJECT_ID.edraak_finance.alerts`
WHERE customer_id = selected_customer_id
ORDER BY created_at DESC;

-- 10. BNPL exposure per customer across banks, from the detected cache.
SELECT customer_id,
       COUNT(*) AS bnpl_plans,
       ROUND(SUM(monthly_amount), 2) AS monthly_bnpl_total
FROM `YOUR_PROJECT_ID.edraak_finance.detected_obligations`
WHERE obligation_type = 'bnpl_installment'
GROUP BY customer_id
ORDER BY monthly_bnpl_total DESC;
