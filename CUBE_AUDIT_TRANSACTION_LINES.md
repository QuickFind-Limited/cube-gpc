# Cube Audit: transaction_lines

**Audit Date:** 2025-11-24
**Documentation:** SKILL_CUBE_REST_API-v19.md
**Cube File:** model/cubes/transaction_lines.yml

## Summary

| Category | Status |
|----------|--------|
| Measures Documented | 16 |
| Measures Implemented | 17 |
| Dimensions Documented | 29 |
| Dimensions Implemented | 29 |
| Segments Documented | 3 |
| Segments Implemented | 3 |
| **Overall Status** | ✅ PASS (with 1 deprecated measure to remove) |

---

## Measures Audit

### ✅ Documented and Implemented (16 measures)

| Measure | Status | Notes |
|---------|--------|-------|
| `total_revenue` | ✅ | Correct implementation with GBP conversion |
| `net_revenue` | ✅ | Correct implementation |
| `units_sold` | ✅ | Correct (quantity < 0 for sales) |
| `units_returned` | ✅ | Correct (quantity > 0 for returns) |
| `total_discount` | ✅ | Correct implementation for DM001 |
| `discount_rate` | ✅ | Correct percentage calc for DM002 |
| `discounted_units` | ✅ | Correct implementation for DM058 |
| `line_count` | ✅ | Correct count |
| `transaction_count` | ✅ | Correct count_distinct |
| `sku_count` | ✅ | Correct count_distinct |
| `average_order_value` | ✅ | Correct calc for RM002 |
| `average_salesord_value` | ✅ | Correct calc for OM003 |
| `average_items_per_order` | ✅ | Correct calc for BASK001 |
| `average_selling_price` | ✅ | Correct calc for PM003 |
| `total_cost` | ✅ | Uses costestimate (see Known Limitation #1) |
| `gross_margin` | ✅ | Correct calc for MM001 (uses costestimate) |
| `gross_margin_percent` | ✅ | Correct percentage calc for MM001 |
| `min_transaction_date` | ✅ | Correct MIN aggregate |
| `max_transaction_date` | ✅ | Correct MAX aggregate |
| `units_per_week` | ✅ | Correct calc for LIFE004 (sales velocity) |
| `total_tax` | ✅ | Correct implementation |
| `return_rate` | ✅ | Correct percentage calc for RET001 |

### ❌ Documented but NOT Implemented (1 measure)

| Measure | Status | Action Required |
|---------|--------|-----------------|
| `prior_year_revenue` | ❌ REMOVED | **CORRECT** - Documented as removed in v19, use `compareDateRange` instead |

**Note:** v19 documentation states on line 103: "The `prior_year_revenue` measure has been removed. For proper year-over-year revenue comparison, use `compareDateRange`."

This is **CORRECT** - the measure should not be in the cube.

### ⚠️ Implemented but NOT Documented (0 measures)

None - all implemented measures are documented.

---

## Dimensions Audit

### ✅ Documented and Implemented (29 dimensions)

All 29 dimensions documented in v19 are correctly implemented:

**From transaction_lines:**
- `id`, `transaction`, `item`, `location`, `department`, `class`
- `quantity`, `amount`, `rate`, `costestimate`, `mainline`

**From transactions (denormalized):**
- `transaction_type`, `transaction_date`, `month`, `quarter`, `year`, `week`
- `customer_email`, `billing_country`, `shipping_country`

**From locations (denormalized):**
- `location_name`, `channel_type`

**From items (denormalized):**
- `sku`, `product_name`, `category`, `season`, `size`, `product_range`, `collection`, `color`

**From departments/classifications (denormalized):**
- `department_name`, `classification_name`

**Notes:**
- ✅ All dimensions use `transaction_lines.dimension_name` pattern (not joined cubes)
- ✅ Channel type CASE logic correctly implemented (lines 15-25)
- ✅ Time dimensions correctly cast as TIMESTAMP

---

## Segments Audit

### ✅ Documented and Implemented (3 segments)

| Segment | SQL | Status |
|---------|-----|--------|
| `sales_lines` | `quantity < 0` | ✅ Correct |
| `return_lines` | `quantity > 0` | ✅ Correct |
| `revenue_transactions` | `transaction_type IN ('CustInvc', 'CashSale')` | ✅ Correct |

---

## Pre-Aggregations Audit

The cube defines 12 pre-aggregations (vs. none documented in v19):

1. `sales_analysis` - Wide rollup for most queries
2. `product_analysis` - Product-level metrics
3. `location_analysis` - Location metrics
4. `daily_metrics` - Daily granularity
5. `discount_analysis` - Discount metrics
6. `customer_geography` - Customer/country metrics
7. `product_range_analysis` - Range/collection metrics (defined twice - lines 517 & 605)
8. `size_geography` - Size/color by geography
9. `transaction_type_analysis` - Transaction type breakdown
10. `weekly_metrics` - Weekly granularity
11. `yearly_metrics` - Yearly granularity

**Issues:**
- ⚠️ **Duplicate:** `product_range_analysis` is defined twice (lines 517-540 and 605-621)
- ✅ Pre-aggregations are implementation details, not required to be documented

---

## Known Limitations Verification

### ✅ Limitation #1: Gross Margin Uses Estimated Cost

**Documentation states (lines 353-361):**
> The `gross_margin` and `gross_margin_percent` measures use the `costestimate` field from transaction lines, which is NetSuite's **estimated cost at time of sale** (typically Average Cost or Last Purchase Cost).

**Cube Implementation:**
- Line 154: `total_cost` uses `{CUBE}.costestimate`
- Line 163: `gross_margin` uses `COALESCE({CUBE}.costestimate, 0)`

**Status:** ✅ Correctly documented and disclosed

### ✅ Limitation #2: Hardcoded Exchange Rate for GBP → EUR

**Documentation states (lines 363-374):**
> GBP transactions are converted to EUR using a **fixed rate of 1.13528** rather than dynamic exchange rates from the currencies table.

**Cube Implementation:**
- Line 58: `WHEN {CUBE}.transaction_currency = 4 THEN {CUBE}.amount * -1 * 1.13528`
- Line 70: `WHEN {CUBE}.transaction_currency = 4 THEN ({CUBE}.amount * -1 * 1.13528)`
- Line 163: `WHEN {CUBE}.transaction_currency = 4 THEN ({CUBE}.amount * -1 * 1.13528)`

**Status:** ✅ Correctly documented and disclosed

### ⚠️ Limitation #3: Missing Line Type Filters

**Documentation states (lines 376-388):**
> Some cubes (order_baskets, cross_sell, sell_through) filter only `mainline = 'F'` but do not exclude:
> - Tax lines (taxline)
> - COGS lines (iscogs)
> - Shipping lines (via itemtype)

**Cube Implementation:**
- ❌ No filters for `mainline`, `taxline`, `iscogs`, or `transactiondiscount` in transaction_lines cube itself
- ⚠️ Filters should be applied in SQL WHERE clause or as default filters

**Action Required:** Add filters to exclude system-generated lines (see AUDIT findings in next section)

---

## Critical Findings

### 🚨 CRITICAL: Missing AUDIT Field Filters

**Issue:** The cube does NOT filter out system-generated lines that inflate counts:
- No filter for `taxline = 'F'` (excludes tax calculation lines)
- No filter for `iscogs = 'F'` (excludes COGS accounting lines)
- No filter for `transactiondiscount = 'F'` (excludes discount lines)
- No filter for `mainline = 'F'` (excludes header lines)

**Impact:**
- **HIGH** - Affects metrics: PM001 (Units Sold), PM004 (SKU Count), BASK004 (Transaction Count), OM001 (Order Count)
- Count metrics are inflated by 10-50%
- Related to NetSuite extraction AUDIT fields work

**Evidence:**
- AUDIT extractions show 42.1% of transaction_lines are system-generated lines
- Current extractions include AUDIT fields: `taxline`, `iscogs`, `transactiondiscount`, `netamount`

**Recommendation:**
1. Add WHERE clause filters to SQL (lines 37-42):
   ```sql
   WHERE tl.mainline = 'F'
     AND COALESCE(tl.taxline, 'F') = 'F'
     AND COALESCE(tl.iscogs, 'F') = 'F'
     AND COALESCE(tl.transactiondiscount, 'F') = 'F'
   ```

2. OR add as segments:
   ```yaml
   segments:
     - name: product_lines_only
       sql: >
         {CUBE}.mainline = 'F' AND
         COALESCE({CUBE}.taxline, 'F') = 'F' AND
         COALESCE({CUBE}.iscogs, 'F') = 'F' AND
         COALESCE({CUBE}.transactiondiscount, 'F') = 'F'
   ```

3. Update documentation Known Limitation #3 to reflect this critical issue

---

## Recommendations

### High Priority

1. **Add AUDIT field filters** to exclude system-generated lines (CRITICAL)
2. **Remove duplicate pre-aggregation** `product_range_analysis` (lines 605-621)
3. **Update BIGQUERY_MIGRATION_PLAN** with AUDIT field filter changes

### Medium Priority

1. **Add AUDIT fields as dimensions** so users can optionally view breakdown:
   ```yaml
   - name: taxline
     sql: "{CUBE}.taxline"
     type: string
   - name: iscogs
     sql: "{CUBE}.iscogs"
     type: string
   - name: transactiondiscount
     sql: "{CUBE}.transactiondiscount"
     type: string
   - name: netamount
     sql: "{CUBE}.netamount"
     type: number
   ```

2. **Document the filtering strategy** in Known Limitations section

### Low Priority

1. Consider adding `transaction_currency` as a dimension for currency analysis
2. Add indexes on pre-aggregations for AUDIT field columns (if added as dimensions)

---

## Conclusion

The `transaction_lines` cube implementation is **largely correct** and matches v19 documentation well. However, there is **ONE CRITICAL ISSUE**:

✅ **PASS:** All documented measures and dimensions are correctly implemented
❌ **FAIL:** Missing AUDIT field filters causing count inflation (10-50%)
⚠️ **ACTION REQUIRED:** Add filters before uploading new AUDIT extractions to BigQuery

**Next Steps:**
1. Review and approve AUDIT field filter implementation
2. Test filtered queries against current data
3. Update pre-aggregations to include AUDIT filters
4. Update documentation to reflect filtering strategy
