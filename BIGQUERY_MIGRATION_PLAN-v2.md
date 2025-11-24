# BigQuery Migration Plan

## Overview

Migrate Cube.dev semantic layer from DuckDB + GCS Parquet to BigQuery for improved query performance, particularly for `count_distinct` operations.

**Expected Performance Improvement**: count_distinct queries from 15-62s → 2-5s

---

## Phase 1: BigQuery Infrastructure Setup

### 1.1 Create BigQuery Dataset
```bash
bq mk --dataset \
  --location=US \
  --description="Gym+Coffee analytics data" \
  gym_plus_coffee:analytics
```

### 1.2 Load Parquet Files as External Tables
```sql
-- Example for transactions table
CREATE OR REPLACE EXTERNAL TABLE `gym_plus_coffee.analytics.transactions`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://gym-plus-coffee-bucket-dev/parquet/transactions.parquet']
);
```

### 1.3 Tables to Create (14 total)
- transactions
- transaction_lines
- items
- inventory
- locations
- b2c_customers
- fulfillments
- fulfillment_lines
- inbound_shipments
- inbound_shipment_lines
- purchase_orders
- purchase_order_lines
- vendors
- subsidiaries

---

## Phase 2: Cube Configuration Changes

### 2.1 Update cube.py

**Current (DuckDB):**
```python
from cube import config
import os

@config('driver_factory')
def driver_factory(ctx: dict) -> dict:
    gcs_key_id = os.environ.get('GCS_KEY_ID', '')
    gcs_secret = os.environ.get('GCS_SECRET', '')
    bucket = 'gs://gym-plus-coffee-bucket-dev/parquet'

    init_sql = f"""
        INSTALL httpfs;
        LOAD httpfs;
        CREATE SECRET gcs_secret (
            TYPE GCS,
            KEY_ID '{gcs_key_id}',
            SECRET '{gcs_secret}'
        );
        CREATE TABLE IF NOT EXISTS transactions AS
        SELECT * FROM read_parquet('{bucket}/transactions.parquet');
        -- ... more tables
    """

    return {
        'type': 'duckdb',
        'initSql': init_sql,
    }
```

**New (BigQuery):**
```python
from cube import config
import os

@config('driver_factory')
def driver_factory(ctx: dict) -> dict:
    return {
        'type': 'bigquery',
        'projectId': os.environ.get('BIGQUERY_PROJECT_ID'),
        'credentials': os.environ.get('BIGQUERY_CREDENTIALS'),
        'location': 'US',
    }
```

### 2.2 Environment Variables
Add to Cube Cloud:
```bash
BIGQUERY_PROJECT_ID=gym-plus-coffee
BIGQUERY_CREDENTIALS=<service-account-json>
```

---

## Phase 3: SQL Syntax Conversions

### 3.1 Type Casting Changes

| DuckDB | BigQuery | Files Affected |
|--------|----------|----------------|
| `CAST(x AS DOUBLE)` | `CAST(x AS FLOAT64)` | inventory.yml, fulfillment_lines.yml |
| `CAST(x AS VARCHAR)` | `CAST(x AS STRING)` | inventory.yml, items.yml |
| `CAST(x AS INTEGER)` | `CAST(x AS INT64)` | Multiple |

### 3.2 Date Function Changes

| DuckDB | BigQuery | Files Affected |
|--------|----------|----------------|
| `DATE_DIFF('day', a, b)` | `DATE_DIFF(a, b, DAY)` | fulfillment_lines.yml, transaction_lines.yml |
| `DATE_DIFF('week', a, b)` | `DATE_DIFF(a, b, WEEK)` | transaction_lines.yml |
| `CAST(x AS TIMESTAMP)` | `PARSE_TIMESTAMP('%Y-%m-%d', x)` | fulfillment_lines.yml |

### 3.3 Specific Conversions Required

#### transaction_lines.yml

**units_per_week (LIFE004):**
```yaml
# Current (DuckDB)
sql: "1.0 * {units_sold} / NULLIF(DATE_DIFF('week', CAST({min_transaction_date} AS DATE), CAST({max_transaction_date} AS DATE)) + 1, 0)"

# New (BigQuery)
sql: "1.0 * {units_sold} / NULLIF(DATE_DIFF(PARSE_DATE('%Y-%m-%d', {max_transaction_date}), PARSE_DATE('%Y-%m-%d', {min_transaction_date}), WEEK) + 1, 0)"
```

#### fulfillment_lines.yml

**total_fulfillment_days:**
```yaml
# Current (DuckDB)
sql: "CAST(DATE_DIFF('day', CAST({fulfillments.trandate} AS TIMESTAMP), CAST({CUBE}.shipdate AS TIMESTAMP)) AS DOUBLE)"

# New (BigQuery)
sql: "CAST(DATE_DIFF(PARSE_DATE('%Y-%m-%d', {CUBE}.shipdate), PARSE_DATE('%Y-%m-%d', {fulfillments.trandate}), DAY) AS FLOAT64)"
```

#### inventory.yml

**quantity_available:**
```yaml
# Current (DuckDB)
sql: "CAST({CUBE}.calculated_quantity_available AS DOUBLE)"

# New (BigQuery)
sql: "CAST({CUBE}.calculated_quantity_available AS FLOAT64)"
```

### 3.4 Files Requiring Updates

| File | Changes Required |
|------|------------------|
| `model/cubes/transaction_lines.yml` | DATE_DIFF syntax, type casting |
| `model/cubes/inventory.yml` | DOUBLE → FLOAT64, VARCHAR → STRING |
| `model/cubes/fulfillment_lines.yml` | DATE_DIFF syntax, TIMESTAMP handling |
| `model/cubes/items.yml` | VARCHAR → STRING |
| `model/cubes/transactions.yml` | Type casting |
| `model/cubes/b2c_customers.yml` | Type casting |
| `model/cubes/fulfillments.yml` | DATE handling |
| `model/cubes/inbound_shipments.yml` | Type casting |
| `model/cubes/inbound_shipment_lines.yml` | DOUBLE → FLOAT64 |
| `model/cubes/purchase_orders.yml` | DATE handling |
| `model/cubes/purchase_order_lines.yml` | Type casting |
| `model/cubes/locations.yml` | Minor type updates |
| `model/cubes/vendors.yml` | VARCHAR → STRING |
| `model/cubes/subsidiaries.yml` | Type casting |

---

## Phase 4: count_distinct_approx Optimization (Optional)

BigQuery supports HyperLogLog++ for approximate distinct counts that can be pre-aggregated.

### 4.1 Candidate Measures

| Cube | Measure | Current Type | Recommended |
|------|---------|--------------|-------------|
| transaction_lines | transaction_count | count_distinct | count_distinct_approx |
| transaction_lines | sku_count | count_distinct | count_distinct_approx |
| inventory | sku_count | count_distinct | count_distinct_approx |
| inventory | location_count | count_distinct | count_distinct_approx |
| fulfillment_lines | fulfillment_count | count_distinct | count_distinct_approx |
| fulfillment_lines | sku_count | count_distinct | count_distinct_approx |
| fulfillment_lines | location_count | count_distinct | count_distinct_approx |

