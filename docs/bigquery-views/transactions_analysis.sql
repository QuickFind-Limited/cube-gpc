-- =============================================================================
-- View: transactions_analysis
-- Purpose: Include all transaction types for Cube analytics
-- =============================================================================
--
-- HISTORY:
-- 2025-11-27: Created to include SalesOrd/RtnAuth for pipeline metrics (OM003)
-- 2025-11-30: FIXED to include revenue transactions (CustInvc, CashSale, etc.)
--
-- ISSUE FIXED (2025-11-30):
-- Revenue transactions have posting=NULL (not 'T'), so the original view
-- excluded all CustInvc and CashSale transactions, causing RM001 to return zero.
--
-- ROOT CAUSE:
-- Original assumption: posting='T' means "posted transaction"
-- Reality: Only ItemRcpt has posting='T', revenue transactions have posting=NULL
--
-- SOLUTION:
-- Explicitly include revenue transaction types regardless of posting field.
--
-- =============================================================================

CREATE OR REPLACE VIEW `magical-desktop.gpc.transactions_analysis` AS
SELECT * FROM `magical-desktop.gpc.transactions`
WHERE COALESCE(voided, 'F') = 'F'
  AND (
    -- Revenue transactions (may have NULL posting, but are always posted)
    type IN ('CustInvc', 'CashSale', 'CustCred', 'CashRfnd')
    -- OR posted transactions of other types (ItemRcpt)
    OR COALESCE(posting, 'F') = 'T'
    -- OR pipeline/return authorization types (for OM003, RET metrics)
    OR type IN ('SalesOrd', 'RtnAuth')
  );

-- =============================================================================
-- EXPECTED TRANSACTION COUNTS (as of 2025-11-30):
-- =============================================================================
--
-- CustInvc:  547,955  (revenue - invoices)
-- SalesOrd:  466,913  (pipeline - sales orders)
-- CashSale:  385,665  (revenue - cash sales)
-- CustCred:   20,298  (revenue - credit memos)
-- ItemRcpt:   18,566  (inventory - item receipts)
-- RtnAuth:    10,504  (pipeline - return authorizations)
-- CashRfnd:    2,521  (revenue - cash refunds)
--
-- Total:   1,452,422 transactions
--
-- =============================================================================
-- USED BY:
-- =============================================================================
--
-- - transaction_lines.yml (main denormalized cube)
-- - sell_through_seasonal.yml (seasonal analysis)
-- - Any cube needing pipeline data (SalesOrd, RtnAuth)
--
-- =============================================================================
-- SEE ALSO:
-- =============================================================================
--
-- - transactions_clean.sql (revenue-only view, excludes SalesOrd/RtnAuth)
-- - transaction_lines_clean.sql (detail lines only, excludes mainline)
--
-- =============================================================================
