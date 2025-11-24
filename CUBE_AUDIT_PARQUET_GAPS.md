# PARQUET DATA GAP ANALYSIS

**Generated:** November 24, 2025
**Purpose:** Identify which audit fixes can/cannot be implemented with current parquet extractions

---

## EXECUTIVE SUMMARY

### CRITICAL FINDING: Most Fixes Cannot Be Implemented

The majority of critical fixes identified in the audit **CANNOT be implemented** because the required NetSuite fields were not included in the parquet extraction.

| Fix Category | Can Implement | Cannot Implement |
|--------------|---------------|------------------|
| Line Type Filtering | PARTIAL | taxline, shippingline, cogsline missing |
| Posting Filter | NO | posting field missing |
| Voided Filter | NO | voided field missing |
| Exchange Rate | YES | currencies.exchangerate available |
| Item Type Classification | YES | items.itemtype available |

---

## DETAILED FIELD ANALYSIS

### transaction_lines (8,683,905 rows)

**Available Fields (20):**
```
amount, class, costestimate, createdfrom, department, dropship, id,
isclosed, isfullyshipped, item, linesequencenumber, links, location,
mainline, quantity, quantityshiprecv, rate, taxamount, taxrate1, transaction
```

**MISSING Critical Fields:**
| Field | Purpose | Impact |
|-------|---------|--------|
| `taxline` | Identify tax system lines | Cannot filter tax lines |
| `shippingline` | Identify shipping system lines | Cannot filter shipping lines |
| `cogsline` | Identify COGS system lines | Cannot filter COGS lines |
| `posting` | Filter to posted lines only | Cannot exclude non-posting |

**Extraction Note:**
- All 8,683,905 rows have `mainline = 'F'`
- Mainline rows were already filtered during extraction
- All rows have `item` populated (no NULLs)

---

### transactions (1,433,856 rows)

**Available Fields (40):**
```
actualshipdate, billing_addr1, billing_city, billing_country, billing_name,
billing_phone, billing_state, billing_zip, closedate, createddate, currency,
custbody_customer_email, custbody_pwks_remote_order_id, custbody_pwks_remote_order_source,
custbody_shopify_order_name, custbody_shopify_total_amount, entity, exchangerate,
foreigntotal, id, lastmodifieddate, links, memo, shipcarrier, shipdate, shipmethod,
shipping_addr1, shipping_city, shipping_country, shipping_name, shipping_phone,
shipping_state, shipping_zip, status, subsidiary, taxtotal, total, trandate, tranid, type
```

**MISSING Critical Fields:**
| Field | Purpose | Impact |
|-------|---------|--------|
| `posting` | Filter posted transactions | Cannot exclude non-posting (SalesOrd) |
| `voided` | Filter voided transactions | Cannot exclude voided |
| `postingperiod` | Financial reporting period | Cannot use accounting period |

**Transaction Types Available:**
- CashRfnd (2,521)
- CashSale (385,665)
- CustCred (20,298)
- CustInvc (547,954)
- RtnAuth (10,504)
- SalesOrd (466,914)

**Issue:** SalesOrd is non-posting but included. Without `posting` field, cannot filter.

---

### fulfillment_lines (3,286,869 rows)

**Available Fields (9):**
```
createdfrom, id, item, links, location, quantity, quantityshiprecv, shipdate, transaction
```

**MISSING Critical Fields:**
| Field | Purpose | Impact |
|-------|---------|--------|
| `mainline` | Identify header lines | Cannot filter mainlines |
| `taxline` | Identify tax lines | Cannot filter tax lines |
| `shippingline` | Identify shipping lines | Cannot filter shipping lines |
| `cogsline` | Identify COGS lines | Cannot filter COGS lines |

---

### items (15,835 rows)

**Available Fields (54):**
All item fields including `itemtype` which can classify:
- InvtPart (14,472)
- Kit (686)
- NonInvtPart (20)
- Service (4)
- Discount (2)
- Group (2)
- OthCharge (2)

**Can Use:** itemtype to identify Discount, Service (shipping), etc.

---

### currencies (7 rows)

**Available Fields (5):**
```
exchangerate, id, links, name, symbol
```

**Can Use:** Join to get dynamic exchange rates instead of hardcoded 1.13528

---

## WORKAROUNDS POSSIBLE

### 1. Partial Line Type Filtering via Item Type

**Can identify some special lines:**
```sql
-- Discount lines (20,990 total)
WHERE i.itemtype = 'Discount'

-- Shipping lines (401 total via CRSHIPPING item)
WHERE i.itemid = 'CRSHIPPING'
```

**Cannot identify:**
- Tax lines (no taxline field, no tax item in data)
- COGS lines (no cogsline field)

---

### 2. Exclude Non-Posting by Transaction Type

**Workaround (imperfect):**
```sql
-- Revenue transactions (exclude SalesOrd which is non-posting)
WHERE type IN ('CustInvc', 'CashSale')
```

**Issues:**
- RtnAuth, CustCred may have posting issues
- Cannot identify voided within these types

---

### 3. Dynamic Exchange Rate

**Can implement Fix 2.2:**
```sql
-- Join to currencies table
LEFT JOIN currencies c ON t.currency = c.id
...
CASE WHEN t.currency = 4 THEN amount * c.exchangerate ELSE amount END
```

---

### 4. Item Type Classification

**Can implement Fix 3.5:**
```yaml
- name: is_financial_item
  sql: "CASE WHEN {items.itemtype} IN ('Discount') THEN FALSE ELSE TRUE END"
```

