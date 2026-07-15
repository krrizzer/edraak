-- BigQuery Standard SQL
-- Edraak manual dataset setup.

-- Replace YOUR_PROJECT_ID with your real Google Cloud project ID.
-- Change the location if you want the dataset in another BigQuery region.

CREATE SCHEMA IF NOT EXISTS `YOUR_PROJECT_ID.edraak_finance`
OPTIONS (
  location = 'us-central1'
);

CREATE SCHEMA IF NOT EXISTS `YOUR_PROJECT_ID.bank_cores`
OPTIONS (
  location = 'us-central1'
);
