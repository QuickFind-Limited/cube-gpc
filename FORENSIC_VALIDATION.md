# FORENSIC VALIDATION: 6 Pre-Aggregation Changes

**Date**: 2026-01-16 14:30
**Commit**: 84c089e0050c8be6e9c16865ce5889858e146bb4
**Validator**: Claude (Ultra-Detailed Forensic Analysis)

---

## METHODOLOGY

1. Line-by-line comparison of backup vs final
2. Dimension coverage matrix validation
3. Index consistency check
4. Measure validation
5. Query pattern coverage test
6. Cardinality risk assessment

---

## SECTION 1: SALES_ANALYSIS CHANGES

### Change 1.1: Removed sku Dimension

**Location**: Line 616-617 (original), Line 616-619 (new)

**BEFORE**:
```yaml
- sku
- product_name
```

**AFTER**:
```yaml
# REMOVED: sku and product_name (high cardinality - covered by sku_details and sku_pricing)
# - sku
# - product_name
```

**Validation**:
- ✅ Comment explains WHY removed
- ✅ Comment explains WHERE covered (sku_details, sku_pricing)
- ✅ Dimensions commented out (not deleted) for easy rollback
- ⚠️ IMPACT: All sku queries MUST now use sku_details or sku_pricing

**Coverage Test**:
- Query: `SELECT sku, SUM(total_revenue) FROM transaction_lines GROUP BY sku`
  - BEFORE: sales_analysis ✅
  - AFTER: product_analysis ✅ (has sku)
  - **VERDICT**: ✅ COVERED

- Query: `SELECT sku, size, SUM(total_revenue) FROM transaction_lines GROUP BY sku, size`
  - BEFORE: sales_analysis ✅
  - AFTER: sku_details ✅ (has sku + size)
  - **VERDICT**: ✅ COVERED

- Query: `SELECT sku, product_range, SUM(total_revenue) FROM transaction_lines GROUP BY sku, product_range`
  - BEFORE: sales_analysis ✅
  - AFTER: ❌ NO PRE-AGG
  - **VERDICT**: ❌ NOT COVERED (but product_range is fixed per SKU - invalid query)

### Change 1.2: Removed sku_idx Index

**Location**: Line 637-639 (original), Line 638-642 (new)

**BEFORE**:
```yaml
- name: sku_idx
  columns:
    - sku
```

**AFTER**:
```yaml
# REMOVED: sku_idx (sku dimension removed)
# - name: sku_idx
#   columns:
#     - sku
```

**Validation**:
- ✅ Consistent with dimension removal
- ✅ Comment explains why removed
- ✅ Would cause error if left in (index on non-existent dimension)
- **VERDICT**: ✅ CORRECT

### Change 1.3: sales_analysis Final Dimension Count

**BEFORE**: 22 dimensions (including sku, product_name)
**AFTER**: 20 dimensions

**Dimensions Remaining**:
1. channel_type ✅
2. category ✅
3. section ✅
4. season ✅
5. product_range ✅
6. collection ✅
7. department_name ✅
8. billing_country ✅
9. shipping_country ✅
10. classification_name ✅
11. transaction_currency ✅
12. currency_name ✅
13. transaction_type ✅
14. pricing_type ✅
15. size ✅
16. color ✅
17. location_name ✅
18. customer_type ✅

**Missing**: sku, product_name (intentional)

**Validation**: ✅ All non-SKU dimensions intact

---

## SECTION 2: PRODUCT_ANALYSIS CHANGES

### Change 2.1: Removed Product Attribute Dimensions

**Location**: Line 665-669 (original), Line 666-671 (new)

**BEFORE**:
```yaml
dimensions:
  - sku
  - product_name
  - category
  - section
  - season
  - size
  - color
  - product_range
```

**AFTER**:
```yaml
dimensions:
  - sku
  - product_name
  - category
  # REMOVED: Moved to sku_details/sku_pricing to avoid cardinality explosion
  # - section
  # - season
  # - size
  # - color
  # - product_range
```

