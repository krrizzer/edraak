# Edraak BigQuery SQL

This folder contains simple BigQuery Standard SQL scripts for manually setting up the Edraak prototype data model.

Use these files for manual BigQuery setup, testing, and quick demos without running Terraform.

## Tables

Source banking tables:

- `customers`
- `transactions`
- `loans`

Derived analytical table:

- `user_profiles`

App workflow tables:

- `decision_requests`
- `recommendations`

`user_profiles` is not an original bank table. It represents the generated customer profile built from customers, transactions, and loans.

## How To Use

Open each SQL file in the BigQuery console, replace `YOUR_PROJECT_ID` with your real Google Cloud project ID, then run:

1. `01_create_dataset.sql`
2. `02_create_tables.sql`
3. `03_insert_sample_data.sql`
4. `04_example_queries.sql`

The default dataset name is `edraak_finance`. 
