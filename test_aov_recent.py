#!/usr/bin/env python3
"""
Test AOV breakdown for recent period to investigate wholesale inflation issue
"""
import requests
import json
from datetime import datetime, timedelta

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njk2MzY1NTZ9.j5ivQl6s3pkUMhpH09Nfs7OAarQyeXKKO7RSs-Moq3A"

headers = {"Authorization": AUTH_TOKEN}

# Use Q4 2024 for recent data
print("="*80)
print("AOV BREAKDOWN ANALYSIS - Q4 2024 (Oct-Dec)")
print("="*80)
print()

query1 = {
    "measures": [
        "transaction_lines.average_order_value",
        "transaction_lines.total_revenue",
        "transaction_lines.transaction_count"
    ],
    "dimensions": ["transaction_lines.channel_type"],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2024-10-01", "2024-12-31"]
    }]
}

print("Query 1: AOV by Channel Type (with updated v63 channel classification)")
print("-"*80)
response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query1)})
data = response.json()

if "data" in data:
    results = data["data"]
    results.sort(key=lambda x: float(x.get("transaction_lines.total_revenue", 0)), reverse=True)

    print(f"\n{'Channel Type':<20} {'AOV (EUR)':<15} {'Revenue (EUR)':<20} {'Orders':<10}")
    print("-"*70)

    total_revenue = 0
    total_orders = 0

    for row in results:
        channel = row.get("transaction_lines.channel_type", "N/A")
        aov = float(row.get("transaction_lines.average_order_value", 0))
        revenue = float(row.get("transaction_lines.total_revenue", 0))
        orders = int(row.get("transaction_lines.transaction_count", 0))

        total_revenue += revenue
        total_orders += orders

        print(f"{channel:<20} €{aov:>13,.2f} €{revenue:>18,.2f} {orders:>9,}")

    overall_aov = total_revenue / total_orders if total_orders > 0 else 0
    print("-"*70)
    print(f"{'OVERALL':<20} €{overall_aov:>13,.2f} €{total_revenue:>18,.2f} {total_orders:>9,}")
    print()

    # Identify problematic channels
    print("ANALYSIS:")
    print("-"*80)
    b2b_channels = [r for r in results if "B2B" in r.get("transaction_lines.channel_type", "")]
    if b2b_channels:
        b2b_revenue = sum(float(r.get("transaction_lines.total_revenue", 0)) for r in b2b_channels)
        b2b_orders = sum(int(r.get("transaction_lines.transaction_count", 0)) for r in b2b_channels)
        b2b_pct = (b2b_revenue / total_revenue * 100) if total_revenue > 0 else 0

        print(f"✅ B2B/Wholesale channels now properly classified (no longer in OTHER)")
        print(f"   Total B2B Revenue: €{b2b_revenue:,.2f} ({b2b_pct:.1f}% of total)")
        print(f"   Total B2B Orders: {b2b_orders:,}")
        print()

        # Calculate AOV without B2B
        retail_revenue = total_revenue - b2b_revenue
        retail_orders = total_orders - b2b_orders
        retail_aov = retail_revenue / retail_orders if retail_orders > 0 else 0

        print(f"📊 AOV Comparison:")
        print(f"   Overall AOV (all channels):    €{overall_aov:,.2f}")
        print(f"   Retail AOV (excl. B2B):        €{retail_aov:,.2f}")
        print(f"   Difference:                    €{overall_aov - retail_aov:,.2f}")

        if retail_orders > 0:
            inflation_pct = ((overall_aov / retail_aov - 1) * 100)
            print()
            print(f"⚠️  Including B2B inflates AOV by {inflation_pct:.1f}%")

    # Check OTHER channel
    other_row = next((r for r in results if r.get("transaction_lines.channel_type") == "OTHER"), None)
    if other_row:
        other_revenue = float(other_row.get("transaction_lines.total_revenue", 0))
        other_pct = (other_revenue / total_revenue * 100) if total_revenue > 0 else 0
        print()
        print(f"ℹ️  OTHER channel: €{other_revenue:,.2f} ({other_pct:.2f}% of total)")

else:
    print(f"❌ Error: {data}")

print()