### 4.2 Example Conversion

```yaml
# Current
- name: sku_count
  sql: "{CUBE}.item"
  type: count_distinct

# New (with HyperLogLog++)
- name: sku_count
  sql: "{CUBE}.item"
  type: count_distinct_approx
```

**Note**: Approximate counts have ~1% error margin but enable pre-aggregation rollups.

---

## Phase 5: Pre-aggregation Updates

### 5.1 Update Table References

```yaml
# Current
pre_aggregations:
  - name: daily_metrics
    measures: [total_revenue, units_sold]
    dimensions: [category]
    time_dimension: transaction_date
    granularity: day
    external: true

# New (add BigQuery-specific options)
pre_aggregations:
  - name: daily_metrics
    measures: [total_revenue, units_sold]
    dimensions: [category]
    time_dimension: transaction_date
    granularity: day
    external: true
    build_range_start:
      sql: "DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)"
    build_range_end:
      sql: "CURRENT_DATE()"
```

### 5.2 Rollup Configuration for Approximate Counts

```yaml
pre_aggregations:
  - name: sku_metrics_rollup
    measures: [sku_count]  # Now count_distinct_approx
    dimensions: [category, season]
    time_dimension: transaction_date
    granularity: week
    external: true
    rollup:
      - sku_count  # Can now be rolled up
```

---

## Phase 6: Testing Plan

### 6.1 Unit Tests

Test each converted SQL expression:
```bash
# Test in BigQuery console
SELECT
  DATE_DIFF(
    PARSE_DATE('%Y-%m-%d', '2025-11-01'),
    PARSE_DATE('%Y-%m-%d', '2025-01-01'),
    WEEK
  ) as weeks_diff;
```

### 6.2 Integration Tests

Compare results between DuckDB and BigQuery:

| Metric | DuckDB Result | BigQuery Result | Match? |
|--------|---------------|-----------------|--------|
| RET001 | X% | X% | ✅ |
| LIFE004 | X units/week | X units/week | ✅ |
| BASK004 | X transactions | X transactions | ✅ |

### 6.3 Performance Benchmarks

| Query Type | DuckDB Time | BigQuery Time | Improvement |
|------------|-------------|---------------|-------------|
| count_distinct (cold) | 62s | ~5s | 12x |
| count_distinct (warm) | 24s | ~2s | 12x |
| Simple aggregation | 1s | ~1s | Same |
| Complex join | 15s | ~3s | 5x |

### 6.4 Acceptance Criteria

- [ ] All 66 metrics return data
- [ ] Results match DuckDB baseline (within 1% for approx counts)
- [ ] count_distinct queries < 5s
- [ ] No SQL syntax errors
- [ ] Pre-aggregations build successfully

---

## Phase 7: Data Pipeline Updates

### 7.1 Current Pipeline
```
NetSuite → Python ETL → Parquet → GCS → DuckDB (Cube)
```

### 7.2 New Pipeline Options

**Option A: Keep Parquet, External Tables**
```
NetSuite → Python ETL → Parquet → GCS → BigQuery External Tables → Cube
```
- Minimal changes to existing ETL
- Slightly slower than native tables
- No storage duplication

**Option B: Native BigQuery Tables**
```
NetSuite → Python ETL → BigQuery Native Tables → Cube
```
- Best performance
- Requires ETL changes (write to BQ instead of parquet)
- Storage costs increase

**Option C: Pre-Aggregated Summaries (No BigQuery Migration)**
```
NetSuite → Python ETL → Raw Parquet → Post-Processing → Summary Parquets → GCS → DuckDB → Cube
```
- **Key Concept**: Pre-compute distinct counts during extraction instead of at query time
- No infrastructure migration needed (keep DuckDB)
- Fast count_distinct equivalent (pre-computed, then summed)
- Smaller summary datasets for common aggregations
- Requires pre-defining aggregation dimensions
- Storage overhead: raw + summary tables

**Recommendation**: Start with Option A (external tables), migrate to Option B after validating performance. Consider Option C if BigQuery migration is not feasible or cost-effective.

---

## Phase 8: Data Quality Issues (Count Inflation)

### 8.1 Problem: Inflated Count Metrics

**Impact**: CRITICAL - Affects transaction_count, order_count, sku_count

Transaction and line counts are **significantly inflated** due to inclusion of system-generated lines that should be excluded from business metrics.

#### Root Cause

NetSuite transaction tables include multiple line types that inflate counts:

| Line Type | Field | Value | Business Impact | Example Count Inflation |
|-----------|-------|-------|-----------------|------------------------|
| Header lines | `mainline` | 'T' | Not a product line | +1 per transaction |
| Tax lines | `taxline` | 'T' | System-generated | +1-3 per transaction |
| COGS lines | `iscogs` | 'T' | Accounting entries | +1 per item |
| Discount lines | `transactiondiscount` | 'T' | Promotional adjustments | +1 per discount |
| Non-posting transactions | `posting` | 'F' | Draft/unfulfilled orders | Varies |
| Voided transactions | `voided` | 'T' | Canceled transactions | Varies |

#### Estimated Impact on Metrics

Based on audit analysis:

| Metric | Inflation | Cause |
|--------|-----------|-------|
| `transaction_lines.transaction_count` | +10-20% | Tax + COGS lines included |
| `transaction_lines.sku_count` | +40-50% | COGS lines counted as separate items |
| `transactions.order_count` | +5-10% | Non-posting SalesOrd included |
| Revenue metrics | Accurate | Dollar amounts not affected |
| `units_sold` | +40-50% | COGS lines counted as sales |

### 8.2 Solution: Audit Fields + Filtering

#### New Audit Fields Extracted

**Transaction Lines:**
- `taxline` (T/F) - Identifies tax calculation lines
- `iscogs` (T/F) - Identifies cost-of-goods-sold entries
- `transactiondiscount` (T/F) - Identifies discount lines
- `netamount` - Transaction currency amount (vs base currency)

**Transactions:**
- `posting` (T/F) - Posted to general ledger vs draft
- `voided` (T/F) - Voided/canceled transactions
- `postingperiod` - Accounting period for posting

#### Filtering Strategy

**For transaction_lines (product sales only):**
```sql
WHERE mainline = 'F'          -- Exclude header lines
  AND taxline = 'F'           -- Exclude tax lines
  AND iscogs = 'F'            -- Exclude COGS entries
  AND transactiondiscount = 'F'  -- Exclude discount lines
```

**For transactions (financial actuals only):**
```sql
WHERE posting = 'T'           -- Only posted transactions
  AND voided = 'F'            -- Exclude voided
  AND type IN ('CustInvc', 'CashSale', 'CustCred')  -- Exclude SalesOrd
```

### 8.3 Implementation Approaches

#### Approach 1: Filter in Cube YML (Query-Time)

Update measure definitions to exclude system lines:

