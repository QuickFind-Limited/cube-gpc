# CUBE.DEV SEMANTIC LAYER AUDIT REPORT

**Generated:** November 24, 2025
**Based on:** NetSuite Calculation Methods & Logic Research
**Audited Cubes:** 17 cube yml files

---

## EXECUTIVE SUMMARY

### Total Issues Found: 32

| Priority | Count | Impact |
|----------|-------|--------|
| **CRITICAL** | 7 | All financial metrics currently incorrect |
| **HIGH** | 9 | Significant data accuracy issues |
| **MEDIUM** | 10 | Missing classifications and edge case handling |
| **LOW** | 6 | Documentation and polish |

### Root Cause of Most Issues

**The single biggest problem:** No filtering of system-generated line types (mainline, taxline, shippingline, cogsline) across 5 cubes. This causes:

- Revenue inflated by shipping/tax amounts
- Unit counts include COGS lines
- Category analysis broken (NULLs from system lines)
- Cross-sell pairs include non-product lines

---

## SYSTEMATIC CHECKLIST (32 Sections from Research)

### SECTION 1-3: TRANSACTION ACCOUNTING FUNDAMENTALS

**Key Rules:**
- [ ] **R1.1**: Use TransactionAccountingLine (not Transaction) for accurate financial metrics
- [ ] **R1.2**: Three-table architecture: Transaction → TransactionLine → TransactionAccountingLine
- [ ] **R1.3**: Filter by accounting_book_id if Multi-Book Accounting enabled
- [ ] **R1.4**: Average cost calculated daily - cost engine runs hourly

### SECTION 4: REVENUE RECOGNITION

- [ ] **R4.1**: Deferred revenue uses separate account type (DeferRevenue)
- [ ] **R4.2**: Revenue = SUM(credit - debit) WHERE account_type = 'Income' AND posting = 'T'

### SECTION 5: FULFILLMENT & COGS LOGIC

- [ ] **R5.1**: COGS books when sold AND fulfilled, not at invoice
- [ ] **R5.2**: Revenue books at invoice creation
- [ ] **R5.3**: Must match revenue and COGS to same period for accurate margin
- [ ] **R5.4**: COGS = SUM(debit - credit) WHERE account_type = 'COGS'

### SECTION 6: GROSS PROFIT CALCULATIONS

- [ ] **R6.1**: NetSuite's costestimate is ESTIMATED cost, NOT actual gross profit
- [ ] **R6.2**: Cost estimate types: Average Cost, Last Purchase Cost, Purchase Price, Custom
- [ ] **R6.3**: For actual gross profit, must aggregate actual revenue and costs from connected transactions

### SECTION 9: MULTI-CURRENCY & EXCHANGE RATES

- [ ] **R9.1**: Three exchange rate types: Current (month-end), Average (weighted), Historical (equity)
- [ ] **R9.3**: TransactionAccountingLine stores base currency; Transaction/TransactionLine store transaction currency
- [ ] **R9.4**: Consolidated rates differ from daily rates

### SECTION 14: TRANSACTION LINE STRUCTURE

- [ ] **R14.1**: Five line type flags: mainline, taxline, shippingline, cogsline, regular
- [ ] **R14.2**: Main line has NULL item on some transactions
- [ ] **R14.4**: Filter pattern: `mainline = 'F' AND taxline = 'F' AND shippingline = 'F' AND cogsline = 'F' AND item IS NOT NULL`

### SECTION 15: NULL ITEM CATEGORY PROBLEM

- [ ] **R15.1**: Shipping lines have item ID but NULL category
- [ ] **R15.2**: Tax lines have item ID but NULL category
- [ ] **R15.3**: Discount lines (posting) have NULL category
- [ ] **R15.4**: COGS lines have NULL category

### SECTION 22: TRANSACTIONACCOUNTINGLINE BEHAVIORS

- [ ] **R22.1**: Filter `posting = 'T'` on BOTH Transaction AND TransactionAccountingLine
- [ ] **R22.2**: Filter `voided = 'F'` to exclude voided transactions
- [ ] **R22.3**: Exclude draft/unposted: `status NOT IN ('Draft', 'Pending Approval')`

### SECTION 23: ASSEMBLY & WORK ORDER QUIRKS

- [ ] **R23.1**: Assembly mainline = +quantity (adding to inventory)
- [ ] **R23.2**: Component lines = NEGATIVE quantity (removing from inventory)

### SECTION 28: POSTING PERIOD VS TRANSACTION DATE

- [ ] **R28.1**: Financial reports use posting_period
- [ ] **R28.2**: Other reports use transaction date

### SECTION 29: NON-POSTING TRANSACTIONS

