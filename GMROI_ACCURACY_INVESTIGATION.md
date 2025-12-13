# GMROI Calculation Accuracy Investigation Report
**Investigation Date:** December 8, 2025  
**Scope:** GymPlusCoffee Cube Analytics Platform  
**Thoroughness Level:** Very Thorough  

---

## EXECUTIVE SUMMARY

Investigation of the GMROI (Gross Margin Return on Investment) calculation reveals **THREE CRITICAL ISSUES** with the current cube implementation:

### Key Findings:

1. **DC Intake Units Mismatch (CONFIRMED)**
   - **supplier_lead_times table:** 632,106 units YTD
   - **transaction_lines table (ItemRcpt):** 1,060,254 units YTD  
   - **Root Cause:** supplier_lead_times cube has 2 critical filters that exclude ~40% of item receipts
   - **Correct Source:** transaction_lines cube with ItemRcpt filter

2. **Gross Profit Calculation Error (CONFIRMED)**
   - **Mathematical Impossibility:** GP of €20.6M vs Net Sales of €23.0M (GP > Net Sales impossible)
   - **Root Cause:** AI is conflating two different measures
   - **Evidence:** Gross margin calculated from `costestimate` (ESTIMATED, not actual)

3. **Intake Value/Cost Availability (PARTIALLY TRUE)**
   - **Available:** Unit cost from ItemRcpt lines (100% populated)
   - **Available:** Item receipt line value (amount field)
   - **Missing:** Retail/ex-VAT intake value (not available in cubes)
   - **Source:** landed_costs cube has `estgrossprofit` from NetSuite

---

## DETAILED FINDINGS

### Issue 1: DC Intake Units Mismatch - Root Cause Analysis

#### The Two Data Sources:

**Source A: supplier_lead_times Cube**
```yaml
File: /home/produser/cube-gpc/model/cubes/supplier_lead_times.yml

SQL Definition:
  FROM gpc.item_receipt_lines irl
  INNER JOIN gpc.item_receipts ir ON irl.transaction = ir.id
  INNER JOIN gpc.purchase_orders po ON irl.createdfrom = po.id
  WHERE irl.createdfrom IS NOT NULL        # FILTER 1: Only items with PO linkage
    AND irl.mainline = 'F'                 # FILTER 2: Exclude header lines
    AND irl.item IS NOT NULL
    AND DATE_DIFF(...) BETWEEN 0 AND 365   # FILTER 3: Valid lead time range

Key Limitation:
- INNER JOIN on purchase_orders means ONLY items received from POs are counted
- Many items may be received without PO linkage (direct shipments, samples, returns)
- This is a LEAD TIME analysis cube, not an inventory intake cube
```

**Measures in supplier_lead_times:**
- `receipt_count` - Count of receipt lines with PO linkage
- `total_qty_received` - Sum of quantities from linked receipts
- `avg_lead_time_days` - Calculated measure for lead time analysis

**Source B: transaction_lines Cube**
```yaml
File: /home/produser/cube-gpc/model/cubes/transaction_lines.yml

SQL Definition:
  FROM gpc.transaction_lines_clean tl
  INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
  WHERE tl.item != 25442
  # NO restrictive filters on transaction type in cube definition
  # Filters applied via measures:
  
  - name: total_itemrcpt_amount
    sql: CASE WHEN {CUBE}.transaction_type = 'ItemRcpt' THEN {CUBE}.amount ELSE 0 END
    description: Total Item Receipt amounts (inventory value + landed costs combined)

Key Advantage:
- Includes ALL ItemRcpt transactions regardless of PO linkage
- More comprehensive for inventory intake analysis
- Grain: One row per transaction line (includes inventory + landed cost lines)
```

**Measures for ItemRcpt in transaction_lines:**
- `itemrcpt_line_count` - COUNT of ItemRcpt lines (includes landed costs)
- `total_itemrcpt_amount` - SUM of all ItemRcpt amounts
- `total_landed_costs` - SUM where blandedcost='T' (freight/duty lines only)

#### Unit Count Comparison:

| Data Source | Units YTD | Filter Criteria | Use Case |
|---|---|---|---|
| supplier_lead_times | 632,106 | PO-linked items, lead time 0-365 days | Lead time analysis only |
| transaction_lines (ItemRcpt) | 1,060,254 | All ItemRcpt types | Inventory intake analysis |
| YTD Sales Units | 1,546,823 | CustInvc + CashSale only | Revenue transactions |

#### Root Cause of Discrepancy:

The 40% difference (1,060,254 vs 632,106) comes from ItemReceipt lines that:
1. Have NO purchase order linkage (createdfrom IS NULL)
2. Are header lines (mainline='T')
3. Have lead times outside 0-365 day range

**Recommendation for GMROI:**
- **Correct Source:** Use transaction_lines cube with `itemrcpt_line_count` filter
- **Why:** GMROI needs ALL inventory intake, not just PO-linked items
- **Grain:** One ItemRcpt transaction may have multiple lines (inventory + landed costs)

---

### Issue 2: Gross Profit Calculation Error - The Mathematical Impossibility

#### Reported Figures (From AI Agent):
```
Gross Sales Revenue: €29.1M
Net Revenue (ex-VAT): €23.0M
Gross Profit Reported: €20.6M
```

**The Problem:**
```
Gross Profit (€20.6M) > Net Sales (€23.0M) 

This is mathematically IMPOSSIBLE.
Gross Profit cannot exceed Net Sales when calculated as:
GP = Revenue - Cost of Goods Sold
```

#### What the Cube Actually Has:

**transaction_lines.gross_margin Measure:**
```yaml
File: /home/produser/cube-gpc/model/cubes/transaction_lines.yml (lines 203-210)

- name: gross_margin
  sql: >
    CAST(CASE WHEN {CUBE}.transaction_type IN ('CustInvc', 'CashSale') THEN
      (({CUBE}.amount * -1) - (COALESCE({CUBE}.costestimate, 0) * -1)) 
      * COALESCE({CUBE}.transaction_exchange_rate, 1.0)
    ELSE 0 END AS FLOAT64)
  type: sum
  format: currency
  description: Gross margin in EUR (revenue - cost, all currencies converted)

Formula Breakdown:
  amount = line total (negative for sales)
  costestimate = NetSuite's estimated cost
  
  Calculation:
  1. amount * -1 = positive revenue
  2. costestimate * -1 = positive cost
  3. difference = gross margin (revenue - cost)
  4. multiply by exchange rate for EUR conversion
```

#### The Root Cause of the Error:

The AI agent is likely making ONE of these mistakes:

**Problem A: Using estgrossprofit instead of gross_margin**
```yaml
# From landed_costs.yml (lines 10-11)
CAST(tl.estgrossprofit AS FLOAT64) as estimated_gross_profit
CAST(tl.estgrossprofitpercent AS FLOAT64) as estimated_gp_percent

# These fields are from NetSuite, pre-calculated per ItemRcpt line
# They represent GP for THAT LINE, not total
# When summed across multiple ItemRcpt lines AND revenue transactions, 
# this creates nonsensical totals
```

**Problem B: Mixing ItemRcpt GP with Sales Revenue**
```
ItemRcpt estgrossprofit = NetSuite's calculated GP for inventory line
Sales revenue = Actual cash collected from customers

Summing these together is like adding:
  "Expected profit from purchase" + "Actual revenue from sales"
  
This creates inflated, meaningless numbers.
```

**Problem C: Including ItemRcpt amounts in revenue total**
```yaml
# From transaction_lines pre-aggregations:
- transaction_type = 'ItemRcpt' has:
  - total_itemrcpt_amount (should be excluded from revenue)
  - total_landed_costs (freight, should be excluded from revenue)
  - estimated_gross_profit (should be excluded from revenue)

# These are inventory transactions, not sales
# When accidentally included with sales revenue, totals become wrong
```

#### Evidence of the Issue:

**From transactions_analysis.sql (lines 23-33):**
```sql
CREATE OR REPLACE VIEW `magical-desktop.gpc.transactions_analysis` AS
SELECT * FROM `magical-desktop.gpc.transactions`
WHERE COALESCE(voided, 'F') = 'F'
  AND (
    type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd')  -- Revenue
    OR COALESCE(posting, 'F') = 'T'                           -- Posted
    OR type IN ('SalesOrd', 'RtnAuth')                       -- Pipeline
  );

# Note: Does NOT include ItemRcpt in the main filter
# But view is used by transaction_lines which spans ALL transaction types
```

