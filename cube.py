# Configuration options: https://cube.dev/docs/product/configuration

from cube import config
import os
import json

@config('driver_factory')
def driver_factory(ctx: dict) -> dict:
    # Get GCS credentials from environment variable
    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON', '{}')
    creds = json.loads(creds_json) if creds_json else {}

    # GCS bucket with Parquet files
    bucket = 'gs://gym-plus-coffee-bucket-dev/parquet'

    # Extract credentials
    client_email = creds.get("client_email", "")
    private_key = creds.get("private_key", "").replace("\n", "\\n")

    # Init SQL to create tables from Parquet files on GCS
    init_sql = f"""
        -- Install and load GCS extension
        INSTALL httpfs;
        LOAD httpfs;

        -- Set GCS credentials
        SET s3_endpoint='storage.googleapis.com';
        SET s3_url_style='path';

        -- Create secret for GCS access
        CREATE SECRET gcs_secret (
            TYPE GCS,
            KEY_ID '{client_email}',
            SECRET '{private_key}'
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