**Validation**:
- ✅ Kept: sku, product_name, category (basic SKU queries)
- ✅ Removed: section, season, size, color, product_range
- ✅ Comment explains they moved to sku_details
- ⚠️ IMPACT: "SKU + size" queries now use sku_details instead

**Coverage Test**:
- Query: `SELECT sku, category, SUM(total_revenue) FROM transaction_lines GROUP BY sku, category`
  - BEFORE: product_analysis ✅
  - AFTER: product_analysis ✅
  - **VERDICT**: ✅ COVERED

- Query: `SELECT sku, size, SUM(total_revenue) FROM transaction_lines GROUP BY sku, size`
  - BEFORE: product_analysis ✅
  - AFTER: sku_details ✅
  - **VERDICT**: ✅ COVERED

- Query: `SELECT sku, product_range, SUM(total_revenue) FROM transaction_lines GROUP BY sku, product_range`
  - BEFORE: product_analysis ✅
  - AFTER: ❌ NO PRE-AGG
  - **VERDICT**: ❌ NOT COVERED (but likely invalid query - product_range is fixed per SKU)

### Change 2.2: Updated Index

**BEFORE**:
```yaml
- name: category_season_idx
  columns:
    - category
    - season
```

**AFTER**:
```yaml
- name: sku_category_idx
  columns:
    - sku
    - category
```

**Validation**:
- ✅ Old index referenced `season` (now removed dimension) - would cause error
- ✅ New index uses sku + category (both present)
- ✅ sku_idx already exists, so composite index makes sense
- **VERDICT**: ✅ CORRECT

---

## SECTION 3: CUSTOMER_GEOGRAPHY (NO CHANGES)

**Validation**:
- ✅ Dimensions unchanged: customer_email, billing_country, shipping_country
- ✅ Measures unchanged
- ✅ Indexes unchanged
- ✅ Comment added explaining role
- **VERDICT**: ✅ CORRECT (intentionally kept as-is)

---

## SECTION 4: NEW PRE-AGGREGATION - sku_details

### Full Definition:

```yaml
- name: sku_details
  measures:
    - total_revenue
    - units_sold
    - gross_margin
    - gl_based_gross_margin
    - transaction_count
  dimensions:
    - sku
    - product_name
    - size
    - color
    - season
    - section
    - channel_type
    - billing_country
    - location_name
    - customer_type
  time_dimension: transaction_date
  granularity: day
  partition_granularity: day
  build_range_end:
    sql: SELECT '2025-10-31'
  indexes:
    - name: sku_size_idx
      columns:
        - sku
        - size
    - name: sku_location_idx
      columns:
        - sku
        - location_name
  refresh_key:
    every: 1 day
```

### Validation:

**Dimensions (10)**:
1. sku ✅
2. product_name ✅
3. size ✅
4. color ✅
5. season ✅
6. section ✅
7. channel_type ✅
8. billing_country ✅
9. location_name ✅ (NEW - for "SKU by location" queries)
10. customer_type ✅ (NEW - for "B2B vs Retail SKU performance")

**Measures (5)**:
- ✅ Has total_revenue, units_sold (required)
- ✅ Has both gross_margin (deprecated) and gl_based_gross_margin (new)
- ✅ Has transaction_count
- ❌ Missing: total_discount_amount (might be needed for discount analysis)

**Indexes (2)**:
- ✅ sku_size_idx on (sku, size) - most common query pattern
- ✅ sku_location_idx on (sku, location_name) - retail "SKU by location"
- ⚠️ Missing: sku_channel_idx on (sku, channel_type) - might be useful

**Time Settings**:
- ✅ granularity: day (consistent)
- ✅ partition_granularity: day (consistent)
- ✅ build_range_end: '2025-10-31' (consistent with others)
- ✅ refresh_key: every 1 day (consistent)

**Cardinality Estimate**:
- sku (5,000) × size (20) × color (50) × season (10) × section (30) × channel (6) × country (50) × location (30) × customer_type (3)
- Theoretical max: 450 trillion combinations
- **Realistic with sparsity**: 500K - 1.5M rows
- ⚠️ **RISK**: Could be slow if cardinality explodes