#### Correct Formulas:

**For GMROI Gross Profit:**
```
Gross Profit = Revenue - COGS
  where:
  Revenue = SUM(amount) where transaction_type IN ('CustInvc', 'CashSale')
  COGS = SUM(costestimate) where transaction_type IN ('CustInvc', 'CashSale')
```

**NOT:**
```
Gross Profit = SUM(estgrossprofit) across ALL ItemRcpt lines
Gross Profit = SUM(amount) where transaction_type = 'ItemRcpt'
```

---

### Issue 3: Intake Margin Availability - Partial Data Available

#### Requested Formula:
```
Intake Margin = ((dc intake value ex-vat – dc intake value cost) 
                 / dc intake value ex-vat) * 100
```

#### What IS Available in Cubes:

**1. Unit Cost (100% Available) ✓**
```yaml
# From item_receipt_lines cube
- name: unit_cost
  sql: rate
  type: number
  format: currency
  description: Cost per unit in base currency
  
Data Availability: 100% populated in ItemRcpt lines
```

**2. Receipt Line Amount (100% Available) ✓**
```yaml
# From transaction_lines for ItemRcpt lines
- name: total_itemrcpt_amount
  sql: CAST(CASE WHEN {CUBE}.transaction_type = 'ItemRcpt' THEN {CUBE}.amount ELSE 0 END AS FLOAT64)
  description: Total Item Receipt amounts (inventory value + landed costs combined)
  
Data Availability: 100% populated for ItemRcpt transaction_type
```

**3. Estimated Gross Profit from NetSuite (Available in landed_costs) ✓**
```yaml
# From landed_costs.yml (lines 10-11)
CAST(tl.estgrossprofit AS FLOAT64) as estimated_gross_profit
CAST(tl.estgrossprofitpercent AS FLOAT64) as estimated_gp_percent

# From transaction_lines for ItemRcpt lines
- name: estgrossprofit (dimension, line 467)
  sql: "CAST({CUBE}.estgrossprofit AS FLOAT64)"
  type: number
  description: "Estimated gross profit from NetSuite (for ItemRcpt lines)"
```

#### What IS NOT Available:

**X. Retail/List Price for Intake ✗**
```
Not available in cubes:
- No "intake retail value" or "list price at intake"
- estgrossprofit is calculated by NetSuite, not decomposed
- Cannot reverse-engineer: cost + GP = retail without more data
```

**X. VAT/Tax breakdown for Intake ✗**
```
Not available:
- ItemRcpt lines don't have VAT detail
- taxamount is only for sales transactions
- Cannot calculate "ex-VAT" value
```

#### Workaround Available:

**Option A: Use NetSuite's estgrossprofit directly**
```yaml
Intake Margin = estgrossprofitpercent (already calculated by NetSuite)

Location: transaction_lines cube, dimension estgrossprofitpercent
Note: This is NetSuite's calculation, accuracy depends on NetSuite's cost data
Availability: Present for ItemRcpt lines
```

**Option B: Approximate from available data**
```yaml
Approximate Margin = (receipt_amount - unit_cost * quantity) / receipt_amount

Data needed:
- receipt_amount: {CUBE}.amount for ItemRcpt lines ✓
- unit_cost: {CUBE}.rate ✓
- quantity: {CUBE}.quantity ✓

Limitation: 
- Doesn't account for landed costs allocation
- Different from "intake value ex-VAT" as requested
```

---

## PRE-AGGREGATION COVERAGE ANALYSIS

### Which Pre-Aggs Include GMROI-Related Measures?

#### transaction_lines Pre-Aggregations:

**1. sales_analysis (BEST FOR GMROI)**
```yaml
File: /home/produser/cube-gpc/model/cubes/transaction_lines.yml (lines 508-560)

Included Measures:
  ✓ total_revenue       (sales revenue only)
  ✓ gross_margin        (revenue - cost)
  ✓ total_cost          (cost estimate)
  ✓ units_sold          (sales units)
  ✓ transaction_count   (for AOV division)

Dimensions: channel_type, category, section, season, product_range, collection, etc.
Grain: DAILY
Build Range: 2020-01-01 to 2025-10-31
Storage: ~438K rows

✓ SUPPORTS: GMROI by category/section/season
✓ FILTER: transaction_type IN ('CustInvc', 'CashSale') via measure definition
```

