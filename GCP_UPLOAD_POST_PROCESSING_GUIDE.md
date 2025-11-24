# GCP Upload & Post-Processing Guide

**Purpose**: Complete guide for uploading AUDIT extractions to GCP and preparing them for Cube/BigQuery

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Upload AUDIT Files to GCS](#upload-audit-files-to-gcs)
3. [Post-Processing: Create Filtered Parquets](#post-processing-create-filtered-parquets)
4. [Load to BigQuery](#load-to-bigquery)
5. [Update Cube Configuration](#update-cube-configuration)
6. [Validation & Testing](#validation--testing)

---

## Prerequisites

### Required Tools

```bash
# Google Cloud SDK
gcloud --version  # Should be installed

# Python packages
pip install pandas pyarrow google-cloud-storage google-cloud-bigquery
```

### Required Permissions

```bash
# Service account needs:
- storage.objects.create (GCS write)
- storage.objects.get (GCS read)
- bigquery.tables.create (BigQuery table creation)
- bigquery.jobs.create (BigQuery query execution)
```

### Environment Setup

```bash
# Set GCP project
export GCP_PROJECT="gym-plus-coffee"
export GCS_BUCKET="gym-plus-coffee-bucket-dev"
export BQ_DATASET="analytics"

# Authenticate
gcloud auth login
gcloud config set project $GCP_PROJECT
```

---

## Upload AUDIT Files to GCS

### Step 1: Upload Raw AUDIT Files

**Upload Transaction Lines (6 files after completion):**
```bash
cd /data/netsuite_extractions

# Upload completed AUDIT files
gsutil -m cp lines_CashRfnd_AUDIT_MONTHLY_*_FINAL.json \
  gs://$GCS_BUCKET/parquet/audit/lines/

gsutil -m cp lines_CashSale_AUDIT_MONTHLY_*_FINAL.json \
  gs://$GCS_BUCKET/parquet/audit/lines/

gsutil -m cp lines_CustCred_AUDIT_MONTHLY_*_FINAL.json \
  gs://$GCS_BUCKET/parquet/audit/lines/

gsutil -m cp lines_CustInvc_AUDIT_MONTHLY_*_FINAL.json \
  gs://$GCS_BUCKET/parquet/audit/lines/

gsutil -m cp lines_RtnAuth_AUDIT_MONTHLY_*_FINAL.json \
  gs://$GCS_BUCKET/parquet/audit/lines/

gsutil -m cp lines_SalesOrd_AUDIT_MONTHLY_*_FINAL.json \
  gs://$GCS_BUCKET/parquet/audit/lines/
```

**Upload Transactions (6 files):**
```bash
gsutil -m cp transactions_*_AUDIT_*_FINAL.json \
  gs://$GCS_BUCKET/parquet/audit/transactions/
```

**Expected Upload Time**: 10-20 minutes (3-4GB total)

**Verify Upload:**
```bash
gsutil ls -lh gs://$GCS_BUCKET/parquet/audit/lines/
gsutil ls -lh gs://$GCS_BUCKET/parquet/audit/transactions/
```

---

## Post-Processing: Create Filtered Parquets

### Step 2: Create Filtering Script

**Save as `filter_audit_data.py`:**

```python
#!/usr/bin/env python3
"""
Post-processing script to create filtered "clean" parquet files
Removes system-generated lines for accurate business metrics
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage
import os

# Configuration
GCS_BUCKET = "gym-plus-coffee-bucket-dev"
INPUT_PREFIX = "parquet/audit/"
OUTPUT_PREFIX = "parquet/clean/"

def download_from_gcs(bucket_name, source_blob, local_file):
    """Download file from GCS"""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob)
    blob.download_to_filename(local_file)
    print(f"✅ Downloaded {source_blob}")

def upload_to_gcs(bucket_name, local_file, dest_blob):
    """Upload file to GCS"""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_blob)
    blob.upload_from_filename(local_file)
    print(f"✅ Uploaded to {dest_blob}")

def filter_transaction_lines(input_json, output_parquet):
    """
    Filter transaction lines to product sales only
    Removes: tax lines, COGS lines, discount lines, header lines
    """
    print(f"\n🔍 Processing {input_json}...")

    # Read JSON
    df = pd.read_json(input_json)
    print(f"   Raw records: {len(df):,}")

    # Filter to product lines only
    df_clean = df[
        (df['mainline'] == 'F') &          # Exclude header lines
        (df['taxline'] == 'F') &           # Exclude tax lines
        (df['iscogs'] == 'F') &            # Exclude COGS lines
        (df['transactiondiscount'] == 'F') # Exclude discount lines
    ].copy()

    print(f"   Clean records: {len(df_clean):,}")
    print(f"   Filtered out: {len(df) - len(df_clean):,} ({(1 - len(df_clean)/len(df)) * 100:.1f}%)")

    # Validate filtering
    print(f"   Validation:")
    print(f"     Headers (mainline='T'): {(df['mainline'] == 'T').sum():,}")
    print(f"     Tax lines (taxline='T'): {(df['taxline'] == 'T').sum():,}")
    print(f"     COGS lines (iscogs='T'): {(df['iscogs'] == 'T').sum():,}")
    print(f"     Discount lines (transactiondiscount='T'): {(df['transactiondiscount'] == 'T').sum():,}")

    # Write to parquet
    table = pa.Table.from_pandas(df_clean)
    pq.write_table(table, output_parquet, compression='snappy')
    print(f"✅ Saved to {output_parquet} ({len(df_clean):,} records)")

    return len(df), len(df_clean)

def filter_transactions(input_json, output_parquet):
    """
    Filter transactions to financial transactions only
    Removes: non-posting (SalesOrd), voided transactions
    """
    print(f"\n🔍 Processing {input_json}...")

    # Read JSON
    df = pd.read_json(input_json)
    print(f"   Raw records: {len(df):,}")

    # Filter to posted, non-voided financial transactions
    df_clean = df[
        (df['posting'] == 'T') &           # Only posted transactions
        (df['voided'] == 'F') &            # Exclude voided
        (df['type'].isin(['CustInvc', 'CashSale', 'CustCred', 'CashRfnd']))  # Financial types
    ].copy()

    print(f"   Clean records: {len(df_clean):,}")
    print(f"   Filtered out: {len(df) - len(df_clean):,} ({(1 - len(df_clean)/len(df)) * 100:.1f}%)")

    # Validate filtering
    print(f"   Validation:")
    print(f"     Non-posting (posting='F'): {(df['posting'] == 'F').sum():,}")
    print(f"     Voided (voided='T'): {(df['voided'] == 'T').sum():,}")
    print(f"     Non-financial types: {(~df['type'].isin(['CustInvc', 'CashSale', 'CustCred', 'CashRfnd'])).sum():,}")

    # Write to parquet
    table = pa.Table.from_pandas(df_clean)
    pq.write_table(table, output_parquet, compression='snappy')
    print(f"✅ Saved to {output_parquet} ({len(df_clean):,} records)")

    return len(df), len(df_clean)

def main():
    """Main processing function"""
    print("="*80)
    print("POST-PROCESSING: Creating Clean Parquet Files")
    print("="*80)

    # Process transaction lines (6 files)
    lines_types = ['CashRfnd', 'CashSale', 'CustCred', 'CustInvc', 'RtnAuth', 'SalesOrd']
    lines_stats = []

    print("\n" + "="*80)
    print("PROCESSING TRANSACTION LINES")
    print("="*80)

    for line_type in lines_types:
        # Find the file in GCS
        source_blob = f"{INPUT_PREFIX}lines/lines_{line_type}_AUDIT_MONTHLY_*_FINAL.json"
        local_input = f"/tmp/lines_{line_type}_AUDIT.json"
        local_output = f"/tmp/lines_{line_type}_CLEAN.parquet"
        dest_blob = f"{OUTPUT_PREFIX}transaction_lines_{line_type.lower()}_clean.parquet"

        # Download from GCS (you'll need to list and get exact filename)
        # For now, assuming files are already local
        input_file = f"/data/netsuite_extractions/lines_{line_type}_AUDIT_MONTHLY_*_FINAL.json"

        # Filter
        raw_count, clean_count = filter_transaction_lines(input_file, local_output)
        lines_stats.append({
            'type': line_type,
            'raw': raw_count,
            'clean': clean_count,
            'filtered_pct': (1 - clean_count/raw_count) * 100
        })

        # Upload to GCS
        upload_to_gcs(GCS_BUCKET, local_output, dest_blob)

    # Process transactions (6 files)
    trans_types = ['CashRfnd', 'CashSale', 'CustCred', 'CustInvc', 'RtnAuth', 'SalesOrd']
    trans_stats = []

    print("\n" + "="*80)
    print("PROCESSING TRANSACTIONS")
    print("="*80)

    for trans_type in trans_types:
        input_file = f"/data/netsuite_extractions/transactions_{trans_type}_AUDIT_*_FINAL.json"
        local_output = f"/tmp/transactions_{trans_type}_CLEAN.parquet"
        dest_blob = f"{OUTPUT_PREFIX}transactions_{trans_type.lower()}_clean.parquet"

        # Filter
        raw_count, clean_count = filter_transactions(input_file, local_output)
        trans_stats.append({
            'type': trans_type,
            'raw': raw_count,
            'clean': clean_count,
            'filtered_pct': (1 - clean_count/raw_count) * 100
        })

        # Upload to GCS
        upload_to_gcs(GCS_BUCKET, local_output, dest_blob)

    # Print summary
    print("\n" + "="*80)
    print("PROCESSING COMPLETE - SUMMARY")
    print("="*80)

    print("\nTransaction Lines:")
    for stat in lines_stats:
        print(f"  {stat['type']:12} {stat['raw']:>10,} → {stat['clean']:>10,} ({stat['filtered_pct']:>5.1f}% filtered)")

    print("\nTransactions:")
    for stat in trans_stats:
        print(f"  {stat['type']:12} {stat['raw']:>10,} → {stat['clean']:>10,} ({stat['filtered_pct']:>5.1f}% filtered)")

    total_lines_raw = sum(s['raw'] for s in lines_stats)
    total_lines_clean = sum(s['clean'] for s in lines_stats)
    total_trans_raw = sum(s['raw'] for s in trans_stats)
    total_trans_clean = sum(s['clean'] for s in trans_stats)

    print(f"\nTOTAL LINES:        {total_lines_raw:>10,} → {total_lines_clean:>10,}")
    print(f"TOTAL TRANSACTIONS: {total_trans_raw:>10,} → {total_trans_clean:>10,}")
    print("\n✅ All clean parquet files uploaded to GCS")
    print(f"   Location: gs://{GCS_BUCKET}/{OUTPUT_PREFIX}")

if __name__ == '__main__':
    main()
```

**Run the script:**
```bash
python3 filter_audit_data.py
```

**Expected Results:**
- Transaction Lines: ~30-40% filtered out
- Transactions: ~5-10% filtered out (mostly SalesOrd)

---

## Load to BigQuery

### Step 3: Create BigQuery External Tables

**Option A: External Tables (Faster Setup)**

```sql
-- Create dataset
CREATE SCHEMA IF NOT EXISTS `gym-plus-coffee.analytics`;

-- Transaction Lines (Clean)
CREATE OR REPLACE EXTERNAL TABLE `gym-plus-coffee.analytics.transaction_lines_clean`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://gym-plus-coffee-bucket-dev/parquet/clean/transaction_lines_*_clean.parquet']
);

-- Transactions (Clean)
CREATE OR REPLACE EXTERNAL TABLE `gym-plus-coffee.analytics.transactions_clean`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://gym-plus-coffee-bucket-dev/parquet/clean/transactions_*_clean.parquet']
);

-- Verify tables
SELECT COUNT(*) as transaction_lines_count
FROM `gym-plus-coffee.analytics.transaction_lines_clean`;

SELECT COUNT(*) as transactions_count
FROM `gym-plus-coffee.analytics.transactions_clean`;
```

**Option B: Native Tables (Better Performance)**

```bash
# Load transaction lines
bq load --source_format=PARQUET \
  --replace \
  gym-plus-coffee:analytics.transaction_lines_clean \
  gs://gym-plus-coffee-bucket-dev/parquet/clean/transaction_lines_*_clean.parquet

# Load transactions
bq load --source_format=PARQUET \
  --replace \
  gym-plus-coffee:analytics.transactions_clean \
  gs://gym-plus-coffee-bucket-dev/parquet/clean/transactions_*_clean.parquet
```

**Expected Load Time**: 5-15 minutes

---

## Update Cube Configuration

### Step 4: Update cube.py

**Edit `/path/to/cube/repo/cube.py`:**

```python
from cube import config
import os

@config('driver_factory')
def driver_factory(ctx: dict) -> dict:
    return {
        'type': 'bigquery',
        'projectId': os.environ.get('BIGQUERY_PROJECT_ID', 'gym-plus-coffee'),
        'credentials': os.environ.get('BIGQUERY_CREDENTIALS'),
        'location': 'US',
        'datasetName': 'analytics',
    }
```

### Step 5: Update Cube YML Files

**Update transaction_lines.yml** to use clean table:

```yaml
cubes:
  - name: transaction_lines
    sql_table: transaction_lines_clean  # CHANGED: Was transaction_lines

    dimensions:
      # ... existing dimensions ...
      # REMOVE: mainline, taxline, iscogs, transactiondiscount
      # (already filtered in clean table)

    measures:
      - name: transaction_count
        sql: "{CUBE}.transaction"
        type: count_distinct_approx  # CHANGED: Was count_distinct
        # REMOVE: filters (already applied in clean table)

      - name: sku_count
        sql: "{CUBE}.item"
        type: count_distinct_approx  # CHANGED: Was count_distinct
        # REMOVE: filters (already applied in clean table)

      - name: units_sold
        sql: "SUM({CUBE}.quantity)"
        type: number
        # REMOVE: filters (already applied in clean table)

      # ... other measures need DATE_DIFF syntax updates per migration plan
```

**Update transactions.yml** to use clean table:

```yaml
cubes:
  - name: transactions
    sql_table: transactions_clean  # CHANGED: Was transactions

    dimensions:
      # ... existing dimensions ...
      # REMOVE: posting, voided, postingperiod
      # (already filtered in clean table)

    measures:
      - name: order_count
        sql: "{CUBE}.id"
        type: count_distinct_approx  # CHANGED: Was count_distinct
        # REMOVE: filters (already applied in clean table)
```

**See `BIGQUERY_MIGRATION_PLAN-v2.md` Phase 9 for complete YML updates**

---

## Validation & Testing

### Step 6: Validate Data Quality

**Test 1: Record Counts**
```sql
-- Should match filtered counts from post-processing
SELECT
  'transaction_lines' as table_name,
  COUNT(*) as record_count
FROM `gym-plus-coffee.analytics.transaction_lines_clean`
UNION ALL
SELECT
  'transactions' as table_name,
  COUNT(*) as record_count
FROM `gym-plus-coffee.analytics.transactions_clean`;
```

**Test 2: Revenue Totals (Should Match Pre-Migration)**
```sql
-- Compare with previous revenue totals
SELECT
  SUM(amount) as total_revenue,
  COUNT(DISTINCT transaction) as transaction_count,
  COUNT(DISTINCT item) as sku_count
FROM `gym-plus-coffee.analytics.transaction_lines_clean`;
```

**Test 3: Line Type Validation (Should Be Zero)**
```sql
-- Verify no system lines in clean table
SELECT
  SUM(CASE WHEN mainline = 'T' THEN 1 ELSE 0 END) as header_lines,
  SUM(CASE WHEN taxline = 'T' THEN 1 ELSE 0 END) as tax_lines,
  SUM(CASE WHEN iscogs = 'T' THEN 1 ELSE 0 END) as cogs_lines
FROM `gym-plus-coffee.analytics.transaction_lines_clean`;
-- All should be 0 (or NULL if columns removed)
```

**Test 4: Cube API Tests**
```bash
# Test critical metrics
curl -X POST https://your-cube-api.com/cubejs-api/v1/load \
  -H "Authorization: Bearer $CUBE_API_TOKEN" \
  -d '{
    "measures": ["transaction_lines.total_revenue", "transaction_lines.transaction_count"],
    "timeDimensions": [{
      "dimension": "transaction_lines.transaction_date",
      "dateRange": "Last 12 months"
    }]
  }'
```

---

## Expected Results Summary

### Before (Raw Data with System Lines)

| Metric | Raw Value | Issues |
|--------|-----------|--------|
| Transaction Count | 10,000 | +10-20% inflated (tax + COGS lines) |
| SKU Count | 1,500 | +40-50% inflated (COGS items counted) |
| Units Sold | 50,000 | +40-50% inflated (COGS lines) |
| Revenue | €1,000,000 | ✅ Accurate (dollar amounts correct) |

### After (Clean Data - System Lines Filtered)

| Metric | Clean Value | Improvement |
|--------|-------------|-------------|
| Transaction Count | 8,500 | ✅ Accurate (-15% filtered) |
| SKU Count | 850 | ✅ Accurate (-43% filtered) |
| Units Sold | 28,000 | ✅ Accurate (-44% filtered) |
| Revenue | €1,000,000 | ✅ Unchanged (as expected) |

### Performance

| Query Type | Before (DuckDB) | After (BigQuery) | Improvement |
|------------|----------------|------------------|-------------|
| count_distinct | 15-62s | 2-5s | 3-31x faster |
| Simple aggregation | 1s | 0.5-2s | Similar |
| Complex joins | 15s | 3-8s | 2-5x faster |

---

## Troubleshooting

### Issue: Upload Fails
```bash
# Check GCS permissions
gsutil iam get gs://$GCS_BUCKET

# Verify authentication
gcloud auth list
```

### Issue: Post-Processing Fails
```python
# Check field existence
import pandas as pd
df = pd.read_json('lines_CustInvc_AUDIT_*_FINAL.json')
print(df.columns.tolist())
# Should include: mainline, taxline, iscogs, transactiondiscount
```

### Issue: BigQuery Load Fails
```bash
# Check parquet schema
bq show --schema --format=prettyjson \
  gym-plus-coffee:analytics.transaction_lines_clean
```

### Issue: Cube Queries Fail
```bash
# Check cube.py configuration
curl https://your-cube-api.com/cubejs-api/v1/meta

# Test BigQuery connection
bq query "SELECT COUNT(*) FROM \`gym-plus-coffee.analytics.transaction_lines_clean\`"
```

---

## Rollback Plan

If issues occur:

1. **Revert cube.py** to DuckDB configuration
2. **Revert YML files** to original versions
3. **Keep clean parquet files** in GCS for future use
4. **Document issues** for resolution

---

## Success Checklist

- [ ] All AUDIT extractions complete (12 files)
- [ ] Raw AUDIT files uploaded to GCS
- [ ] Post-processing script run successfully
- [ ] Clean parquet files created and uploaded
- [ ] BigQuery tables created (external or native)
- [ ] Record counts validated
- [ ] Revenue totals match pre-migration
- [ ] cube.py updated and deployed
- [ ] transaction_lines.yml updated
- [ ] transactions.yml updated
- [ ] All 66 metrics tested
- [ ] Performance benchmarks met (<5s for count_distinct)
- [ ] Documentation updated

---

## Timeline

| Step | Duration | Dependencies |
|------|----------|--------------|
| 1. Upload AUDIT files to GCS | 10-20 min | All extractions complete |
| 2. Run post-processing script | 15-30 min | Files uploaded |
| 3. Load to BigQuery | 5-15 min | Clean parquets created |
| 4. Update cube.py | 5 min | BigQuery tables ready |
| 5. Update YML files | 2-4 hours | See migration plan Phase 9 |
| 6. Testing & validation | 4-8 hours | All changes deployed |

**Total**: 1-2 days for complete migration

---

## Contact & Support

- Migration Plan: `BIGQUERY_MIGRATION_PLAN-v2.md`
- Extraction Summary: `AUDIT_EXTRACTIONS_SUMMARY.md`
- Cube Updates: See Phase 9 of migration plan
