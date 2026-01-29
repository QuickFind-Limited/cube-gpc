-- Investigation: What transactions are categorized as "OTHER" channel?
--
-- Current channel_type logic:
-- - Department 109 → D2C
-- - Department 108 → RETAIL
-- - Department 207 → B2B_MARKETPLACE
-- - Department name LIKE '%Wholesale%' → B2B_WHOLESALE
-- - Department name LIKE '%Event%' → EVENTS
-- - ELSE → OTHER
--
-- Question: What's the €6.55m in "OTHER" channel (7.6% of total revenue)?

WITH revenue_by_channel AS (
  SELECT
    CASE
      WHEN tl.department = 109 THEN 'D2C'
      WHEN tl.department = 108 THEN 'RETAIL'
      WHEN tl.department = 207 THEN 'B2B_MARKETPLACE'
      WHEN d.name LIKE '%Wholesale%' THEN 'B2B_WHOLESALE'
      WHEN d.name LIKE '%Event%' THEN 'EVENTS'
      ELSE 'OTHER'
    END AS channel_type,
    tl.department,
    d.name as department_name,
    COUNT(*) as line_count,
    COUNT(DISTINCT tl.transaction) as transaction_count,
    ROUND(SUM(
      CASE WHEN t.type IN ('CustInvc', 'CashSale') THEN
        (tl.amount * -1 * COALESCE(t.exchangerate, 1.0))
      ELSE 0 END
    ) / 1000000, 2) as revenue_millions_eur
  FROM demo.transaction_lines_clean tl
  LEFT JOIN demo.transactions_analysis t ON tl.transaction = t.id
  LEFT JOIN demo.departments d ON tl.department = d.id
  WHERE t.trandate BETWEEN '01/07/2022' AND '31/10/2025'
    AND t.type IN ('CustInvc', 'CashSale')
  GROUP BY 1, 2, 3
)
SELECT
  channel_type,
  department,
  department_name,
  line_count,
  transaction_count,
  revenue_millions_eur,
  ROUND(100.0 * revenue_millions_eur / SUM(revenue_millions_eur) OVER(), 2) as pct_of_total
FROM revenue_by_channel
ORDER BY revenue_millions_eur DESC;

-- Deep dive into "OTHER" transactions
-- SELECT
--   tl.department,
--   d.name as department_name,
--   COUNT(*) as line_count,
--   COUNT(DISTINCT tl.transaction) as transaction_count,
--   ROUND(SUM(
--     CASE WHEN t.type IN ('CustInvc', 'CashSale') THEN
--       (tl.amount * -1 * COALESCE(t.exchangerate, 1.0))
--     ELSE 0 END
--   ) / 1000000, 2) as revenue_millions_eur
-- FROM demo.transaction_lines_clean tl
-- LEFT JOIN demo.transactions_analysis t ON tl.transaction = t.id
-- LEFT JOIN demo.departments d ON tl.department = d.id
-- WHERE t.trandate BETWEEN '01/07/2022' AND '31/10/2025'
--   AND t.type IN ('CustInvc', 'CashSale')
--   AND tl.department NOT IN (109, 108, 207)  -- Not D2C, RETAIL, or B2B_MARKETPLACE
--   AND (d.name IS NULL OR (d.name NOT LIKE '%Wholesale%' AND d.name NOT LIKE '%Event%'))
-- GROUP BY 1, 2
-- ORDER BY revenue_millions_eur DESC;
