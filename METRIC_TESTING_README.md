# Systematic Metrics Performance Testing

**Created**: January 18, 2026
**Purpose**: Identify and resolve timeout issues in Cube.js metrics
**Status**: Ready for execution - awaiting API credentials

---

## Overview

Following the discovery that `revenue_analysis_monthly` timeouts were caused by too many dimensions (15), we're now systematically testing all HIGH RISK metrics to identify similar issues.

### Testing Strategy

1. **HIGH RISK** metrics (current phase) - Known issues with JOINs, complex calculations, or high cardinality
2. **MEDIUM RISK** metrics - Moderate complexity
3. **LOW RISK** metrics - Simple aggregations for validation

---

## High-Risk Metrics Being Tested

### 1. MM001 - Gross Margin % (GL-based COGS)
- **Measure**: `transaction_lines.gl_based_gross_margin_pct`
- **Risk Factor**: Requires JOIN to `transaction_accounting_lines_cogs` (one-to-many)
- **Known Issue**: JOIN explosion potential
- **Expected Behavior**: May timeout on 12-month queries due to cartesian product
- **Query**:
  ```json
  {
    "measures": ["transaction_lines.gl_based_gross_margin_pct"],
    "dimensions": ["transaction_lines.channel_type"],
    "timeDimensions": [{
      "dimension": "transaction_lines.transaction_date",
      "granularity": "month",
      "dateRange": ["2024-11-01", "2025-10-31"]
    }]
  }
  ```

### 2. GMROI001 - Gross Margin Return on Investment
- **Measure**: `transaction_lines.gl_based_gmroi`
- **Risk Factor**: Same JOIN issue as MM001
- **Formula**: `(Revenue - GL COGS) / GL COGS`
- **Expected Behavior**: May timeout on 12-month queries

### 3. LIFE004 - Sales Velocity (units per week)
- **Measure**: `transaction_lines.units_per_week`
- **Risk Factor**: Complex calculated measure with MIN/MAX date aggregation
- **Formula**: `SUM(units) / ((MAX(date) - MIN(date)) / 7.0 + 1)`
- **Known Issue**: Cannot be pre-aggregated (uses window functions)
- **Expected Behavior**: May timeout due to query-time calculation

### 4. RET004 - Return Rate (transaction level)
- **Measures**: `transactions.customer_credits_aligned`, `transactions.revenue_transaction_count_aligned`
- **Risk Factor**: Time-aligned filters
- **Expected Behavior**: Should work (has monthly pre-agg)

### 5. RET005 - Return Rate % (line level)
- **Measure**: `transaction_lines.return_rate`
- **Risk Factor**: Calculated measure at query time
- **Formula**: `100.0 * units_returned / (units_sold + units_returned)`
- **Expected Behavior**: Should work (component measures in pre-agg)

### 6. FD002 - Fulfillments per Order
- **Measure**: `fulfillments.fulfillments_per_order`
- **Risk Factor**: Calculated measure
- **Formula**: `fulfillment_count / unique_orders`
- **Expected Behavior**: Should work (new monthly pre-agg added)

### 7. MM001_COMP - Revenue + GL COGS (components)
- **Measures**: `transaction_lines.total_revenue`, `transaction_lines.gl_based_cogs`
- **Purpose**: Isolate JOIN issue - test if components work separately
- **Expected Behavior**: May work if JOIN is the only issue

### 8. COGS_DIRECT - GL COGS from COGS cube directly
- **Measure**: `transaction_accounting_lines_cogs.gl_cogs`
- **Purpose**: Test if COGS cube itself has performance issues
- **Risk Factor**: COGS cube has **18 dimensions** in pre-aggregation (even worse than transaction_lines)
- **Expected Behavior**: Likely to timeout

---

## How to Run Tests

### Prerequisites
- Cube Cloud API credentials
- Python 3.6+ installed

### Option 1: Environment Variables
```bash
export CUBE_API_URL="https://aquamarine-ibex.gcp-europe-west1.cubecloudapp.dev/cubejs-api/v1"
export CUBE_API_TOKEN="your-api-token-here"
cd /home/produser/cube-gpc
python3 test_metrics.py
```

