-- =============================================================================
-- Table: gpc_prod_native_v1.inventory_current
-- Purpose: Canonical inventory snapshot table for Cube inventory metrics.
-- =============================================================================
--
-- Upstream dependency:
-- - `gpc_prod_native_v1.inventory_current_raw_netsuite` must be refreshed from
--   NetSuite `AggregateItemLocation` before running this script.
--
-- Why this exists:
-- - Cube inventory metrics need a single canonical table with explicit freshness
--   metadata and lineage.
--
-- Output fields added:
-- - quantity_on_hand: raw NetSuite on-hand quantity from AggregateItemLocation
-- - stock_asof_date: parsed DATE from source last_transaction_date
-- - source_max_last_transaction_date: max stock_asof_date in this snapshot build
-- - snapshot_loaded_at: timestamp when this canonical table was materialized
-- - source_table: lineage marker for downstream disclosures
-- =============================================================================

CREATE OR REPLACE TABLE `magical-desktop.gpc_prod_native_v1.inventory_current` AS
WITH src AS (
  SELECT
    SAFE_CAST(item AS INT64) AS item,
    CAST(itemid AS STRING) AS itemid,
    CAST(displayname AS STRING) AS displayname,
    CAST(itemtype AS STRING) AS itemtype,
    SAFE_CAST(location AS INT64) AS location,
    COALESCE(
      SAFE_CAST(JSON_VALUE(TO_JSON_STRING(t), '$.quantity_on_hand') AS FLOAT64),
      SAFE_CAST(calculated_quantity_available AS FLOAT64)
    ) AS quantity_on_hand,
    SAFE_CAST(calculated_quantity_available AS FLOAT64) AS calculated_quantity_available,
    CAST(last_transaction_date AS STRING) AS last_transaction_date,
    SAFE_CAST(transaction_count AS INT64) AS transaction_count,
    SAFE_CAST(last_transaction_date AS DATE) AS stock_asof_date
  FROM `magical-desktop.gpc_prod_native_v1.inventory_current_raw_netsuite` t
),
snapshot_stats AS (
  SELECT MAX(stock_asof_date) AS source_max_last_transaction_date
  FROM src
)
SELECT
  src.item,
  src.itemid,
  src.displayname,
  src.itemtype,
  src.location,
  src.quantity_on_hand,
  src.calculated_quantity_available,
  src.last_transaction_date,
  src.transaction_count,
  src.stock_asof_date,
  snapshot_stats.source_max_last_transaction_date,
  CURRENT_TIMESTAMP() AS snapshot_loaded_at,
  "netsuite.AggregateItemLocation" AS source_table
FROM src
CROSS JOIN snapshot_stats;
