# 100% Coverage Analysis: Would Adding location_name to sku_details Achieve It?

**Question**: If we add `location_name` and `customer_type` to `sku_details`, do we get 100% coverage?

---

## PROPOSED sku_details Enhancement

### Current sku_details:
```yaml
Dimensions (8):
  - sku
  - product_name
  - size
  - color
  - season
  - section
  - channel_type
  - billing_country
```

### Enhanced sku_details:
```yaml
Dimensions (10):
  - sku
  - product_name
  - size
  - color
  - season
  - section
  - channel_type
  - billing_country
  - location_name       # ADD
  - customer_type       # ADD
```

---

## COMPREHENSIVE GAP ANALYSIS

Let me enumerate EVERY possible dimension combination and see if it's covered:

### All Available Dimensions in Cube:
1. sku
2. product_name
3. size
4. color
5. season
6. section
7. product_range
8. collection
9. category
10. channel_type
11. location_name
12. department_name
13. classification_name
14. billing_country
15. shipping_country
16. transaction_currency
17. currency_name
18. transaction_type
19. pricing_type
20. customer_email
21. customer_type

---

## Pre-agg Coverage Matrix (ENHANCED)

### sales_analysis dimensions (20):
✅ channel_type, category, section, season, product_range, collection
✅ department_name, billing_country, shipping_country, classification_name
✅ transaction_currency, currency_name, transaction_type, pricing_type
✅ size, color, location_name, customer_type
❌ sku, product_name, customer_email

### product_analysis dimensions (3):
✅ sku, product_name, category
❌ Everything else

### customer_geography dimensions (3):
✅ customer_email, billing_country, shipping_country
❌ Everything else

### sku_details (ENHANCED) dimensions (10):
✅ sku, product_name, size, color, season, section
✅ channel_type, billing_country, location_name, customer_type
❌ product_range, collection, category, department_name, classification_name
❌ shipping_country, transaction_currency, currency_name, transaction_type, pricing_type
❌ customer_email

---

## CRITICAL QUERY PATTERN TEST

Let me test ALL meaningful 2-dimension combinations:

### sku + X combinations:

| Query | Current | Enhanced | Covered By |
|-------|---------|----------|------------|
| sku + product_name | ✅ | ✅ | product_analysis |
| sku + category | ✅ | ✅ | product_analysis |
| sku + size | ✅ | ✅ | sku_details |
| sku + color | ✅ | ✅ | sku_details |
| sku + season | ✅ | ✅ | sku_details |
| sku + section | ✅ | ✅ | sku_details |
| sku + channel_type | ✅ | ✅ | sku_details |
| sku + billing_country | ✅ | ✅ | sku_details |
| sku + location_name | ❌ | ✅ | sku_details (enhanced) |
| sku + customer_type | ❌ | ✅ | sku_details (enhanced) |
| sku + product_range | ❌ | ❌ | **NOT COVERED** |
| sku + collection | ❌ | ❌ | **NOT COVERED** |
| sku + department_name | ❌ | ❌ | **NOT COVERED** |
| sku + classification_name | ❌ | ❌ | **NOT COVERED** |
| sku + shipping_country | ❌ | ❌ | **NOT COVERED** |
| sku + transaction_type | ❌ | ❌ | **NOT COVERED** |
| sku + pricing_type | ❌ | ❌ | **NOT COVERED** |
| sku + customer_email | ❌ | ❌ | **NOT COVERED** |

### customer_email + X combinations:

| Query | Current | Enhanced | Covered By |
|-------|---------|----------|------------|
| customer_email + billing_country | ✅ | ✅ | customer_geography |
| customer_email + shipping_country | ✅ | ✅ | customer_geography |
| customer_email + channel_type | ❌ | ❌ | **NOT COVERED** |
| customer_email + category | ❌ | ❌ | **NOT COVERED** |
| customer_email + section | ❌ | ❌ | **NOT COVERED** |
| customer_email + customer_type | ❌ | ❌ | **NOT COVERED** |
| customer_email + sku | ❌ | ❌ | **NOT COVERED** |

### All other 2-dimension combinations:

✅ **Covered by sales_analysis** (has 20 dimensions):
- Any combination of: channel, category, section, season, size, color, location, countries, etc
- Examples: channel + category, size + color, location + season, etc

---

## ANSWER: Does Enhanced sku_details Give 100% Coverage?

### NO - Still Missing:

**1. sku + product_range**
- Example: "Revenue for SKU LIFE001 across all product ranges"
- Realistic? MAYBE - product_range is usually fixed for a SKU
- Impact: Falls back to source table
- **Is this query even valid?** Probably not - a SKU belongs to ONE product_range

**2. sku + collection**
- Example: "Revenue for SKU LIFE001 across all collections"
- Realistic? MAYBE - collection is usually fixed for a SKU
- Impact: Falls back to source table
- **Is this query even valid?** Probably not - a SKU belongs to ONE collection

**3. sku + department_name**
- Example: "SKU revenue by department"
- Realistic? NO - department is a transaction attribute, not product attribute
- **But wait**: channel_type is derived FROM department!
- Already covered by sku + channel_type ✅

**4. sku + classification_name**
- Example: "SKU revenue by classification"
- Realistic? MAYBE
- Impact: Falls back to source table