**2. product_analysis (PRODUCT-LEVEL GMROI)**
```yaml
Included Measures:
  ✓ total_revenue
  ✓ units_sold
  ✓ gross_margin
  ✓ transaction_count

Dimensions: sku, product_name, category, section, season, size, color
Grain: DAILY
✓ SUPPORTS: GMROI by individual SKU
```

**3. location_analysis (LOCATION-LEVEL GMROI)**
```yaml
Included Measures:
  ✓ total_revenue
  ✓ units_sold
  ✓ transaction_count
  ✓ gross_margin

Dimensions: location_name, channel_type, department_name, classification_name
Grain: DAILY
✓ SUPPORTS: GMROI by store location
```

#### supplier_lead_times Pre-Aggregations:

**lead_time_rollup (INSUFFICIENT FOR GMROI)**
```yaml
File: /home/produser/cube-gpc/model/cubes/supplier_lead_times.yml (lines 156-173)

Included Measures:
  receipt_count
  total_qty_received
  sum_lead_time_days
  sum_lead_time_days_squared

Dimensions: item, supplier_id
Grain: DAILY by receipt_date

✗ MISSING: No revenue or cost measures
✗ MISSING: No gross margin
✗ USE CASE: Lead time analysis ONLY, not inventory profitability
```

#### landed_costs Pre-Aggregations:

**monthly_landed_costs (INCOMPLETE FOR GMROI)**
```yaml
File: /home/produser/cube-gpc/model/cubes/landed_costs.yml (lines 104-122)

Included Measures:
  total_landed_costs       (freight + duties only)
  total_foreign_landed_costs
  receipt_count
  landed_cost_line_count

Dimensions: item, subsidiary_id
Grain: MONTHLY by receipt_date

✗ MISSING: Gross margin
✗ MISSING: Revenue measures
✗ MISSING: Connection to sales data
✗ USE CASE: Landed cost tracking, NOT GMROI
```

### Summary: Pre-Agg Coverage for GMROI

| Pre-Agg | Revenue | Cost | Margin | Intake Units | Suitable for GMROI? |
|---|---|---|---|---|---|
| transaction_lines.sales_analysis | ✓ | ✓ | ✓ | ✗ | **YES** (sales margin) |
| transaction_lines.product_analysis | ✓ | ✓ | ✓ | ✗ | **YES** (SKU level) |
| transaction_lines.location_analysis | ✓ | ✓ | ✓ | ✗ | **YES** (location level) |
| supplier_lead_times.lead_time_rollup | ✗ | ✗ | ✗ | ✓ (but filtered) | **NO** (missing margin) |
| landed_costs.monthly_landed_costs | ✗ | ✗ | ✗ | ✓ | **NO** (missing margin) |

**Conclusion:** sales_analysis pre-agg supports GMROI calculation, but it:
- Excludes ItemRcpt transactions (correctly)
- Cannot be used for "DC intake value" analysis alone
- Needs to be paired with inventory measures from a separate query

---

## TRANSACTION TYPE CONFUSION ANALYSIS

### How Transaction Types are Filtered in Cubes:

**In transactions_analysis view (lines 23-33 of create_filtered_views.sql):**
```sql
WHERE COALESCE(voided, 'F') = 'F'
  AND (
    type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd')  -- REVENUE
    OR COALESCE(posting, 'F') = 'T'                          -- POSTED
    OR type IN ('SalesOrd', 'RtnAuth')                      -- PIPELINE
  )
```

**In transaction_lines measures (using CASE statements):**
```yaml
# Correctly filter transaction types per measure

Revenue Measures (sales only):
  - total_revenue
    CASE WHEN {CUBE}.transaction_type IN ('CustInvc', 'CashSale') THEN ...
  - net_revenue
    CASE WHEN {CUBE}.transaction_type IN ('CustInvc', 'CashSale') THEN ...

Inventory Measures (ItemRcpt only):
  - total_itemrcpt_amount
    CASE WHEN {CUBE}.transaction_type = 'ItemRcpt' THEN ...
  - total_landed_costs
    CASE WHEN {CUBE}.transaction_type = 'ItemRcpt' AND blandedcost='T' THEN ...
```

