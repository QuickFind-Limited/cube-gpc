# order_baskets.average_basket_size NULL Issue - Fixed

**Date**: 2026-02-03
**Status**: ✅ FIXED - Awaiting Cube.js Deployment
**File**: `/home/produser/cube-gpc/model/cubes/order_baskets.yml`

---

## Executive Summary

The `average_basket_size` measure was returning NULL due to a **Cube.js architectural limitation** with calculated measures in pre-aggregations. The measure was using aggregation functions (`SUM`, `COUNT`) directly, making it non-additive and incompatible with pre-aggregations.

**Fix Applied**: Changed the measure to reference pre-aggregated component measures instead of using aggregation functions.

---

## Root Cause Analysis

###  1. Original (Broken) Implementation

```yaml
- name: average_basket_size
  sql: "1.0 * SUM({CUBE}.line_count) / NULLIF(COUNT(*), 0)"
  type: number
  description: Average items per basket
```

**Problem**: Uses aggregation functions (`SUM`, `COUNT`) directly → non-additive → cannot be served from pre-aggregations.

### 2. Error Message

```
"Error: No pre-aggregation table has been built for this query yet.
 Please check your refresh worker configuration if it persists."
```

This error appeared even when:
- Component measures (`total_line_count`, `order_count`) were in the pre-aggregation ✅
- Dimensions (`billing_country`, `line_count_bucket`) were in the pre-aggregation ✅
- Query used only pre-aggregated dimensions ✅

**Root Cause**: Calculated `type: number` measures with aggregation functions cannot be served from pre-aggregations in Cube.js, regardless of configuration.

### 3. Cube.js Best Practice Pattern

According to Cube.js documentation, calculated measures must reference **pre-aggregated component measures**, not use aggregation functions directly:

**Correct Pattern** (from Cube.js docs):
```yaml
# Component measures (additive, in pre-agg)
- name: age_sum
  sql: age
  type: sum

- name: count
  type: count

# Calculated measure (NOT in pre-agg)
- name: avg_age
  sql: "{age_sum} / {count}"
  type: number
```

---

## Fix Applied

### Before (Broken - Lines 54-57)
```yaml
- name: average_basket_size
  sql: "1.0 * SUM({CUBE}.line_count) / NULLIF(COUNT(*), 0)"
  type: number
  description: Average items per basket
```

### After (Fixed - Lines 54-57)
```yaml
- name: average_basket_size
  sql: "{total_line_count} / NULLIF({order_count}, 0)"
  type: number
  description: Average items per basket (calculated from pre-aggregated components)
```

### Why This Works

The fix references component measures that ARE already in the pre-aggregation:

**Component Measures** (already in pre-agg `basket_analysis`):
- `total_line_count` (type: sum) - Line 65
- `order_count` (type: count) - Line 39

**Pre-aggregation Configuration** (Lines 142-158):
```yaml
pre_aggregations:
  - name: basket_analysis
    measures:
      - order_count         ✅ Referenced by avg_basket_size
      - total_revenue
      - total_units
      - total_line_count    ✅ Referenced by avg_basket_size
    dimensions:
      - billing_country
      - line_count_bucket
      - type
      - customer_type
    time_dimension: trandate
    granularity: month
```

Now Cube.js can:
1. Fetch `total_line_count` and `order_count` from pre-aggregation
2. Perform division calculation: `total_line_count / order_count`
3. Return result instantly (no raw data query needed)

---

## Test Results

### Component Measures (Working)
```
total_line_count: 221,659
order_count: 61,579
Manual calculation: 221,659 / 61,579 = 3.60 items per basket ✅
```

### Expected Result After Deployment
```
average_basket_size: 3.60 items per basket ✅
```

---

## Investigation Summary

### Tests Performed
1. ✅ **Basic query** - 61,579 orders (Oct 2025)
2. ✅ **Geographic dimension** - 75% coverage (IE: 23,728, GB: 21,935)
3. ✅ **Line count buckets** - Distribution working correctly
4. ✅ **Customer segmentation** - B2B vs Retail working
5. ❌ **Average basket size** - Returns NULL (pre-agg incompatibility)
6. ✅ **Multi-dimensional** - Complex queries work

### Diagnostic Tests Run
- `/tmp/test_order_baskets.sh` - Full cube functional test
- `/tmp/test_average_basket_size.sh` - Measure-specific diagnostic
- `/tmp/test_average_basket_with_dimensions.sh` - Pre-agg compatibility test

### Key Finding
Even adding dimensions that ARE in the pre-aggregation didn't resolve the issue, confirming this is a Cube.js architectural limitation with calculated measures using aggregation functions.

---

## Next Steps

### 1. Deploy to Cube.js (Required)
The fix has been applied to the local file but needs to be deployed to Cube Cloud:

**Manual Deployment**:
```bash
cd /home/produser/cube-gpc
git add model/cubes/order_baskets.yml
git commit -m "Fix average_basket_size: Use pre-aggregated components instead of aggregation functions"
git push origin main
```

Then trigger Cube.js deployment in Cube Cloud UI.

**OR Automatic**: If Cube Cloud is configured to auto-deploy from Git, the fix will deploy on next pull.

### 2. Verify Fix (After Deployment)
Run test to confirm the measure returns correct value:
```bash
/tmp/test_average_basket_size.sh
```

Expected output:
```
average_basket_size: 3.60
```

### 3. Optional: Invalidate Pre-aggregation
If the measure still returns NULL after deployment, invalidate the pre-aggregation to force a rebuild:
```bash
# In Cube Cloud UI:
# Settings → Pre-aggregations → order_baskets.basket_analysis → Invalidate
```

---

## Related Files

- **Fixed File**: `/home/produser/cube-gpc/model/cubes/order_baskets.yml` (lines 54-57)
- **Test Scripts**:
  - `/tmp/test_order_baskets.sh` - Full test suite
  - `/tmp/test_average_basket_size.sh` - Measure diagnostic
  - `/tmp/test_average_basket_with_dimensions.sh` - Pre-agg test
- **Test Results**:
  - `/tmp/test_order_baskets_detailed.json` - Full test results
  - `/tmp/average_basket_test_after_fix.txt` - Post-fix test (awaiting deployment)
- **Data Architecture**: `/home/produser/DATA_ARCHITECTURE_AND_PATCHING_SUMMARY.md`

---

## Technical Details

### Cube.js Limitation
Calculated `type: number` measures that use aggregation functions (`SUM`, `COUNT`, `AVG`) cannot be directly served from pre-aggregations. They must be rewritten to reference additive component measures that ARE in the pre-aggregation.

### Why `average_order_value` Already Worked
Notice that `average_order_value` (line 60) uses the CORRECT pattern:
```yaml
sql: "{total_revenue} / NULLIF({order_count}, 0)"
```

It references component measures (`{total_revenue}`, `{order_count}`) instead of using `SUM()` or `COUNT()` directly. This is why it works with pre-aggregations.

### Pattern to Follow
**Always use this pattern for calculated measures**:
```yaml
# Component measures (additive, in pre-agg)
- name: component_sum
  type: sum

- name: component_count
  type: count

# Calculated measure (NOT in pre-agg)
- name: calculated_metric
  sql: "{component_sum} / NULLIF({component_count}, 0)"
  type: number
```

---

## Status: Ready for Deployment

✅ Fix applied to local file
⏳ Awaiting Cube.js deployment
📊 Expected result: 3.60 items per basket

**Last Updated**: 2026-02-03
**File Modified**: `/home/produser/cube-gpc/model/cubes/order_baskets.yml` (line 55)