- [ ] **R29.1**: Sales Orders and Purchase Orders are non-posting (no GL entries)
- [ ] **R29.3**: Always filter `posting = 'T'` for financial metrics

### SECTION 32: CUBE.DEV DEFENSIVE PATTERNS

- [ ] **R32.1**: Create `line_type` dimension classifying all line types
- [ ] **R32.2**: Create `is_financial_line` boolean
- [ ] **R32.3**: Create `is_actual_item` boolean
- [ ] **R32.4**: Create `has_data_quality_issue` flag

---

## AUDIT BY CUBE FILE

### transaction_lines.yml (13 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | CRITICAL | No line type filtering (mainline/taxline/shippingline/cogsline) | R14.4 |
| 2 | CRITICAL | No posting filter (`posting = 'T'`) | R22.1, R29.1 |
| 3 | HIGH | Using estimated cost (`costestimate`), not actual COGS | R6.1 |
| 4 | HIGH | Hardcoded exchange rate (1.13528 for GBP) | R9.4 |
| 5 | HIGH | No voided transaction filter | R22.2 |
| 6 | HIGH | Tax calculation from line-level taxamount (incorrect) | R17.1 |
| 7 | MEDIUM | No line type classification dimension | R32.1-3 |
| 8 | MEDIUM | NULL category handling missing | R15.1-5 |
| 9 | MEDIUM | No discount item type handling | R16.2-3 |
| 10 | MEDIUM | No status filter for drafts | R22.3 |
| 11 | MEDIUM | No separate shipping/tax measures | R18.3 |
| 12 | LOW | Missing posting period dimension | R28.1 |
| 13 | LOW | No data quality flag | R32.4 |

### transactions.yml (4 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | CRITICAL | No posting filter | R22.1, R29.1 |
| 2 | HIGH | No voided filter | R22.2 |
| 3 | MEDIUM | Status codes not documented/mapped | R13.4 |
| 4 | LOW | Missing posting period | R28.1 |

### fulfillments.yml (2 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | HIGH | Incorrect join (entity vs createdfrom) | - |
| 2 | MEDIUM | No line type context documentation | R20.1 |

### fulfillment_lines.yml (3 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | CRITICAL | No line type filtering | R14.4, R20.1 |
| 2 | MEDIUM | No negative quantity handling | R23.2 |
| 3 | LOW | Segment logic doesn't account for negative quantities | R23.2 |

### inventory.yml (2 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | MEDIUM | No data quality flag dimension | R24.3 |
| 2 | LOW | Cost engine timing not documented | R13.1 |

### items.yml (1 Issue)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | MEDIUM | No item type classification (Description, Discount, etc.) | R16.1-5 |

### order_baskets.yml (2 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | CRITICAL | Incomplete line type filtering (only mainline) | R14.4 |
| 2 | HIGH | No posting/voided filter | R22.1-2 |

### cross_sell.yml (2 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | CRITICAL | Incomplete line type filtering (only mainline) | R14.4 |
| 2 | HIGH | No posting/voided filter | R22.1-2 |

### sell_through.yml (2 Issues)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | CRITICAL | No line type filtering in subquery | R14.4 |
| 2 | HIGH | No posting/voided filter | R22.1-2 |

### b2b_customers.yml (1 Issue)

| # | Severity | Issue | Rule |
|---|----------|-------|------|
| 1 | LOW | Overdue segment logic inverted (< 0 should be > 0) | R11.5 |

---

## PRIORITY 1: CRITICAL FIXES (7 Issues)

### FIX 1.1: Add Complete Line Type Filtering to transaction_lines.yml

**Required WHERE clause:**
```sql
WHERE tl.mainline = 'F'
  AND tl.taxline = 'F'
  AND tl.shippingline = 'F'
  AND tl.cogsline = 'F'
  AND t.posting = 'T'
  AND t.voided = 'F'
```

### FIX 1.2: Add Complete Line Type Filtering to fulfillment_lines.yml

```sql
WHERE mainline = 'F'
  AND taxline = 'F'
  AND shippingline = 'F'
  AND cogsline = 'F'
```

### FIX 1.3: Add Complete Line Type Filtering to order_baskets.yml

```sql
WHERE tl.mainline = 'F'
  AND tl.taxline = 'F'
  AND tl.shippingline = 'F'
  AND tl.cogsline = 'F'
  AND t.type IN ('CustInvc', 'CashSale')
  AND t.posting = 'T'
  AND t.voided = 'F'
```

### FIX 1.4: Add Complete Line Type Filtering to cross_sell.yml

```sql
AND tl1.mainline = 'F'
AND tl1.taxline = 'F'
AND tl1.shippingline = 'F'
AND tl1.cogsline = 'F'
AND tl2.mainline = 'F'
AND tl2.taxline = 'F'
AND tl2.shippingline = 'F'
AND tl2.cogsline = 'F'
AND t.posting = 'T'
AND t.voided = 'F'
```

