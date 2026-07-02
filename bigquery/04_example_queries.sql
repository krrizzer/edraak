-- BigQuery Standard SQL
-- Edraak development and testing queries.

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

-- Use this value in the examples below when testing one customer.
DECLARE selected_user_id STRING DEFAULT 'stable';

-- 1. Get all customer profiles.
SELECT
  *
FROM `YOUR_PROJECT_ID.edraak_finance.customer_profiles`
ORDER BY created_at DESC;

-- 2. Get transactions for a specific user.
SELECT
  *
FROM `YOUR_PROJECT_ID.edraak_finance.transactions`
WHERE user_id = selected_user_id
ORDER BY transaction_date DESC;

-- 3. Calculate total spending by category for a user.
SELECT
  category,
  ROUND(SUM(ABS(amount)), 2) AS total_spending
FROM `YOUR_PROJECT_ID.edraak_finance.transactions`
WHERE user_id = selected_user_id
  AND transaction_type = 'expense'
GROUP BY category
ORDER BY total_spending DESC;

-- 4. Calculate recurring obligations for a user.
SELECT
  user_id,
  ROUND(SUM(ABS(amount)), 2) AS recurring_obligations
FROM `YOUR_PROJECT_ID.edraak_finance.transactions`
WHERE user_id = selected_user_id
  AND transaction_type = 'expense'
  AND is_recurring = TRUE
GROUP BY user_id;

-- 5. Get latest decision requests.
SELECT
  request_id,
  user_id,
  goal_type,
  goal_amount,
  monthly_installment,
  duration_months,
  urgency,
  created_at
FROM `YOUR_PROJECT_ID.edraak_finance.decision_requests`
ORDER BY created_at DESC
LIMIT 20;

-- 6. Get recommendations with risk score.
SELECT
  recommendation_id,
  request_id,
  user_id,
  recommendation,
  risk_score,
  safety_score,
  explanation_ar,
  created_at
FROM `YOUR_PROJECT_ID.edraak_finance.recommendations`
ORDER BY risk_score DESC;

-- 7. Compare obligation ratio before vs after a decision.
SELECT
  recommendation_id,
  user_id,
  recommendation,
  obligation_ratio_before,
  obligation_ratio_after,
  obligation_ratio_after - obligation_ratio_before AS obligation_ratio_change
FROM `YOUR_PROJECT_ID.edraak_finance.recommendations`
ORDER BY obligation_ratio_change DESC;

-- 8. Query customers with high financial risk.
SELECT
  profile.user_id,
  profile.name_ar,
  profile.monthly_income,
  profile.monthly_obligations,
  recommendation.recommendation,
  recommendation.risk_score,
  recommendation.monthly_buffer_after
FROM `YOUR_PROJECT_ID.edraak_finance.customer_profiles` AS profile
JOIN `YOUR_PROJECT_ID.edraak_finance.recommendations` AS recommendation
  ON profile.user_id = recommendation.user_id
WHERE recommendation.risk_score >= 65
   OR recommendation.monthly_buffer_after < 0
ORDER BY recommendation.risk_score DESC;
