-- =============================================================================
-- Inventory 3PL Reconciliation Scope Diagnostics (BQ + CSV snapshot)
-- =============================================================================
--
-- Purpose
-- - Explain WHY canonical BQ inventory_current does not align to the 3PL CSV totals.
-- - Quantify candidate scope/definition differences before changing business logic.
--
-- Input tables
-- - BQ canonical: magical-desktop.gpc_prod_native_v1.inventory_current
-- - CSV (normalized): magical-desktop.gpc_prod_native_v1.inventory_3pl_csv_20260224
--
-- Locations in scope
-- - Bleckmann UK, Meteor Space, Wholesale IE, Wholesale UK
--
-- Output sections
-- 1) Global total delta
-- 2) SKU membership split (in CSV vs not in CSV)
-- 3) Per-location overlap split (both positive / BQ-only / CSV-only)
-- 4) Category-level delta contribution
-- 5) Positive stock concentration by stock_asof_date (staleness signal)
-- =============================================================================

WITH csv_item AS (
  SELECT
    itemid,
    CAST(bleck_avail AS FLOAT64) AS csv_bleck,
    CAST(meteor_avail AS FLOAT64) AS csv_meteor,
    CAST(wh_ie_avail AS FLOAT64) AS csv_ie,
    CAST(wh_uk_avail AS FLOAT64) AS csv_uk,
    CAST(total_avail AS FLOAT64) AS csv_total
  FROM `magical-desktop.gpc_prod_native_v1.inventory_3pl_csv_20260224`
),
bq_item_loc AS (
  SELECT
    inv.itemid,
    loc.name AS location_name,
    SAFE_CAST(inv.calculated_quantity_available AS FLOAT64) AS qty,
    inv.stock_asof_date
  FROM `magical-desktop.gpc_prod_native_v1.inventory_current` inv
  JOIN `magical-desktop.gpc_prod_native_v1.locations` loc
    ON inv.location = loc.id
  WHERE loc.name IN ('Bleckmann UK', 'Meteor Space', 'Wholesale IE', 'Wholesale UK')
),
bq_item AS (
  SELECT
    itemid,
    SUM(CASE WHEN location_name = 'Bleckmann UK' AND qty > 0 THEN qty ELSE 0 END) AS bq_bleck,
    SUM(CASE WHEN location_name = 'Meteor Space' AND qty > 0 THEN qty ELSE 0 END) AS bq_meteor,
    SUM(CASE WHEN location_name = 'Wholesale IE' AND qty > 0 THEN qty ELSE 0 END) AS bq_ie,
    SUM(CASE WHEN location_name = 'Wholesale UK' AND qty > 0 THEN qty ELSE 0 END) AS bq_uk,
    SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END) AS bq_total
  FROM bq_item_loc
  GROUP BY itemid
),
item_delta AS (
  SELECT
    COALESCE(c.itemid, b.itemid) AS itemid,
    COALESCE(c.csv_bleck, 0) AS csv_bleck,
    COALESCE(c.csv_meteor, 0) AS csv_meteor,
    COALESCE(c.csv_ie, 0) AS csv_ie,
    COALESCE(c.csv_uk, 0) AS csv_uk,
    COALESCE(c.csv_total, 0) AS csv_total,
    COALESCE(b.bq_bleck, 0) AS bq_bleck,
    COALESCE(b.bq_meteor, 0) AS bq_meteor,
    COALESCE(b.bq_ie, 0) AS bq_ie,
    COALESCE(b.bq_uk, 0) AS bq_uk,
    COALESCE(b.bq_total, 0) AS bq_total,
    COALESCE(b.bq_total, 0) - COALESCE(c.csv_total, 0) AS delta_total,
    CASE WHEN c.itemid IS NULL THEN 'not_in_csv' ELSE 'in_csv' END AS csv_membership
  FROM csv_item c
  FULL OUTER JOIN bq_item b
    ON c.itemid = b.itemid
),
item_attr AS (
  SELECT
    itemid,
    COALESCE(custitem_gpc_category, '(null)') AS category,
    COALESCE(custitem_gpc_sections, '(null)') AS section,
    COALESCE(itemtype, '(null)') AS itemtype,
    COALESCE(isinactive, '(null)') AS isinactive
  FROM `magical-desktop.gpc_prod_native_v1.items`
),
loc_overlap AS (
  SELECT
    COALESCE(c.itemid, b.itemid) AS itemid,
    COALESCE(c.location_name, b.location_name) AS location_name,
    COALESCE(c.csv_avail, 0) AS csv_avail,
    COALESCE(b.bq_avail, 0) AS bq_avail
  FROM (
    SELECT itemid, 'Bleckmann UK' AS location_name, CAST(bleck_avail AS FLOAT64) AS csv_avail
    FROM `magical-desktop.gpc_prod_native_v1.inventory_3pl_csv_20260224`
    UNION ALL
    SELECT itemid, 'Meteor Space', CAST(meteor_avail AS FLOAT64)
    FROM `magical-desktop.gpc_prod_native_v1.inventory_3pl_csv_20260224`
    UNION ALL
    SELECT itemid, 'Wholesale IE', CAST(wh_ie_avail AS FLOAT64)
    FROM `magical-desktop.gpc_prod_native_v1.inventory_3pl_csv_20260224`
    UNION ALL
    SELECT itemid, 'Wholesale UK', CAST(wh_uk_avail AS FLOAT64)
    FROM `magical-desktop.gpc_prod_native_v1.inventory_3pl_csv_20260224`
  ) c
  FULL OUTER JOIN (
    SELECT
      itemid,
      location_name,
      SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END) AS bq_avail
    FROM bq_item_loc
    GROUP BY itemid, location_name
  ) b
    ON c.itemid = b.itemid AND c.location_name = b.location_name
)

