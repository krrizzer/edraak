-- BigQuery Standard SQL
-- Edraak manual table setup (cross-bank reshape).

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change edraak_finance if you use a different dataset name.

-- ============================================================
-- BANK CORES (separate dataset): the simulated core-banking data
-- behind the mock gateway. Create the dataset first:
--   CREATE SCHEMA IF NOT EXISTS `YOUR_PROJECT_ID.bank_cores`;
-- Same column shapes as the edraak_finance silver tables.
-- ============================================================

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.bank_cores.accounts` (
  account_id STRING NOT NULL, customer_id STRING NOT NULL, bank_code STRING,
  bank_name_ar STRING, account_type STRING, iban STRING, balance FLOAT64,
  is_primary BOOL, created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.bank_cores.transactions` (
  transaction_id STRING NOT NULL, customer_id STRING NOT NULL, account_id STRING,
  bank_code STRING, transaction_date DATE, merchant STRING,
  raw_description STRING, amount FLOAT64, transaction_type STRING, channel STRING,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.bank_cores.loans` (
  loan_id STRING NOT NULL, customer_id STRING NOT NULL, bank_code STRING,
  loan_type STRING, loan_total_amount FLOAT64, total_profit_amount FLOAT64,
  total_amount FLOAT64, remaining_amount FLOAT64, monthly_installment FLOAT64,
  remaining_months INT64, first_installment_date DATE, start_date DATE,
  end_date DATE, status STRING, created_at TIMESTAMP
);

-- Date + generator layout version; the backend re-seeds when either is stale.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.bank_cores.seed_meta` (
  anchor_date DATE NOT NULL,
  seeded_at TIMESTAMP,
  seed_version STRING
);

-- Append-only bank-side consent versions. The latest updated_at row is current.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.bank_cores.consents` (
  consent_id STRING NOT NULL, customer_id STRING NOT NULL, bank_code STRING NOT NULL,
  permissions ARRAY<STRING>, status STRING NOT NULL, created_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL, redirect_uri STRING, updated_at TIMESTAMP NOT NULL
);

-- ============================================================
-- EDRAAK_FINANCE (the app's own warehouse) below.
-- ============================================================

-- Source banking table: customer identity and employment information.
-- Balances live per bank in the accounts table.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.customers` (
  customer_id STRING NOT NULL,
  username_en STRING NOT NULL,
  ar_name STRING,
  en_name STRING,
  national_id STRING,
  birthday DATE,
  salary FLOAT64,
  city STRING,
  employment_sector STRING,
  employer_name STRING,
  account_open_date DATE,
  created_at TIMESTAMP
);

-- Cross-bank accounts: one row per bank account the customer holds anywhere.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.accounts` (
  account_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  bank_code STRING,
  bank_name_ar STRING,
  account_type STRING,
  iban STRING,
  balance FLOAT64,
  is_primary BOOL,
  created_at TIMESTAMP
);

-- Source banking table: cross-bank transaction feed.
-- raw_description carries the messy bank narrative the LLM agent classifies.
-- No source category: merchant/description/channel are the actual evidence.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.transactions` (
  transaction_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  account_id STRING,
  bank_code STRING,
  transaction_date DATE,
  merchant STRING,
  raw_description STRING,
  amount FLOAT64,
  transaction_type STRING,
  channel STRING,
  created_at TIMESTAMP
);

-- Source banking table: loans across ALL banks.
-- remaining_months drives the month-by-month forecast: a loan with
-- remaining_months = 1 disappears from the projection after next month.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.loans` (
  loan_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  bank_code STRING,
  loan_type STRING,
  loan_total_amount FLOAT64,
  total_profit_amount FLOAT64,
  total_amount FLOAT64,
  remaining_amount FLOAT64,
  monthly_installment FLOAT64,
  remaining_months INT64,
  first_installment_date DATE,
  start_date DATE,
  end_date DATE,
  status STRING,
  created_at TIMESTAMP
);

-- Derived analytical table: cross-bank aggregates built by the backend.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.user_profiles` (
  customer_id STRING NOT NULL,
  ar_name STRING,
  en_name STRING,
  salary FLOAT64,
  salary_day INT64,
  salary_timing_variance_days FLOAT64,
  total_balance FLOAT64,
  banks_count INT64,
  active_loans_count INT64,
  total_remaining_loans FLOAT64,
  monthly_loan_installments FLOAT64,
  avg_monthly_spending FLOAT64,
  avg_flexible_spending FLOAT64,
  monthly_spending_std FLOAT64,
  profile_generated_at TIMESTAMP
);

-- Derived cache table: Transaction Intelligence Agent output.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.detected_obligations` (
  customer_id STRING NOT NULL,
  obligation_type STRING,
  counterparty STRING,
  monthly_amount FLOAT64,
  day_of_month INT64,
  remaining_months INT64,
  confidence FLOAT64,
  is_committed BOOL,
  source_bank_codes ARRAY<STRING>,
  detected_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.transaction_classifications` (
  customer_id STRING NOT NULL, transaction_id STRING NOT NULL,
  category STRING NOT NULL, confidence FLOAT64, classified_at TIMESTAMP NOT NULL
);

-- TPP-side consent ledger: Edraak's record of every consent it holds.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.ob_consents` (
  consent_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  bank_code STRING,
  status STRING,
  permissions ARRAY<STRING>,
  created_at TIMESTAMP,
  expires_at TIMESTAMP,
  revoked_at TIMESTAMP
);

-- Bronze layer: raw KSAOB JSON as pulled from a bank gateway, before normalization.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.ob_raw_payloads` (
  payload_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  bank_code STRING,
  consent_id STRING,
  resource STRING,
  account_id STRING,
  page INT64,
  raw_json STRING,
  fetched_at TIMESTAMP
);

-- Storage-only table: radar alerts shown in the UI. Agents never read it.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.alerts` (
  alert_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  created_at TIMESTAMP,
  alert_type STRING,
  gap_amount FLOAT64,
  gap_date DATE,
  cause_category STRING,
  message_ar STRING,
  trajectory_json STRING
);

-- Storage-only table: user-submitted commitment requests.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.decision_requests` (
  request_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  goal_type STRING,
  goal_amount FLOAT64,
  monthly_installment FLOAT64,
  duration_months INT64,
  down_payment FLOAT64,
  created_at TIMESTAMP
);

-- Storage-only table: final recommendation output per analyzed decision.
-- JSON fields are stored as STRING for simple prototype copy/paste usage.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance.recommendations` (
  recommendation_id STRING NOT NULL,
  request_id STRING,
  customer_id STRING,
  recommendation STRING,
  ready_in_months INT64,
  risk_probability FLOAT64,
  obligation_ratio_now FLOAT64,
  obligation_ratio_peak FLOAT64,
  first_shortfall_month INT64,
  first_shortfall_amount FLOAT64,
  min_buffer_value FLOAT64,
  months_of_savings_cover FLOAT64,
  forecast_json STRING,
  validation_warnings_json STRING,
  explanation_ar STRING,
  risk_factors_json STRING,
  safer_options_json STRING,
  step_trace_json STRING,
  created_at TIMESTAMP
);
