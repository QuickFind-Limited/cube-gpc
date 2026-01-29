#!/usr/bin/env python3
"""
Test AOV breakdown for July 2022 to investigate wholesale inflation issue
"""
import requests
import json

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njk2MzY1NTZ9.j5ivQl6s3pkUMhpH09Nfs7OAarQyeXKKO7RSs-Moq3A"

headers = {"Authorization": AUTH_TOKEN}

# Query 1: AOV by channel_type for July 2022
print("="*80)
print("AOV BREAKDOWN ANALYSIS - JULY 2022")
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
        "dateRange": ["2022-07-01", "2022-07-31"]
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
        print()
        print(f"⚠️  Including B2B inflates AOV by {((overall_aov / retail_aov - 1) * 100):.1f}%")

else:
    print(f"❌ Error: {data}")

print()
print()

# Query 2: AOV by customer_type for July 2022
query2 = {
    "measures": [
        "transaction_lines.average_order_value",
        "transaction_lines.total_revenue",
        "transaction_lines.transaction_count"
    ],
    "dimensions": ["transaction_lines.customer_type"],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2022-07-01", "2022-07-31"]
    }]
}

print("Query 2: AOV by Customer Type")
print("-"*80)
response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query2)})
data = response.json()

if "data" in data:
    results = data["data"]

    print(f"\n{'Customer Type':<20} {'AOV (EUR)':<15} {'Revenue (EUR)':<20} {'Orders':<10}")
    print("-"*70)

    for row in results:
        cust_type = row.get("transaction_lines.customer_type", "N/A")
        aov = float(row.get("transaction_lines.average_order_value", 0))
        revenue = float(row.get("transaction_lines.total_revenue", 0))
        orders = int(row.get("transaction_lines.transaction_count", 0))

        print(f"{cust_type:<20} €{aov:>13,.2f} €{revenue:>18,.2f} {orders:>9,}")

    print()
else:
    print(f"❌ Error: {data}")

print()
print()

# Query 3: Cross-tabulation - channel_type x customer_type
query3 = {
    "measures": [
        "transaction_lines.average_order_value",
        "transaction_lines.total_revenue",
        "transaction_lines.transaction_count"
    ],
    "dimensions": ["transaction_lines.channel_type", "transaction_lines.customer_type"],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2022-07-01", "2022-07-31"]
    }]
}

print("Query 3: Cross-Tabulation - Channel Type x Customer Type")
print("-"*80)
response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query3)})
data = response.json()

if "data" in data:
    results = data["data"]
    results.sort(key=lambda x: float(x.get("transaction_lines.total_revenue", 0)), reverse=True)

    print(f"\n{'Channel Type':<20} {'Customer Type':<20} {'AOV (EUR)':<15} {'Revenue':<15} {'Orders':<10}")
    print("-"*85)

    for row in results:
        channel = row.get("transaction_lines.channel_type", "N/A")
        cust_type = row.get("transaction_lines.customer_type", "N/A")
        aov = float(row.get("transaction_lines.average_order_value", 0))
        revenue = float(row.get("transaction_lines.total_revenue", 0))
        orders = int(row.get("transaction_lines.transaction_count", 0))

        print(f"{channel:<20} {cust_type:<20} €{aov:>13,.2f} €{revenue:>13,.2f} {orders:>9,}")

    print()
else:
    print(f"❌ Error: {data}")

print()
print("="*80)
print("RECOMMENDATIONS")
print("="*80)
print("""
Based on the analysis above, the recommended solution is:

1. ✅ Channel classification is now fixed (v63) - wholesale properly categorized

2. 📋 User Guidance Options:

   Option A: Update measure description to recommend filtering
   - Add note in average_order_value description: "For retail-only AOV, filter
     out B2B_WHOLESALE, B2B_CORPORATE, and B2B_MARKETPLACE channels"

   Option B: Create separate retail-focused AOV measure
   - Create new measure: average_order_value_retail
   - Filters: Exclude all B2B_* channels
   - Use as default for consumer-facing analysis

   Option C: Update default AOV to exclude B2B
   - Modify average_order_value to filter out B2B by default
   - Create average_order_value_all_channels for when B2B is needed

RECOMMENDED: Option B - Create separate measure for clarity and flexibility
- Keeps original measure unchanged for historical consistency
- Provides clear, purpose-built measure for retail analysis
- Allows users to choose based on their analysis needs
""")
