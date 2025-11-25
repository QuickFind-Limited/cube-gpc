# Comprehensive Dimension Analysis Summary

**Date:** November 25, 2025
**Analysis:** Systematic review of ALL dimensions across ALL 18 cube YML files
**Purpose:** Identify hardcoded logic in dimensions (CASE statements, date intervals, COALESCE defaults)

---

## Executive Summary

**Total Cubes Analyzed:** 18
**Total Dimensions Found:** 207
**Dimensions with Hardcoded Logic:** 11 (before cleanup), 9 (after cleanup)

### Actions Taken:
1. ✅ Removed 2 anti-pattern dimensions (category_with_default, season_with_default)
2. ✅ Parameterized transaction_type filters in 4 virtual cubes
3. ✅ Documented remaining hardcoded logic as intentional business rules

---

## Dimensions with Hardcoded Logic (Final State)

### 1. b2c_customers Cube (3 dimensions)

#### `customer_tier`
- **Type:** CASE statement
- **Logic:** Hardcoded LTV thresholds
  - >= 500: 'VIP'
  - >= 200: 'Regular'
  - >= 100: 'Occasional'
  - else: 'New'
- **Recommendation:** **KEEP** - Standard RFM tier logic, business rule
- **Parameterization:** Not needed - tiers are business policy

#### `recency_bucket`
- **Type:** CASE + CURRENT_DATE + INTERVAL
- **Logic:** Dynamic recency calculation relative to today
  - >= CURRENT_DATE - 30 days: 'Active (30d)'
  - >= CURRENT_DATE - 90 days: 'Recent (90d)'
  - >= CURRENT_DATE - 180 days: 'Lapsed (180d)'
  - else: 'Dormant (180d+)'
- **Recommendation:** **KEEP** - RFM recency must be relative to "now"
- **Parameterization:** Not needed - dynamic by design

#### `purchase_frequency_bucket`
- **Type:** CASE statement
- **Logic:** Hardcoded frequency buckets
  - = 1: '1x'
  - = 2: '2x'
  - = 3: '3x'
  - else: '4+'
- **Recommendation:** **KEEP** - Standard bucketing for analysis
- **Parameterization:** Not needed - business convention

---

### 2. fulfillments Cube (1 dimension)

#### `status_name`
- **Type:** CASE statement
- **Logic:** Status code to human-readable mapping
  - 'A': 'Pending'
  - 'B': 'Picked'
  - 'C': 'Shipped'
  - else: 'Unknown'
- **Recommendation:** **KEEP** - UI convenience dimension
- **Parameterization:** Not needed - exposes raw `status` dimension alongside

---

### 3. inventory Cube (1 dimension)

#### `stock_status`
- **Type:** CASE statement
- **Logic:** Quantity-based status
  - > 0: 'In Stock'
  - = 0: 'Zero Stock'
  - < 0: 'Backorder'
- **Recommendation:** **KEEP** - Logical derived dimension
- **Parameterization:** Not needed - users can filter by raw `quantity` dimension

---

### 4. items Cube (1 dimension)

#### `has_dimensions`
- **Type:** CASE statement
- **Logic:** NULL check on category
  - category IS NOT NULL: 'Yes'
  - else: 'No'
- **Recommendation:** **KEEP** - Data quality indicator
- **Parameterization:** Not needed - users can filter by `category IS NOT NULL`

**REMOVED (2 dimensions):**
- ❌ `category_with_default` - COALESCE('Uncategorized') - **DELETED** - hides data quality
- ❌ `season_with_default` - COALESCE('No Season') - **DELETED** - hides data quality

---

### 5. locations Cube (3 dimensions)

#### `channel_type`
- **Type:** Complex CASE statement
- **Logic:** Location name pattern matching to assign channels
  - D2C (default for NULL or Bleckmann)
  - RETAIL (store locations like Dundrum, Mahon Point)
  - B2B_WHOLESALE (trade customers)
  - PARTNER (John Lewis, Arnotts, Avoca)
  - EVENTS (pop-up locations)
  - OTHER (fallback)
- **Recommendation:** **KEEP** - Critical business dimension
- **Parameterization:** Not needed - complex business rules

#### `location_type`
- **Type:** Complex CASE statement
- **Logic:** Location name to type mapping
  - RETAIL, FULFILLMENT, WHOLESALE, B2B_PARTNER, MARKETPLACE, RETURNS_QC, EVENTS, HQ_ADMIN, SOURCING, OTHER
- **Recommendation:** **KEEP** - Operational classification
- **Parameterization:** Not needed - business taxonomy

#### `region`
- **Type:** CASE statement
- **Logic:** Location name to geographic region
  - IRELAND, UK, EU, GLOBAL
- **Recommendation:** **KEEP** - Geographic classification
- **Parameterization:** Not needed - standard geography

---

### 6. transactions Cube (1 dimension)

#### `is_partner_order`
- **Type:** CASE statement
- **Logic:** Partner detection
  - custbody_pwks_remote_order_source = 'John Lewis': 'Yes'
  - else: 'No'
- **Recommendation:** **KEEP** - UI convenience dimension
- **Parameterization:** Not needed - exposes raw `remote_order_source` alongside

---

## Dimensions That Were Parameterized

### Transaction Type (4 cubes)

**Previous State:** Hardcoded `WHERE t.type IN (...)` filters in cube SQL
**New State:** `transaction_type` exposed as queryable dimension

