#!/bin/bash

# SQL Query Validation Script for Cube YML Files
# Tests each SQL query against BigQuery using --dry_run flag

set -e

RESULTS_FILE="/tmp/cube_sql_validation_results.txt"
ERROR_FILE="/tmp/cube_sql_validation_errors.txt"

echo "==================================================" > "$RESULTS_FILE"
echo "Cube YML SQL Validation Report" >> "$RESULTS_FILE"
echo "Test Date: $(date)" >> "$RESULTS_FILE"
echo "==================================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

> "$ERROR_FILE"  # Clear error file

TOTAL_QUERIES=0
PASSED_QUERIES=0
FAILED_QUERIES=0

test_sql_query() {
    local file_name="$1"
    local sql_query="$2"

    TOTAL_QUERIES=$((TOTAL_QUERIES + 1))

    echo "Testing: $file_name" >> "$RESULTS_FILE"
    echo "----------------------------------------" >> "$RESULTS_FILE"

    # Create temp file for SQL
    local temp_sql_file=$(mktemp)
    echo "SELECT * FROM (" > "$temp_sql_file"
    echo "$sql_query" >> "$temp_sql_file"
    echo ") LIMIT 1" >> "$temp_sql_file"

    # Run BigQuery dry run validation
    if bq query --use_legacy_sql=false --dry_run < "$temp_sql_file" 2>&1 | tee /tmp/bq_output.txt | grep -q "Query successfully validated"; then
        echo "✅ PASSED" >> "$RESULTS_FILE"
        PASSED_QUERIES=$((PASSED_QUERIES + 1))
    else
        echo "❌ FAILED" >> "$RESULTS_FILE"
        FAILED_QUERIES=$((FAILED_QUERIES + 1))

        # Capture error details
        echo "" >> "$ERROR_FILE"
        echo "==================================================" >> "$ERROR_FILE"
        echo "File: $file_name" >> "$ERROR_FILE"
        echo "==================================================" >> "$ERROR_FILE"
        cat /tmp/bq_output.txt >> "$ERROR_FILE"

        # Add error summary to main results
        echo "" >> "$RESULTS_FILE"
        echo "Error details:" >> "$RESULTS_FILE"
        cat /tmp/bq_output.txt >> "$RESULTS_FILE"
    fi

    echo "" >> "$RESULTS_FILE"

    rm -f "$temp_sql_file"
}

