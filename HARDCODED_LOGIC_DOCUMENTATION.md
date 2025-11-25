# Hardcoded Logic Documentation

**Last Updated:** November 25, 2025
**Change Reference:** Transaction type parameterization (cross_sell, order_baskets, sell_through, b2c_customers)

This document explains which business logic remains hardcoded in Cube.js YML files, which logic has been parameterized as dimensions, and migration guidance for queries.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Hardcoded Logic That Should Remain](#hardcoded-logic-that-should-remain)
3. [Parameterized Logic (Was Hardcoded, Now Dimensions)](#parameterized-logic-was-hardcoded-now-dimensions)
4. [Convenience Measures with Filters](#convenience-measures-with-filters)
5. [Query Migration Guide](#query-migration-guide)
6. [Best Practices](#best-practices)

---

## Executive Summary

### Recent Changes (November 2025)

**What Changed:**
- Removed hardcoded `transaction_type` WHERE clauses from 4 virtual cubes
- Added `transaction_type` dimensions for flexible filtering
- Users can now query across all transaction types (SalesOrd, CustInvc, CashSale)

**Cubes Modified:**
1. `cross_sell` - Product affinity analysis (BASK002)
2. `order_baskets` - Order basket analysis (BASK003)
3. `sell_through` - Sell-through rate analysis (STR001, PP058)
4. `b2c_customers` - B2C customer metrics (CM058, CM059, CM060, CM061)

**Why:**
- **Flexibility:** Users can now slice data by transaction type instead of being locked to hardcoded filters
- **Completeness:** Queries can include SalesOrd (orders), CustInvc (invoices), and CashSale (cash sales)
- **Dimensional Modeling:** Follows best practice of exposing filters as queryable dimensions

**Backwards Compatibility:**
- Existing queries will return MORE data (all transaction types) unless filtered
- Add `"filters": [{"member": "cube_name.transaction_type", "operator": "equals", "values": ["CustInvc"]}]` to restore old behavior

---

## Hardcoded Logic That Should Remain

The following hardcoded filters are **intentional business rules** and should NOT be parameterized:

### 1. `mainline = 'F'` Filters
**Purpose:** Exclude transaction header rows, include only line-level detail
**Cubes:** `transaction_lines`, `order_baskets`, `cross_sell`, and others
**Why Keep:** Core data model requirement - header records would create double-counting

```yaml
# Example from transaction_lines.yml
WHERE tl.mainline = 'F'  # ✅ Keep this - excludes header records
```

**Files:**
- `/home/produser/cube-gpc/model/cubes/transaction_lines.yml` (line 4)
- `/home/produser/cube-gpc/model/cubes/order_baskets.yml` (line 21)
- `/home/produser/cube-gpc/model/cubes/cross_sell.yml` (line 21)

---

### 2. Quantity Sign Logic (Negative = Sales)
**Purpose:** Negative quantities indicate sales, positive indicates returns
**Cubes:** `transaction_lines`, `sell_through`, `cross_sell`
**Why Keep:** NetSuite data model convention for revenue recognition

```yaml
# Example from transaction_lines.yml
CASE WHEN tl.quantity < 0 THEN ABS(tl.quantity) ELSE 0 END  # ✅ Keep this - sales logic
```

**Files:**
- `/home/produser/cube-gpc/model/cubes/transaction_lines.yml` (lines 29-42)
- `/home/produser/cube-gpc/model/cubes/sell_through.yml` (line 20)
- `/home/produser/cube-gpc/model/cubes/cross_sell.yml` (lines 21-22)

---

### 3. Revenue Transaction Type Filters in CASE Statements
**Purpose:** Only CustInvc/CashSale are revenue transactions (not SalesOrd)
**Cubes:** `transaction_lines` (revenue/cost calculations)
**Why Keep:** Proper revenue recognition - orders (SalesOrd) are not revenue until invoiced

```yaml
# Example from transaction_lines.yml (revenue calculation)
CASE
  WHEN t.type IN ('CustInvc', 'CashSale') AND tl.quantity < 0
  THEN tl.amount * -1
  ELSE 0
END  # ✅ Keep this - revenue recognition rule
```

**File:** `/home/produser/cube-gpc/model/cubes/transaction_lines.yml` (lines 29-42)

**Note:** This is different from WHERE clause filters. These CASE statements correctly calculate revenue while allowing queries to include all transaction types for analysis.

---

### 4. Non-Empty Email Filters (B2C Customers)
**Purpose:** B2C customers must have valid email addresses
**Cube:** `b2c_customers`
**Why Keep:** Data quality requirement - email is primary key for B2C analysis

```yaml
# Example from b2c_customers.yml
WHERE t.custbody_customer_email IS NOT NULL
  AND t.custbody_customer_email != ''  # ✅ Keep this - data quality filter
```

**File:** `/home/produser/cube-gpc/model/cubes/b2c_customers.yml` (lines 13-14)

---

## Parameterized Logic (Was Hardcoded, Now Dimensions)

The following logic was previously hardcoded but is now available as dimensions for flexible filtering:

### 1. Transaction Type (✅ PARAMETERIZED)

**Previous Behavior:**
- `cross_sell`: Hardcoded to `WHERE t.type IN ('CustInvc', 'CashSale')`
- `order_baskets`: Hardcoded to `WHERE t.type IN ('CustInvc', 'CashSale')`
- `sell_through`: Hardcoded to `WHERE t.type IN ('CustInvc', 'CashSale')`
- `b2c_customers`: Hardcoded to `WHERE t.type = 'SalesOrd'`

**New Behavior:**
- All 4 cubes now include `transaction_type` dimension
- No WHERE clause filter - queries return all transaction types by default
- Users can filter by dimension in queries

**Available Values:**
- `SalesOrd` - Sales orders (order stage)
- `CustInvc` - Customer invoices (invoiced/billed)
- `CashSale` - Cash sales (immediate payment)

**Files Modified:**
1. `/home/produser/cube-gpc/model/cubes/cross_sell.yml` (lines 13, 99-102)
2. `/home/produser/cube-gpc/model/cubes/order_baskets.yml` (lines 75-77)
3. `/home/produser/cube-gpc/model/cubes/sell_through.yml` (lines 12, 75-78)
4. `/home/produser/cube-gpc/model/cubes/b2c_customers.yml` (lines 7, 15, 65-68)

**Dimension Definition:**
```yaml
- name: transaction_type
  sql: "{CUBE}.transaction_type"
  type: string
  description: "Transaction type: SalesOrd, CustInvc, CashSale. Previously hardcoded to CustInvc/CashSale only. Now parameterized for flexible filtering."
```

---

## Convenience Measures with Filters

These measures have hardcoded filters for **user experience** but expose underlying dimensions for flexibility:

### Status-Filtered Measures

| Cube | Measure | Filter | Dimension Available |
|------|---------|--------|---------------------|
| `b2b_customers` | `active_customer_count` | `isInactive = 'False'` | ✅ `isInactive` (line 99) |
| `departments` | `active_department_count` | `isinactive = 'F'` | ✅ `isinactive` (line 39) |
| `classifications` | `active_count` | `isinactive = 'F'` | ✅ `isinactive` (line 34) |
| `items` | `active_item_count` | `isinactive = 'F'` | ✅ `is_inactive` (line 101) |
| `transactions` | `fulfilled_orders` | `status = 'G'` | ✅ `status` (line 55) |
| `transactions` | `cancelled_orders` | `status = 'C'` | ✅ `status` (line 55) |
| `fulfillments` | `shipped_count` | `status = 'C'` | ✅ `status` (line 66) |
| `fulfillments` | `pending_count` | `status = 'A'` | ✅ `status` (line 66) |

**Why Keep These:**
- UX benefit: Most queries want active/shipped records by default
- Flexibility maintained: Users can query by status dimension for custom filtering
- Pattern: Convenience measure + exposed dimension = best of both worlds

---

## Query Migration Guide

### Migrating Queries After Transaction Type Parameterization

#### Scenario 1: Restoring Old Behavior (CustInvc/CashSale only)

**Old Query (Automatic):**
```json
{
  "measures": ["cross_sell.total_co_purchases"],
  "dimensions": ["cross_sell.item_a_category"]
}
```
Previously returned only CustInvc/CashSale transactions.

**New Query (Explicit Filter Required):**
```json
{
  "measures": ["cross_sell.total_co_purchases"],
  "dimensions": ["cross_sell.item_a_category"],
  "filters": [
    {
      "member": "cross_sell.transaction_type",
      "operator": "equals",
      "values": ["CustInvc", "CashSale"]
    }
  ]
}
```

#### Scenario 2: Analyzing All Transaction Types

**New Query (Now Possible):**
```json
{
  "measures": ["cross_sell.total_co_purchases"],
  "dimensions": [
    "cross_sell.item_a_category",
    "cross_sell.transaction_type"
  ]
}
```
Returns breakdown by transaction type - was impossible before.

#### Scenario 3: B2C Customer Analysis (Was SalesOrd only)

**Old Query (Automatic):**
```json
{
  "measures": ["b2c_customers.customer_count"],
  "dimensions": ["b2c_customers.customer_tier"]
}
```
Previously returned only SalesOrd transactions.

**New Query Options:**

**Option A - Restore SalesOrd only:**
```json
{
  "measures": ["b2c_customers.customer_count"],
  "dimensions": ["b2c_customers.customer_tier"],
  "filters": [
    {
      "member": "b2c_customers.transaction_type",
      "operator": "equals",
      "values": ["SalesOrd"]
    }
  ]
}
```

**Option B - Include all transaction types:**
```json
{
  "measures": ["b2c_customers.customer_count"],
  "dimensions": [
    "b2c_customers.customer_tier",
    "b2c_customers.transaction_type"
  ]
}
```

**Option C - Revenue transactions only (invoices + cash sales):**
```json
{
  "measures": ["b2c_customers.total_lifetime_value"],
  "dimensions": ["b2c_customers.customer_tier"],
  "filters": [
    {
      "member": "b2c_customers.transaction_type",
      "operator": "equals",
      "values": ["CustInvc", "CashSale"]
    }
  ]
}
```

---

### Affected Metrics Reference

| Metric ID | Metric Name | Cube | Migration Action |
|-----------|-------------|------|------------------|
| BASK002 | Product Affinity Pairs | `cross_sell` | Add transaction_type filter if needed |
| BASK003 | Basket Size Distribution | `order_baskets` | Add transaction_type filter if needed |
| STR001 | Sell-Through Rate by Season | `sell_through` | Add transaction_type filter if needed |
| PP058 | Sell-Through Rate by Category | `sell_through` | Add transaction_type filter if needed |
| CM058 | Customer LTV by Tier | `b2c_customers` | Add transaction_type filter if needed |
| CM059 | Purchase Frequency Distribution | `b2c_customers` | Add transaction_type filter if needed |
| CM060 | Customer Recency Buckets | `b2c_customers` | Add transaction_type filter if needed |
| CM061 | Repeat Rate by Country | `b2c_customers` | Add transaction_type filter if needed |

**Pre-Aggregations:**
- All 4 cubes have updated pre-aggregations that include transaction_type
- Pre-aggregations will need rebuild after these changes (done automatically)
- Queries with transaction_type filters will use pre-aggregations efficiently

---

## Best Practices

### When to Keep Logic Hardcoded

✅ **Keep hardcoded when:**
1. **Data Model Requirements** - `mainline = 'F'` prevents double-counting
2. **Business Rules** - Quantity sign logic for sales vs returns
3. **Revenue Recognition** - CASE statements for revenue transaction types
4. **Data Quality** - Non-empty email filters for B2C customers
5. **Calculation Logic** - Component formulas that must be consistent

### When to Parameterize as Dimensions

✅ **Parameterize when:**
1. **User Flexibility Needed** - Users want to slice/filter by this attribute
2. **No Data Integrity Risk** - Removing filter won't cause double-counting
3. **Multiple Valid Values** - Transaction types, status codes, categories
4. **Analysis Scenarios** - Users need to compare filtered vs unfiltered data
5. **Reporting Requirements** - Different reports need different filter combinations

### Convenience Measures Pattern

✅ **Best of both worlds:**
1. Create filtered measure for common use case (e.g., `active_customer_count`)
2. Expose dimension for custom filtering (e.g., `isInactive` dimension)
3. Document both in descriptions
4. Users choose convenience or flexibility

**Example:**
```yaml
measures:
  - name: active_item_count
    type: count
    filters:
      - sql: "{CUBE}.isinactive = 'F'"
    description: Number of active items

dimensions:
  - name: is_inactive
    sql: "{CUBE}.isinactive"
    type: string
    description: Whether item is inactive
```

---

## Change Log

### November 25, 2025 - Transaction Type Parameterization

**Changes:**
1. Removed hardcoded `WHERE t.type IN (...)` from 4 virtual cubes
2. Added `transaction_type` dimensions to all 4 cubes
3. Updated dimension descriptions to document the change
4. Updated pre-aggregations to include transaction_type

**Files Modified:**
- `model/cubes/cross_sell.yml`
- `model/cubes/order_baskets.yml`
- `model/cubes/sell_through.yml`
- `model/cubes/b2c_customers.yml`

**Impact:**
- Queries return more data by default (all transaction types)
- Add filters to restore previous behavior
- 8 metrics affected (BASK002, BASK003, STR001, PP058, CM058-CM061)

**Backwards Compatibility:**
- Breaking change: Existing queries will return different result sets
- Migration: Add transaction_type filters to maintain old behavior
- Pre-aggregations: Automatic rebuild required (done)

---

## Support and Questions

**Documentation Location:** `/home/produser/cube-gpc/HARDCODED_LOGIC_DOCUMENTATION.md`

**Related Documentation:**
- Phase 1 test results: `/tmp/PHASE1_FINAL_RESULTS.md`
- Expected failures: `/tmp/13_EXPECTED_FAILURES_DETAILED.md`
- Cube.js docs: https://cube.dev/docs

**Key Files:**
- Virtual cubes with transaction_type: `cross_sell.yml`, `order_baskets.yml`, `sell_through.yml`, `b2c_customers.yml`
- Status-filtered cubes: `b2b_customers.yml`, `departments.yml`, `classifications.yml`, `items.yml`, `transactions.yml`, `fulfillments.yml`
- Transaction line details: `transaction_lines.yml`

**Contact:** For questions about hardcoded logic decisions, refer to this document or check git commit history for rationale.