| Cube | Previous Filter | Now Parameterized |
|------|----------------|-------------------|
| `cross_sell` | `WHERE t.type IN ('CustInvc', 'CashSale')` | ✅ `transaction_type` dimension |
| `order_baskets` | `WHERE t.type IN ('CustInvc', 'CashSale')` | ✅ `type` dimension |
| `sell_through` | `WHERE t.type IN ('CustInvc', 'CashSale')` | ✅ `transaction_type` dimension |
| `b2c_customers` | `WHERE t.type = 'SalesOrd'` | ✅ `transaction_type` dimension |

**Benefit:** Users can now slice by transaction type for flexible analysis
**Migration:** SKILL file applies old defaults as filters for backwards compatibility

---

## Summary: What Should Stay Hardcoded vs Parameterized

### ✅ KEEP HARDCODED (9 dimensions):

**Business Logic Buckets/Tiers:**
- `b2c_customers.customer_tier` - LTV thresholds (500/200/100)
- `b2c_customers.purchase_frequency_bucket` - Frequency buckets (1x/2x/3x/4+)

**Dynamic/Calculated Dimensions:**
- `b2c_customers.recency_bucket` - CURRENT_DATE - INTERVAL (30d/90d/180d)

**Status Mappings:**
- `fulfillments.status_name` - Status code to name (A/B/C → Pending/Picked/Shipped)
- `inventory.stock_status` - Quantity to status (>0/=0/<0)

**Classification Dimensions:**
- `locations.channel_type` - Location name to channel
- `locations.location_type` - Location name to type
- `locations.region` - Location name to region

**Data Quality Indicators:**
- `items.has_dimensions` - Category NULL check
- `transactions.is_partner_order` - Partner detection

### ✅ PARAMETERIZED (4 dimensions):

**Filters → Dimensions:**
- `cross_sell.transaction_type` (was WHERE filter)
- `order_baskets.type` (was WHERE filter)
- `sell_through.transaction_type` (was WHERE filter)
- `b2c_customers.transaction_type` (was WHERE filter)

### ❌ REMOVED (2 dimensions):

**Anti-Patterns:**
- `items.category_with_default` - COALESCE('Uncategorized') - hides missing data
- `items.season_with_default` - COALESCE('No Season') - hides missing data

---

## Guidelines for Future Dimensions

### When to Keep Logic Hardcoded:

1. **Business Rules** - Tiers, thresholds, buckets defined by business policy
2. **Dynamic Calculations** - Logic that must be relative to "now" (CURRENT_DATE)
3. **Status Mappings** - Code-to-name translations for UX
4. **Classification Logic** - Complex pattern matching for categorization
5. **Data Quality Indicators** - Derived dimensions showing data completeness

### When to Parameterize:

1. **Filters** - WHERE clauses that limit data scope (transaction_type example)
2. **User Preferences** - Anything users might want to slice/filter differently
3. **Analysis Scenarios** - Values that enable different analytical perspectives
4. **No Data Integrity Risk** - Removal won't cause double-counting or data errors

### Anti-Patterns to Avoid:

1. **COALESCE with Fake Defaults** - Don't replace NULL with 'Uncategorized', 'Unknown', etc.
2. **Hidden Filters** - Filters belong in queries, not baked into dimensions
3. **Magic Numbers without Business Context** - Document why thresholds exist
4. **Inflexible Bucketing** - If users might want different buckets, expose raw value

---

## Files Modified

### Cube YML Files:
- `model/cubes/b2c_customers.yml` - Added transaction_type dimension
- `model/cubes/cross_sell.yml` - Added transaction_type dimension
- `model/cubes/order_baskets.yml` - Already had type dimension
- `model/cubes/sell_through.yml` - Added transaction_type dimension
- `model/cubes/items.yml` - Removed category_with_default, season_with_default

### Documentation:
- `HARDCODED_LOGIC_DOCUMENTATION.md` - Comprehensive migration guide
- `DIMENSION_ANALYSIS_SUMMARY.md` - This file

### SKILL File:
- `backend/SKILL_CUBE_REST_API-v22.md` - Added transaction_type and date range defaults

---

## Related Documentation

- **Migration Guide:** `/home/produser/cube-gpc/HARDCODED_LOGIC_DOCUMENTATION.md`
- **Dimension Analysis:** `/tmp/dimension_analysis.txt` (raw output)
- **SKILL File:** `/home/produser/GymPlusCoffee-Preview/backend/SKILL_CUBE_REST_API-v22.md`

---

## Conclusion

After systematic analysis of all 207 dimensions across 18 cubes:

- **11 dimensions** had hardcoded logic (CASE, INTERVAL, COALESCE)
- **2 dimensions** were anti-patterns and removed (COALESCE with fake defaults)
- **4 dimensions** were parameterized (transaction_type filters)
- **9 dimensions** remain with hardcoded logic (intentional business rules)

All remaining hardcoded logic serves legitimate purposes:
- Business policy (tiers, buckets)
- Dynamic calculations (recency)
- UX conveniences (status names)
- Classification rules (channel types, regions)

The cube model now properly separates:
- **Cube-level:** Business logic dimensions (stay hardcoded)
- **Query-level:** User preferences (parameterized as filters)
- **Client-level:** Presentation logic (NULL handling in client code)