---

## EXTRACTION REQUIREMENTS

### Fields to Add to transaction_lines Extraction

```sql
SELECT
  -- existing fields...
  taxline,
  shippingline,
  cogsline
FROM TransactionLine
```

### Fields to Add to transactions Extraction

```sql
SELECT
  -- existing fields...
  posting,
  voided,
  postingperiod
FROM Transaction
```

### Fields to Add to fulfillment_lines Extraction

```sql
SELECT
  -- existing fields...
  mainline,
  taxline,
  shippingline,
  cogsline
FROM TransactionLine
WHERE transaction IN (SELECT id FROM Transaction WHERE type = 'ItemShip')
```

---

## REVISED FIX FEASIBILITY

### CRITICAL Fixes - Feasibility

| Fix | Description | Feasibility | Action Required |
|-----|-------------|-------------|-----------------|
| 1.1 | Line type filtering (transaction_lines) | **PARTIAL** | Add taxline/shippingline/cogsline to extraction |
| 1.2 | Line type filtering (fulfillment_lines) | **NO** | Add all line type fields to extraction |
| 1.3 | Line type filtering (order_baskets) | **PARTIAL** | Can exclude discounts via itemtype |
| 1.4 | Line type filtering (cross_sell) | **PARTIAL** | Can exclude discounts via itemtype |
| 1.5 | Line type filtering (sell_through) | **PARTIAL** | Can exclude discounts via itemtype |
| 1.6 | Posting filter (transactions) | **NO** | Add posting field to extraction |

### HIGH Fixes - Feasibility

| Fix | Description | Feasibility | Action Required |
|-----|-------------|-------------|-----------------|
| 2.1 | Rename costestimate | **YES** | Documentation change only |
| 2.2 | Dynamic exchange rate | **YES** | Use currencies table |
| 2.3 | Voided filter | **NO** | Add voided field to extraction |
| 2.4 | Tax calculation | **PARTIAL** | No taxline field available |
| 2.5 | Fix fulfillments join | **YES** | Use createdfrom field |

### MEDIUM Fixes - Feasibility

| Fix | Description | Feasibility | Notes |
|-----|-------------|-------------|-------|
| 3.1 | Line type dimensions | **PARTIAL** | Only mainline available |
| 3.2 | NULL category handling | **YES** | Use COALESCE |
| 3.5 | Item type classification | **YES** | itemtype available |

---

## IMMEDIATE ACTIONS

### Action 1: Update NetSuite Extraction (REQUIRED)

Add these fields to extraction queries:

**transaction_lines:**
- taxline
- shippingline
- cogsline

**transactions:**
- posting
- voided
- postingperiod

**fulfillment_lines:**
- mainline
- taxline
- shippingline
- cogsline

### Action 2: Implement Feasible Fixes Now

These can be done with current data:
1. Fix 2.2: Replace hardcoded exchange rate with currencies join
2. Fix 3.2: Handle NULL categories with COALESCE
3. Fix 3.5: Add item type classification
4. Fix 2.5: Fix fulfillments join (createdfrom)
5. Partial line filtering using itemtype to exclude Discounts

### Action 3: Implement Workarounds

For transaction type filtering:
```yaml
# Exclude known non-posting type
segments:
  - name: posting_transactions
    sql: "{CUBE}.type NOT IN ('SalesOrd', 'RtnAuth')"
```

For discount line filtering:
```yaml
segments:
  - name: product_lines_only
    sql: "{items.itemtype} NOT IN ('Discount', 'Service')"
```

---

## WORKAROUND CODE EXAMPLES

### Example 1: Exclude Discount Lines from Revenue

```yaml
- name: product_revenue
  sql: >
    CAST(CASE
      WHEN {CUBE}.transaction_type IN ('CustInvc', 'CashSale')
       AND {items.itemtype} NOT IN ('Discount', 'Service')
      THEN {CUBE}.amount * -1
      ELSE 0
    END AS DOUBLE)
  type: sum
  description: Revenue from products only (excludes discounts and services)
```

### Example 2: Dynamic Currency Conversion

```yaml
# In SQL definition, join currencies
LEFT JOIN currencies curr ON t.currency = curr.id

# In measure
- name: total_revenue_eur
  sql: >
    CAST(CASE
      WHEN {CUBE}.transaction_type IN ('CustInvc', 'CashSale')
      THEN {CUBE}.amount * -1 * COALESCE({currencies.exchangerate}, 1)
      ELSE 0
    END AS DOUBLE)
```

### Example 3: Approximate Posting Filter

```yaml
segments:
  - name: likely_posted
    sql: >
      {CUBE}.type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd')
      AND {CUBE}.status NOT IN ('A')
    description: Transactions likely to be posted (excludes pending status A)
```

---

## SUMMARY

### What CAN Be Fixed Now (6 items)
1. Dynamic exchange rate (currencies table)
2. NULL category handling
3. Item type classification
4. Fulfillments join correction
5. Partial discount line filtering
6. Documentation improvements

### What CANNOT Be Fixed Without Re-extraction (8 items)
1. Complete line type filtering (taxline/shippingline/cogsline)
2. Posting transaction filter
3. Voided transaction filter
4. Posting period dimension
5. Tax line separation
6. COGS line separation
7. Shipping line separation
8. Fulfillment line type filtering

### Recommendation

**Priority 1:** Re-run NetSuite extraction with missing fields
**Priority 2:** Implement feasible fixes with current data
**Priority 3:** Use workarounds until re-extraction complete

---

**Report End**