# Test b2c_customer_channels.yml
SQL_B2C_CHANNELS='SELECT
  t.custbody_customer_email as email,
  t.billing_country,
  CASE
    WHEN l.name IS NULL THEN '"'"'D2C'"'"'
    WHEN l.name LIKE '"'"'Bleckmann%'"'"' AND l.name NOT LIKE '"'"'%Quarantine%'"'"' AND l.name NOT LIKE '"'"'%Miscellaneous%'"'"' THEN '"'"'D2C'"'"'
    WHEN l.name IN ('"'"'Meteor Space'"'"', '"'"'2Flow'"'"') THEN '"'"'D2C'"'"'
    WHEN l.name IN (
      '"'"'Dundrum Town Centre'"'"', '"'"'Mahon Point'"'"', '"'"'Crescent Centre'"'"', '"'"'Liffey Valley'"'"',
      '"'"'Kildare Village'"'"', '"'"'Blanchardstown Centre'"'"', '"'"'Galway'"'"', '"'"'Swords Pavillon'"'"', '"'"'Jervis Centre'"'"',
      '"'"'Westfield London'"'"', '"'"'Manchester'"'"', '"'"'Belfast'"'"', '"'"'Liverpool'"'"'
    ) THEN '"'"'RETAIL'"'"'
    WHEN l.name LIKE '"'"'Wholesale%'"'"' THEN '"'"'B2B_WHOLESALE'"'"'
    WHEN l.name LIKE '"'"'Lifestyle Sports%'"'"' AND l.name NOT LIKE '"'"'%Quarantine%'"'"' THEN '"'"'B2B_WHOLESALE'"'"'
    WHEN l.name IN ('"'"'Otrium'"'"', '"'"'The Very Group'"'"', '"'"'Digme'"'"', '"'"'Academy Crests'"'"') THEN '"'"'PARTNER'"'"'
    WHEN l.name LIKE '"'"'Events%'"'"' THEN '"'"'EVENTS'"'"'
    ELSE '"'"'OTHER'"'"'
  END as channel_type,
  MIN(CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"', '"'"'SalesOrd'"'"')
    THEN t.trandate
  END) as first_order_date,
  MAX(CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"', '"'"'SalesOrd'"'"')
    THEN t.trandate
  END) as last_order_date,
  CAST(COUNT(DISTINCT CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"', '"'"'SalesOrd'"'"')
    THEN t.id
  END) AS INT64) as order_count,
  CAST(SUM(CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"', '"'"'SalesOrd'"'"')
    THEN tl.amount
    ELSE 0
  END) AS FLOAT64) as channel_lifetime_value,
  CAST(COUNT(DISTINCT CASE WHEN t.type = '"'"'CustInvc'"'"' THEN t.id END) AS INT64) as invoice_orders,
  CAST(COUNT(DISTINCT CASE WHEN t.type = '"'"'CashSale'"'"' THEN t.id END) AS INT64) as cash_sale_orders,
  CAST(COUNT(DISTINCT CASE WHEN t.type = '"'"'SalesOrd'"'"' THEN t.id END) AS INT64) as salesord_orders,
  CAST(SUM(CASE WHEN t.type = '"'"'CustInvc'"'"' THEN tl.amount ELSE 0 END) AS FLOAT64) as invoice_revenue,
  CAST(SUM(CASE WHEN t.type = '"'"'CashSale'"'"' THEN tl.amount ELSE 0 END) AS FLOAT64) as cash_sale_revenue,
  CAST(SUM(CASE WHEN t.type = '"'"'SalesOrd'"'"' THEN tl.amount ELSE 0 END) AS FLOAT64) as salesord_revenue
FROM gpc.transaction_lines tl
JOIN gpc.transactions_analysis t ON tl.transaction = t.id
LEFT JOIN gpc.locations l ON tl.location = l.id
WHERE t.custbody_customer_email IS NOT NULL
  AND t.custbody_customer_email != '"'"''"'"'
GROUP BY
  t.custbody_customer_email,
  t.billing_country,
  channel_type'

test_sql_query "b2c_customer_channels.yml" "$SQL_B2C_CHANNELS"

# Test b2c_customers.yml
SQL_B2C_CUSTOMERS='SELECT
  t.custbody_customer_email as email,
  t.billing_country,
  MIN(CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"')
    THEN t.trandate
  END) as first_order_date,
  MAX(CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"')
    THEN t.trandate
  END) as last_order_date,
  CAST(COUNT(DISTINCT CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"')
    THEN t.id
  END) AS INT64) as order_count,
  CAST(SUM(CASE
    WHEN t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"')
    THEN t.foreigntotal
    ELSE 0
  END) AS FLOAT64) as lifetime_value,
  CAST(COUNT(DISTINCT CASE WHEN t.type = '"'"'CustInvc'"'"' THEN t.id END) AS INT64) as invoice_orders,
  CAST(COUNT(DISTINCT CASE WHEN t.type = '"'"'CashSale'"'"' THEN t.id END) AS INT64) as cash_sale_orders,
  CAST(COUNT(DISTINCT CASE WHEN t.type = '"'"'SalesOrd'"'"' THEN t.id END) AS INT64) as salesord_orders,
  CAST(SUM(CASE WHEN t.type = '"'"'CustInvc'"'"' THEN t.foreigntotal ELSE 0 END) AS FLOAT64) as invoice_revenue,
  CAST(SUM(CASE WHEN t.type = '"'"'CashSale'"'"' THEN t.foreigntotal ELSE 0 END) AS FLOAT64) as cash_sale_revenue,
  CAST(SUM(CASE WHEN t.type = '"'"'SalesOrd'"'"' THEN t.foreigntotal ELSE 0 END) AS FLOAT64) as salesord_revenue
