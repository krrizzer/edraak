-- BigQuery Standard SQL
-- Edraak manual table setup.

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.customer_profiles` (
  user_id STRING NOT NULL,
  name_ar STRING,
  customer_type STRING,
  monthly_income FLOAT64,
  current_balance FLOAT64,
  savings FLOAT64,
  monthly_obligations FLOAT64,
  avg_flexible_spending FLOAT64,
  risk_preference_ar STRING,
  behavior_summary_ar STRING,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.transactions` (
  transaction_id STRING NOT NULL,
  user_id STRING NOT NULL,
  transaction_date DATE,
  merchant STRING,
  category STRING,
  amount FLOAT64,
  transaction_type STRING,
  is_recurring BOOL,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.decision_requests` (
  request_id STRING NOT NULL,
  user_id STRING NOT NULL,
  goal_type STRING,
  goal_amount FLOAT64,
  monthly_installment FLOAT64,
  duration_months INT64,
  down_payment FLOAT64,
  urgency STRING,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.recommendations` (
  recommendation_id STRING NOT NULL,
  request_id STRING,
  user_id STRING,
  recommendation STRING,
  risk_score FLOAT64,
  safety_score FLOAT64,
  obligation_ratio_before FLOAT64,
  obligation_ratio_after FLOAT64,
  monthly_buffer_after FLOAT64,
  financial_seatbelt_status STRING,
  explanation_ar STRING,
  risk_factors_json STRING,
  safer_options_json STRING,
  readiness_path_json STRING,
  agent_trace_json STRING,
  created_at TIMESTAMP
);