### FIX 1.5: Add Complete Line Type Filtering to sell_through.yml

```sql
WHERE t.type IN ('CustInvc', 'CashSale')
  AND t.posting = 'T'
  AND t.voided = 'F'
  AND tl.mainline = 'F'
  AND tl.taxline = 'F'
  AND tl.shippingline = 'F'
  AND tl.cogsline = 'F'
```

### FIX 1.6: Add Posting Filter to transactions.yml

```yaml
sql: >
  SELECT * FROM transactions
  WHERE posting = 'T'
    AND voided = 'F'
```

---

## PRIORITY 2: HIGH FIXES (9 Issues)

### FIX 2.1: Address Estimated vs Actual Cost

**Option A - Rename (Quick):**
```yaml
- name: estimated_cost
  description: ESTIMATED cost - NOT actual COGS
```

**Option B - Add TransactionAccountingLine cube (Proper):**
Query where account_type = 'COGS' for actual costs

### FIX 2.2: Replace Hardcoded Exchange Rate

Use currencies table or TransactionAccountingLine base currency values

### FIX 2.3: Add Voided Filter

Add `AND voided = 'F'` to all WHERE clauses

### FIX 2.4: Fix Tax Calculation

Sum from taxline = 'T' lines or transaction header

### FIX 2.5: Fix Join in fulfillments.yml

Change `entity` to `createdfrom` for sales order link

---

## PRIORITY 3: MEDIUM FIXES (10 Issues)

### FIX 3.1: Add Line Type Classification Dimensions

```yaml
- name: line_type
  sql: >
    CASE
      WHEN {CUBE}.mainline = 'T' THEN 'Main'
      WHEN {CUBE}.taxline = 'T' THEN 'Tax'
      WHEN {CUBE}.shippingline = 'T' THEN 'Shipping'
      WHEN {CUBE}.cogsline = 'T' THEN 'COGS'
      ELSE 'Item'
    END
  type: string
```

### FIX 3.2: Handle NULL Categories

```sql
CASE
  WHEN tl.taxline = 'T' THEN 'Tax'
  WHEN tl.shippingline = 'T' THEN 'Shipping'
  WHEN tl.cogsline = 'T' THEN 'COGS'
  ELSE COALESCE(i.custitem_gpc_category, 'Uncategorized')
END as category
```

### FIX 3.5: Add Item Type Classification

```yaml
- name: is_financial_item
  sql: "CASE WHEN {CUBE}.itemtype IN ('Description', 'Subtotal') THEN FALSE ELSE TRUE END"
```

---

## PRIORITY 4: LOW FIXES (6 Issues)

### FIX 4.1: Add Posting Period Dimension

```yaml
- name: posting_period
  sql: "{CUBE}.postingperiod"
  type: string
```

### FIX 4.4: Fix Overdue Segment in b2b_customers.yml

Change `< 0` to `> 0`

---

## IMPLEMENTATION ORDER

### Phase 1: Critical Data Accuracy (Week 1)
- Fix 1.1-1.6: Add line type and posting filters
- Fix 2.3: Add voided filters

### Phase 2: Financial Accuracy (Week 2)
- Fix 2.1: Address estimated vs actual cost
- Fix 2.2: Replace hardcoded exchange rates
- Fix 2.4: Fix tax calculation
- Fix 2.5: Fix fulfillments join

### Phase 3: Data Quality & Classification (Week 3)
- Fix 3.1-3.2: Add line type dimensions
- Fix 3.5: Add item type classification
- Fix 3.8: Add data quality checks

### Phase 4: Documentation & Polish (Week 4)
- All remaining medium and low fixes

---

## VALIDATION QUERIES

```sql
-- Check for system lines in metrics
SELECT line_type, COUNT(*), SUM(amount)
FROM transaction_lines_cube
GROUP BY line_type;

-- Check for non-posting transactions
SELECT posting, COUNT(*)
FROM transactions_cube
GROUP BY posting;

-- Check for voided transactions
SELECT voided, COUNT(*)
FROM transactions_cube
GROUP BY voided;

-- Check category coverage
SELECT
  CASE WHEN category IS NULL THEN 'NULL' ELSE 'Has Value' END,
  COUNT(*)
FROM transaction_lines_cube
GROUP BY 1;
```

---

## ARCHITECTURAL GAP

Your current design queries `TransactionLine` directly. For true financial accuracy matching NetSuite's financial statements, consider:

1. Creating a `transaction_accounting_lines` cube querying `TransactionAccountingLine`
2. Using account_type for proper debit/credit logic
3. This gives actual COGS, not estimated

---

**Report End**
