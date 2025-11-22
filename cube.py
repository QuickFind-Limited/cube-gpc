# Configuration options: https://cube.dev/docs/product/configuration

from cube import config
import os

@config('driver_factory')
def driver_factory(ctx: dict) -> dict:
    # Get GCS HMAC credentials from environment variables
    gcs_key_id = os.environ.get('GCS_KEY_ID', '')
    gcs_secret = os.environ.get('GCS_SECRET', '')

    # GCS bucket with Parquet files
    bucket = 'gs://gym-plus-coffee-bucket-dev/parquet'

    # Init SQL to create tables from Parquet files on GCS
    init_sql = f"""
        -- Install and load GCS extension
        INSTALL httpfs;
        LOAD httpfs;

        -- Create secret for GCS access using HMAC keys
        CREATE SECRET gcs_secret (
            TYPE GCS,
            KEY_ID '{gcs_key_id}',
            SECRET '{gcs_secret}'
        );

        -- Create tables from Parquet files
        CREATE TABLE IF NOT EXISTS transactions AS
        SELECT * FROM read_parquet('{bucket}/transactions.parquet');

        CREATE TABLE IF NOT EXISTS transaction_lines AS
        SELECT * FROM read_parquet('{bucket}/transaction_lines.parquet');

        CREATE TABLE IF NOT EXISTS items AS
        SELECT * FROM read_parquet('{bucket}/items.parquet');

        CREATE TABLE IF NOT EXISTS locations AS
        SELECT * FROM read_parquet('{bucket}/locations.parquet');

        CREATE TABLE IF NOT EXISTS inventory_calculated AS
        SELECT * FROM read_parquet('{bucket}/inventory_calculated.parquet');

        CREATE TABLE IF NOT EXISTS fulfillments AS
        SELECT * FROM read_parquet('{bucket}/fulfillments.parquet');

        CREATE TABLE IF NOT EXISTS fulfillment_lines AS
        SELECT * FROM read_parquet('{bucket}/fulfillment_lines.parquet');

        CREATE TABLE IF NOT EXISTS currencies AS
        SELECT * FROM read_parquet('{bucket}/currencies.parquet');

        CREATE TABLE IF NOT EXISTS subsidiaries AS
        SELECT * FROM read_parquet('{bucket}/subsidiaries.parquet');

        CREATE TABLE IF NOT EXISTS departments AS
        SELECT * FROM read_parquet('{bucket}/departments.parquet');

        CREATE TABLE IF NOT EXISTS classifications AS
        SELECT * FROM read_parquet('{bucket}/classifications.parquet');

        CREATE TABLE IF NOT EXISTS b2b_customers AS
        SELECT * FROM read_parquet('{bucket}/b2b_customers.parquet');
    """

    return {
        'type': 'duckdb',
        'initSql': init_sql,
    }