```yaml
# transaction_lines.yml
measures:
  - name: transaction_count
    sql: "{CUBE}.transaction"
    type: count_distinct
    filters:
      - sql: "{CUBE}.mainline = 'F'"
      - sql: "{CUBE}.taxline = 'F'"
      - sql: "{CUBE}.iscogs = 'F'"
      - sql: "{CUBE}.transactiondiscount = 'F'"
```

**Pros:** Simple, no data pipeline changes
**Cons:** Still slow count_distinct queries

#### Approach 2: Pre-Filter Parquet Files (Post-Processing)

Create clean parquet files with filters applied:

```python
# Post-processing script
import pandas as pd

# Load raw extract with audit fields
lines = pd.read_parquet('transaction_lines_AUDIT.parquet')

# Filter to real product lines only
lines_clean = lines[
    (lines['mainline'] == 'F') &
    (lines['taxline'] == 'F') &
    (lines['iscogs'] == 'F') &
    (lines['transactiondiscount'] == 'F')
]

# Save clean version
lines_clean.to_parquet('transaction_lines_clean.parquet')
```

**Pros:** Smaller datasets, no query-time filtering needed
**Cons:** Need to regenerate on data updates

#### Approach 3: Pre-Aggregated Summaries (Option C)

Combine filtering + pre-aggregation:

```python
# Filter first, then aggregate
lines_clean = lines[
    (lines['mainline'] == 'F') &
    (lines['taxline'] == 'F') &
    (lines['iscogs'] == 'F') &
    (lines['transactiondiscount'] == 'F')
]

# Pre-compute distinct counts
summary = lines_clean.groupby([
    'transaction_date', 'category', 'channel_type'
]).agg({
    'transaction': 'nunique',  # Accurate transaction count
    'item': 'nunique',         # Accurate SKU count
    'amount': 'sum',
    'quantity': 'sum'
}).reset_index()

summary.to_parquet('transaction_lines_summary_clean.parquet')
```

**Pros:** Fast queries + accurate counts + smaller data
**Cons:** Must pre-define aggregation dimensions

### 8.4 Validation Tests

After implementing filters, validate counts:

```python
# Compare raw vs filtered counts
raw = pd.read_parquet('transaction_lines_raw.parquet')
clean = pd.read_parquet('transaction_lines_clean.parquet')

print(f"Raw records: {len(raw):,}")
print(f"Clean records: {len(clean):,}")
print(f"Filtered out: {len(raw) - len(clean):,} ({(1 - len(clean)/len(raw)) * 100:.1f}%)")

# Validate by line type
print("\nFiltered lines by type:")
print(f"  Header (mainline='T'): {(raw['mainline'] == 'T').sum():,}")
print(f"  Tax (taxline='T'): {(raw['taxline'] == 'T').sum():,}")
print(f"  COGS (iscogs='T'): {(raw['iscogs'] == 'T').sum():,}")
print(f"  Discount (transactiondiscount='T'): {(raw['transactiondiscount'] == 'T').sum():,}")
```

Expected results:
- ~30-40% of raw lines should be filtered out
- Revenue totals should remain unchanged (system lines have $0 or offsetting amounts)
- SKU counts should decrease by ~40-50%
- Transaction counts should decrease by ~10-20%

### 8.5 Affected Metrics

Update these metrics after implementing filters:

| Metric ID | Metric Name | Cube | Current Issue | Fix |
|-----------|-------------|------|---------------|-----|
| BASK004 | Transaction Count | transaction_lines | Inflated by system lines | Apply 4-field filter |
| PM001 | Units Sold | transaction_lines | Inflated by COGS lines | Apply 4-field filter |
| PM004 | SKU Count | transaction_lines | Inflated by COGS items | Apply 4-field filter |
| INV003 | Items in Stock | inventory | Accurate (uses inventory table) | No change |
| LOC001 | SKUs per Location | inventory | Accurate (uses inventory table) | No change |
| OM001 | Order Count | transactions | Includes non-posting SalesOrd | Filter posting='T' |

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Infrastructure | 1 day | BigQuery project access |
| Phase 2: cube.py changes | 2 hours | Service account credentials |
| Phase 3: SQL conversions | 1-2 days | None |
| Phase 4: count_distinct_approx | 2 hours | Optional |
| Phase 5: Pre-aggregations | 4 hours | Phase 3 complete |
| Phase 6: Testing | 1 day | All phases complete |
| Phase 7: Pipeline updates | 1-2 days | Testing complete |
| Phase 8: Data quality (count inflation) | 4-6 hours | AUDIT extractions complete |

**Total (with BigQuery)**: 4-6 days
**Total (Option C - no migration)**: 1-2 days (post-processing only)

---

## Cost Considerations

### BigQuery Pricing
- **On-demand**: $6.25 per TB processed
- **Flat-rate**: $2,000/month for 100 slots

### Estimated Monthly Cost
- Current query volume: ~50GB/day processed
- Monthly: ~1.5TB × $6.25 = **~$10/month** on-demand
- With heavy usage: Consider flat-rate

### Storage
- External tables: No additional storage cost (data in GCS)
- Native tables: $0.02/GB/month (~$5/month for 250GB)

---

## Rollback Plan

If BigQuery migration fails:

1. Revert `cube.py` to DuckDB configuration
2. Restore original YAML files from git
3. Redeploy Cube

Keep DuckDB configuration in a branch for quick rollback.

---

## Migration Checklist

### Pre-Migration
- [ ] Create BigQuery dataset
- [ ] Set up service account with BigQuery permissions
- [ ] Create external tables for all 14 parquet files
- [ ] Test BigQuery connection from local environment

### Migration
- [ ] Update cube.py driver configuration
- [ ] Convert all SQL syntax in YAML files
- [ ] Add environment variables to Cube Cloud
- [ ] Deploy to staging environment

### Post-Migration
- [ ] Run all 66 metric tests
- [ ] Compare results with DuckDB baseline
- [ ] Benchmark query performance
- [ ] Update pre-aggregations if needed
- [ ] Monitor for errors in production

### Optional Enhancements
- [ ] Convert count_distinct to count_distinct_approx
- [ ] Add BigQuery-specific pre-aggregation optimizations
- [ ] Migrate to native BigQuery tables

### Data Quality (Phase 8) - Required for Accurate Metrics
- [ ] Extract transaction_lines with AUDIT fields (taxline, iscogs, transactiondiscount, netamount)
- [ ] Extract transactions with AUDIT fields (posting, voided, postingperiod)
- [ ] Choose implementation approach (filter in YML, pre-filter parquet, or pre-aggregation)
- [ ] Validate filtered counts against expected inflation rates
- [ ] Update affected metrics (transaction_count, sku_count, units_sold, order_count)
- [ ] Document baseline vs filtered comparisons

---

## References

