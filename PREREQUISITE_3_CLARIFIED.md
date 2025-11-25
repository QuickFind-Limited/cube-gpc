# Prerequisite 3 Clarified: Post-Processing Options

**Question:** Which post-processing script to run?

**Answer:** You have **TWO OPTIONS** - choose based on your preference.

---

## Current Situation

**You already have:**
- ✅ `transaction_lines_AUDIT_combined_20251124_225608_STREAMING.csv` (8.6M records, 622MB)
- ✅ `transactions_AUDIT_combined_20251124_225608_STREAMING.csv` (1.4M records, 401MB)
- ✅ All AUDIT fields present in both files

**What you need:**
- Filtered data with AUDIT filters applied
- Data in format BigQuery can use (CSV or Parquet)

---

## OPTION A: Direct CSV Upload (FASTEST - Recommended)

**Skip post-processing entirely** - just upload CSV and filter in BigQuery!

### Step-by-Step

**Step 1: Upload CSV to GCS (20 minutes)**
```bash
cd /data/netsuite_extractions

# Upload transaction lines CSV
gsutil cp transaction_lines_AUDIT_combined_20251124_225608_STREAMING.csv \
  gs://gym-plus-coffee-bucket-dev/parquet/audit/transaction_lines_raw.csv

# Upload transactions CSV
gsutil cp transactions_AUDIT_combined_20251124_225608_STREAMING.csv \
  gs://gym-plus-coffee-bucket-dev/parquet/audit/transactions_raw.csv
```

**Step 2: Load to BigQuery (10 minutes)**
```bash
# Load transaction lines
bq load --source_format=CSV \
  --skip_leading_rows=1 \
  --autodetect \
  --replace \
  gym-plus-coffee:analytics.transaction_lines_raw \
  gs://gym-plus-coffee-bucket-dev/parquet/audit/transaction_lines_raw.csv

# Load transactions
bq load --source_format=CSV \
  --skip_leading_rows=1 \
  --autodetect \
  --replace \
  gym-plus-coffee:analytics.transactions_raw \
  gs://gym-plus-coffee-bucket-dev/parquet/audit/transactions_raw.csv
```

**Step 3: Create Filtered Views (5 minutes)**
```sql
-- Create filtered transaction_lines view
CREATE OR REPLACE VIEW `gym-plus-coffee.analytics.transaction_lines_clean` AS
SELECT * FROM `gym-plus-coffee.analytics.transaction_lines_raw`
WHERE mainline = 'F'
  AND COALESCE(taxline, 'F') = 'F'
  AND COALESCE(iscogs, 'F') = 'F'
  AND COALESCE(transactiondiscount, 'F') = 'F';

-- Create filtered transactions view
CREATE OR REPLACE VIEW `gym-plus-coffee.analytics.transactions_clean` AS
SELECT * FROM `gym-plus-coffee.analytics.transactions_raw`
WHERE COALESCE(posting, 'F') = 'T'
  AND COALESCE(voided, 'F') = 'F'
  AND type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd');

-- Test the views
SELECT COUNT(*) as raw_count FROM `gym-plus-coffee.analytics.transaction_lines_raw`;
SELECT COUNT(*) as clean_count FROM `gym-plus-coffee.analytics.transaction_lines_clean`;
-- Clean should be ~40% less than raw
```

**Total Time: 35 minutes**

**Pros:**
- ✅ Fastest approach
- ✅ No Python script needed
- ✅ Filtering in SQL (easy to adjust)
- ✅ Views are free (no storage duplication)

**Cons:**
- ⚠️ Queries always filter at runtime (slight performance hit)
- ⚠️ Can't use external tables (but that's fine)

---

## OPTION B: Convert to Parquet with Filtering (BEST PERFORMANCE)

**Create filtered Parquet files** - best query performance but more setup.

### Step-by-Step

**Step 1: Create Python Script (5 minutes)**

Save this as `/data/netsuite_extractions/filter_csv_to_parquet.py`:

