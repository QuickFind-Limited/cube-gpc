-- =============================================================================
-- Inventory 3PL CSV vs BQ SKU Delta (strict scope)
-- =============================================================================
--
-- Purpose:
-- - Reconcile SC_CurrentInventory3PLs export against canonical inventory_current.
-- - Compare "Current Quantity Available" values by SKU for the four 3PL locations.
--
-- Prerequisite:
-- 1) Load the CSV into BigQuery with this structure (STRING columns):
--    item_type, sku, description,
--    bleckmann_uk_on_hand, bleckmann_uk_current_qty_available,
--    meteor_space_on_hand, meteor_space_current_qty_available,
--    wholesale_ie_on_hand, wholesale_ie_current_qty_available,
--    wholesale_uk_on_hand, wholesale_uk_current_qty_available,
--    total_on_hand, total_current_qty_available
--
-- Example load command:
-- bq load \
--   --source_format=CSV \
--   --skip_leading_rows=8 \
--   magical-desktop:gpc_prod_native_v1.inventory_3pl_csv_snapshot \
--   /path/to/SC_CurrentInventory3PLs-651.csv \
--   item_type:STRING,sku:STRING,description:STRING,\
--   bleckmann_uk_on_hand:STRING,bleckmann_uk_current_qty_available:STRING,\
--   meteor_space_on_hand:STRING,meteor_space_current_qty_available:STRING,\
--   wholesale_ie_on_hand:STRING,wholesale_ie_current_qty_available:STRING,\
--   wholesale_uk_on_hand:STRING,wholesale_uk_current_qty_available:STRING,\
--   total_on_hand:STRING,total_current_qty_available:STRING
-- =============================================================================

WITH csv_source AS (
  SELECT
    sku,
    SAFE_CAST(REPLACE(IFNULL(bleckmann_uk_current_qty_available, '0'), ',', '') AS FLOAT64) AS csv_bleckmann_uk,
    SAFE_CAST(REPLACE(IFNULL(meteor_space_current_qty_available, '0'), ',', '') AS FLOAT64) AS csv_meteor_space,
    SAFE_CAST(REPLACE(IFNULL(wholesale_ie_current_qty_available, '0'), ',', '') AS FLOAT64) AS csv_wholesale_ie,
    SAFE_CAST(REPLACE(IFNULL(wholesale_uk_current_qty_available, '0'), ',', '') AS FLOAT64) AS csv_wholesale_uk,
    SAFE_CAST(REPLACE(IFNULL(total_current_qty_available, '0'), ',', '') AS FLOAT64) AS csv_total_4loc
  FROM `magical-desktop.gpc_prod_native_v1.inventory_3pl_csv_snapshot`
  WHERE item_type = 'Inventory Item'
    AND COALESCE(TRIM(sku), '') != ''
),
bq_source AS (
  SELECT
    ic.itemid AS sku,
    SUM(CASE WHEN l.name = 'Bleckmann UK' THEN SAFE_CAST(ic.calculated_quantity_available AS FLOAT64) ELSE 0 END) AS bq_bleckmann_uk,
    SUM(CASE WHEN l.name = 'Meteor Space' THEN SAFE_CAST(ic.calculated_quantity_available AS FLOAT64) ELSE 0 END) AS bq_meteor_space,
    SUM(CASE WHEN l.name = 'Wholesale IE' THEN SAFE_CAST(ic.calculated_quantity_available AS FLOAT64) ELSE 0 END) AS bq_wholesale_ie,
    SUM(CASE WHEN l.name = 'Wholesale UK' THEN SAFE_CAST(ic.calculated_quantity_available AS FLOAT64) ELSE 0 END) AS bq_wholesale_uk,
    SUM(SAFE_CAST(ic.calculated_quantity_available AS FLOAT64)) AS bq_total_4loc
  FROM `magical-desktop.gpc_prod_native_v1.inventory_current` ic
  JOIN `magical-desktop.gpc_prod_native_v1.locations` l
    ON ic.location = l.id
  WHERE l.name IN ('Bleckmann UK', 'Meteor Space', 'Wholesale IE', 'Wholesale UK')
  GROUP BY ic.itemid
)
SELECT
  COALESCE(c.sku, b.sku) AS sku,

  COALESCE(c.csv_bleckmann_uk, 0) AS csv_bleckmann_uk,
  COALESCE(b.bq_bleckmann_uk, 0) AS bq_bleckmann_uk,
  COALESCE(b.bq_bleckmann_uk, 0) - COALESCE(c.csv_bleckmann_uk, 0) AS delta_bleckmann_uk,

  COALESCE(c.csv_meteor_space, 0) AS csv_meteor_space,
  COALESCE(b.bq_meteor_space, 0) AS bq_meteor_space,
  COALESCE(b.bq_meteor_space, 0) - COALESCE(c.csv_meteor_space, 0) AS delta_meteor_space,

  COALESCE(c.csv_wholesale_ie, 0) AS csv_wholesale_ie,
  COALESCE(b.bq_wholesale_ie, 0) AS bq_wholesale_ie,
  COALESCE(b.bq_wholesale_ie, 0) - COALESCE(c.csv_wholesale_ie, 0) AS delta_wholesale_ie,

  COALESCE(c.csv_wholesale_uk, 0) AS csv_wholesale_uk,
  COALESCE(b.bq_wholesale_uk, 0) AS bq_wholesale_uk,
  COALESCE(b.bq_wholesale_uk, 0) - COALESCE(c.csv_wholesale_uk, 0) AS delta_wholesale_uk,

  COALESCE(c.csv_total_4loc, 0) AS csv_total_4loc,
  COALESCE(b.bq_total_4loc, 0) AS bq_total_4loc,
  COALESCE(b.bq_total_4loc, 0) - COALESCE(c.csv_total_4loc, 0) AS delta_total_4loc
FROM csv_source c
FULL OUTER JOIN bq_source b
  ON c.sku = b.sku
ORDER BY ABS(delta_total_4loc) DESC, sku;
