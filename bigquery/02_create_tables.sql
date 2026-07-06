-- BigQuery Standard SQL
-- Edraak manual table setup.

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

-- Source banking table: customer identity and base account information.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.customers` (
  customer_id STRING NOT NULL,
  username_en STRING NOT NULL,
  ar_name STRING,
  en_name STRING,
  national_id STRING,
  birthday DATE,
  salary FLOAT64,
  current_balance FLOAT64,
  city STRING,
  employment_sector STRING,
  employer_name STRING,
  account_open_date DATE,
  created_at TIMESTAMP
);

-- Source banking table: income, spending, transfers, and recurring payments.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.transactions` (
  transaction_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  transaction_date DATE,
  merchant STRING,
  category STRING,
  amount FLOAT64,
  transaction_type STRING,
  is_recurring BOOL,
  channel STRING,
  created_at TIMESTAMP
);

-- Source banking table: active and closed loan commitments.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.loans` (
  loan_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  loan_type STRING,
  loan_total_amount FLOAT64,
  total_profit_amount FLOAT64,
  total_amount FLOAT64,
  remaining_amount FLOAT64,
  monthly_installment FLOAT64,
  start_date DATE,
  end_date DATE,
  status STRING,
  created_at TIMESTAMP
);

-- Derived analytical table: generated from customers + transactions + loans.
-- This is not an original bank source table.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.user_profiles` (
  customer_id STRING NOT NULL,
  ar_name STRING,
  en_name STRING,
  salary FLOAT64,
  current_balance FLOAT64,
  active_loans_count INT64,
  total_remaining_loans FLOAT64,
  monthly_loan_installments FLOAT64,
  avg_monthly_spending FLOAT64,
  avg_flexible_spending FLOAT64,
  recurring_obligations FLOAT64,
  savings_estimate FLOAT64,
  obligation_ratio FLOAT64,
  spending_behavior_summary_ar STRING,
  risk_preference_estimate_ar STRING,
  profile_generated_at TIMESTAMP
);

-- User-submitted commitment requests.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.decision_requests` (
  request_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  goal_type STRING,
  goal_amount FLOAT64,
  monthly_installment FLOAT64,
  duration_months INT64,
  down_payment FLOAT64,
  urgency STRING,
  created_at TIMESTAMP
);

-- Agent recommendation output.
-- JSON fields are stored as STRING for simple prototype copy/paste usage.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.recommendations` (
  recommendation_id STRING NOT NULL,
  request_id STRING,
  customer_id STRING,
  recommendation STRING,
  risk_score FLOAT64,
  safety_score FLOAT64,
  obligation_ratio_before FLOAT64,
  obligation_ratio_after FLOAT64,
  monthly_buffer_after FLOAT64,
  financial_seatbelt_status STRING,
  confidence STRING,
  validation_warnings_json STRING,
  explanation_ar STRING,
  risk_factors_json STRING,
  safer_options_json STRING,
  readiness_path_json STRING,
  agent_trace_json STRING,
  created_at TIMESTAMP
);
