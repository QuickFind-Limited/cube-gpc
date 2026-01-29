# HIGH RISK Metrics Test Results - Complete Analysis

**Test Date**: January 18, 2026
**Total Tests**: 8
**Results**: 2 PASSED, 2 TIMEOUT, 4 PRE-AGG MISSING

---

## Executive Summary

### Root Causes Identified

1. **Missing transaction_id dimension** (FIXED) - Caused 3 test failures initially
2. **GL-based COGS measures not in pre-aggregations** - Causes 3 test failures
3. **Calculated measures not in pre-aggregations** - Causes 2 test failures
4. **COGS cube has 18 dimensions + daily-only granularity** - Causes 1 timeout

---

## Test Results with Root Cause Analysis

| Test ID | Status | Duration | Root Cause | Evidence |
|---------|--------|----------|------------|----------|
| MM001 | ERROR → PRE-AGG | 0.59s | gl_based_gross_margin_pct not in any pre-agg | Line 539: "NO COST MEASURES" comment |
| GMROI001 | ERROR → PRE-AGG | 0.46s | gl_based_gmroi not in any pre-agg | Same as MM001 |
| LIFE004 | PRE-AGG | 0.61s | units_per_week not in any pre-agg | grep shows no matches in pre_aggregations |
| RET004 | ✅ PASSED | 1.01s | Uses monthly pre-agg (orders_monthly) | transactions.yml:280-310 |
| RET005 | TIMEOUT | 13.85s | return_rate not in any pre-agg | grep shows no matches in pre_aggregations |
| FD002 | ✅ PASSED | 0.31s | Uses monthly pre-agg (fulfillment_monthly) | fulfillments.yml:150-171 |
| MM001_COMP | ERROR → PRE-AGG | 0.24s | gl_based_cogs not in any pre-agg | Line 539: "NO COST MEASURES" comment |
| COGS_DIRECT | TIMEOUT | 11.33s | 18 dimensions + daily-only = 365 huge partitions | transaction_accounting_lines_cogs.yml:136-167 |

---

## Detailed Analysis

### ✅ PASSED Tests (2/8)

#### RET004 - Return Rate Components (PASSED - 1.01s)

**Query**:
```json
{
  "measures": ["transactions.customer_credits_aligned", "transactions.revenue_transaction_count_aligned"],
  "dimensions": ["transactions.customer_type"],
  "timeDimensions": [{
    "dimension": "transactions.trandate",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}
```

**Why it works**:
- Uses `orders_monthly` pre-aggregation (transactions.yml:280-310)
- Both measures included in pre-agg:
  - `customer_credits_aligned` (line 286)
  - `revenue_transaction_count_aligned` (line 288)
- Dimension `customer_type` included (line 298)
- Monthly granularity matches query
- **Optimal performance**: 12 months × small partition size = fast scan

---

#### FD002 - Fulfillments per Order (PASSED - 0.31s)

**Query**:
```json
{
  "measures": ["fulfillments.fulfillments_per_order"],
  "dimensions": ["fulfillments.status_name"],
  "timeDimensions": [{
    "dimension": "fulfillments.trandate",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}
```

**Why it works**:
- Uses `fulfillment_monthly` pre-aggregation (fulfillments.yml:150-171)
- **Note**: `fulfillments_per_order` is a **calculated measure** NOT in pre-agg
- But component measures ARE in pre-agg:
  - `fulfillment_count` (line 152)
  - `unique_orders` (line 153)
- Cube.js calculates ratio from pre-aggregated components at query time
- Very fast because components are pre-aggregated
- **Key learning**: Ratios can work IF components are pre-aggregated

---

### ❌ PRE-AGGREGATION MISSING Errors (4/8)

#### MM001 - Gross Margin % (GL-based COGS)

**Error**: "No pre-aggregation table has been built for this query yet"

**Root Cause**: `gl_based_gross_margin_pct` NOT in any pre-aggregation

**Evidence**:
- Measure definition: transaction_lines.yml:221-223
- Pre-agg check: Line 539 comment "NO COST MEASURES (no gl_based_cogs, no gl_based_gross_margin, no gross_margin, no total_cost)"
- grep confirmation: `gl_based` measures not found in any pre_aggregations section

**Why excluded**:
- GL-based measures require JOIN to transaction_accounting_lines_cogs
- JOINs cause cartesian product (one-to-many relationship)
- Intentionally excluded from pre-aggs to prevent explosion

**Measure SQL**:
```yaml
- name: gl_based_gross_margin_pct
  sql: "100.0 * ({total_revenue} - {gl_based_cogs}) / NULLIF({total_revenue}, 0)"
  type: number
```

