#!/usr/bin/env python3
"""
Query BigQuery directly to find departments in OTHER channel
"""
from google.cloud import bigquery
import sys

try:
    client = bigquery.Client(project="gym-plus-coffee")
    
    query = """
    WITH channel_classification AS (
      SELECT
        tl.department,
        d.name as department_name,
        CASE
          WHEN tl.department = 109 THEN 'D2C'
          WHEN tl.department = 108 THEN 'RETAIL'
          WHEN tl.department = 207 THEN 'B2B_MARKETPLACE'
          WHEN d.name LIKE '%Wholesale%' THEN 'B2B_WHOLESALE'
          WHEN d.name LIKE '%Event%' THEN 'EVENTS'
          ELSE 'OTHER'
        END AS channel_type,
        COUNT(*) as line_count,
        ROUND(SUM(
          CASE WHEN t.type IN ('CustInvc', 'CashSale') THEN
            (tl.amount * -1 * COALESCE(t.exchangerate, 1.0))
          ELSE 0 END
        ), 2) as revenue_eur
      FROM demo.transaction_lines_clean tl
      LEFT JOIN demo.transactions_analysis t ON tl.transaction = t.id
      LEFT JOIN demo.departments d ON tl.department = d.id
      WHERE t.trandate BETWEEN '01/07/2022' AND '31/10/2025'
        AND t.type IN ('CustInvc', 'CashSale')
      GROUP BY 1, 2, 3
    )
    SELECT
      department,
      department_name,
      line_count,
      revenue_eur,
      ROUND(100.0 * revenue_eur / (SELECT SUM(revenue_eur) FROM channel_classification), 2) as pct_of_total
    FROM channel_classification
    WHERE channel_type = 'OTHER'
    ORDER BY revenue_eur DESC;
    """
    
    print("Executing query to find departments in OTHER channel...")
    print()
    
    df = client.query(query).to_dataframe()
    
    if len(df) > 0:
        print(f"{'Department ID':<15} {'Department Name':<40} {'Line Count':<12} {'Revenue (EUR)':<18} {'% of Total':<10}")
        print("=" * 105)
        
        for _, row in df.iterrows():
            dept_id = str(row['department']) if row['department'] is not None else 'NULL'
            dept_name = row['department_name'] if row['department_name'] else 'UNKNOWN'
            lines = f"{int(row['line_count']):,}"
            revenue = f"€{row['revenue_eur']:,.2f}"
            pct = f"{row['pct_of_total']:.2f}%"
            
            print(f"{dept_id:<15} {dept_name:<40} {lines:<12} {revenue:<18} {pct:<10}")
        
        print()
        print(f"Total departments in OTHER: {len(df)}")
        print(f"Total OTHER revenue: €{df['revenue_eur'].sum():,.2f}")
    else:
        print("✅ No departments found in OTHER channel!")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