### Option 2: Command-Line Arguments
```bash
cd /home/produser/cube-gpc
python3 test_metrics.py \
  --url "https://aquamarine-ibex.gcp-europe-west1.cubecloudapp.dev/cubejs-api/v1" \
  --token "your-api-token-here"
```

### Option 3: Custom Timeout and Output
```bash
python3 test_metrics.py \
  --url "your-url" \
  --token "your-token" \
  --timeout 45 \
  --output my_results.json
```

---

## Understanding Results

### Success Indicators
- ✓ PASSED (< 10s) - **Excellent** performance
- ✓ PASSED (10-20s) - **Good** performance
- ✓ PASSED (20-30s) - **Acceptable** but monitor

### Failure Indicators
- ❌ TIMEOUT (30s+) - **Critical** - needs optimization
- ❌ FAILED (< 30s) - **Error** - check error message
- ❌ ERROR - **Bug** - query syntax or API issue

### Output Files
- `test_results.json` - Detailed JSON results
- Console output - Real-time colored status

---

## Expected Failures and Root Causes

### JOIN Explosion (MM001, GMROI001, MM001_COMP)
**Root Cause**: `transaction_accounting_lines_cogs` is one-to-many with `transaction_lines`
- Each transaction_line can have multiple GL COGS entries (freight, duty, product cost)
- 12-month query × JOIN = cartesian product

**Fix Options**:
1. **Denormalize** - Create view with COGS aggregated per transaction_line
2. **Component measures** - Query revenue and COGS separately, calculate ratio client-side
3. **Separate pre-agg** - Create COGS-specific fast pre-agg with fewer dimensions

### Too Many Dimensions (COGS_DIRECT)
**Root Cause**: `cogs_analysis` pre-agg has **18 dimensions**
- category, section, season, product_range, collection, department, billing_country, shipping_country, classification, currency, transaction_currency, sku, product_name, size, color, location, cogs_account, transaction_type
- 12 months × 18 dimensions = massive partition scan

**Fix**: Create `cogs_fast_monthly` with 4-6 dimensions (same as `revenue_monthly_fast`)

### Non-Additive Measures (LIFE004)
**Root Cause**: `units_per_week` uses MIN/MAX window functions
- Cannot be pre-aggregated
- Must be calculated at query time

**Fix**:
1. **Remove from cube** - Calculate client-side from `units_sold` and date range
2. **Component measures** - Store min_date, max_date, total_units separately

---

## Next Steps After Testing

### If All Tests Pass
- Document success
- Add weekly/monthly pre-aggs to remaining cubes
- Move to MEDIUM RISK testing

### If Tests Fail (Expected)
1. **Analyze failures** by root cause
2. **Apply fixes** from 7 options plan:
   - Option 1: Multi-Granularity Pre-Aggregation Strategy
   - Option 2: Denormalize GL-Based COGS Data
   - Option 3: Component Measure Strategy
   - Option 4: Separate High-Cardinality Pre-Aggs
   - Option 5: Optimize Existing Pre-Agg Dimension Lists
   - Option 6: Add Quarterly Pre-Aggregations
   - Option 7: Materialized Views for Complex Cubes
3. **Re-test** to verify fixes
4. **Document** solutions

---

## Test Results Template

```
Test ID: MM001
Status: TIMEOUT
Duration: 30.2s
Root Cause: JOIN explosion (transaction_accounting_lines_cogs one-to-many)
Fix Applied: Option 2 - Denormalized COGS into transaction_lines view
Retest Status: PASSED (3.4s)
```

---

## Files Created

1. **test_metrics.py** - Main Python test script
2. **test_high_risk_metrics.sh** - Bash alternative (less robust)
3. **METRIC_TESTING_README.md** - This file
4. **test_results.json** - Output from test runs (generated)

---

## Related Documentation

- [WEEKLY_MONTHLY_PREAGGS_ADDED.md](/home/produser/cube-gpc/WEEKLY_MONTHLY_PREAGGS_ADDED.md) - Pre-agg strategy documentation
- [NETSUITE_INVENTORY_CALCULATION_GUIDE.md](../backend/NETSUITE_INVENTORY_CALCULATION_GUIDE.md) - NetSuite data model research

---

**Status**: Ready for execution
**Awaiting**: API credentials from user
**Next**: Run tests → Analyze failures → Apply fixes → Re-test