**Fix options**:
1. **Denormalize COGS** into transaction_lines (recommended)
2. **Component measures** - store revenue and COGS separately, calculate % client-side
3. **Accept slow queries** - allow fallback to raw data

---

#### GMROI001 - GMROI (GL-based COGS)

**Error**: "No pre-aggregation table has been built for this query yet"

**Root Cause**: Same as MM001 - `gl_based_gmroi` NOT in any pre-aggregation

**Measure SQL**:
```yaml
- name: gl_based_gmroi
  sql: "({total_revenue} - {gl_based_cogs}) / NULLIF({gl_based_cogs}, 0)"
  type: number
```

**Same fix needed as MM001**

---

#### MM001_COMP - Revenue + GL COGS Components

**Error**: "No pre-aggregation table has been built for this query yet"

**Root Cause**: `gl_based_cogs` NOT in any pre-aggregation (even though it's a component)

**Note**: `total_revenue` IS in pre-aggs, but `gl_based_cogs` is not

**This confirms**: GL-based measures are globally excluded from all pre-aggs

---

#### LIFE004 - Units Per Week (Sales Velocity)

**Error**: "No pre-aggregation table has been built for this query yet"

**Root Cause**: `units_per_week` NOT in any pre-aggregation

**Evidence**: grep shows no matches in pre_aggregations sections

**Measure SQL**:
```yaml
- name: units_per_week
  sql: >
    1.0 * SUM(CASE WHEN {CUBE}.transaction_type IN ('CustInvc', 'CashSale') AND {CUBE}.quantity < 0 THEN ABS({CUBE}.quantity) ELSE 0 END) /
    NULLIF(
      (MAX(CAST({CUBE}.transaction_date AS DATE)) - MIN(CAST({CUBE}.transaction_date AS DATE))) / 7.0 + 1,
      0
    )
  type: number
```

**Why excluded**:
- Uses **MIN/MAX window functions** within the measure SQL
- **NOT ROLLUP-SAFE** - Cannot be pre-aggregated
- Must be calculated at query time from raw data

**Fix options**:
1. **Remove from cube** - calculate client-side from units_sold and date range
2. **Store components** - add min_date, max_date, total_units to pre-agg
3. **Accept slow queries** - document as query-time calculation

---

### 🕐 TIMEOUT Failures (2/8)

#### RET005 - Return Rate % (TIMEOUT - 13.85s)

**Error**: "Continue wait" (timeout approaching)

**Root Cause**: `return_rate` NOT in any pre-aggregation

**Evidence**: grep shows no matches in pre_aggregations sections

**Measure SQL**:
```yaml
- name: return_rate
  sql: "100.0 * {units_returned} / NULLIF({units_sold} + {units_returned}, 0)"
  type: number
```

**Why it timed out (vs FD002 which passed)**:
- `units_returned` and `units_sold` ARE in pre-aggs (revenue_analysis_monthly)
- BUT query asked for `category` dimension
- `revenue_analysis_monthly` has **15 dimensions**
- 12 months × 15-dimension partitions = slow scan (~14 seconds)

**Comparison to FD002** (which passed in 0.31s):
- FD002 used `fulfillment_monthly` with only **3 dimensions**
- RET005 used `revenue_analysis_monthly` with **15 dimensions**
- 5x more dimensions = much larger partitions = 45x slower (14s vs 0.3s)

**Fix needed**:
- Add lightweight monthly pre-agg with fewer dimensions (like revenue_monthly_fast)
- Similar fix to what we did for total_revenue timeout

---

#### COGS_DIRECT - GL COGS Direct (TIMEOUT - 11.33s)

**Error**: "Continue wait" (timeout approaching)

**Root Cause**: COGS cube has **18 dimensions** and **daily-only** granularity

**Evidence**: transaction_accounting_lines_cogs.yml:136-167

**Pre-aggregation config**:
```yaml
- name: cogs_analysis
  measures: [gl_cogs, gl_cogs_debit, gl_cogs_credit, cogs_entry_count]
  dimensions:
    - transaction_type       # 1
    - category               # 2
    - section                # 3
    - season                 # 4
    - product_range          # 5
    - collection             # 6
    - department_name        # 7
    - billing_country        # 8
    - shipping_country       # 9
    - classification_name    # 10
    - transaction_currency   # 11
    - currency_name          # 12
    - sku                    # 13
    - product_name           # 14
    - size                   # 15
    - color                  # 16
    - location_name          # 17
    - cogs_account_name      # 18
  time_dimension: transaction_date
  granularity: day           # ← DAILY ONLY
  partition_granularity: day
```

**Why it timed out**:
- **18 dimensions** (vs 15 in revenue_analysis_monthly which also timed out)
- **Daily granularity** for 12-month query = 365 daily partitions
- Each partition is HUGE (18-dimensional cartesian product)
- Total scan: 365 partitions × massive partition size = 11+ seconds

**Comparison to revenue_monthly_fast** (which we fixed):
- revenue_monthly_fast: 6 dimensions, monthly granularity (12 partitions) = <2s
- cogs_analysis: 18 dimensions, daily granularity (365 partitions) = 11+s

**Fix needed**:
- Add `cogs_monthly_fast` pre-aggregation with 4-6 dimensions
- Monthly granularity (12 partitions instead of 365)
- Same pattern as revenue_monthly_fast fix

---

## Summary of Issues

### Issue 1: GL-Based COGS Measures Not in Pre-Aggs ❌
**Affected**: MM001, GMROI001, MM001_COMP (3 tests)
**Why**: JOIN to transaction_accounting_lines_cogs causes cartesian product
**Status**: Intentionally excluded (documented in line 539)
**Fix needed**: Denormalize COGS or use component measure strategy

### Issue 2: Non-Rollup Measures Not in Pre-Aggs ❌
**Affected**: LIFE004 (units_per_week) (1 test)
**Why**: Uses MIN/MAX window functions - not additive
**Status**: Cannot be pre-aggregated by design
**Fix needed**: Remove measure or document as slow

### Issue 3: Too Many Dimensions in Monthly Pre-Agg 🕐
**Affected**: RET005 (return_rate) (1 test)
**Why**: revenue_analysis_monthly has 15 dimensions = large partitions
**Status**: Same root cause as original revenue timeout issue
**Fix needed**: Add lightweight monthly pre-agg (like revenue_monthly_fast)

### Issue 4: COGS Cube Has 18 Dimensions + Daily-Only 🕐
**Affected**: COGS_DIRECT (1 test)
**Why**: 18 dimensions × 365 daily partitions = massive scan
**Status**: Worse than revenue_analysis_monthly
**Fix needed**: Add cogs_monthly_fast with 4-6 dimensions

---

## Fix Recommendations (Prioritized)

### Priority 1: Add Lightweight Monthly Pre-Aggs (HIGH IMPACT)

**Fix RET005 and prevent future timeouts**:
```yaml
# In transaction_lines.yml
- name: operations_monthly_fast
  measures:
    - units_sold
    - units_returned
    - line_count
  dimensions:
    - category
    - season
    - customer_type
    - transaction_type
  time_dimension: transaction_date
  granularity: month
  partition_granularity: month
```

**Fix COGS_DIRECT**:
```yaml
# In transaction_accounting_lines_cogs.yml
- name: cogs_monthly_fast
  measures:
    - gl_cogs
  dimensions:
    - category
    - season
    - customer_type
    - currency_name
  time_dimension: transaction_date
  granularity: month
  partition_granularity: month
```

**Expected impact**: Both tests should complete in <2 seconds (10x improvement)

---

### Priority 2: Denormalize GL-Based COGS (MEDIUM IMPACT)

**Fix MM001, GMROI001, MM001_COMP**:

Create BigQuery view that pre-joins COGS:
```sql
CREATE OR REPLACE VIEW gpc.transaction_lines_with_gl_cogs AS
SELECT
  tl.*,
  SUM(tal.gl_cogs_amount) as gl_cogs_aggregated
FROM gpc.transaction_lines_denormalized_mv tl
LEFT JOIN gpc.transaction_accounting_lines_cogs tal
  ON tl.transaction = tal.transaction
GROUP BY ALL tl.* columns
```

Then update transaction_lines cube to use this view and add gl_cogs to pre-aggs.

**Expected impact**: MM001, GMROI001, MM001_COMP should complete in <2 seconds

---

### Priority 3: Handle Non-Rollup Measures (LOW IMPACT)

**Fix LIFE004**:

**Option A: Remove measure** (recommended)
- Document that units_per_week must be calculated client-side
- Provide formula in documentation

**Option B: Store components**
- Add min_transaction_date and max_transaction_date to pre-aggs (already exist!)
- Calculate rate client-side from components

**Expected impact**: Not performance-critical, low usage metric

---

## Validation Plan

1. Apply Priority 1 fixes (lightweight monthly pre-aggs)
2. Wait 15 minutes for pre-agg builds
3. Re-test RET005 and COGS_DIRECT
4. Apply Priority 2 fixes (denormalize COGS)
5. Wait for pre-agg builds
6. Re-test MM001, GMROI001, MM001_COMP
7. Document Priority 3 (LIFE004) as known limitation

---

**Analysis complete**: 2026-01-18
**Next step**: Apply Priority 1 fixes (lightweight monthly pre-aggs)