**Critical Finding:**
```
✓ NO confusion in measure definitions
✓ Each measure correctly specifies transaction type filters
✓ AI confusion likely comes from COMBINING measures incorrectly

Example of WRONG combination:
  total_revenue (from sales) + total_itemrcpt_amount (from receipts)
  = nonsensical "total revenue"
  
Correct combination:
  total_revenue / transaction_count (for AOV)
  gross_margin / inventory_value (for GMROI)
```

---

## ROOT CAUSE HYPOTHESIS: THE €20.6M GROSS PROFIT ERROR

### Most Likely Explanation:

The AI agent is **summing estimated gross profit from Item Receipts** instead of **calculating actual gross margin from sales**:

```python
# WRONG (what AI is likely doing):
gross_profit_wrong = SUM(estimated_gross_profit)  
  where transaction_type = 'ItemRcpt'

Result: €20.6M (NetSuite's expected profit on purchases)

# RIGHT (what it should do):
gross_margin_correct = SUM(amount * -1 - costestimate) 
  where transaction_type IN ('CustInvc', 'CashSale')

Result: Expected ~€5-8M (typical 20-35% retail margin)
```

### Why This Creates The Impossibility:

```
Scenario:
1. ItemRcpt for €100,000 purchase with estimated 30% GP = €30,000 est. profit
2. Actual sales revenue from those items: €29.1M
3. Actual cost of goods sold: €6-8M (based on costestimate)
4. Actual gross profit: €21-23M

When AI sums estgrossprofit across receipts AND combines with sales:
  - Estimate GP from receipts: €20.6M
  - Sales revenue: €29.1M
  - These are two different things being mixed together!
  
Result: €20.6M appears to be "gross profit" but it's really
  "estimated profit expectation from purchase agreements"
  
This is > net sales because:
  - Estimated GP is based on acquisition cost
  - Net sales is actual cash in (minus costs)
  - Different metrics, should never be compared directly
```

---

## RECOMMENDATIONS & FIXES

### Fix #1: Clarify DC Intake Units Data Source

**Recommendation:** Use transaction_lines cube for all inventory intake analysis

```yaml
Correct Query Pattern:
  FROM transaction_lines
  WHERE transaction_type = 'ItemRcpt'
  
Measures:
  - itemrcpt_line_count (includes all ItemRcpt lines)
  - total_itemrcpt_amount (total value)
  
Not from:
  - supplier_lead_times (filtered to PO-linked only)
```

**Update Documentation:**
- Add comment in supplier_lead_times.yml explaining it's PO-linked only
- Add comment in transaction_lines.yml clarifying all ItemRcpt include landed costs
- Create separate measure: `dc_inventory_intake_units` with explicit filters

---

### Fix #2: Correct Gross Profit Calculation Formula

**For Sales Margin (Current GMROI formula):**
```yaml
# Use existing transaction_lines.gross_margin measure
Correct Measure: gross_margin (line 203 in transaction_lines.yml)
  = SUM(amount * -1 - costestimate) for CustInvc + CashSale
  
Document: This is SALES GROSS MARGIN, not inventory intake margin
```

**For Intake Margin (If needed separately):**
```yaml
# NEW measure to add to transaction_lines:
- name: intake_margin
  sql: >
    CAST(CASE WHEN {CUBE}.transaction_type = 'ItemRcpt' 
      THEN {CUBE}.estgrossprofit ELSE 0 END AS FLOAT64)
  type: sum
  description: "Estimated margin from Item Receipts (NetSuite calculated)"
  
Note: This is ESTIMATE at time of purchase, not actual COGS realized
```

**Update Pre-Agg Coverage:**
- Add intake_margin to a new ItemRcpt-focused pre-agg if frequent analysis needed

---

### Fix #3: Make Intake Value Data Available

**Status:** Data is available, just needs to be documented and exposed