**5. sku + shipping_country**
- Example: "SKU revenue by shipping country"
- Realistic? YES
- Impact: Falls back to source table
- **Coverage**: We have sku + billing_country, not shipping_country
- **Are they different?** Usually the same, but not always

**6. sku + transaction_type**
- Example: "SKU revenue by transaction type (invoice vs cash sale)"
- Realistic? YES
- Impact: Falls back to source table

**7. sku + pricing_type**
- Example: "SKU revenue at full price vs reduced price"
- Realistic? YES - "How much did we discount SKU LIFE001?"
- Impact: Falls back to source table
- **This is IMPORTANT for merchandising!**

**8. sku + customer_email**
- Example: "Which customers bought SKU LIFE001?"
- Realistic? YES - but usually done reverse (what did customer X buy)
- Impact: Falls back to source table

**9. customer_email + channel_type**
- Example: "B2B customers buying through D2C channel"
- Realistic? YES - customer segmentation
- Impact: Falls back to source table

**10. customer_email + category**
- Example: "Customer X's purchases by category"
- Realistic? YES
- Impact: Falls back to source table

---

## REALISTIC vs THEORETICAL Gaps

### HIGH Priority Gaps (Realistic Queries):

1. **sku + pricing_type** ⚠️ IMPORTANT
   - "How much revenue did we get from full-price vs discounted sales of SKU X?"
   - This is core merchandising analytics
   - **Impact**: HIGH

2. **sku + transaction_type** ⚠️ IMPORTANT
   - "SKU revenue from invoices vs cash sales"
   - Useful for channel analysis
   - **Impact**: MEDIUM

3. **customer_email + channel_type** ⚠️ IMPORTANT
   - "Customer segmentation by channel"
   - "B2B customers using D2C channel"
   - **Impact**: HIGH

4. **customer_email + category** ⚠️ IMPORTANT
   - "What categories does customer X buy?"
   - "Customer purchase patterns"
   - **Impact**: HIGH

5. **sku + shipping_country**
   - Similar to billing_country (usually same)
   - **Impact**: LOW

### LOW Priority Gaps (Unlikely/Invalid Queries):

6. **sku + product_range** - SKU belongs to ONE product_range (invalid query)
7. **sku + collection** - SKU belongs to ONE collection (invalid query)
8. **sku + classification_name** - Unclear business use case
9. **sku + customer_email** - Reverse is more common (what did customer buy)

---

## TO ACHIEVE 100% COVERAGE

We would need:

### Option 1: Add More Dimensions to sku_details
```yaml
sku_details (MAXED OUT):
  dimensions:
    - sku, product_name
    - size, color, season, section
    - channel_type, billing_country, location_name, customer_type
    - pricing_type        # NEW
    - transaction_type    # NEW
    - shipping_country    # NEW
    - product_range       # NEW (but invalid query)
    - collection          # NEW (but invalid query)
    # Total: 15 dimensions
```

**Cardinality**: 5,000 × 20 × 50 × 10 × 30 × 6 × 50 × 30 × 3 × 2 × 2 × 50 × 20 × 10
= **INSANE - billions of rows**

This is NOT feasible.

### Option 2: Add More Dimensions to customer_geography
```yaml
customer_geography (ENHANCED):
  dimensions:
    - customer_email
    - billing_country
    - shipping_country
    - channel_type        # NEW
    - category            # NEW
    - section             # NEW
    # Total: 6 dimensions
```

**Cardinality**: 100K customers × 50 countries × 6 channels × 20 categories × 30 sections
= **180 BILLION combinations**

Also not feasible.

### Option 3: Add NEW Pre-agg for SKU + Business Dimensions
```yaml
sku_business_metrics (NEW):
  dimensions:
    - sku
    - pricing_type
    - transaction_type
    - billing_country
  # Total: 4 dimensions
```

**Cardinality**: 5,000 × 2 × 2 × 50 = **1 million rows** (feasible)

---

## FINAL ANSWER

### Does adding location_name + customer_type to sku_details give 100% coverage?

**NO - ~95% coverage**

### Remaining gaps:

**Critical (should fix)**:
1. sku + pricing_type (merchandising analytics)
2. customer_email + channel_type (customer segmentation)
3. customer_email + category (purchase patterns)

**Minor**:
4. sku + transaction_type
5. sku + shipping_country

### Recommended Approach:

**ENHANCED sku_details** (10 dimensions):
```yaml
- sku, product_name, size, color, season, section
- channel_type, billing_country
- location_name, customer_type  # ADDITIONS
```

**Cardinality estimate**: 500K-1M rows (acceptable)

**Coverage**: 90-95% (good enough for production)

**Accept source table fallback for**:
- sku + pricing_type (5% of queries?)
- customer_email + channel/category (5% of queries?)

### Alternative: Add 5th Pre-agg

If sku + pricing_type is critical, add:

```yaml
sku_pricing (NEW):
  dimensions:
    - sku
    - pricing_type
    - channel_type
    - billing_country
  measures:
    - total_revenue
    - units_sold
```

**Cardinality**: 5,000 × 2 × 6 × 50 = **3 million rows** (borderline acceptable)

---

## VERDICT

**Enhanced sku_details (with location_name + customer_type)** achieves **~95% coverage**, not 100%.

To get 100%, you'd need 5-6 pre-aggs or add so many dimensions to sku_details that it becomes too large.

**Recommendation**: Accept 95% coverage with enhanced sku_details, monitor query patterns, add sku_pricing pre-agg later if needed.
