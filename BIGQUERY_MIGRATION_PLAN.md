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

**Recommendation**: Start with Option A (external tables), migrate to Option B after validating performance.

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

**Total: 4-6 days**

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

---

## References

- [Cube BigQuery Driver Documentation](https://cube.dev/docs/product/configuration/data-sources/bigquery)
- [BigQuery SQL Syntax](https://cloud.google.com/bigquery/docs/reference/standard-sql)
- [HyperLogLog++ in BigQuery](https://cloud.google.com/bigquery/docs/reference/standard-sql/hll_functions)
- [Cube Pre-aggregations](https://cube.dev/docs/product/caching/pre-aggregations)
