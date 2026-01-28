#!/usr/bin/env python3
"""
Test both AOV measures - validate average_order_value vs average_order_value_retail
"""
import requests
import json

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njk2MzY1NTZ9.j5ivQl6s3pkUMhpH09Nfs7OAarQyeXKKO7RSs-Moq3A"

headers = {"Authorization": AUTH_TOKEN}

print("="*80)
print("AOV MEASURES VALIDATION - Q4 2024")
print("="*80)
print()

# Query comparing both AOV measures
query = {
    "measures": [
        "transaction_lines.average_order_value",
        "transaction_lines.average_order_value_retail",
        "transaction_lines.total_revenue",
        "transaction_lines.transaction_count"
    ],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2024-10-01", "2024-12-31"]
    }]
}

print("Comparing AOV Measures:")
print("-"*80)
response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query)})
data = response.json()

if "data" in data and len(data["data"]) > 0:
    row = data["data"][0]

    aov_all = float(row.get("transaction_lines.average_order_value", 0))
    aov_retail = float(row.get("transaction_lines.average_order_value_retail", 0))
    revenue = float(row.get("transaction_lines.total_revenue", 0))
    orders = int(row.get("transaction_lines.transaction_count", 0))

    print(f"\n📊 Overall Metrics:")
    print(f"   Total Revenue:     €{revenue:,.2f}")
    print(f"   Total Orders:      {orders:,}")
    print()
    print(f"💰 AOV Comparison:")
    print(f"   average_order_value (all channels):   €{aov_all:,.2f}")
    print(f"   average_order_value_retail (no B2B):  €{aov_retail:,.2f}")
    print(f"   Difference:                            €{aov_all - aov_retail:,.2f}")

    if aov_retail > 0:
        inflation_pct = ((aov_all / aov_retail - 1) * 100)
        print(f"   B2B Inflation:                         {inflation_pct:,.1f}%")

    print()

    if aov_retail > 0 and aov_retail < aov_all:
        print("✅ SUCCESS: New retail AOV measure working correctly!")
        print(f"   Retail AOV (€{aov_retail:,.2f}) is lower than overall AOV (€{aov_all:,.2f})")
        print(f"   This confirms B2B wholesale orders are being excluded as expected")
    elif aov_retail == aov_all:
        print("⚠️  WARNING: Both measures show the same value")
        print("   This could mean: no B2B orders in this period, or filter not working")
    else:
        print("❌ ERROR: Unexpected values - retail AOV should not be higher than overall")

else:
    print(f"❌ Error: {data}")

print()
print()

# Query by channel to verify filtering
query2 = {
    "measures": [
        "transaction_lines.average_order_value",
        "transaction_lines.average_order_value_retail",
        "transaction_lines.total_revenue",
        "transaction_lines.transaction_count"
    ],
    "dimensions": ["transaction_lines.channel_type"],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2024-10-01", "2024-12-31"]
    }]
}

print("Breakdown by Channel Type:")
print("-"*80)
response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query2)})
data = response.json()

if "data" in data:
    results = data["data"]
    results.sort(key=lambda x: float(x.get("transaction_lines.total_revenue", 0)), reverse=True)

    print(f"\n{'Channel':<20} {'AOV (all)':<15} {'AOV (retail)':<15} {'Revenue':<20}")
    print("-"*75)

    for row in results:
        channel = row.get("transaction_lines.channel_type", "N/A")
        aov_all = float(row.get("transaction_lines.average_order_value", 0))
        aov_retail = float(row.get("transaction_lines.average_order_value_retail", 0))
        revenue = float(row.get("transaction_lines.total_revenue", 0))

        # Highlight B2B channels
        marker = "🔴" if "B2B" in channel else "  "

        print(f"{marker} {channel:<18} €{aov_all:>13,.2f} €{aov_retail:>13,.2f} €{revenue:>18,.2f}")

    print()
    print("Legend: 🔴 = B2B channels (should show €0.00 for retail AOV)")
    print()

    # Validation checks
    print("VALIDATION:")
    print("-"*80)
    b2b_channels = [r for r in results if "B2B" in r.get("transaction_lines.channel_type", "")]
    b2b_with_retail_aov = [r for r in b2b_channels if float(r.get("transaction_lines.average_order_value_retail", 0)) > 0]

    if b2b_with_retail_aov:
        print("❌ FAILED: B2B channels have non-zero retail AOV")
        for r in b2b_with_retail_aov:
            channel = r.get("transaction_lines.channel_type")
            aov = r.get("transaction_lines.average_order_value_retail")
            print(f"   {channel}: €{aov}")
    else:
        print("✅ PASSED: All B2B channels correctly excluded from retail AOV")

    retail_channels = [r for r in results if "B2B" not in r.get("transaction_lines.channel_type", "")]
    retail_with_aov = [r for r in retail_channels if float(r.get("transaction_lines.average_order_value_retail", 0)) > 0]

    if retail_with_aov:
        print("✅ PASSED: Non-B2B channels have retail AOV values")
    else:
        print("⚠️  WARNING: No non-B2B channels have retail AOV")

else:
    print(f"❌ Error: {data}")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print("""
Two AOV measures are now available:

1. average_order_value
   - Includes ALL channels (D2C, Retail, B2B Wholesale, B2B Corporate, etc.)
   - Use when analyzing total business performance
   - WARNING: B2B orders inflate this metric significantly

2. average_order_value_retail ⭐ RECOMMENDED
   - Excludes B2B_WHOLESALE, B2B_CORPORATE, B2B_MARKETPLACE
   - Use for consumer/retail analysis, marketing performance, pricing strategy
   - Represents typical consumer basket size
   - This is the measure most users want when asking "what's our AOV?"

Example queries:
- "What's our average order value?" → Use average_order_value_retail
- "What's our AOV this quarter?" → Use average_order_value_retail
- "Show me total business AOV including wholesale" → Use average_order_value
""")