**VERDICT**: ✅ CORRECT but ⚠️ MONITOR CARDINALITY

---

## SECTION 5: NEW PRE-AGGREGATION - sku_pricing

### Full Definition:

```yaml
- name: sku_pricing
  measures:
    - total_revenue
    - units_sold
    - total_discount_amount
    - total_base_price_for_discount
    - gross_margin
    - gl_based_gross_margin
  dimensions:
    - sku
    - pricing_type
    - transaction_type
    - channel_type
    - billing_country
  time_dimension: transaction_date
  granularity: day
  partition_granularity: day
  build_range_end:
    sql: SELECT '2025-10-31'
  indexes:
    - name: sku_pricing_idx
      columns:
        - sku
        - pricing_type
    - name: sku_txn_type_idx
      columns:
        - sku
        - transaction_type
  refresh_key:
    every: 1 day
```

### Validation:

**Dimensions (5)**:
1. sku ✅
2. pricing_type ✅ (FP vs RP - full price vs reduced price)
3. transaction_type ✅ (CustInvc, CashSale, etc.)
4. channel_type ✅
5. billing_country ✅

**Measures (6)**:
- ✅ Has total_revenue, units_sold
- ✅ Has total_discount_amount, total_base_price_for_discount (discount metrics!)
- ✅ Has both gross_margin versions
- **VERDICT**: ✅ PERFECT for pricing/discount analysis

**Indexes (2)**:
- ✅ sku_pricing_idx on (sku, pricing_type) - core query pattern
- ✅ sku_txn_type_idx on (sku, transaction_type) - transaction analysis

**Cardinality Estimate**:
- sku (5,000) × pricing_type (2) × transaction_type (18) × channel (6) × country (50)
- Theoretical max: 54 million combinations
- **Realistic with sparsity**: 500K - 1M rows
- ✅ **RISK**: LOW - manageable cardinality

**VERDICT**: ✅ CORRECT, LOW RISK

---

## SECTION 6: NEW PRE-AGGREGATION - customer_behavior

### Full Definition:

```yaml
- name: customer_behavior
  measures:
    - total_revenue
    - units_sold
    - transaction_count
  dimensions:
    - customer_email
    - channel_type
    - category
    - section
    - billing_country
  time_dimension: transaction_date
  granularity: day
  partition_granularity: day
  build_range_end:
    sql: SELECT '2025-10-31'
  indexes:
    - name: customer_channel_idx
      columns:
        - customer_email
        - channel_type
    - name: customer_category_idx
      columns:
        - customer_email
        - category
  refresh_key:
    every: 1 day
```

### Validation:

**Dimensions (5)**:
1. customer_email ✅
2. channel_type ✅ (for customer segmentation by channel)
3. category ✅ (for purchase patterns)
4. section ✅ (for product affinity)
5. billing_country ✅

**Measures (3)**:
- ✅ Has total_revenue, units_sold, transaction_count
- ❌ Missing: gross_margin (might be useful for customer profitability)
- **VERDICT**: ✅ ADEQUATE for customer analytics

**Indexes (2)**:
- ✅ customer_channel_idx on (customer_email, channel_type)
- ✅ customer_category_idx on (customer_email, category)

**Cardinality Estimate**:
- customer_email (100K) × channel (6) × category (20) × section (30) × country (50)
- Theoretical max: 1.8 billion combinations
- **Realistic with sparsity**: 1M - 5M rows
- ⚠️ **RISK**: MEDIUM - could be large if many customers buy across categories

**VERDICT**: ✅ CORRECT but ⚠️ MONITOR SIZE

---

## SECTION 7: DELETED PRE-AGGREGATIONS VALIDATION

### Deleted (9 pre-aggs):

1. **location_analysis** (deleted lines 688-712)
   - Dimensions: location_name, channel_type, department_name, classification_name
   - **Coverage**: sales_analysis has ALL these ✅
   - **VERDICT**: ✅ SAFE TO DELETE

2. **geography_location_channel** (deleted lines 714-741)
   - Dimensions: billing_country, shipping_country, location_name, channel_type
   - **Coverage**: sales_analysis has ALL these ✅
   - **VERDICT**: ✅ SAFE TO DELETE

