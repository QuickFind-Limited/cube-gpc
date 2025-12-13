# Cube.dev Data Model - Visual Architecture

## Overall Schema Structure

```
                                    DIMENSION TABLES
                                   ================
                                       items
                                    (SKU, category,
                                   section, size,
                                    color, season)
                                         |
                                         |
    transactions_analysis -----> transaction_lines -----> locations
         (order                      (MAIN FACT)        (channel_type
         headers)                                         region,
                                                          location_type)
         |                               |
         |                               |
      JOINS:                          DENORMALIZED:
      - currencies                    - sku, product_name
      - subsidiaries                  - category, section, season
                                      - size, color, collection
                                      - location_name
                                      - currency_name
                                      - department_name
                                      - classification_name


                                   REFERENCE TABLES
                                  ==================
                                   currencies
                                   departments
                                   classifications
                                   subsidiaries
```

## Customer Dimension (Problematic Split)

```
B2C CUSTOMERS (TWO SEPARATE CUBES - GRAIN CONFLICT)

b2c_customers                        b2c_customer_channels
(email, billing_country)             (email, country, channel)
        |                                    |
        |-- Grain: 2x email                 |-- Grain: 3x email
        |   if buys to UK+Ireland           |   per channel
        |
        |-- NO channel dimension        |-- HAS channel_type
        |-- All channels aggregated    |-- HAS channel_lifetime_value
        |-- customer_count            |-- unique_customers measure
        |-- total_lifetime_value      |   (for cross-channel count)

PROBLEM: Cannot easily pivot between these two cubes
SOLUTION: Merge into single b2c_customers_bridge cube
```

## Supply Chain / Procurement Stream

```
purchase_orders ──┐
  (po_id,        |
   supplier_id)  |  (one_to_many)
                 |
                 └──> purchase_order_lines
                        (po_line_id, item_id, quantity)
                              |
                              | (createdfrom link)
                              |
                              └──> item_receipt_lines
                                     (receipt_line_id)
                                        |
                                        |
                                   item_receipts
                                   (receipt_id)
                                        |
                                        └──> supplier_lead_times
                                             (lead_time_days)

ISSUE: Supplier not queryable directly from transactions
       (hidden in purchase_orders.entity field)
```

## Inventory & Fulfillment Streams

```
INVENTORY STREAM:                    FULFILLMENT STREAM:

inventory                            transactions
(item_id, location_id)               (order_id)
  |                                      |
  |-- SNAPSHOT: Current stock            |
  |-- Grain: item X location             |-- FACT_HDR
  |-- Joins: items, locations            |
                                         |
                                         └──> fulfillments
                                              (fulfillment_id)
                                                  |
                                                  └──> fulfillment_lines
                                                       (item_id, qty_shipped)

on_order_inventory                   order_baskets
(po_line_id)                         (order_id)
  |                                     |
  |-- Derived from open POs             |-- Aggregated view
  |-- On-order qty & value              |-- Line count, basket size


PRE-BUILT SNAPSHOTS:
- on_order_inventory (real-time PO status)
- sell_through_seasonal (season-specific)
```

## Fact Cubes by Type

```
TRANSACTION-GRAIN FACTS:              HEADER-GRAIN FACTS:
- transaction_lines ★★★ (main)       - transactions
  └ 19 pre-aggs                       - purchase_orders
  └ extensive denormalization         - item_receipts
  └ channel_type via location         - fulfillments

DERIVED/FILTERED:                     AGGREGATED:
- landed_costs                        - order_baskets
  └ ItemRcpt subset                   - b2c_customers
  └ blandedcost='T'                   - b2b_customers
                                      - on_order_inventory
ANALYTICAL:                           
- supplier_lead_times                 SNAPSHOT:
  └ PO-to-receipt link                - inventory
- cross_sell                          - sell_through_seasonal (✓ correct)
- sell_through (✗ deprecated)         - on_order_inventory
```

## Key Dimension Flows

```
PRODUCT DIMENSIONS:
items ──> used in:
          - transaction_lines (denormalized)
          - inventory (join)
          - purchase_order_lines (join)
          - supplier_lead_times (join)

LOCATION DIMENSIONS:
locations ──> used in:
              - transaction_lines (join via NAME - BRITTLE!)
              - inventory (join via ID - good)
              - fulfillment_lines (join via ID - good)
              - Centralized channel_type logic (good)

GEOGRAPHY DIMENSIONS:
billing_country ──> transaction_lines, transactions, b2c_customers
shipping_country ──> transaction_lines, transactions
(STRING-BASED - NO COUNTRY DIMENSION - PROBLEM!)

CUSTOMER DIMENSIONS:
b2c_customers ──> email lookup + LTV
b2c_customer_channels ──> email lookup + channel + LTV
(TWO CUBES, DIFFERENT GRAINS - CONFUSING!)

CURRENCY DIMENSIONS:
currencies ──> all transaction cubes
subsidiary ──> all transaction cubes
```