FROM gpc.transactions_analysis t
WHERE t.custbody_customer_email IS NOT NULL
  AND t.custbody_customer_email != '"'"''"'"'
GROUP BY t.custbody_customer_email, t.billing_country'

test_sql_query "b2c_customers.yml" "$SQL_B2C_CUSTOMERS"

# Test cross_sell.yml
SQL_CROSS_SELL='SELECT
  tl1.item as item_a,
  tl2.item as item_b,
  i1.itemid as item_a_sku,
  i2.itemid as item_b_sku,
  i1.displayname as item_a_name,
  i2.displayname as item_b_name,
  i1.custitem_gpc_category as item_a_category,
  i2.custitem_gpc_category as item_b_category,
  i1.custitem_gpc_sections as item_a_section,
  i2.custitem_gpc_sections as item_b_section,
  t.type as transaction_type,
  CAST(t.trandate AS TIMESTAMP) as trandate,
  CAST(COUNT(DISTINCT tl1.transaction) AS INT64) as co_purchase_count
FROM gpc.transaction_lines_clean tl1
JOIN gpc.transaction_lines_clean tl2 ON tl1.transaction = tl2.transaction AND tl1.item < tl2.item
JOIN gpc.transactions_clean t ON tl1.transaction = t.id
JOIN gpc.items i1 ON tl1.item = i1.id
JOIN gpc.items i2 ON tl2.item = i2.id
WHERE tl1.quantity < 0
  AND tl2.quantity < 0
GROUP BY tl1.item, tl2.item, i1.itemid, i2.itemid, i1.displayname, i2.displayname,
         i1.custitem_gpc_category, i2.custitem_gpc_category,
         i1.custitem_gpc_sections, i2.custitem_gpc_sections,
         t.type, CAST(t.trandate AS TIMESTAMP)'

test_sql_query "cross_sell.yml" "$SQL_CROSS_SELL"

# Test item_receipt_lines.yml
SQL_ITEM_RECEIPT='SELECT
  irl.*,
  CAST(ir.trandate AS TIMESTAMP) as receipt_date,
  i.displayname as item_displayname,
  i.itemid as item_sku
FROM gpc.item_receipt_lines irl
LEFT JOIN gpc.item_receipts ir ON CAST(irl.transaction AS INT64) = CAST(ir.id AS INT64)
LEFT JOIN gpc.items i ON irl.item = i.id
WHERE irl.mainline = '"'"'F'"'"''

test_sql_query "item_receipt_lines.yml" "$SQL_ITEM_RECEIPT"

# Test landed_costs.yml
SQL_LANDED_COSTS='SELECT
  tl.transaction,
  tl.id as line_id,
  tl.item,
  CAST(tl.amount AS FLOAT64) as landed_cost_amount,
  CAST(tl.foreignamount AS FLOAT64) as foreign_landed_cost,
  CAST(tl.estgrossprofit AS FLOAT64) as estimated_gross_profit,
  CAST(tl.estgrossprofitpercent AS FLOAT64) as estimated_gp_percent,
  CAST(tl.subsidiary AS INT64) as subsidiary_id,
  t.trandate as receipt_date,
  t.tranid as receipt_number,
  t.type as transaction_type
FROM gpc.transaction_lines tl
INNER JOIN gpc.transactions t ON tl.transaction = t.id
WHERE t.type = '"'"'ItemRcpt'"'"'
  AND tl.blandedcost = '"'"'T'"'"'
  AND tl.mainline = FALSE'

test_sql_query "landed_costs.yml" "$SQL_LANDED_COSTS"

# Test on_order_inventory.yml
SQL_ON_ORDER='SELECT
  pol.id,
  pol.po_id,
  pol.item,
  pol.quantity,
  pol.quantityshiprecv,
  pol.unit_cost,
  (pol.quantity - COALESCE(pol.quantityshiprecv, 0)) as qty_on_order,
  (pol.quantity - COALESCE(pol.quantityshiprecv, 0)) * pol.unit_cost as line_on_order_value,
  po.status as po_status,
  CAST(po.trandate AS TIMESTAMP) as po_date,
  i.itemid,
  i.displayname
