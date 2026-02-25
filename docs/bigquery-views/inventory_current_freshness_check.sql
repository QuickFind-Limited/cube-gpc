-- =============================================================================
-- Inventory freshness guardrail (canonical table)
-- =============================================================================
--
-- Use this check before refreshing Cube pre-aggregations.
-- Fail if:
-- - row_count = 0
-- - source_max_last_transaction_date is NULL
-- - source_max_last_transaction_date is older than freshness_sla_days
-- =============================================================================

DECLARE freshness_sla_days INT64 DEFAULT 1;

WITH snapshot_stats AS (
  SELECT
    COUNT(*) AS row_count,
    MAX(source_max_last_transaction_date) AS source_max_last_transaction_date,
    MAX(snapshot_loaded_at) AS snapshot_loaded_at
  FROM `magical-desktop.gpc_prod_native_v1.inventory_current`
)
SELECT
  row_count,
  source_max_last_transaction_date,
  snapshot_loaded_at,
  CASE
    WHEN row_count = 0 THEN "FAIL_EMPTY"
    WHEN source_max_last_transaction_date IS NULL THEN "FAIL_NO_SOURCE_DATE"
    WHEN source_max_last_transaction_date < DATE_SUB(CURRENT_DATE(), INTERVAL freshness_sla_days DAY) THEN "FAIL_STALE"
    ELSE "PASS"
  END AS freshness_status
FROM snapshot_stats;
