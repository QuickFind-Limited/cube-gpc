-- ============================================================================
-- CREATE FILTERED BIGQUERY VIEWS - AUDIT Filter Application
-- ============================================================================
-- Project: magical-desktop
-- Dataset: gpc
-- Date: 2025-11-25
--
-- INSTRUCTIONS:
-- 1. Open BigQuery console: https://console.cloud.google.com/bigquery
-- 2. Select project: magical-desktop
-- 3. Copy and paste this SQL into the query editor
-- 4. Click "Run" to execute
-- 5. Verify views created successfully
-- ============================================================================

-- ============================================================================
-- VIEW 1: transaction_lines_clean
-- ============================================================================
-- Purpose: Filter out system-generated lines (tax, COGS, discounts, headers)
-- Impact: Reduces records from 8,566,293 to 4,961,732 (42% filtered)
-- ============================================================================

CREATE OR REPLACE VIEW `magical-desktop.gpc.transaction_lines_clean` AS
SELECT * FROM `magical-desktop.gpc.transaction_lines`
WHERE mainline = 'F'                          -- Exclude header/summary lines
  AND COALESCE(taxline, 'F') = 'F'           -- Exclude tax calculation lines
  AND COALESCE(iscogs, 'F') = 'F'            -- Exclude COGS accounting entries
  AND COALESCE(transactiondiscount, 'F') = 'F'; -- Exclude discount lines

-- ============================================================================
-- VIEW 2: transactions_clean
-- ============================================================================
-- Purpose: Filter to posted, non-voided revenue transactions only
-- Impact: Reduces records from 1,433,870 to 956,446 (33% filtered)
-- ============================================================================

CREATE OR REPLACE VIEW `magical-desktop.gpc.transactions_clean` AS
SELECT * FROM `magical-desktop.gpc.transactions`
WHERE COALESCE(posting, 'F') = 'T'            -- Only posted transactions (GL impact)
  AND COALESCE(voided, 'F') = 'F'             -- Exclude voided/cancelled
  AND type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd'); -- Revenue transactions only

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these queries to verify views were created successfully
-- ============================================================================

-- Check record counts
SELECT 'transaction_lines (raw)' as table_name, COUNT(*) as record_count
FROM `magical-desktop.gpc.transaction_lines`
UNION ALL
SELECT 'transaction_lines_clean' as table_name, COUNT(*) as record_count
FROM `magical-desktop.gpc.transaction_lines_clean`
UNION ALL
SELECT 'transactions (raw)' as table_name, COUNT(*) as record_count
FROM `magical-desktop.gpc.transactions`
UNION ALL
SELECT 'transactions_clean' as table_name, COUNT(*) as record_count
FROM `magical-desktop.gpc.transactions_clean`;

-- Expected results:
-- transaction_lines (raw):    8,566,293 records
-- transaction_lines_clean:    4,961,732 records (58% of raw)
-- transactions (raw):         1,433,870 records
-- transactions_clean:           956,446 records (67% of raw)

-- ============================================================================
-- TEST QUERIES
-- ============================================================================
-- Verify AUDIT fields are correctly filtered
-- ============================================================================

-- Test 1: Verify no system lines in transaction_lines_clean
SELECT
  SUM(CASE WHEN mainline = 'T' THEN 1 ELSE 0 END) as mainline_true_count,
  SUM(CASE WHEN taxline = 'T' THEN 1 ELSE 0 END) as taxline_true_count,
  SUM(CASE WHEN iscogs = 'T' THEN 1 ELSE 0 END) as iscogs_true_count,
  SUM(CASE WHEN transactiondiscount = 'T' THEN 1 ELSE 0 END) as discount_true_count
FROM `magical-desktop.gpc.transaction_lines_clean`;

-- Expected: All counts should be 0

-- Test 2: Verify no invalid transactions in transactions_clean
SELECT
  SUM(CASE WHEN COALESCE(posting, 'F') = 'F' THEN 1 ELSE 0 END) as non_posted_count,
  SUM(CASE WHEN COALESCE(voided, 'F') = 'T' THEN 1 ELSE 0 END) as voided_count,
  SUM(CASE WHEN type NOT IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd') THEN 1 ELSE 0 END) as non_revenue_count
FROM `magical-desktop.gpc.transactions_clean`;

-- Expected: All counts should be 0

-- ============================================================================
-- SAMPLE DATA QUERIES
-- ============================================================================
-- Preview clean data
-- ============================================================================

-- Sample 10 records from transaction_lines_clean
SELECT
  id,
  transaction,
  item,
  quantity,
  amount,
  mainline,
  taxline,
  iscogs,
  transactiondiscount
FROM `magical-desktop.gpc.transaction_lines_clean`
LIMIT 10;

-- Sample 10 records from transactions_clean
SELECT
  id,
  tranid,
  type,
  trandate,
  posting,
  voided,
  total
FROM `magical-desktop.gpc.transactions_clean`
LIMIT 10;

-- ============================================================================
-- DONE!
-- ============================================================================
-- Next steps:
-- 1. Verify all queries above return expected results
-- 2. Update Cube.js YML files to use _clean views
-- 3. Restart Cube.js and test queries
-- ============================================================================
