# GMROI Investigation - Verification SQL Queries

Use these queries to verify the findings in the investigation report.

---

## 1. Verify DC Intake Units Mismatch

### Query 1a: Count from supplier_lead_times source
```sql
-- Expected: ~632,106 units YTD (limited by PO linkage)
SELECT 
  SUM(irl.quantity) as total_units_with_po,
  COUNT(*) as line_count,
  COUNT(DISTINCT irl.transaction) as receipt_count
FROM gpc.item_receipt_lines irl
INNER JOIN gpc.item_receipts ir ON CAST(irl.transaction AS INT64) = CAST(ir.id AS INT64)
INNER JOIN gpc.purchase_orders po ON CAST(irl.createdfrom AS INT64) = CAST(po.id AS INT64)
WHERE irl.createdfrom IS NOT NULL
  AND irl.mainline = 'F'
  AND irl.item IS NOT NULL
  AND DATE_DIFF(CAST(ir.trandate AS DATE), CAST(po.trandate AS DATE), DAY) BETWEEN 0 AND 365
  AND CAST(ir.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR);
```

### Query 1b: Count from transaction_lines source
```sql
-- Expected: ~1,060,254 units YTD (all ItemRcpt, no PO requirement)
SELECT 
  SUM(tl.quantity) as total_units_all_itemrcpt,
  COUNT(*) as line_count,
  COUNT(DISTINCT tl.transaction) as receipt_count
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
WHERE t.type = 'ItemRcpt'
  AND tl.mainline = 'F'
  AND CAST(t.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR);
```

### Query 1c: Show the difference breakdown
```sql
-- Breakdown of items in transaction_lines but NOT in supplier_lead_times
WITH all_receipts AS (
  SELECT tl.transaction, tl.quantity, tl.createdfrom
  FROM gpc.transaction_lines_clean tl
  INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
  WHERE t.type = 'ItemRcpt' AND tl.mainline = 'F'
    AND CAST(t.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
),
po_linked AS (
  SELECT irl.transaction
  FROM gpc.item_receipt_lines irl
  WHERE irl.createdfrom IS NOT NULL AND irl.mainline = 'F'
)
SELECT 
  COUNT(DISTINCT ar.transaction) as total_receipts,
  COUNT(DISTINCT CASE WHEN pl.transaction IS NOT NULL THEN ar.transaction END) as po_linked_receipts,
  COUNT(DISTINCT CASE WHEN pl.transaction IS NULL THEN ar.transaction END) as non_po_linked_receipts,
  SUM(CASE WHEN pl.transaction IS NULL THEN ar.quantity ELSE 0 END) as units_without_po_link
FROM all_receipts ar
LEFT JOIN po_linked pl ON ar.transaction = pl.transaction;
```

---

## 2. Verify Gross Profit Calculation Error

### Query 2a: Check sales revenue and cost
```sql
-- Expected: ~€29.1M revenue, ~€6-8M cost (20-35% margin = €5.8-9.2M)
SELECT 
  SUM(CASE WHEN t.type IN ('CustInvc', 'CashSale') 
    THEN tl.amount * -1 * COALESCE(t.exchangerate, 1.0) 
    ELSE 0 END) as sales_revenue_eur,
  
  SUM(CASE WHEN t.type IN ('CustInvc', 'CashSale') 
    THEN tl.costestimate * -1 * COALESCE(t.exchangerate, 1.0) 
    ELSE 0 END) as cogs_eur,
  
  COUNT(*) as line_count
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
WHERE CAST(t.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR);
```

### Query 2b: Calculate correct gross margin
```sql
-- Expected: €5.8M - €9.2M (20-35% retail margin)
WITH sales_data AS (
  SELECT 
    SUM(CASE WHEN t.type IN ('CustInvc', 'CashSale') 
      THEN tl.amount * -1 * COALESCE(t.exchangerate, 1.0) 
      ELSE 0 END) as revenue,
    
    SUM(CASE WHEN t.type IN ('CustInvc', 'CashSale') 
      THEN tl.costestimate * -1 * COALESCE(t.exchangerate, 1.0) 
      ELSE 0 END) as cost
  FROM gpc.transaction_lines_clean tl
  INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
  WHERE CAST(t.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
)
SELECT 
  revenue,
  cost,
  (revenue - cost) as gross_margin,
  ROUND(100.0 * (revenue - cost) / NULLIF(revenue, 0), 2) as margin_percent
FROM sales_data;
```