## Pre-Aggregation Landscape (19 on transaction_lines)

```
HIGHEST PRIORITY (Most Used):
├─ sales_analysis (channel, category, section, season, country)
├─ product_analysis (sku, category, season, size, color)
├─ daily_metrics (channel only)
└─ transaction_grain_aov (exact AOV calculations - OM002)

SECONDARY (Common Queries):
├─ customer_geography (email, country, shipping_country)
├─ product_geography (sku, category, country)
├─ channel_product (channel, sku, season, size)
├─ discount_analysis (channel, category, pricing_type)
└─ transaction_type_analysis (type, channel, country)

SPECIALIZED:
├─ size_geography (size, color, country)
├─ size_color_analysis (size, color, section, season)
├─ size_location_analysis (size, location, category)
├─ product_range_analysis (range, collection, season)
├─ location_analysis (location, channel, dept)
├─ weekly_metrics (channel, category, section)
└─ yearly_metrics (channel, category, section)

MISSING (Should Add):
├─ supplier_analysis (supplier, category, channel) - CRITICAL
└─ customer_cohort_analysis (cohort_month, tier, country) - NICE
```

## Critical Join Paths & Their Issues

```
1. CLEAN JOIN (ID-Based):
   purchase_order_lines --(po_id)--> purchase_orders ✓
   inventory --(location_id)--> locations ✓
   fulfillment_lines --(location_id)--> locations ✓

2. FRAGILE JOIN (Name-Based):
   transaction_lines --(location_name)--> locations ✗
   └─ Risk: Name changes break join
   └─ Risk: Duplicate names create ambiguity
   └─ Should use: location_id (need denormalization)

3. MANY-TO-MANY RISK:
   transaction_lines + inventory (via item only)
   └─ No location filter = fan-out potential
   └─ Current use: OK for analysis, but needs dimension care

4. DEEP JOIN PATH:
   transaction_lines -> items -> purchase_order_lines -> purchase_orders
   └─ 4 levels to get supplier info
   └─ Problem: No supplier_id in transaction_lines directly
```

## Data Quality Issues by Cube

```
CRITICAL:
✗ transaction_lines: Missing supplier_id, customer_id, status
✗ locations: Location join in transaction_lines via NAME
✗ All geography: No countries dimension (strings only)

MAJOR:
⚠ b2c_customers: Grain conflict with b2c_customer_channels
⚠ inventory: No country dimension
⚠ purchase_orders: Supplier ID not exposed

MINOR:
- supply chain: No unified supplier master
- customers: Missing customer tier in transaction_lines
- orders: Missing fulfillment status linkage

DEPRECATED:
✗ sell_through: Use sell_through_seasonal instead
```

## Recommended Fixes (Priority Order)

```
PHASE 1 - Critical (20-25 hours):
  1. Add supplier_dimension cube
  2. Create countries reference cube
  3. Fix location join (name -> ID)

PHASE 2 - Major (15-20 hours):
  4. Consolidate B2C customer dimensions
  5. Create order-level cube
  6. Add pre-aggs for supplier & customer cohorts

PHASE 3 - Minor (5-10 hours):
  7. Document grain contracts & access patterns
  8. Remove measures from reference cubes
  9. Add missing dimensions to transaction_lines

PHASE 4 - Cleanup (5 hours):
  10. Remove deprecated sell_through cube
  11. Consolidate redundant pre-aggs
  12. Add comprehensive documentation
```

---

## Summary: Architecture Health Score

| Aspect | Score | Notes |
|--------|-------|-------|
| Fact Table Design | 7/10 | Good denormalization, but missing key dimensions |
| Dimension Management | 5/10 | Multiple non-conformed dims, string-based geography |
| Join Patterns | 6/10 | One brittle join (name-based), some M2M risks |
| Pre-Aggregation | 9/10 | Excellent coverage, well-aligned with queries |
| Customer Dimensions | 4/10 | Problematic split across two cubes |
| Supply Chain | 6/10 | Good structure but supplier not exposed directly |
| Overall | 6/10 | Functional but needs architectural cleanup |

**Verdict**: Well-built foundation with good pre-agg strategy, but needs fixes to enable full analytical capability without complex custom joins.