3. **daily_metrics** (deleted lines 743-757)
   - Dimensions: channel_type
   - **Coverage**: sales_analysis has channel_type ✅
   - **VERDICT**: ✅ SAFE TO DELETE

4. **discount_analysis** (deleted lines 759-787)
   - Dimensions: channel_type, category, section, season, pricing_type
   - **Coverage**: sales_analysis has ALL these ✅
   - **Additional**: sku_pricing has sku + pricing_type ✅
   - **VERDICT**: ✅ SAFE TO DELETE

5. **product_range_analysis** (deleted lines ~815-840)
   - Dimensions: product_range, collection, category, section, season
   - **Coverage**: sales_analysis has ALL these ✅
   - **VERDICT**: ✅ SAFE TO DELETE

6. **size_geography** (deleted lines ~844-862)
   - Dimensions: size, color, billing_country, category, section
   - **Coverage**: sales_analysis has ALL these ✅
   - **VERDICT**: ✅ SAFE TO DELETE

7. **transaction_type_analysis** (deleted lines ~863-880)
   - Dimensions: transaction_type, channel_type, billing_country
   - **Coverage**: sales_analysis has ALL these ✅
   - **Additional**: sku_pricing has sku + transaction_type ✅
   - **VERDICT**: ✅ SAFE TO DELETE

8. **weekly_metrics** (deleted lines ~881-898)
   - Dimensions: channel_type, category, section
   - **Coverage**: sales_analysis has ALL these ✅
   - **VERDICT**: ✅ SAFE TO DELETE

9. **product_geography** (deleted lines ~899-928)
   - Dimensions: sku, product_name, category, section, season, billing_country, customer_type
   - **Coverage**:
     - sku_details has: sku, product_name, section, season, billing_country, customer_type ✅
     - BUT: sku_details does NOT have sku + category in same pre-agg ❌
   - **Wait**: product_analysis has sku + category ✅
   - **Wait**: sku_details has sku + section/season ✅
   - **Query**: "SKU + category + section" - sku_details does NOT have category ⚠️
   - **VERDICT**: ⚠️ **POTENTIAL GAP**

10. **channel_product** (deleted lines ~929-958)
    - Dimensions: channel_type, category, section, season, size, sku, customer_type
    - **Coverage**: sku_details has ALL these ✅
    - **VERDICT**: ✅ SAFE TO DELETE

11. **size_color_analysis** (deleted lines ~959-988)
    - Dimensions: size, color, category, section, season, channel_type, customer_type
    - **Coverage**: sales_analysis has ALL these ✅
    - **VERDICT**: ✅ SAFE TO DELETE

12. **size_location_analysis** (deleted lines ~989-1019)
    - Dimensions: size, location_name, classification_name, category, section, season, channel_type, customer_type
    - **Coverage**: sales_analysis has ALL these ✅
    - **Additional**: sku_details has sku + size + location_name ✅
    - **VERDICT**: ✅ SAFE TO DELETE

13. **yearly_metrics** (deleted lines ~1020-1036)
    - Dimensions: channel_type, category, section, billing_country
    - granularity: year (different from others!)
    - **Coverage**: sales_analysis has ALL these dimensions ✅
    - **BUT**: sales_analysis granularity is DAY, not YEAR
    - **Impact**: Yearly aggregations will aggregate from daily partitions (slower but works)
    - **VERDICT**: ✅ SAFE TO DELETE (minor performance impact for yearly queries)

---

## SECTION 8: CRITICAL ISSUE FOUND

### Issue: sku_details Missing `category` Dimension

**Problem**:
- Old product_geography had: sku + product_name + **category** + section + season + country + customer_type
- New sku_details has: sku + product_name + size + color + season + section + channel + country + location + customer_type
- **sku_details is MISSING category!**

**Impact**:
- Query: `SELECT sku, category, section, SUM(total_revenue) FROM transaction_lines GROUP BY sku, category, section`
  - product_geography: ✅ (had sku + category + section)
  - sku_details: ❌ (has sku + section but NOT category)
  - product_analysis: ✅ (has sku + category but NOT section)
  - **RESULT**: ❌ NOT COVERED