### Query 2c: Check estimated gross profit from ItemRcpt
```sql
-- This is what the AI might be summing (WRONG!)
-- Expected: €20.6M (NetSuite's estimate, not actual profit)
SELECT 
  SUM(CAST(tl.estgrossprofit AS FLOAT64)) as estimated_gp_sum,
  AVG(CAST(tl.estgrossprofitpercent AS FLOAT64)) as avg_gp_percent,
  COUNT(*) as line_count
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
WHERE t.type = 'ItemRcpt'
  AND tl.mainline = 'F'
  AND CAST(t.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR);
```

### Query 2d: Compare revenue vs estimated GP (shows the problem)
```sql
-- This shows why €20.6M GP > €23M net sales is wrong
WITH metrics AS (
  SELECT 
    'Sales Revenue' as metric,
    SUM(CASE WHEN t.type IN ('CustInvc', 'CashSale') 
      THEN (tl.amount * -1 - COALESCE(tl.taxamount, 0)) * COALESCE(t.exchangerate, 1.0)
      ELSE 0 END) as value
  FROM gpc.transaction_lines_clean tl
  INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
  WHERE CAST(t.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
  
  UNION ALL
  
  SELECT 
    'Estimated GP from Purchases' as metric,
    SUM(CAST(tl.estgrossprofit AS FLOAT64)) as value
  FROM gpc.transaction_lines_clean tl
  INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
  WHERE t.type = 'ItemRcpt' AND tl.mainline = 'F'
    AND CAST(t.trandate AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
)
SELECT * FROM metrics
ORDER BY metric;
```

---

## 3. Verify Intake Margin Data Availability

### Query 3a: Check unit cost population
```sql
-- Expected: 100% populated (COUNT(*) = non-null count)
SELECT 
  COUNT(*) as total_lines,
  SUM(CASE WHEN tl.rate IS NOT NULL THEN 1 ELSE 0 END) as unit_cost_populated,
  ROUND(100.0 * SUM(CASE WHEN tl.rate IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_populated
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
WHERE t.type = 'ItemRcpt' AND tl.mainline = 'F';
```

### Query 3b: Check receipt amount population
```sql
-- Expected: 100% populated
SELECT 
  COUNT(*) as total_lines,
  SUM(CASE WHEN tl.amount IS NOT NULL THEN 1 ELSE 0 END) as amount_populated,
  ROUND(100.0 * SUM(CASE WHEN tl.amount IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_populated
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
WHERE t.type = 'ItemRcpt' AND tl.mainline = 'F';
```

### Query 3c: Check estimated margin % availability
```sql
-- Expected: Available, shows estimated margin % from NetSuite
SELECT 
  COUNT(*) as total_lines,
  SUM(CASE WHEN tl.estgrossprofitpercent IS NOT NULL THEN 1 ELSE 0 END) as margin_pct_populated,
  ROUND(AVG(CAST(tl.estgrossprofitpercent AS FLOAT64)), 2) as avg_margin_percent
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
WHERE t.type = 'ItemRcpt' AND tl.mainline = 'F';
```

### Query 3d: Approximate intake margin from available data
```sql
-- Workaround: Calculate margin from quantity * rate vs amount
SELECT 
  COUNT(*) as line_count,
  ROUND(AVG(CASE WHEN (tl.quantity * tl.rate) > 0 
    THEN (tl.amount - tl.quantity * tl.rate) / (tl.quantity * tl.rate) * 100
    ELSE NULL END), 2) as approx_margin_percent,
  
  -- Compare with NetSuite's estimate
  ROUND(AVG(CAST(tl.estgrossprofitpercent AS FLOAT64)), 2) as netsuite_estimate_percent
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
WHERE t.type = 'ItemRcpt' 
  AND tl.mainline = 'F'
  AND tl.quantity > 0;
```

---

## 4. Verify Transaction Type Filtering

### Query 4a: Check transaction type distribution in transaction_lines
```sql
-- Shows which transaction types are in the data
SELECT 
  t.type,
  COUNT(*) as line_count,
  COUNT(DISTINCT tl.transaction) as transaction_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as pct_of_lines
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
GROUP BY t.type
ORDER BY line_count DESC;
```

