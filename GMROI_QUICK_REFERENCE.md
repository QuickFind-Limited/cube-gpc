# GMROI Investigation - Quick Reference Guide

## Three Critical Issues Found

### 1. DC INTAKE UNITS MISMATCH
**Problem:** AI reports 632,106 units from supplier_lead_times, but correct count is 1,060,254 from transaction_lines

**Root Cause:** supplier_lead_times has INNER JOIN to purchase_orders, filtering out:
- Items received without PO linkage
- Header lines (mainline='T')
- Lead times outside 0-365 days

**Correct Data Source:**
```
FROM transaction_lines 
WHERE transaction_type = 'ItemRcpt'
MEASURE: itemrcpt_line_count
```

**40% Difference Breakdown:**
- supplier_lead_times: 632,106 units (PO-linked only)
- transaction_lines: 1,060,254 units (all receipts)
- YTD Sales: 1,546,823 units

---

### 2. GROSS PROFIT CALCULATION ERROR (€20.6M > €23.0M net sales = IMPOSSIBLE)

**Root Cause:** AI is summing NetSuite's estimated gross profit from ItemRcpt lines instead of calculating actual sales gross margin

**WRONG Approach:**
```
SUM(estgrossprofit) where transaction_type = 'ItemRcpt'
= €20.6M (expected profit estimate from purchases)
```

**RIGHT Approach:**
```
SUM(amount * -1 - costestimate) where transaction_type IN ('CustInvc', 'CashSale')
= Revenue - COGS = Actual Gross Margin
= Expected: €5-8M (20-35% typical retail margin)
```

**Why It's Wrong:**
- estgrossprofit = NetSuite's estimated margin at time of purchase
- sales revenue = actual cash collected from customers
- These are fundamentally different measures and should never be mixed

**Correct Formula:**
```
Gross Margin = Revenue - Cost of Goods Sold
  = transaction_lines.gross_margin (pre-agged in sales_analysis)
```

---

### 3. INTAKE MARGIN AVAILABILITY

**Status:** PARTIALLY AVAILABLE

**What IS Available (100%):**
- ✓ Unit cost (rate field): 100% populated in ItemRcpt lines
- ✓ Receipt line amount: 100% populated
- ✓ NetSuite's estimated margin: estgrossprofitpercent available

**What IS NOT Available:**
- ✗ Retail/list price for intake (not exported from NetSuite)
- ✗ VAT breakdown for intake (tax only on sales, not purchases)
- ✗ Cannot calculate "intake value ex-VAT" as requested

**Workaround Available:**
Use NetSuite's estgrossprofitpercent directly (already calculated in landed_costs cube)

---

## Pre-Aggregation Coverage

| Pre-Agg | Has Revenue | Has Cost | Has Margin | Has Intake Units | Use for GMROI? |
|---|---|---|---|---|---|
| transaction_lines.sales_analysis | ✓ | ✓ | ✓ | ✗ | **YES** |
| transaction_lines.product_analysis | ✓ | ✓ | ✓ | ✗ | **YES** |
| transaction_lines.location_analysis | ✓ | ✓ | ✓ | ✗ | **YES** |
| supplier_lead_times.lead_time_rollup | ✗ | ✗ | ✗ | ✓ (filtered) | **NO** |
| landed_costs.monthly_landed_costs | ✗ | ✗ | ✗ | ✓ | **NO** |

---

## Measure Definitions - What to Use

### For GMROI Calculation

**Gross Margin (CORRECT):**
```yaml
transaction_lines.gross_margin
= SUM(amount * -1 - costestimate) for CustInvc + CashSale only
In pre-agg: sales_analysis
```

**Sales Revenue (CORRECT):**
```yaml
transaction_lines.total_revenue
= SUM(amount * -1) for CustInvc + CashSale only
In pre-agg: sales_analysis
```

**Intake Units (CORRECT):**
```yaml
transaction_lines.itemrcpt_line_count
= COUNT of ItemRcpt lines (includes inventory + landed costs)
NOT from: supplier_lead_times (too filtered)
```

**Intake Value (CORRECT):**
```yaml
transaction_lines.total_itemrcpt_amount
= SUM(amount) for ItemRcpt only
Contains inventory + landed costs combined
```

### For Intake Margin Analysis

**Estimated Margin % (FROM NetSuite):**
```yaml
transaction_lines.estgrossprofitpercent
= NetSuite's pre-calculated margin %
Available as dimension in transaction_lines
```

**Landed Costs (FREIGHT + DUTY):**
```yaml
transaction_lines.total_landed_costs OR landed_costs.total_landed_costs
= SUM(amount) where blandedcost='T'
Use blandedcost filter to exclude inventory lines
```

---

## Quick Diagnostic Queries

### Check DC Intake Units
```
Use: transaction_lines.itemrcpt_line_count
NOT: supplier_lead_times.receipt_count
```

### Check Gross Profit Accuracy
```
If result > net_revenue, you're using wrong formula
Correct: gross_margin = revenue - cost (from sales only)
Wrong: estgrossprofit = ItemRcpt estimate
```

### Check Data Availability
```
Unit Cost:         100% populated ✓
Receipt Amount:    100% populated ✓
Estimated Margin:  In transaction_lines dimensions ✓
Retail Value:      NOT available ✗
```

---

## Key Files to Review

1. **transaction_lines.yml** (lines 203-210)
   - gross_margin measure definition
   - itemrcpt_line_count measure
   - estgrossprofit dimension

2. **supplier_lead_times.yml** (lines 3-23)
   - SQL definition with INNER JOIN to PO (the filter!)
   - receipt_count measure (PO-linked only)

3. **landed_costs.yml** (lines 3-26)
   - estgrossprofit and estgrossprofitpercent fields
   - monthly_landed_costs pre-agg

4. **create_filtered_views.sql** (lines 23-42)
   - transactions_analysis view logic
   - Shows how transaction types are included

---

## Recommendations Summary

1. **For DC Intake:** Use transaction_lines with ItemRcpt filter (not supplier_lead_times)
2. **For Gross Profit:** Use transaction_lines.gross_margin (not estgrossprofit)
3. **For Intake Margin:** Use NetSuite's estgrossprofitpercent (retail value not available)
4. **For GMROI:** Calculate = gross_margin / (avg_intake_unit_cost * current_inventory)

---

## Full Investigation Report
See: `/home/produser/cube-gpc/GMROI_ACCURACY_INVESTIGATION.md` (656 lines)

Contains:
- Detailed root cause analysis
- SQL code snippets for each issue
- Pre-aggregation coverage tables
- Transaction type filtering analysis
- Verification checklist
- Implementation recommendations