```python
#!/usr/bin/env python3
"""
Convert CSV files to filtered Parquet files
Reads from CSV, applies AUDIT filters, writes clean Parquet
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def filter_transaction_lines(input_csv, output_parquet):
    """Filter transaction lines to product sales only"""
    print(f"\n🔍 Processing {input_csv}...")

    # Read CSV
    df = pd.read_csv(input_csv)
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

    # Write to parquet
    table = pa.Table.from_pandas(df_clean)
    pq.write_table(table, output_parquet, compression='snappy')
    print(f"✅ Saved to {output_parquet}")

    return len(df), len(df_clean)

def filter_transactions(input_csv, output_parquet):
    """Filter transactions to financial transactions only"""
    print(f"\n🔍 Processing {input_csv}...")

    # Read CSV
    df = pd.read_csv(input_csv)
    print(f"   Raw records: {len(df):,}")

    # Handle missing values for AUDIT fields
    df['posting'] = df['posting'].fillna('F')
    df['voided'] = df['voided'].fillna('F')

    # Filter to posted, non-voided financial transactions
    df_clean = df[
        (df['posting'] == 'T') &           # Only posted transactions
        (df['voided'] == 'F') &            # Exclude voided
        (df['type'].isin(['CustInvc', 'CashSale', 'CustCred', 'CashRfnd']))
    ].copy()

    print(f"   Clean records: {len(df_clean):,}")
    print(f"   Filtered out: {len(df) - len(df_clean):,} ({(1 - len(df_clean)/len(df)) * 100:.1f}%)")

    # Write to parquet
    table = pa.Table.from_pandas(df_clean)
    pq.write_table(table, output_parquet, compression='snappy')
    print(f"✅ Saved to {output_parquet}")

    return len(df), len(df_clean)

def main():
    """Main processing function"""
    print("="*80)
    print("POST-PROCESSING: CSV → Filtered Parquet")
    print("="*80)

    # Process transaction lines
    print("\n" + "="*80)
    print("PROCESSING TRANSACTION LINES")
    print("="*80)

    lines_raw, lines_clean = filter_transaction_lines(
        'transaction_lines_AUDIT_combined_20251124_225608_STREAMING.csv',
        'transaction_lines_clean.parquet'
    )

    # Process transactions
    print("\n" + "="*80)
    print("PROCESSING TRANSACTIONS")
    print("="*80)

    trans_raw, trans_clean = filter_transactions(
        'transactions_AUDIT_combined_20251124_225608_STREAMING.csv',
        'transactions_clean.parquet'
    )

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nTransaction Lines: {lines_raw:,} → {lines_clean:,} ({(1-lines_clean/lines_raw)*100:.1f}% filtered)")
    print(f"Transactions:      {trans_raw:,} → {trans_clean:,} ({(1-trans_clean/trans_raw)*100:.1f}% filtered)")
    print("\n✅ Clean parquet files created")
    print("   Next: Upload to GCS with 'gsutil cp *.parquet gs://...'")

if __name__ == '__main__':
    main()
```

**Step 2: Run Script (15 minutes)**
```bash
cd /data/netsuite_extractions

# Install dependencies if needed
pip install pandas pyarrow

# Run filtering
python3 filter_csv_to_parquet.py
```

**Step 3: Upload Parquet to GCS (10 minutes)**
```bash
# Upload clean parquet files
gsutil cp transaction_lines_clean.parquet \
  gs://gym-plus-coffee-bucket-dev/parquet/clean/transaction_lines_clean.parquet

gsutil cp transactions_clean.parquet \
  gs://gym-plus-coffee-bucket-dev/parquet/clean/transactions_clean.parquet
```

**Step 4: Create External Tables (5 minutes)**
```sql
-- Create external table on clean parquet
CREATE OR REPLACE EXTERNAL TABLE `gym-plus-coffee.analytics.transaction_lines_clean`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://gym-plus-coffee-bucket-dev/parquet/clean/transaction_lines_clean.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `gym-plus-coffee.analytics.transactions_clean`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://gym-plus-coffee-bucket-dev/parquet/clean/transactions_clean.parquet']
);

-- Test
SELECT COUNT(*) FROM `gym-plus-coffee.analytics.transaction_lines_clean`;
SELECT COUNT(*) FROM `gym-plus-coffee.analytics.transactions_clean`;
```