FROM gpc.purchase_order_lines pol
LEFT JOIN gpc.purchase_orders po ON pol.po_id = po.id
LEFT JOIN gpc.items i ON pol.item = i.id
WHERE po.status IN ('"'"'B'"'"', '"'"'D'"'"', '"'"'E'"'"')
  AND (pol.quantity - COALESCE(pol.quantityshiprecv, 0)) > 0'

test_sql_query "on_order_inventory.yml" "$SQL_ON_ORDER"

# Test order_baskets.yml
SQL_ORDER_BASKETS='SELECT
  tl.transaction as order_id,
  CAST(t.trandate AS TIMESTAMP) as trandate,
  t.type,
  t.custbody_customer_email as customer_email,
  t.billing_country,
  CAST(COUNT(*) AS FLOAT64) as line_count,
  CAST(SUM(CASE WHEN tl.quantity < 0 THEN ABS(tl.quantity) ELSE 0 END) AS FLOAT64) as units,
  CAST(SUM(tl.amount * -1) AS FLOAT64) as order_total,
  CASE
    WHEN COUNT(*) = 1 THEN '"'"'1 item'"'"'
    WHEN COUNT(*) = 2 THEN '"'"'2 items'"'"'
    WHEN COUNT(*) = 3 THEN '"'"'3 items'"'"'
    ELSE '"'"'4+ items'"'"'
  END as line_count_bucket,
  CASE
    WHEN b2b.id IS NOT NULL THEN '"'"'B2B/Wholesale'"'"'
    ELSE '"'"'Retail/D2C'"'"'
  END as customer_type
FROM gpc.transaction_lines_clean tl
JOIN gpc.transactions_clean t ON tl.transaction = t.id
LEFT JOIN gpc.b2b_customers b2b ON t.entity = b2b.id
GROUP BY tl.transaction, CAST(t.trandate AS TIMESTAMP), t.type, t.custbody_customer_email, t.billing_country, customer_type'

test_sql_query "order_baskets.yml" "$SQL_ORDER_BASKETS"

# Test sell_through_seasonal.yml
SQL_SELL_THROUGH='SELECT
  tl.item,
  i.itemid,
  i.displayname,
  i.custitem_gpc_season as season,
  i.custitem_gpc_category as category,
  i.custitem_gpc_sections as section,
  i.custitem_gpc_size as size,
  i.custitem_gpc_child_colour as color,
  SUM(CASE
    WHEN i.custitem_gpc_season IS NOT NULL
      AND i.custitem_gpc_season != '"'"''"'"'
    THEN ABS(tl.quantity)
    ELSE 0
  END) as units_sold_in_season,
  SUM(CASE
    WHEN i.custitem_gpc_season IS NOT NULL
      AND i.custitem_gpc_season != '"'"''"'"'
    THEN CAST(tl.amount AS FLOAT64)
    ELSE 0
  END) as revenue_in_season,
  COALESCE(MAX(inv.current_stock), 0) as current_stock
FROM gpc.transaction_lines_clean tl
LEFT JOIN gpc.transactions_analysis t ON tl.transaction = t.id
INNER JOIN gpc.items i ON tl.item = i.id
LEFT JOIN (
  SELECT
    item,
    SUM(calculated_quantity_available) as current_stock
  FROM gpc.inventory_calculated
  WHERE calculated_quantity_available > 0
  GROUP BY item
) inv ON tl.item = inv.item
WHERE t.type IN ('"'"'CustInvc'"'"', '"'"'CashSale'"'"')
  AND COALESCE(t.posting, '"'"'F'"'"') = '"'"'T'"'"'
  AND COALESCE(t.voided, '"'"'F'"'"') = '"'"'F'"'"'
GROUP BY
  tl.item,
  i.itemid,
  i.displayname,
  i.custitem_gpc_season,
  i.custitem_gpc_category,
  i.custitem_gpc_sections,
  i.custitem_gpc_size,
  i.custitem_gpc_child_colour'