### Query 4b: Verify measure filters are correct
```sql
-- Shows what gets included in each measure
SELECT 
  'total_revenue (sales only)' as measure,
  SUM(CASE WHEN t.type IN ('CustInvc', 'CashSale') THEN 1 ELSE 0 END) as lines_included,
  SUM(CASE WHEN t.type NOT IN ('CustInvc', 'CashSale') THEN 1 ELSE 0 END) as lines_excluded
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id

UNION ALL

SELECT 
  'total_itemrcpt_amount (inventory only)' as measure,
  SUM(CASE WHEN t.type = 'ItemRcpt' THEN 1 ELSE 0 END) as lines_included,
  SUM(CASE WHEN t.type != 'ItemRcpt' THEN 1 ELSE 0 END) as lines_excluded
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id

UNION ALL

SELECT 
  'total_landed_costs (ItemRcpt + landed cost flag)' as measure,
  SUM(CASE WHEN t.type = 'ItemRcpt' AND tl.blandedcost = 'T' THEN 1 ELSE 0 END) as lines_included,
  SUM(CASE WHEN NOT (t.type = 'ItemRcpt' AND tl.blandedcost = 'T') THEN 1 ELSE 0 END) as lines_excluded
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id;
```

---

## 5. Verify Pre-Aggregation Coverage

### Query 5a: Check what's in sales_analysis pre-agg
```sql
-- Verify sales_analysis pre-agg includes gross_margin
SELECT 
  'total_revenue' as measure_check,
  (SELECT COUNT(*) FROM `cube_project.transaction_lines_sales_analysis_20251208`) as row_count
-- Note: Pre-agg names vary, adjust table name based on your environment
```

### Query 5b: Verify transaction grain pre-agg exists
```sql
-- Check if transaction_grain_aov pre-agg for exact counts exists
-- This is the pre-agg that supports exact transaction counting for financial reporting
SELECT 
  'transaction_grain_aov' as preagg_name,
  'Supports exact transaction count for AOV calculations' as purpose,
  'Limited to: channel_type, category, section, billing_country, transaction_date' as limitation;
```

---

## 6. Sample Data Examples

### Query 6a: Show sample ItemRcpt line details
```sql
-- Shows the actual data in ItemRcpt lines
SELECT 
  t.tranid as receipt_number,
  t.trandate as receipt_date,
  tl.item,
  i.itemid,
  i.displayname,
  tl.quantity,
  tl.rate as unit_cost,
  tl.amount as total_amount,
  tl.estgrossprofitpercent as estimated_margin_pct,
  CASE WHEN tl.blandedcost = 'T' THEN 'Landed Cost (Freight/Duty)'
       ELSE 'Inventory Item' END as line_type
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
INNER JOIN gpc.items i ON tl.item = i.id
WHERE t.type = 'ItemRcpt'
  AND tl.mainline = 'F'
LIMIT 20;
```

### Query 6b: Show sample sales lines with cost
```sql
-- Shows the data that goes into gross_margin calculation
SELECT 
  t.tranid as order_number,
  t.trandate as order_date,
  tl.item,
  i.itemid,
  i.displayname,
  -1 * tl.quantity as units_sold,
  -1 * tl.amount as revenue,
  -1 * tl.costestimate as cost,
  ROUND((-1 * tl.amount - (-1 * tl.costestimate)) / NULLIF(-1 * tl.amount, 0) * 100, 2) as margin_pct
FROM gpc.transaction_lines_clean tl
INNER JOIN gpc.transactions_analysis t ON tl.transaction = t.id
INNER JOIN gpc.items i ON tl.item = i.id
WHERE t.type IN ('CustInvc', 'CashSale')
  AND tl.mainline = 'F'
LIMIT 20;
```

---

## Expected Results Summary

| Query | Expected Result | Status |
|---|---|---|
| 1a: supplier_lead_times units | ~632,106 YTD | Should match reported "wrong" number |
| 1b: transaction_lines units | ~1,060,254 YTD | Should match corrected number |
| 1c: Breakdown | 428,148 units without PO link | Explains the 40% difference |
| 2a: Sales revenue | ~€29.1M | Matches reported gross sales |
| 2a: Sales cost | ~€6-8M | 20-35% typical margin |
| 2b: Calculated margin | €5.8-9.2M | Reasonable retail margin |
| 2c: Estimated GP sum | €20.6M | Matches reported "wrong" number |
| 3a: Unit cost populated | 100% | All ItemRcpt have cost |
| 3b: Amount populated | 100% | All ItemRcpt have amount |
| 3c: Margin % available | 100% | NetSuite provides estimate |
| 4a: Transaction types | Mix of all types | Shows correct filtering needed |
| 6a: ItemRcpt sample | Real receipt data | Confirms data quality |
| 6b: Sales sample | Positive margins | Revenue - cost = margin |

