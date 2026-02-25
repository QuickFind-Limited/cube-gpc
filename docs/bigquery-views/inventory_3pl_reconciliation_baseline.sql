-- =============================================================================
-- Inventory 3PL Reconciliation Baseline (BQ-only)
-- =============================================================================
--
-- Purpose:
-- - Produce deterministic baseline totals from canonical inventory_current for the
--   four 3PL locations used in the SC_CurrentInventory3PLs report:
--     * Bleckmann UK
--     * Meteor Space
--     * Wholesale IE
--     * Wholesale UK
--
-- Notes:
-- - This query is intentionally BQ-only (no CSV join) so we can verify source
--   inventory scope and freshness before comparing against external exports.
-- - Keep both sum_qty_raw and sum_qty_positive_only for debugging semantics.
-- =============================================================================

WITH scoped_inventory AS (
  SELECT
    l.name AS location_name,
    ic.itemid AS sku,
    ic.itemtype AS item_type,
    SAFE_CAST(ic.calculated_quantity_available AS FLOAT64) AS qty_available
  FROM `magical-desktop.gpc_prod_native_v1.inventory_current` ic
  JOIN `magical-desktop.gpc_prod_native_v1.locations` l
    ON ic.location = l.id
  WHERE l.name IN ('Bleckmann UK', 'Meteor Space', 'Wholesale IE', 'Wholesale UK')
),
location_rollup AS (
  SELECT
    location_name,
    COUNT(*) AS position_count,
    COUNT(DISTINCT sku) AS sku_count,
    SUM(qty_available) AS sum_qty_raw,
    SUM(CASE WHEN qty_available > 0 THEN qty_available ELSE 0 END) AS sum_qty_positive_only
  FROM scoped_inventory
  GROUP BY location_name
)
SELECT
  location_name,
  position_count,
  sku_count,
  sum_qty_raw,
  sum_qty_positive_only
FROM location_rollup

UNION ALL

SELECT
  'ALL_4_LOCATIONS' AS location_name,
  SUM(position_count) AS position_count,
  NULL AS sku_count,
  SUM(sum_qty_raw) AS sum_qty_raw,
  SUM(sum_qty_positive_only) AS sum_qty_positive_only
FROM location_rollup

ORDER BY location_name;