test_sql_query "sell_through_seasonal.yml" "$SQL_SELL_THROUGH"

# Test supplier_lead_times.yml
SQL_SUPPLIER_LEAD='SELECT
  irl.id,
  irl.transaction as receipt_id,
  irl.createdfrom as po_id,
  irl.item,
  irl.quantity,
  irl.mainline,
  CAST(ir.trandate AS TIMESTAMP) as receipt_date,
  ir.tranid as receipt_number,
  CAST(po.trandate AS TIMESTAMP) as po_date,
  po.tranid as po_number,
  po.entity as supplier_id,
  DATE_DIFF(CAST(ir.trandate AS DATE), CAST(po.trandate AS DATE), DAY) as lead_time_days
FROM gpc.item_receipt_lines irl
INNER JOIN gpc.item_receipts ir ON CAST(irl.transaction AS INT64) = CAST(ir.id AS INT64)
INNER JOIN gpc.purchase_orders po ON CAST(irl.createdfrom AS INT64) = CAST(po.id AS INT64)
WHERE irl.createdfrom IS NOT NULL
  AND irl.mainline = '"'"'F'"'"'
  AND irl.item IS NOT NULL
  AND DATE_DIFF(CAST(ir.trandate AS DATE), CAST(po.trandate AS DATE), DAY) BETWEEN 0 AND 365'

test_sql_query "supplier_lead_times.yml" "$SQL_SUPPLIER_LEAD"

# Test transaction_lines.yml
SQL_TRANSACTION_LINES='SELECT
  tl.*,
  t.type as transaction_type,
  t.currency as transaction_currency,
  t.trandate as transaction_date,
  t.status as transaction_status,
  t.subsidiary as transaction_subsidiary,
  t.custbody_customer_email as customer_email,
  t.billing_country,
  t.shipping_country,
  l.name as location_name,
  i.itemid as sku,
  i.displayname as product_name,
  i.custitem_gpc_category as category,
  i.custitem_gpc_sections as section,
  i.custitem_gpc_season as season,
  i.custitem_gpc_size as size,
  i.custitem_gpc_range as product_range,
  i.custitem_gpc_collection as collection,
  i.custitem_gpc_child_colour as color,
  i.baseprice as item_base_price,
  t.exchangerate as transaction_exchange_rate,
  curr.name as currency_name,
  d.name as department_name,
  c.name as classification_name
FROM gpc.transaction_lines_clean tl
LEFT JOIN gpc.transactions_analysis t ON tl.transaction = t.id
LEFT JOIN gpc.currencies curr ON t.currency = curr.id
LEFT JOIN gpc.locations l ON tl.location = l.id
LEFT JOIN gpc.items i ON tl.item = i.id
LEFT JOIN gpc.departments d ON tl.department = d.id
LEFT JOIN gpc.classifications c ON tl.class = c.id
WHERE tl.item != 25442'

test_sql_query "transaction_lines.yml" "$SQL_TRANSACTION_LINES"

# Generate summary report
echo "==================================================" >> "$RESULTS_FILE"
echo "VALIDATION SUMMARY" >> "$RESULTS_FILE"
echo "==================================================" >> "$RESULTS_FILE"
echo "Total Queries Tested: $TOTAL_QUERIES" >> "$RESULTS_FILE"
echo "Passed: $PASSED_QUERIES" >> "$RESULTS_FILE"
echo "Failed: $FAILED_QUERIES" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

if [ $FAILED_QUERIES -gt 0 ]; then
    echo "⚠️  ERRORS DETECTED - See details below and in $ERROR_FILE" >> "$RESULTS_FILE"
    echo "" >> "$RESULTS_FILE"
    cat "$ERROR_FILE" >> "$RESULTS_FILE"
else
    echo "✅ ALL QUERIES VALIDATED SUCCESSFULLY" >> "$RESULTS_FILE"
fi

# Display results
cat "$RESULTS_FILE"

# Return exit code based on results
if [ $FAILED_QUERIES -gt 0 ]; then
    exit 1
else
    exit 0
fi