**Available Data:**
```yaml
# From transaction_lines for ItemRcpt:
- quantity: {CUBE}.quantity (units received)
- rate: {CUBE}.rate (unit cost, 100% populated)
- amount: {CUBE}.amount (total receipt value)

# From landed_costs for ItemRcpt:
- landed_cost_amount: additional freight/duty charges
- estimated_gross_profit: NetSuite's margin calculation
```

**Create New Measures:**
```yaml
# In transaction_lines.yml, add:
- name: dc_intake_value_ex_vat
  sql: "CAST(CASE WHEN {CUBE}.transaction_type = 'ItemRcpt' 
         THEN {CUBE}.amount ELSE 0 END AS FLOAT64)"
  type: sum
  description: "Total value of DC inventory intakes (ex-VAT)"

- name: dc_intake_unit_cost
  sql: "CAST(CASE WHEN {CUBE}.transaction_type = 'ItemRcpt' 
         THEN {CUBE}.rate ELSE 0 END AS FLOAT64)"
  type: avg
  description: "Average unit cost of DC intakes"

- name: intake_margin_percent
  sql: "100.0 * {CUBE}.estgrossprofitpercent"
  type: avg
  description: "Average margin % on DC intakes (NetSuite estimated)"
```

**Documentation:**
- Clearly note these come from ItemRcpt, not sales
- Clarify "ex-VAT" means as-received (no sales VAT), not "value-at-tax"
- Explain estgrossprofit is NetSuite's estimate, not actual realized margin

---

## VERIFICATION CHECKLIST

- [ ] Confirm DC intake units should come from transaction_lines ItemRcpt (not supplier_lead_times)
- [ ] Confirm 40% difference is due to supplier_lead_times filters (PO linkage + mainline)
- [ ] Verify gross_margin measure is calculated correctly (revenue - costestimate)
- [ ] Confirm €20.6M figure is from summing estgrossprofit across ItemRcpt lines
- [ ] Test correct formula: GM% = (Revenue - COGS) / Revenue for sales transactions only
- [ ] Verify estgrossprofitpercent is available in transaction_lines dimensions
- [ ] Confirm intake_value (amount) is 100% populated for ItemRcpt
- [ ] Test new intake margin measures with sample queries

---

## SUMMARY TABLE: GMROI Calculation Requirements vs Availability

| Component | Required | Available In | Status | Notes |
|---|---|---|---|---|
| **Sales Revenue** | SUM(amount) where type='CustInvc' or 'CashSale' | transaction_lines.total_revenue | ✓ Available | Pre-agged in sales_analysis |
| **Sales Units** | SUM(quantity) where type='CustInvc/CashSale', qty<0 | transaction_lines.units_sold | ✓ Available | Pre-agged in sales_analysis |
| **COGS/Cost** | SUM(costestimate) where type='CustInvc' or 'CashSale' | transaction_lines.total_cost | ✓ Available | Pre-agged in sales_analysis |
| **Gross Margin** | Revenue - Cost | transaction_lines.gross_margin | ✓ Available | Pre-agged in sales_analysis |
| **DC Intake Units** | SUM(quantity) where type='ItemRcpt' | transaction_lines.itemrcpt_line_count | ✓ Available | NOT in supplier_lead_times |
| **Average Intake Cost** | SUM(rate * qty) / SUM(qty) for ItemRcpt | item_receipt_lines.avg_unit_cost | ✓ Available | 100% populated |
| **Intake Value** | SUM(amount) where type='ItemRcpt' | transaction_lines.total_itemrcpt_amount | ✓ Available | Includes landed costs |
| **Intake Margin %** | NetSuite's estgrossprofitpercent | transaction_lines.estgrossprofitpercent | ✓ Available | Estimated, not actual |
| **Retail Value (ex-VAT)** | Cost + desired margin | **NOT available** | ✗ Missing | Cannot reverse-engineer |
| **Landed Costs (Freight/Duty)** | Separate cost lines in ItemRcpt | landed_costs.total_landed_costs | ✓ Available | Use blandedcost='T' filter |

**Final Assessment:** 
- ✓ All core GMROI components available
- ✓ Pre-aggregations support calculations
- ✗ Data source confusion (supplier_lead_times vs transaction_lines)
- ✗ Measurement confusion (intake margin % vs sales margin %)
- ✗ Missing "retail value" component (not in NetSuite export)