-- 1) Global total delta
SELECT
  '1_global_totals' AS section,
  CAST(NULL AS STRING) AS key_1,
  CAST(NULL AS STRING) AS key_2,
  SUM(csv_total) AS csv_value,
  SUM(bq_total) AS bq_value,
  SUM(delta_total) AS delta_value,
  COUNT(*) AS row_count
FROM item_delta

UNION ALL

-- 2) Membership split
SELECT
  '2_membership_split' AS section,
  csv_membership AS key_1,
  CAST(NULL AS STRING) AS key_2,
  SUM(csv_total) AS csv_value,
  SUM(bq_total) AS bq_value,
  SUM(delta_total) AS delta_value,
  COUNT(*) AS row_count
FROM item_delta
GROUP BY csv_membership

UNION ALL

-- 3) Per-location overlap split
SELECT
  '3_location_overlap' AS section,
  location_name AS key_1,
  CASE
    WHEN csv_avail > 0 AND bq_avail > 0 THEN 'both_positive'
    WHEN csv_avail = 0 AND bq_avail > 0 THEN 'bq_only_positive'
    WHEN csv_avail > 0 AND bq_avail = 0 THEN 'csv_only_positive'
    ELSE 'both_zero'
  END AS key_2,
  SUM(csv_avail) AS csv_value,
  SUM(bq_avail) AS bq_value,
  SUM(bq_avail - csv_avail) AS delta_value,
  COUNT(*) AS row_count
FROM loc_overlap
GROUP BY location_name, key_2

UNION ALL

-- 4) Category contribution
SELECT
  '4_category_delta' AS section,
  COALESCE(a.category, '(missing_item)') AS key_1,
  CAST(NULL AS STRING) AS key_2,
  SUM(d.csv_total) AS csv_value,
  SUM(d.bq_total) AS bq_value,
  SUM(d.delta_total) AS delta_value,
  COUNT(*) AS row_count
FROM item_delta d
LEFT JOIN item_attr a
  ON d.itemid = a.itemid
GROUP BY key_1

UNION ALL

-- 5) Positive stock by stock_asof_date
SELECT
  '5_stock_asof_date' AS section,
  CAST(stock_asof_date AS STRING) AS key_1,
  CAST(NULL AS STRING) AS key_2,
  CAST(0 AS FLOAT64) AS csv_value,
  SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END) AS bq_value,
  SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END) AS delta_value,
  COUNTIF(qty > 0) AS row_count
FROM bq_item_loc
GROUP BY stock_asof_date
HAVING SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END) > 0

ORDER BY section, ABS(delta_value) DESC, key_1, key_2;