**Total Time: 45 minutes**

**Pros:**
- ✅ Best query performance (no runtime filtering)
- ✅ Smaller data size (parquet compression)
- ✅ External tables (no storage cost in BigQuery)
- ✅ Data pre-filtered (queries simpler)

**Cons:**
- ⚠️ Requires Python script creation
- ⚠️ Takes longer to set up
- ⚠️ Filtering logic in Python (harder to adjust)

---

## OPTION C: Hybrid Approach (RECOMMENDED)

**Best of both worlds** - start with Option A, migrate to Option B later if needed.

### Phase 1: Start with CSV (Day 1)
```bash
# Quick start - 35 minutes
1. Upload CSV to GCS
2. Load to BigQuery
3. Create filtered views
4. Begin migration
```

### Phase 2: Optimize with Parquet (Later, if needed)
```bash
# If query performance needs improvement
1. Run Python filtering script
2. Upload parquet files
3. Switch external tables to parquet
4. Update cube.py (minimal change)
```

**Pros:**
- ✅ Fastest time to start migration
- ✅ Easy rollback (just views)
- ✅ Can optimize later without blocking
- ✅ Learn what performance is really needed

**Cons:**
- None! Best approach for getting started.

---

## Recommendation: **OPTION A or C**

### Use Option A (Direct CSV Upload) if:
- ✅ Want to start migration immediately
- ✅ Don't want to write Python scripts
- ✅ Views with runtime filtering acceptable
- ✅ Can always optimize later

### Use Option B (Parquet) if:
- ✅ Have time for proper setup
- ✅ Want maximum performance from day 1
- ✅ Comfortable with Python scripts
- ✅ Want external tables

### Use Option C (Hybrid) if:
- ✅ **Want to move fast but keep options open** ← **BEST CHOICE**

---

## Updated Prerequisites Checklist

**Before Migration:**

- [ ] **PREREQUISITE 1:** Create BigQuery dataset (5 min)
- [ ] **PREREQUISITE 2:** Upload AUDIT CSV to GCS (20 min)
- [ ] **PREREQUISITE 3:** Choose approach:
  - [ ] **OPTION A:** Load CSV + Create Views (35 min total)
  - [ ] **OPTION B:** Filter to Parquet + External Tables (45 min total)
  - [ ] **OPTION C:** Start with A, do B later (35 min now)
- [ ] **PREREQUISITE 4:** Test queries on BigQuery
- [ ] **PREREQUISITE 5:** Verify service account permissions

**Total Time:**
- Option A/C: **1 hour**
- Option B: **1 hour 10 min**

---

## Quick Decision Matrix

| Factor | Option A (CSV+Views) | Option B (Parquet) | Option C (Hybrid) |
|--------|---------------------|-------------------|------------------|
| Setup time | 35 min | 45 min | 35 min |
| Query performance | Good (runtime filter) | Best (pre-filtered) | Good→Best |
| Maintenance | Easy (SQL views) | Medium (Python) | Easy |
| Storage cost | Higher (CSV+Views) | Lower (Parquet) | Higher→Lower |
| Flexibility | High | Medium | Highest |
| **RECOMMENDED?** | ✅ Yes | ✅ Yes | ✅✅ **BEST** |

---

## Summary

**Prerequisite 3 is NOT about running a specific script.**

**It's about getting filtered data into BigQuery:**

1. **Option A:** Upload CSV → Load to BQ → Create filtered views (35 min)
2. **Option B:** Run Python script → Upload Parquet → Create external tables (45 min)
3. **Option C:** Start with A, migrate to B later (35 min + optional optimization)

**RECOMMENDED:** **Option C (Hybrid Approach)**
- Start with CSV+Views to unblock migration
- Optimize to Parquet later if needed
- Total setup: 35 minutes
- Can optimize later: 30 minutes
