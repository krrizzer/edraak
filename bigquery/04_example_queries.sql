-- BigQuery Standard SQL
-- Edraak development and testing queries.

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

-- Use this value in the examples below when testing one customer.
DECLARE selected_customer_id STRING DEFAULT 'CUST001';
DECLARE selected_username STRING DEFAULT 'fahad';

-- 1. Find the customer by English username, same as the login flow.
SELECT
  customer_id,
  username_en,
  ar_name,
  en_name,
  salary,
  current_balance
FROM `YOUR_PROJECT_ID.edraak_finance.customers`
WHERE username_en = selected_username;

-- 2. Get all source customer records.
SELECT
  customer_id,
  username_en,
  ar_name,
  en_name,
  salary,
  current_balance,
  city,
  employment_sector
FROM `YOUR_PROJECT_ID.edraak_finance.customers`
ORDER BY customer_id;

-- 3. Get transactions for one customer.
SELECT
  transaction_id,
  transaction_date,
  merchant,
  category,
  amount,
  transaction_type,
  is_recurring,
  channel
FROM `YOUR_PROJECT_ID.edraak_finance.transactions`
WHERE customer_id = selected_customer_id
ORDER BY transaction_date DESC;

-- 4. Calculate spending by category for one customer.
SELECT
  category,
  ROUND(SUM(ABS(amount)), 2) AS total_spending
FROM `YOUR_PROJECT_ID.edraak_finance.transactions`
WHERE customer_id = selected_customer_id
  AND transaction_type = 'expense'
GROUP BY category
ORDER BY total_spending DESC;

-- 5. Calculate recurring obligations from transactions and active loans.
SELECT
  customer.customer_id,
  customer.ar_name,
  IFNULL(transaction_obligations.recurring_transaction_amount, 0) AS recurring_transaction_amount,
  IFNULL(loan_obligations.monthly_loan_installments, 0) AS monthly_loan_installments,
  IFNULL(transaction_obligations.recurring_transaction_amount, 0)
    + IFNULL(loan_obligations.monthly_loan_installments, 0) AS estimated_recurring_obligations
FROM `YOUR_PROJECT_ID.edraak_finance.customers` AS customer
LEFT JOIN (
  SELECT
    customer_id,
    SUM(ABS(amount)) AS recurring_transaction_amount
  FROM `YOUR_PROJECT_ID.edraak_finance.transactions`
  WHERE transaction_type = 'expense'
    AND is_recurring = TRUE
  GROUP BY customer_id
) AS transaction_obligations
  ON customer.customer_id = transaction_obligations.customer_id
LEFT JOIN (
  SELECT
    customer_id,
    SUM(monthly_installment) AS monthly_loan_installments
  FROM `YOUR_PROJECT_ID.edraak_finance.loans`
  WHERE status = 'active'
  GROUP BY customer_id
) AS loan_obligations
  ON customer.customer_id = loan_obligations.customer_id
WHERE customer.customer_id = selected_customer_id;

-- 6. Get active loans for one customer.
SELECT
  loan_id,
  loan_type,
  loan_total_amount,
  total_profit_amount,
  total_amount,
  remaining_amount,
  monthly_installment,
  start_date,
  end_date,
  status
FROM `YOUR_PROJECT_ID.edraak_finance.loans`
WHERE customer_id = selected_customer_id
  AND status = 'active'
ORDER BY start_date DESC;

-- 7. Get the derived user profile used by the agents.
SELECT
  customer_id,
  ar_name,
  salary,
  active_loans_count,
  total_remaining_loans,
  monthly_loan_installments,
  avg_flexible_spending,
  recurring_obligations,
  obligation_ratio,
  spending_behavior_summary_ar
FROM `YOUR_PROJECT_ID.edraak_finance.user_profiles`
WHERE customer_id = selected_customer_id;

-- 8. Get latest decision requests.
SELECT
  request_id,
  customer_id,
  goal_type,
  goal_amount,
  monthly_installment,
  duration_months,
  urgency,
  created_at
FROM `YOUR_PROJECT_ID.edraak_finance.decision_requests`
ORDER BY created_at DESC
LIMIT 20;

-- 9. Get recommendations with risk score.
SELECT
  recommendation_id,
  request_id,
  customer_id,
  recommendation,
  risk_score,
  safety_score,
  confidence,
  explanation_ar,
  created_at
FROM `YOUR_PROJECT_ID.edraak_finance.recommendations`
ORDER BY risk_score DESC;

-- 10. Compare obligation ratio before vs after each analyzed decision.
SELECT
  recommendation_id,
  customer_id,
  recommendation,
  obligation_ratio_before,
  obligation_ratio_after,
  obligation_ratio_after - obligation_ratio_before AS obligation_ratio_change
FROM `YOUR_PROJECT_ID.edraak_finance.recommendations`
ORDER BY obligation_ratio_change DESC;

-- 11. Query customers with high financial risk.
SELECT
  customer.customer_id,
  customer.ar_name,
  customer.salary,
  profile.recurring_obligations,
  profile.obligation_ratio,
  recommendation.recommendation,
  recommendation.risk_score,
  recommendation.monthly_buffer_after
FROM `YOUR_PROJECT_ID.edraak_finance.customers` AS customer
JOIN `YOUR_PROJECT_ID.edraak_finance.user_profiles` AS profile
  ON customer.customer_id = profile.customer_id
JOIN `YOUR_PROJECT_ID.edraak_finance.recommendations` AS recommendation
  ON customer.customer_id = recommendation.customer_id
WHERE recommendation.risk_score >= 65
   OR recommendation.monthly_buffer_after < 0
   OR profile.obligation_ratio >= 55
ORDER BY recommendation.risk_score DESC;
