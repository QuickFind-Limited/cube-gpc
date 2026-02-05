-- =============================================================================
-- View: transactions_analysis (WITH ItemShip UNION)
-- Purpose: Include all transaction types INCLUDING ItemShip for OM002
-- =============================================================================
--
-- HISTORY:
-- 2025-11-27: Created to include SalesOrd/RtnAuth for pipeline metrics (OM003)
-- 2025-11-30: FIXED to include revenue transactions (CustInvc, CashSale, etc.)
-- 2026-02-05: Added UNION with transactions_itemship for OM002 fulfilled orders (v74)
--
-- ISSUE (2026-02-05):
-- ItemShip transactions are stored in a separate table (transactions_itemship)
-- with only 17 columns vs 48 in the main transactions table.
--
-- SOLUTION:
-- UNION ALL approach selecting only common columns, padding rest with NULL.
-- =============================================================================

CREATE OR REPLACE VIEW `magical-desktop.gpc.transactions_analysis` AS

-- Main transactions (all types except ItemShip)
SELECT
  id,
  type,
  tranid,
  trandate,
  status,
  entity,
  subsidiary,
  currency,
  exchangerate,
  CAST(NULL AS STRING) AS foreigntotal,  -- Not in itemship
  CAST(NULL AS STRING) AS total,  -- Not in itemship
  CAST(NULL AS STRING) AS taxtotal,  -- Not in itemship
  posting,
  postingperiod,
  voided,
  createddate,
  lastmodifieddate,
  CAST(NULL AS STRING) AS closedate,  -- Not in itemship
  CAST(NULL AS STRING) AS actualshipdate,  -- Not in itemship
  CAST(NULL AS STRING) AS shipdate,  -- Not in itemship
  shipmethod,
  shipcarrier,
  CAST(NULL AS STRING) AS memo,  -- Not in itemship
  CAST(NULL AS STRING) AS links,  -- Not in itemship
  CAST(NULL AS STRING) AS approvalstatus,  -- Not in itemship
  CAST(NULL AS STRING) AS paymentmethod,  -- Not in itemship
  recordtype,
  CAST(NULL AS STRING) AS source,  -- Not in itemship
  CAST(NULL AS STRING) AS terms,  -- Not in itemship
  CAST(NULL AS STRING) AS billing_city,  -- Not in itemship
  CAST(NULL AS STRING) AS billing_country,  -- Not in itemship
  CAST(NULL AS STRING) AS billing_state,  -- Not in itemship
  CAST(NULL AS STRING) AS billing_zip,  -- Not in itemship
  CAST(NULL AS STRING) AS billing_name,  -- Not in itemship
  CAST(NULL AS STRING) AS billing_phone,  -- Not in itemship
  CAST(NULL AS STRING) AS billing_addr1,  -- Not in itemship
  CAST(NULL AS STRING) AS shipping_city,  -- Not in itemship
  CAST(NULL AS STRING) AS shipping_country,  -- Not in itemship
  CAST(NULL AS STRING) AS shipping_state,  -- Not in itemship
  CAST(NULL AS STRING) AS shipping_zip,  -- Not in itemship
  CAST(NULL AS STRING) AS shipping_name,  -- Not in itemship
  CAST(NULL AS STRING) AS shipping_phone,  -- Not in itemship
  CAST(NULL AS STRING) AS shipping_addr1,  -- Not in itemship
  CAST(NULL AS STRING) AS custbody_shopify_order_name,  -- Not in itemship
  CAST(NULL AS STRING) AS custbody_shopify_total_amount,  -- Not in itemship
  CAST(NULL AS STRING) AS custbody_pwks_remote_order_id,  -- Not in itemship
  CAST(NULL AS STRING) AS custbody_pwks_remote_order_source,  -- Not in itemship
  CAST(NULL AS STRING) AS custbody_customer_email  -- Not in itemship
FROM `magical-desktop.gpc.transactions`
WHERE COALESCE(voided, 'F') = 'F'
  AND (
    -- Revenue transactions (may have NULL posting, but are always posted)
    type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd')
    -- OR posted transactions of other types (ItemRcpt)
    OR COALESCE(posting, 'F') = 'T'
    -- OR pipeline/return authorization types (for OM003, RET metrics)
    OR type IN ('SalesOrd', 'RtnAuth')
  )

UNION ALL

-- ItemShip transactions (fulfillments for OM002)
SELECT
  id,
  type,
  tranid,
  trandate,
  status,
  entity,
  subsidiary,
  currency,
  exchangerate,
  CAST(NULL AS STRING) AS foreigntotal,
  CAST(NULL AS STRING) AS total,
  CAST(NULL AS STRING) AS taxtotal,
  posting,
  postingperiod,
  voided,
  createddate,
  lastmodifieddate,
  CAST(NULL AS STRING) AS closedate,
  CAST(NULL AS STRING) AS actualshipdate,
  CAST(NULL AS STRING) AS shipdate,
  shipmethod,
  shipcarrier,
  CAST(NULL AS STRING) AS memo,
  CAST(NULL AS STRING) AS links,
  CAST(NULL AS STRING) AS approvalstatus,
  CAST(NULL AS STRING) AS paymentmethod,
  recordtype,
  CAST(NULL AS STRING) AS source,
  CAST(NULL AS STRING) AS terms,
  CAST(NULL AS STRING) AS billing_city,
  CAST(NULL AS STRING) AS billing_country,
  CAST(NULL AS STRING) AS billing_state,
  CAST(NULL AS STRING) AS billing_zip,
  CAST(NULL AS STRING) AS billing_name,
  CAST(NULL AS STRING) AS billing_phone,
  CAST(NULL AS STRING) AS billing_addr1,
  CAST(NULL AS STRING) AS shipping_city,
  CAST(NULL AS STRING) AS shipping_country,
  CAST(NULL AS STRING) AS shipping_state,
  CAST(NULL AS STRING) AS shipping_zip,
  CAST(NULL AS STRING) AS shipping_name,
  CAST(NULL AS STRING) AS shipping_phone,
  CAST(NULL AS STRING) AS shipping_addr1,
  CAST(NULL AS STRING) AS custbody_shopify_order_name,
  CAST(NULL AS STRING) AS custbody_shopify_total_amount,
  CAST(NULL AS STRING) AS custbody_pwks_remote_order_id,
  CAST(NULL AS STRING) AS custbody_pwks_remote_order_source,
  CAST(NULL AS STRING) AS custbody_customer_email
FROM `magical-desktop.gpc.transactions_itemship`;

-- =============================================================================
-- EXPECTED TRANSACTION COUNTS (as of 2026-02-05):
-- =============================================================================
--
-- CustInvc:  547,955  (revenue - invoices)
-- SalesOrd:  466,913  (pipeline - sales orders)
-- ItemShip:  469,092  (fulfillments - item shipments) *** NEW ***
-- CashSale:  385,665  (revenue - cash sales)
-- CustCred:   20,298  (revenue - credit memos)
-- ItemRcpt:   18,566  (inventory - item receipts)
-- RtnAuth:    10,504  (pipeline - return authorizations)
-- CashRfnd:    2,521  (revenue - cash refunds)
--
-- Total:   1,921,514 transactions (+469,092 ItemShip)
--
-- =============================================================================