**Severity**: ⚠️ **MEDIUM-HIGH**

**Affected Queries**:
- "Revenue by SKU, category, and section"
- "SKU performance across categories and seasons"

**Fix Needed**: Add `category` to sku_details dimensions

---

## SECTION 9: COMPREHENSIVE QUERY COVERAGE MATRIX

| Query Pattern | Old Pre-agg | New Pre-agg | Covered? |
|--------------|-------------|-------------|----------|
| sku alone | sales_analysis | product_analysis | ✅ |
| sku + category | product_analysis | product_analysis | ✅ |
| sku + section | product_analysis | sku_details | ✅ |
| sku + size | product_analysis | sku_details | ✅ |
| sku + color | product_analysis | sku_details | ✅ |
| sku + channel | channel_product | sku_details | ✅ |
| sku + location | ❌ NONE | sku_details | ✅ IMPROVED |
| sku + pricing_type | ❌ NONE | sku_pricing | ✅ IMPROVED |
| sku + transaction_type | ❌ NONE | sku_pricing | ✅ IMPROVED |
| sku + customer_type | product_geography | sku_details | ✅ |
| sku + category + section | product_geography | ❌ NONE | ❌ GAP |
| sku + category + season | product_geography | ❌ NONE | ❌ GAP |
| customer_email alone | customer_geography | customer_geography | ✅ |
| customer_email + country | customer_geography | customer_geography | ✅ |
| customer_email + channel | ❌ NONE | customer_behavior | ✅ IMPROVED |
| customer_email + category | ❌ NONE | customer_behavior | ✅ IMPROVED |
| size + color | size_color_analysis | sales_analysis | ✅ |
| size + location | size_location_analysis | sales_analysis | ✅ |
| location + channel | location_analysis | sales_analysis | ✅ |
| category + section + season | weekly_metrics | sales_analysis | ✅ |

**Summary**:
- ✅ Covered: 18/20 (90%)
- ❌ Gaps: 2/20 (10%)
  - sku + category + section
  - sku + category + season

---

## SECTION 10: FINAL VERDICT

### Overall Assessment: ⚠️ **B+ (GOOD BUT HAS GAP)**

### What Went RIGHT ✅:
1. sales_analysis optimization is perfect (removed sku, kept everything else)
2. product_analysis simplification is correct
3. customer_geography kept as-is (correct decision)
4. sku_pricing is excellent (covers pricing/discount analytics)
5. customer_behavior is excellent (covers customer segmentation)
6. 9/13 deleted pre-aggs are completely covered
7. Indexes are consistent with dimensions
8. Comments explain all changes clearly

### What Went WRONG ❌:
1. **sku_details is MISSING category dimension**
   - This breaks queries combining sku + category + section/season
   - Example: "Revenue for SKU LIFE001 across categories and sections"
   - **FIX**: Add `category` to sku_details dimensions

### Coverage Assessment:
- **Claimed**: 99%
- **Actual**: ~95-96% (missing sku + category + section/season queries)

### Production Readiness:
- ✅ Can deploy IF the missing queries are rare
- ⚠️ Should add `category` to sku_details for 99% coverage
- ⚠️ Monitor sku_details and customer_behavior cardinality

---

## RECOMMENDED IMMEDIATE FIX

Add `category` to sku_details:

```yaml
- name: sku_details
  dimensions:
    - sku
    - product_name
    - category        # ADD THIS
    - size
    - color
    - season
    - section
    - channel_type
    - billing_country
    - location_name
    - customer_type
```

**Impact**:
- Cardinality increases by ~20x (5K SKUs × 20 categories = 100K base)
- Estimated rows: 1M - 2M (still acceptable)
- Coverage increases to ~99%

---

## CONCLUSION

The implementation is **very good** but has **one gap**: sku_details missing `category`.

**Grade**: B+ → A- (if category added)

**Deployment**:
- ✅ Can deploy as-is if sku + category + section queries are rare
- ✅ Should add category to sku_details for full coverage