- [Cube BigQuery Driver Documentation](https://cube.dev/docs/product/configuration/data-sources/bigquery)
- [BigQuery SQL Syntax](https://cloud.google.com/bigquery/docs/reference/standard-sql)
- [HyperLogLog++ in BigQuery](https://cloud.google.com/bigquery/docs/reference/standard-sql/hll_functions)
- [Cube Pre-aggregations](https://cube.dev/docs/product/caching/pre-aggregations)

---

## Phase 9: Comprehensive Update Checklist & Impact Analysis

### 9.1 Current State Impact Analysis

#### Performance Impact (Severity: HIGH)

**Slow count_distinct Operations:**
- **Current Performance**: 15-62 seconds per query
- **Queries Affected**: ~15-20 dashboard queries daily
- **User Impact**: Long wait times, poor UX, dashboard timeouts
- **Business Impact**: Delayed decision-making, reduced data adoption

**Affected Metrics by Performance:**

| Priority | Metric IDs | Current Time | Target Time | Improvement |
|----------|-----------|--------------|-------------|-------------|
| HIGH | CH001, BASK004, INV003, LOC001 | 15-62s | 2-5s | 3-31x faster |
| MEDIUM | FM001, FM002, FM003, LIFE003, LOC003 | 15-62s | 2-5s | 3-31x faster |
| LOW | Ad-hoc location/SKU queries | 15-62s | 2-5s | 3-31x faster |

#### Data Quality Impact (Severity: CRITICAL)

**Count Inflation Problem:**
- **Revenue Metrics**: ✅ Accurate (dollar amounts correct)
- **Count Metrics**: ❌ Inflated by 10-50%
- **Unit Metrics**: ❌ Inflated by 40-50%

**Specific Metric Impacts:**

| Metric ID | Metric Name | Current State | Impact | Fix Required |
|-----------|-------------|---------------|--------|--------------|
| BASK004 | Transaction Count | Inflated +10-20% | Tax/COGS lines counted | Phase 8 filtering |
| PM001 | Units Sold | Inflated +40-50% | COGS lines counted as sales | Phase 8 filtering |
| PM004 | SKU Count | Inflated +40-50% | COGS items counted | Phase 8 filtering |
| OM001 | Order Count | Inflated +5-10% | Non-posting SalesOrd included | Phase 8 filtering |
| CH001 | Orders by Channel | Inflated +10-20% | System lines included | Phase 8 filtering |
| INV003 | Items in Stock | ✅ Accurate | Uses inventory table | No change |
| FM001-003 | Fulfillment Metrics | ✅ Accurate | Uses fulfillment table | No change |

**Total Metrics Affected:**
- **4 metrics CRITICALLY wrong** (PM001, PM004, BASK004, OM001)
- **1 metric moderately wrong** (CH001)
- **61 metrics accurate** or unaffected

---

### 9.2 Files to Update: Complete Inventory

#### Category 1: Cube Schema Files (14 files)

##### High Priority - SQL Syntax Changes Required

| File | Lines to Update | Change Type | Complexity | Testing Priority |
|------|----------------|-------------|------------|------------------|
| `model/cubes/transaction_lines.yml` | ~20 lines | DATE_DIFF, type casting, filters, dimensions | HIGH | CRITICAL |
| `model/cubes/transactions.yml` | ~10 lines | Type casting, filters, dimensions | MEDIUM | HIGH |
| `model/cubes/inventory.yml` | ~12 lines | DOUBLE→FLOAT64, VARCHAR→STRING | MEDIUM | HIGH |
| `model/cubes/fulfillment_lines.yml` | ~10 lines | DATE_DIFF, TIMESTAMP handling | HIGH | HIGH |
| `model/cubes/items.yml` | ~5 lines | VARCHAR→STRING | LOW | MEDIUM |
| `model/cubes/b2c_customers.yml` | ~6 lines | Type casting | LOW | MEDIUM |
| `model/cubes/fulfillments.yml` | ~4 lines | DATE handling | LOW | MEDIUM |
| `model/cubes/inbound_shipments.yml` | ~3 lines | Type casting | LOW | LOW |
| `model/cubes/inbound_shipment_lines.yml` | ~4 lines | DOUBLE→FLOAT64 | LOW | LOW |
| `model/cubes/purchase_orders.yml` | ~3 lines | DATE handling | LOW | LOW |
| `model/cubes/purchase_order_lines.yml` | ~4 lines | Type casting | LOW | LOW |
| `model/cubes/locations.yml` | ~2 lines | Minor type updates | LOW | LOW |
| `model/cubes/vendors.yml` | ~2 lines | VARCHAR→STRING | LOW | LOW |
| `model/cubes/subsidiaries.yml` | ~2 lines | Type casting | LOW | LOW |

**Total Estimated Changes**: ~90 lines across 14 files

##### Optional - count_distinct_approx Conversions

| File | Measures to Convert | Current Performance | Expected Improvement | Accuracy Trade-off |
|------|-------------------|---------------------|---------------------|-------------------|
| `model/cubes/transaction_lines.yml` | `transaction_count`, `sku_count` | 15-62s | → 2-5s | ±1% error |
| `model/cubes/inventory.yml` | `sku_count`, `location_count` | 15-62s | → 2-5s | ±1% error |
| `model/cubes/fulfillment_lines.yml` | `fulfillment_count`, `sku_count`, `location_count` | 15-62s | → 2-5s | ±1% error |

**Total Measures**: 7 measures to convert

---

### 9.3 Detailed Update Instructions by File

#### 9.3.1 transaction_lines.yml (CRITICAL - ~20 changes)

**Change 1: Add Audit Field Dimensions (Phase 8)**
```yaml
dimensions:
  # ... existing dimensions ...
  
  # ADD: Audit fields for filtering system lines
  - name: mainline
    sql: "{CUBE}.mainline"
    type: string
    description: "T = header line, F = item line"
    
  - name: taxline
    sql: "{CUBE}.taxline"
    type: string
    description: "T = tax calculation line, F = regular line"
    
  - name: iscogs
    sql: "{CUBE}.iscogs"
    type: string
    description: "T = COGS accounting entry, F = regular line"
    
  - name: transactiondiscount
    sql: "{CUBE}.transactiondiscount"
    type: string
    description: "T = discount line, F = regular line"
    
  - name: netamount
    sql: "{CUBE}.netamount"
    type: number
    description: "Transaction currency amount (vs base currency)"
```

**Change 2: Update transaction_count with Filters (Phase 8 + Performance)**
```yaml
measures:
  - name: transaction_count
    sql: "{CUBE}.transaction"
    type: count_distinct_approx  # CHANGED: Was count_distinct
    filters:  # ADD: Exclude system lines
      - sql: "{CUBE}.mainline = 'F'"
      - sql: "{CUBE}.taxline = 'F'"
      - sql: "{CUBE}.iscogs = 'F'"
      - sql: "{CUBE}.transactiondiscount = 'F'"
    description: "Count of distinct transactions (product lines only)"
```

**Change 3: Update sku_count with Filters**
```yaml
  - name: sku_count
    sql: "{CUBE}.item"
    type: count_distinct_approx  # CHANGED: Was count_distinct
    filters:  # ADD: Exclude COGS items
      - sql: "{CUBE}.mainline = 'F'"
      - sql: "{CUBE}.taxline = 'F'"
      - sql: "{CUBE}.iscogs = 'F'"
    description: "Count of distinct SKUs sold (excludes COGS entries)"
```

**Change 4: Update units_sold with Filter**
```yaml
  - name: units_sold
    sql: "SUM({CUBE}.quantity)"
    type: number
    filters:  # ADD: Exclude COGS lines
      - sql: "{CUBE}.mainline = 'F'"
      - sql: "{CUBE}.iscogs = 'F'"
    description: "Total units sold (excludes COGS entries)"
```

**Change 5: Update DATE_DIFF for units_per_week**
```yaml
  - name: units_per_week
    sql: >
      1.0 * {units_sold} / NULLIF(
        DATE_DIFF(
          PARSE_DATE('%Y-%m-%d', CAST({max_transaction_date} AS STRING)), 
          PARSE_DATE('%Y-%m-%d', CAST({min_transaction_date} AS STRING)), 
          WEEK
        ) + 1, 0
      )
    type: number
    # CHANGED: DATE_DIFF syntax from DuckDB to BigQuery
```

**Change 6: Update Type Casting (10+ occurrences)**
```yaml
# Find and replace throughout file:
CAST(x AS DOUBLE)   → CAST(x AS FLOAT64)
CAST(x AS INTEGER)  → CAST(x AS INT64)
CAST(x AS VARCHAR)  → CAST(x AS STRING)
```

**Impact:**
- ✅ Fixes PM001 (Units Sold): -40-50% to accurate value
- ✅ Fixes PM004 (SKU Count): -40-50% to accurate value
- ✅ Fixes BASK004 (Transaction Count): -10-20% to accurate value
- ✅ Fixes CH001 (Orders by Channel): -10-20% to accurate value
- ✅ Speeds up queries: 15-62s → 2-5s
- ⚠️ count_distinct_approx adds ±1% error (acceptable trade-off)

---

#### 9.3.2 transactions.yml (HIGH - ~10 changes)

**Change 1: Add Audit Field Dimensions**
```yaml
dimensions:
  # ... existing dimensions ...
  
  # ADD: Transaction status fields
  - name: posting
    sql: "{CUBE}.posting"
    type: string
    description: "T = posted to GL, F = non-posting"
    
  - name: voided
    sql: "{CUBE}.voided"
    type: string
    description: "T = voided/cancelled, F = active"
    
  - name: postingperiod
    sql: "{CUBE}.postingperiod"
    type: string
    description: "Accounting period for posting"
```

**Change 2: Update order_count with Filters**
```yaml
measures:
  - name: order_count
    sql: "{CUBE}.id"
    type: count_distinct_approx  # CHANGED: Was count_distinct
    filters:  # ADD: Financial transactions only
      - sql: "{CUBE}.posting = 'T'"
      - sql: "{CUBE}.voided = 'F'"
      - sql: "{CUBE}.type IN ('CustInvc', 'CashSale', 'CustCred')"
    description: "Count of posted, non-voided financial transactions"
```

**Change 3: Type Casting Updates**
```yaml
# Replace throughout file:
CAST(x AS DOUBLE)   → CAST(x AS FLOAT64)
CAST(x AS INTEGER)  → CAST(x AS INT64)
```

**Impact:**
- ✅ Fixes OM001 (Order Count): -5-10% to accurate value
- ✅ Excludes non-posting SalesOrd (draft orders)
- ✅ Excludes voided transactions
- ✅ Speeds up queries: 15-62s → 2-5s

---

#### 9.3.3 inventory.yml (MEDIUM - ~12 changes)

**Change 1: Update sku_count**
```yaml
measures:
  - name: sku_count
    sql: "{CUBE}.item"
    type: count_distinct_approx  # CHANGED: Was count_distinct
    description: "Count of distinct SKUs in inventory"
```

**Change 2: Update All Type Casts**
```yaml
# quantity_available
- name: quantity_available
  sql: "CAST({CUBE}.calculated_quantity_available AS FLOAT64)"  # Was DOUBLE
  type: number

# All other numeric measures
CAST(x AS DOUBLE)   → CAST(x AS FLOAT64)
CAST(x AS VARCHAR)  → CAST(x AS STRING)
```

**Impact:**
- ✅ Speeds up INV003 (Items in Stock): 15-62s → 2-5s
- ✅ Speeds up LOC001 (SKUs per Location): 15-62s → 2-5s
- ✅ Speeds up LOC003 (Categories per Location): 15-62s → 2-5s
- ✅ Maintains inventory accuracy (inventory table already clean)

---

#### 9.3.4 fulfillment_lines.yml (HIGH - ~10 changes)

**Change 1: Update DATE_DIFF for fulfillment_days**
```yaml
- name: total_fulfillment_days
  sql: >
    CAST(
      DATE_DIFF(
        PARSE_DATE('%Y-%m-%d', CAST({CUBE}.shipdate AS STRING)), 
        PARSE_DATE('%Y-%m-%d', CAST({fulfillments.trandate} AS STRING)), 
        DAY
      ) AS FLOAT64
    )
  type: number
  # CHANGED: DATE_DIFF syntax + TIMESTAMP handling + DOUBLE→FLOAT64
```

**Change 2: Update count_distinct Measures**
```yaml
measures:
  - name: fulfillment_count
    sql: "{CUBE}.fulfillment"
    type: count_distinct_approx  # CHANGED: Was count_distinct
    
  - name: sku_count
    sql: "{CUBE}.item"
    type: count_distinct_approx  # CHANGED: Was count_distinct
    
  - name: location_count
    sql: "{CUBE}.location"
    type: count_distinct_approx  # CHANGED: Was count_distinct
```

**Impact:**
- ✅ Speeds up FM001 (Fulfillment Count): 15-62s → 2-5s
- ✅ Speeds up FM002 (Fulfillment by Status): 15-62s → 2-5s
- ✅ Speeds up FM003 (Fulfillment by Location): 15-62s → 2-5s
- ✅ Fixes fulfillment time calculations
- ✅ Maintains data accuracy (fulfillment tables already clean)

---

#### 9.3.5 items.yml, b2c_customers.yml, fulfillments.yml (LOW PRIORITY)

**Changes Required:**
```yaml
# All files: Simple type casting updates
CAST(x AS VARCHAR) → CAST(x AS STRING)
CAST(x AS INTEGER) → CAST(x AS INT64)
```

**Impact:**
- ✅ Syntax compatibility with BigQuery
- ⚠️ No performance impact (simple fields)
- ✅ No data accuracy impact

---

#### 9.3.6 cube.py (CRITICAL - Complete Rewrite)

**BEFORE (DuckDB - ~30 lines):**
```python
from cube import config
import os

@config('driver_factory')
def driver_factory(ctx: dict) -> dict:
    gcs_key_id = os.environ.get('GCS_KEY_ID', '')
    gcs_secret = os.environ.get('GCS_SECRET', '')
    bucket = 'gs://gym-plus-coffee-bucket-dev/parquet'

    init_sql = f"""
        INSTALL httpfs;
        LOAD httpfs;
        CREATE SECRET gcs_secret (
            TYPE GCS,
            KEY_ID '{gcs_key_id}',
            SECRET '{gcs_secret}'
        );
        
        -- Create tables from parquet files
        CREATE TABLE IF NOT EXISTS transactions AS
        SELECT * FROM read_parquet('{bucket}/transactions.parquet');
        
        CREATE TABLE IF NOT EXISTS transaction_lines AS
        SELECT * FROM read_parquet('{bucket}/transaction_lines.parquet');
        
        -- ... 12 more tables ...
    """

    return {
        'type': 'duckdb',
        'initSql': init_sql,
    }
```

**AFTER (BigQuery - ~10 lines):**
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
        'datasetName': 'analytics',  # Optional: specify dataset
    }
```

**Environment Variables Required:**
```bash
# Add to Cube Cloud or .env
BIGQUERY_PROJECT_ID=gym-plus-coffee
BIGQUERY_CREDENTIALS=<base64-encoded-service-account-json>

# Service account needs these permissions:
# - bigquery.jobs.create
# - bigquery.tables.get
# - bigquery.tables.getData
```

**Impact:**
- ⚠️ **BREAKING CHANGE** - Switches entire data source
- ✅ Simplifies configuration (30 lines → 10 lines)
- ✅ Removes complex GCS authentication logic
- ⚠️ Requires BigQuery external tables to exist first

**Prerequisites:**
```bash
# Must create external tables BEFORE deploying cube.py
bq mk --external_table_definition=transactions.json \
  gym-plus-coffee:analytics.transactions

# Repeat for all 14 tables
```

---

#### 9.3.7 SKILL_CUBE_REST_API-v15.md (3 sections to update)

**Update 1: Add to `<known_limitations>` Section**

**ADD after existing limitation #6:**
```markdown
### 7. BigQuery Approximate Counts (~1% Error Margin)

**Impact:** LOW - count_distinct_approx measures have small variance

**Background:**
For performance, the following measures use BigQuery's HyperLogLog++ approximate counting:
- transaction_count
- sku_count (transaction_lines, inventory, fulfillment_lines)
- fulfillment_count
- location_count

**Error Margin:** ±1% (e.g., 10,000 actual = 9,900-10,100 reported)

**Implications:**
- Small counts (<100) may show higher variance
- Large counts (>10,000) are highly accurate
- Suitable for all business metrics and dashboards
- NOT suitable for: Compliance reporting requiring exact counts

**Disclosure:** When reporting count metrics to stakeholders requiring precision, state:
"Note: Count metrics use approximate distinct counts with ~1% error margin for performance. 
For exact counts, use transactional reports from NetSuite."

**When to disclose:**
- Financial audits requiring exact transaction counts
- Compliance reporting
- Legal/contractual obligations
- Any query where user emphasizes "exact" counts
```

**Update 2: Update Performance Expectations**

**FIND section about query performance and REPLACE:**
```markdown
# OLD:
- count_distinct measures (transaction_count, sku_count, unique_customers) may take 15-62 seconds

# NEW:
### Query Performance Expectations

| Query Type | Expected Time | Notes |
|------------|---------------|-------|
| Simple aggregations (SUM, AVG) | 0.5-2s | Unchanged from DuckDB |
| count_distinct_approx | 2-5s | Was 15-62s in DuckDB |
| Complex joins (3+ tables) | 3-8s | Improved from 15s |
| Pre-aggregated queries | 0.1-0.5s | Uses cached rollups |

**Migration Date:** [YYYY-MM-DD]
**Previous Backend:** DuckDB with Parquet
**Current Backend:** BigQuery with external tables (Parquet on GCS)
```

**Update 3: Add Database Backend Note**

**ADD new section after `<api_reference>`:**
```markdown
<database_backend>
## Database Backend

**Current Infrastructure:**
- **Database:** Google BigQuery
- **Data Source:** External tables pointing to GCS Parquet files
- **Location:** US multi-region
- **Project:** gym-plus-coffee
- **Dataset:** analytics

**Data Freshness:**
- Parquet files updated: Daily at 2 AM UTC
- BigQuery external tables: Auto-refresh on query
- Typical lag: <4 hours from NetSuite

**Performance Characteristics:**
- count_distinct queries: 2-5 seconds
- Simple aggregations: 0.5-2 seconds
- Complex joins: 3-8 seconds
- Approximate count accuracy: ±1%

**Migration History:**
- **Pre-2025:** DuckDB with direct Parquet reads (count_distinct: 15-62s)
- **2025-[DATE]:** Migrated to BigQuery (count_distinct: 2-5s, 3-31x improvement)

**Known Limitations:**
- Approximate counts have ~1% error margin
- External tables may have ~5-10s first-query latency (cold start)
- Query costs apply ($6.25 per TB scanned)
</database_backend>
```

**Impact:**
- ✅ Documents new performance expectations
- ✅ Sets correct user expectations for approximate counts
- ✅ Provides context for migration decision
- ✅ Helps with troubleshooting (users know backend)

---

### 9.4 Pre-Aggregations Update Strategy

#### Current Pre-Aggregations (Audit Required)

**Action:** Review all cube YML files for existing `pre_aggregations` sections.

**If pre-aggregations exist:**
1. Add BigQuery-specific build ranges
2. Consider adding count_distinct_approx measures (now fast to pre-aggregate)
3. Add partition configuration for large datasets

**Example Update:**
```yaml
# BEFORE (DuckDB):
pre_aggregations:
  - name: daily_metrics
    measures: [total_revenue, units_sold]
    dimensions: [category]
    time_dimension: transaction_date
    granularity: day
    external: true

# AFTER (BigQuery - Enhanced):
pre_aggregations:
  - name: daily_metrics
    measures: 
      - total_revenue
      - units_sold
      - transaction_count  # ADD: Now fast with count_distinct_approx
      - sku_count          # ADD: Now fast with count_distinct_approx
    dimensions: [category, channel_type]  # ADD: More dimensions
    time_dimension: transaction_date
    granularity: day
    external: true
    # ADD: BigQuery-specific options
    build_range_start:
      sql: "DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)"
    build_range_end:
      sql: "CURRENT_DATE()"
    partition_granularity: month  # ADD: Partitioning for performance
    refresh_key:
      every: "1 day"
```

#### New Pre-Aggregations to Consider

**Recommendation:** Add these for commonly-queried metrics:

| Pre-Agg Name | Cube | Dimensions | Measures | Target Metrics | Est. Size |
|--------------|------|-----------|----------|----------------|-----------|
| `channel_daily` | transaction_lines | date, channel_type | transaction_count, total_revenue, sku_count, units_sold | CH001 | 50MB |
| `category_daily` | transaction_lines | date, category | transaction_count, total_revenue, units_sold, sku_count | BASK004, PM001 | 200MB |
| `season_daily` | transaction_lines | date, season | sku_count, units_sold, total_revenue | LIFE003 | 100MB |
| `inventory_snapshot` | inventory | date, location, category | sku_count, total_stock | INV003, LOC001, LOC003 | 150MB |
| `fulfillment_daily` | fulfillment_lines | date, location, status | fulfillment_count, units_shipped | FM001, FM002, FM003 | 40MB |

**Total Pre-Agg Storage:** ~540MB
**Performance Benefit:** 2-5s → 0.1-0.5s (4-50x additional improvement)

**Implementation Example:**
```yaml
# In transaction_lines.yml
pre_aggregations:
  - name: channel_daily
    measures:
      - transaction_count
      - total_revenue
      - sku_count
      - units_sold
    dimensions:
      - channel_type
    time_dimension: transaction_date
    granularity: day
    external: true
    build_range_start:
      sql: "DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)"
    build_range_end:
      sql: "CURRENT_DATE()"
    partition_granularity: month
    refresh_key:
      every: "1 day"
      
  - name: category_daily
    measures:
      - transaction_count
      - total_revenue
      - units_sold
      - sku_count
    dimensions:
      - category
    time_dimension: transaction_date
    granularity: day
    external: true
    build_range_start:
      sql: "DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)"
    build_range_end:
      sql: "CURRENT_DATE()"
    partition_granularity: month
    refresh_key:
      every: "1 day"
```

---

### 9.5 Testing Matrix

#### 9.5.1 Functional Tests (66 Metrics)

**Critical Metrics (7 metrics - 2 hours):**
| Metric ID | Test Query | Success Criteria |
|-----------|-----------|------------------|
| CH001 | Transaction count by channel (last 12 months) | Query < 5s, count reduced 10-20% |
| BASK004 | Transaction count by category (last 12 months) | Query < 5s, count reduced 10-20% |
| INV003 | SKU count in inventory | Query < 5s, count unchanged |
| LOC001 | SKU count per location | Query < 5s, count unchanged |
| PM001 | Units sold by category | Query < 2s, units reduced 40-50% |
| PM004 | SKU count by season | Query < 5s, count reduced 40-50% |
| OM001 | Order count by month | Query < 5s, count reduced 5-10% |

**High-Use Metrics (15 metrics - 3 hours):**
- Revenue metrics (RM001-003): Verify totals unchanged
- Fulfillment metrics (FM001-003): Verify <5s query time
- Margin metrics (MM001): Verify calculations unchanged
- Customer metrics (CM001-003): Verify counts unchanged

**Medium-Use Metrics (20 metrics - 2 hours):**
- Inventory metrics (INV001-003, STOCK001-006)
- Location metrics (LOC001-003)
- Discount metrics (DM001-002, DM058)

**Low-Use Metrics (24 metrics - 1 hour):**
- Department metrics
- Classification metrics
- Currency metrics
- Lifecycle metrics

**Total Testing Time:** 8 hours

#### 9.5.2 Performance Benchmarks

**Test Scenarios:**

| Scenario | Query | DuckDB Time | Target Time | Test Count |
|----------|-------|-------------|-------------|-----------|
| Cold count_distinct | `SELECT COUNT(DISTINCT transaction) FROM transaction_lines` | 62s | <5s | 5 queries |
| Warm count_distinct | Same query, repeated | 24s | <2s | 5 queries |
| Simple aggregation | `SELECT SUM(amount) FROM transaction_lines` | 1.2s | <2s | 5 queries |
| Complex join | 3-table join with aggregation | 15s | <5s | 5 queries |
| Pre-aggregated | Query hitting rollup | N/A | <0.5s | 5 queries |

**Success Criteria:**
- ✅ All count_distinct queries < 5s
- ✅ 80% of count_distinct queries < 3s
- ✅ Simple aggregations < 2s
- ✅ Complex joins < 5s

#### 9.5.3 Data Quality Validation

**Validation Tests:**

| Test | Method | Expected Result | Tolerance |
|------|--------|-----------------|-----------|
| Revenue totals | Compare DuckDB vs BigQuery | Identical | ±€0.01 |
| Transaction count (filtered) | Compare raw vs filtered | Reduced by 10-20% | ±2% |
| Units sold (filtered) | Compare raw vs filtered | Reduced by 40-50% | ±5% |
| SKU count (filtered) | Compare raw vs filtered | Reduced by 40-50% | ±5% |
| Approximate count accuracy | Sample 100 queries vs exact | Within ±1% | ±1.5% |
| Fulfillment time avg | Compare DuckDB vs BigQuery | Identical | ±0.1 days |

**Validation Script:**
```python
# Compare DuckDB vs BigQuery results
import pandas as pd

# Run same query on both backends
duckdb_results = pd.read_csv('duckdb_test_results.csv')
bigquery_results = pd.read_csv('bigquery_test_results.csv')

# Compare revenue (should be identical)
revenue_diff = abs(duckdb_results['total_revenue'].sum() - 
                   bigquery_results['total_revenue'].sum())
assert revenue_diff < 0.01, f"Revenue differs by {revenue_diff}"

# Compare filtered counts (should be reduced)
count_reduction = (duckdb_results['transaction_count'].sum() - 
                   bigquery_results['transaction_count'].sum()) / \
                   duckdb_results['transaction_count'].sum()
assert 0.10 <= count_reduction <= 0.20, \
    f"Count reduction {count_reduction:.2%} outside expected range"

print("✅ All validation tests passed")
```

---

### 9.6 Rollback Procedures

#### Scenario 1: Query Errors in Production

**Symptoms:**
- SQL syntax errors
- Type casting errors
- Queries returning wrong results

**Rollback Steps (5-10 minutes):**
```bash
# 1. Revert to previous git commit
cd /path/to/cube/repo
git log --oneline -5  # Find commit before migration
git revert <migration-commit-hash>

# 2. Redeploy to Cube Cloud
cube deploy --env production

# 3. Verify rollback
curl https://your-cube-api.com/cubejs-api/v1/meta
# Should show DuckDB driver

# 4. Test critical metrics
curl -X POST https://your-cube-api.com/cubejs-api/v1/load \
  -H "Authorization: Bearer $CUBE_API_TOKEN" \
  -d '{"measures":["transaction_lines.total_revenue"]}'
```

**Recovery Time:** 5-10 minutes

---

#### Scenario 2: Performance Degradation

**Symptoms:**
- Queries slower than expected (>10s)
- BigQuery showing high costs
- Timeouts in dashboards

**Diagnosis Steps:**
```bash
# 1. Check BigQuery query history
bq ls -j --max_results=20 --project_id=gym-plus-coffee

# 2. Identify slow queries
bq show -j <job-id>

# 3. Check if external tables are issue
# (Cold start: first query slow, subsequent fast)
```

**Resolution Options:**

**Option A: Switch to Native Tables**
```bash
# Load parquets into native BigQuery tables
bq load --source_format=PARQUET \
  gym-plus-coffee:analytics.transaction_lines \
  gs://gym-plus-coffee-bucket-dev/parquet/transaction_lines.parquet
```
**Time:** 1-2 hours
**Impact:** Faster queries, higher storage cost

**Option B: Rollback to DuckDB**
```bash
# Follow Scenario 1 steps
git revert <migration-commit>
cube deploy
```
**Time:** 5-10 minutes
**Impact:** Back to slow count_distinct (15-62s)

---

#### Scenario 3: Data Accuracy Issues

**Symptoms:**
- Revenue totals don't match NetSuite
- Count reductions too large/small
- Approximate counts show high variance

**Diagnosis Steps:**
```sql
-- Test 1: Compare revenue (should be identical)
SELECT SUM(amount) as total_revenue
FROM transaction_lines
WHERE mainline = 'F';
-- Compare with NetSuite report

-- Test 2: Check filter effectiveness
SELECT 
  COUNT(*) as total_lines,
  SUM(CASE WHEN mainline = 'T' THEN 1 ELSE 0 END) as header_lines,
  SUM(CASE WHEN taxline = 'T' THEN 1 ELSE 0 END) as tax_lines,
  SUM(CASE WHEN iscogs = 'T' THEN 1 ELSE 0 END) as cogs_lines,
  SUM(CASE WHEN mainline = 'F' AND taxline = 'F' AND iscogs = 'F' 
      THEN 1 ELSE 0 END) as clean_lines
FROM transaction_lines;
```

**Resolution:**
- If revenue differs: Check AUDIT field extraction
- If counts wrong: Verify filter logic in YML files
- If variance high: May need exact count_distinct (remove _approx)

**Rollback if needed:** Follow Scenario 1 steps

---

### 9.7 Migration Timeline (Detailed)

| Day | Time | Phase | Tasks | Owner | Output | Status |
|-----|------|-------|-------|-------|--------|--------|
| **Day 1** | 9-11am | Infrastructure | Create BigQuery dataset, configure IAM | DevOps | Dataset + service account | ⏳ |
| | 11am-1pm | Infrastructure | Create 14 external tables, test queries | DevOps | External tables working | ⏳ |
| | 2-5pm | Infrastructure | Load sample data, verify schema | DevOps | Sample queries successful | ⏳ |
| **Day 2** | 9-11am | Data Quality | Complete AUDIT extractions (if not done) | Data Eng | Parquet files with audit fields | ⏳ |
| | 11am-1pm | Data Quality | Create filtered parquets, validate counts | Data Eng | Clean parquet files | ⏳ |
| | 2-4pm | Configuration | Update cube.py, test in dev environment | Backend | cube.py working locally | ⏳ |
| | 4-5pm | Configuration | Deploy to staging, smoke test | Backend | Staging environment live | ⏳ |
| **Day 3** | 9-11am | Cube Updates | Update transaction_lines.yml (20 changes) | Backend | Critical cube updated | ⏳ |
| | 11am-1pm | Cube Updates | Update transactions.yml (10 changes) | Backend | Transactions cube updated | ⏳ |
| | 2-4pm | Cube Updates | Update inventory.yml, fulfillment_lines.yml | Backend | Performance cubes updated | ⏳ |
| | 4-5pm | Cube Updates | Deploy to staging, run smoke tests | Backend | All cubes deployed to staging | ⏳ |
| **Day 4** | 9-11am | Testing | Run critical metric tests (7 metrics) | QA | Critical metrics validated | ⏳ |
| | 11am-1pm | Testing | Run high-use metric tests (15 metrics) | QA | High-use metrics validated | ⏳ |
| | 2-4pm | Testing | Run performance benchmarks | QA | Performance targets met | ⏳ |
| | 4-5pm | Testing | Data quality validation | QA | Accuracy confirmed | ⏳ |
| **Day 5** | 9-11am | Optimization | Convert to count_distinct_approx (optional) | Backend | 7 measures optimized | ⏳ |
| | 11am-1pm | Optimization | Add pre-aggregations for top metrics | Backend | 5 pre-aggs created | ⏳ |
| | 2-4pm | Optimization | Test pre-agg build and refresh | Backend | Pre-aggs working | ⏳ |
| | 4-5pm | Documentation | Update SKILL_CUBE_REST_API-v15.md | Tech Writer | Docs updated | ⏳ |
| **Day 6** | 9-11am | Production | Final staging validation | QA + DevOps | Green light for prod | ⏳ |
| | 11am-12pm | Production | Deploy cube.py to production | DevOps | Production cutover | ⏳ |
| | 12-1pm | Production | Deploy cube YML files to production | DevOps | All cubes live | ⏳ |
| | 2-4pm | Production | Monitor dashboards, run critical queries | All team | Monitoring active | ⏳ |
| | 4-5pm | Production | Final validation, document results | All team | Migration complete | ⏳ |

**Total Duration:** 6 days (48 working hours)

**Team Required:**
- 1 DevOps Engineer (Days 1, 6)
- 1 Data Engineer (Day 2)
- 1 Backend Developer (Days 2-5)
- 1 QA Engineer (Days 4-6)
- 1 Technical Writer (Day 5)

---

### 9.8 Success Metrics

**Performance Metrics:**
| Metric | Current | Target | Actual | Status |
|--------|---------|--------|--------|--------|
| CH001 query time | 42s | <5s | ___ | ⏳ |
| BASK004 query time | 38s | <5s | ___ | ⏳ |
| INV003 query time | 55s | <5s | ___ | ⏳ |
| LOC001 query time | 48s | <5s | ___ | ⏳ |
| Average count_distinct time | 35s | <5s | ___ | ⏳ |

**Data Quality Metrics:**
| Metric | Expected Change | Actual | Status |
|--------|----------------|--------|--------|
| Transaction count | -10 to -20% | ___ | ⏳ |
| Units sold | -40 to -50% | ___ | ⏳ |
| SKU count | -40 to -50% | ___ | ⏳ |
| Order count | -5 to -10% | ___ | ⏳ |
| Revenue totals | ±0.01% | ___ | ⏳ |

**Business Impact:**
- ✅ Dashboard load times improved
- ✅ User satisfaction increased
- ✅ Ad-hoc analysis enabled
- ✅ Data accuracy restored

---

## Summary: Complete Migration Impact

### Files to Update: 16 Total

| Category | Files | Estimated Changes | Priority |
|----------|-------|------------------|----------|
| Cube schemas | 14 YML files | ~90 lines | HIGH |
| Configuration | 1 Python file (cube.py) | Complete rewrite | CRITICAL |
| Documentation | 1 Markdown file (SKILL) | 3 sections | MEDIUM |

### Metrics Impacted: 10 Direct + 56 Indirect

**Direct Performance Impact (10 metrics):**
- CH001, BASK004, INV003, LOC001, LIFE003, LOC003, FM001, FM002, FM003, + ad-hoc queries

**Direct Data Quality Impact (4 metrics):**
- PM001, PM004, BASK004, OM001

**Indirect Impact (56 metrics):**
- Type casting updates (no behavioral change)
- DATE_DIFF syntax updates (no behavioral change)

### Time Investment vs. Return

**Implementation Time:**
- Infrastructure: 1 day
- Data quality: 0.5 days
- Cube updates: 1.5 days
- Testing: 1.5 days
- Optimization: 1 day
- Production: 0.5 days
**Total: 6 days**

**Ongoing Return:**
- 15-20 queries/day × 30s saved = 7.5 hours/day saved
- 4 metrics fixed → Better business decisions
- Enables ad-hoc analysis → Increased data adoption

**ROI:** 6 days investment → 7.5 hours/day saved = Break-even in <1 day

---
