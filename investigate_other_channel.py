#!/usr/bin/env python3
"""
Investigate "OTHER" channel revenue (€6.55m / 7.6% of total).

According to user:
- All sales should be Store, Website, Wholesale, Events, or Marketplace
- "OTHER" shouldn't contain staff sales, stock transfers, samples, legacy locations, or adjustments
"""

from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project="gym-plus-coffee")

query = """
-- Revenue by channel with department details
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
"""

print("="*80)
print("CHANNEL REVENUE ANALYSIS - July 2022 to October 2025")
print("="*80)
print()

df = client.query(query).to_dataframe()

# Display all results
print(df.to_string(index=False))
print()

# Summary
total_revenue = df['revenue_millions_eur'].sum()
other_revenue = df[df['channel_type'] == 'OTHER']['revenue_millions_eur'].sum()
other_pct = (other_revenue / total_revenue * 100) if total_revenue > 0 else 0

print("="*80)
print(f"SUMMARY:")
print(f"  Total Revenue: €{total_revenue:.2f}m")
print(f"  OTHER Revenue: €{other_revenue:.2f}m ({other_pct:.1f}%)")
print("="*80)
print()

# Deep dive into OTHER
print("="*80)
print("DEEP DIVE: What departments are in OTHER?")
print("="*80)
print()

other_df = df[df['channel_type'] == 'OTHER'].copy()
if len(other_df) > 0:
    print(other_df[['department', 'department_name', 'line_count', 'transaction_count', 'revenue_millions_eur']].to_string(index=False))
    print()
    print("INSIGHT:")
    print("These transactions are categorized as OTHER because:")
    print("  - Department is NOT 109 (D2C), 108 (RETAIL), or 207 (B2B_MARKETPLACE)")
    print("  - Department name does NOT contain 'Wholesale' or 'Event'")
    print()
    print("RECOMMENDATION:")
    print("Review each department above and determine correct channel classification.")
    print("Update the channel_type CASE statement in transaction_lines.yml accordingly.")
else:
    print("No transactions found in OTHER category!")

print()
