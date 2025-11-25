# Configuration options: https://cube.dev/docs/product/configuration
#
# For Cube Cloud deployments, database configuration is managed via environment variables:
# - CUBEJS_DB_TYPE=bigquery
# - CUBEJS_DB_BQ_PROJECT_ID=gym-plus-coffee
# - CUBEJS_DB_BQ_CREDENTIALS=<service-account-json>
# - CUBEJS_DB_BQ_LOCATION=US (optional)
#
# The custom driver_factory below is commented out for Cube Cloud deployments.
# Uncomment it only for local development with DuckDB.

from cube import config
import os

# COMMENTED OUT FOR CUBE CLOUD - Use environment variables instead
# Uncomment for local DuckDB development only
#
# @config('driver_factory')
# def driver_factory(ctx: dict) -> dict:
#     # Get GCS HMAC credentials from environment variables
#     gcs_key_id = os.environ.get('GCS_KEY_ID', '')
#     gcs_secret = os.environ.get('GCS_SECRET', '')
#
#     # GCS bucket with Parquet files
#     bucket = 'gs://gym-plus-coffee-bucket-dev/parquet'
#
#     # Init SQL to create tables from Parquet files on GCS
#     init_sql = f"""
#         -- Install and load GCS extension
#         INSTALL httpfs;
#         LOAD httpfs;
#
#         -- Create secret for GCS access using HMAC keys
#         CREATE SECRET gcs_secret (
#             TYPE GCS,
#             KEY_ID '{gcs_key_id}',
#             SECRET '{gcs_secret}'
#         );
#
#         -- Create tables from Parquet files
#         CREATE TABLE IF NOT EXISTS transactions AS
#         SELECT * FROM read_parquet('{bucket}/transactions.parquet');
#
#         CREATE TABLE IF NOT EXISTS transaction_lines AS
#         SELECT * FROM read_parquet('{bucket}/transaction_lines.parquet');
#
#         CREATE TABLE IF NOT EXISTS items AS
#         SELECT * FROM read_parquet('{bucket}/items.parquet');
#
#         CREATE TABLE IF NOT EXISTS locations AS
#         SELECT * FROM read_parquet('{bucket}/locations.parquet');
#
#         CREATE TABLE IF NOT EXISTS inventory_calculated AS
#         SELECT * FROM read_parquet('{bucket}/inventory_calculated.parquet');
#
#         CREATE TABLE IF NOT EXISTS fulfillments AS
#         SELECT * FROM read_parquet('{bucket}/fulfillments.parquet');
#
#         CREATE TABLE IF NOT EXISTS fulfillment_lines AS
#         SELECT * FROM read_parquet('{bucket}/fulfillment_lines.parquet');
#
#         CREATE TABLE IF NOT EXISTS currencies AS
#         SELECT * FROM read_parquet('{bucket}/currencies.parquet');
#
#         CREATE TABLE IF NOT EXISTS subsidiaries AS
#         SELECT * FROM read_parquet('{bucket}/subsidiaries.parquet');
#
#         CREATE TABLE IF NOT EXISTS departments AS
#         SELECT * FROM read_parquet('{bucket}/departments.parquet');
#
#         CREATE TABLE IF NOT EXISTS classifications AS
#         SELECT * FROM read_parquet('{bucket}/classifications.parquet');
#
#         CREATE TABLE IF NOT EXISTS b2b_customers AS
#         SELECT * FROM read_parquet('{bucket}/b2b_customers.parquet');
#
#         CREATE TABLE IF NOT EXISTS b2b_addresses AS
#         SELECT * FROM read_parquet('{bucket}/b2b_addresses.parquet');
#
#         CREATE TABLE IF NOT EXISTS b2b_customer_addresses AS
#         SELECT * FROM read_parquet('{bucket}/b2b_customer_addresses.parquet');
#
#         -- Create filtered views with AUDIT filters applied
#         CREATE VIEW IF NOT EXISTS transaction_lines_clean AS
#         SELECT * FROM transaction_lines
#         WHERE mainline = 'F'
#           AND COALESCE(taxline, 'F') = 'F'
#           AND COALESCE(iscogs, 'F') = 'F'
#           AND COALESCE(transactiondiscount, 'F') = 'F';
#
#         CREATE VIEW IF NOT EXISTS transactions_clean AS
#         SELECT * FROM transactions
#         WHERE COALESCE(posting, 'F') = 'T'
#           AND COALESCE(voided, 'F') = 'F'
#           AND type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd');
#     """
#
#     # DuckDB configuration (for local development with GCS parquet)
#     duckdb_config = {
#         'type': 'duckdb',
#         'initSql': init_sql,
#     }
#
#     return duckdb_config
