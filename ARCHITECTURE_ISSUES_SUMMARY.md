# Cube.dev Architecture - Issues Summary

## 11 Critical Issues Found

### Priority 1: Critical (Must Fix)

**Issue #1: Missing Supplier Dimension**
- Status: CRITICAL
- Impact: Cannot analyze "Revenue by supplier" without complex joins
- Location: All cubes (especially transaction_lines)
- Solution: Create supplier_dimension cube, denormalize supplier_id into transaction_lines
- Fix Time: 2-3 hours

**Issue #2: Location Join via Name (Not ID)**
- Status: CRITICAL  
- Impact: Brittle join - breaks if location name changes; ambiguous if names duplicate
- Location: transaction_lines.yml (line 54-56)
- Current: `"{CUBE}.location_name = {locations.name}"`
- Should be: `"{CUBE}.location = {locations.id}"` (requires denormalizing location_id)
- Fix Time: 1 hour

**Issue #3: Missing Country Dimension**
- Status: CRITICAL
- Impact: Countries are strings, no master list; cannot validate or standardize
- Location: transaction_lines, transactions, b2c_customers, inventory
- Solution: Create countries reference cube; replace string columns with foreign keys
- Fix Time: 4-5 hours

### Priority 2: Major (Should Fix)

**Issue #4: B2C Customer Dimension Split**
- Status: MAJOR
- Impact: Cannot easily switch between "all customers" and "customers by channel" views
- Location: b2c_customers.yml (email, billing_country) + b2c_customer_channels.yml (email, country, channel)
- Root Cause: Same customer appearing in multiple rows if they buy through different channels
- Solution: Consolidate into single b2c_customers_bridge cube with (email, country, channel) grain
- Fix Time: 3-4 hours

**Issue #5: No Order-Level Cube**
- Status: MAJOR
- Impact: Order analysis requires aggregating from transaction_lines; missing order status, fulfillment status
- Location: Only order_baskets.yml exists (minimal)
- Solution: Create full orders cube with order_id grain, order status, fulfillment status
- Fix Time: 3-4 hours

**Issue #6: Inconsistent Location Join Paths**
- Status: MEDIUM-MAJOR
- Impact: Some cubes join via location_id, others via location_name
- Location: transaction_lines (via name), inventory (via id), fulfillment_lines (via id)
- Solution: Standardize all to use location_id
- Fix Time: 1-2 hours

**Issue #7: Grain Conflict in Sell-Through Cubes**
- Status: MEDIUM-MAJOR  
- Impact: sell_through cube mixes all-time sales with point-in-time inventory (deprecated)
- Location: sell_through.yml (DEPRECATED), sell_through_seasonal.yml (CORRECT)
- Solution: Remove sell_through cube; migrate to sell_through_seasonal
- Fix Time: 1 hour (migration) + testing

**Issue #8: Missing Dimensions in transaction_lines**
- Status: MEDIUM
- Impact: Cannot analyze by supplier, customer tier, order status, fulfillment status, payment method
- Location: transaction_lines.yml
- Missing Fields: supplier_id, customer_id, order_id, status, shipping_method, payment_method
- Solution: Add these dimensions via denormalization or joins
- Fix Time: 2-3 hours per dimension

### Priority 3: Minor (Nice to Fix)

**Issue #9: Channel Type Access Path Inconsistency**
- Status: MINOR
- Impact: Some cubes access channel_type directly, others via locations dimension
- Location: transaction_lines (direct), inventory (via locations)
- Solution: Document access patterns; consider centralizing further
- Fix Time: 1-2 hours (documentation)

**Issue #10: Measures in Dimension Cubes**
- Status: COSMETIC
- Impact: Slightly messy design (items, locations, currencies have count measures)
- Location: items.yml, locations.yml, currencies.yml
- Solution: Remove or move to separate monitoring cube
- Fix Time: 30 minutes

**Issue #11: Missing Pre-Aggregations for Supplier & Customer Cohorts**
- Status: MINOR
- Impact: No pre-aggs for supplier analysis or customer cohort trends
- Location: Missing from all cubes
- Solution: Add supplier_analysis and customer_cohort_analysis pre-aggs
- Fix Time: 1-2 hours

---

## Issues by Cube

### transaction_lines (Most Issues)
- Missing supplier_id dimension
- Missing customer_id dimension  
- Missing order status dimension
- Location join via name (should be ID)
- Extensive denormalization (acceptable but increases complexity)

### b2c_customers
- Grain: (email, country) - same customer appears 2x if they buy to UK+Ireland
- Missing channel_type dimension
- Cannot pivot to "customers by channel" without switching cubes

### b2c_customer_channels
- Complex to use for all-customer view
- Requires using unique_customers measure for cross-channel totals

### inventory
- Missing country dimension (only has region)
- Location join works (via ID) - OK
- Channel type available but via locations dimension

### locations
- Channel type logic hardcoded as CASE statement (good centralization)
- Should add country mapping for inventory/transaction_lines usage

### purchase_orders
- Supplier ID hidden in entity field (not directly queryable)
- Should expose supplier_id as explicit dimension

### sell_through (DEPRECATED)
- Flawed grain: mixes all-time sales with point-in-time inventory
- Use sell_through_seasonal instead

---

## Fix Priority Order

1. **Add supplier_id denormalization to transaction_lines** (highest impact)
2. **Create countries reference cube** (unblocks multiple features)
3. **Fix location join from name to ID** (removes brittleness)
4. **Consolidate B2C customer dimensions** (improves usability)
5. **Create order-level cube** (enables order analysis)
6. **Add missing pre-aggs** (improves performance)
7. **Documentation cleanup** (reduces confusion)

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Issues Found | 11 |
| Critical Issues | 3 |
| Major Issues | 4 |
| Minor Issues | 4 |
| Total Cubes | 27 |
| Fact Cubes | 8 |
| Dimension Cubes | 12 |
| Bridge/Aggregate Cubes | 7 |
| Pre-Aggregations | 30+ |
| Max Join Depth | 5 levels |
| Estimated Fix Time (All) | 20-25 hours |

