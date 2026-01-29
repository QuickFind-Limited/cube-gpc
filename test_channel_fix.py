#!/usr/bin/env python3
"""
Test the channel_type fix - verify OTHER is reduced from 7.6% to <1%
"""
import requests
import json

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njk2MzY1NTZ9.j5ivQl6s3pkUMhpH09Nfs7OAarQyeXKKO7RSs-Moq3A"

headers = {"Authorization": AUTH_TOKEN}

query = {
    "measures": ["transaction_lines.total_revenue"],
    "dimensions": ["transaction_lines.channel_type"],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2022-07-01", "2025-10-31"]
    }]
}

print("="*80)
print("CHANNEL TYPE FIX VALIDATION")
print("="*80)
print()
print("Testing channel_type dimension with CLASS field fallback (v63)...")
print()

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query)})
data = response.json()

if "data" in data:
    results = data["data"]
    results.sort(key=lambda x: float(x.get("transaction_lines.total_revenue", 0)), reverse=True)
    
    total_revenue = sum(float(r.get("transaction_lines.total_revenue", 0)) for r in results)
    
    print(f"{'Channel':<25} {'Revenue (EUR)':<20} {'% of Total':<15}")
    print("-" * 60)
    
    for row in results:
        channel = row.get("transaction_lines.channel_type", "N/A")
        revenue = float(row.get("transaction_lines.total_revenue", 0))
        pct = (revenue / total_revenue * 100) if total_revenue > 0 else 0
        print(f"{channel:<25} €{revenue:>18,.2f} {pct:>13.2f}%")
    
    print("-" * 60)
    print(f"{'TOTAL':<25} €{total_revenue:>18,.2f} {100:>13.2f}%")
    print()
    
    # Check for the fix
    other_row = next((r for r in results if r.get("transaction_lines.channel_type") == "OTHER"), None)
    if other_row:
        other_revenue = float(other_row.get("transaction_lines.total_revenue", 0))
        other_pct = (other_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        print("VALIDATION RESULTS:")
        print("-" * 60)
        if other_pct < 1.0:
            print(f"✅ SUCCESS: OTHER channel is {other_pct:.2f}% (target: <1%)")
            print(f"   Previous: 7.6% (€6.55m)")
            print(f"   Current:  {other_pct:.2f}% (€{other_revenue:,.2f})")
            print(f"   Reduction: {7.6 - other_pct:.2f} percentage points")
        else:
            print(f"⚠️  WARNING: OTHER channel is {other_pct:.2f}% (target: <1%)")
            print(f"   Expected <1%, got {other_pct:.2f}%")
            print(f"   Cube may need to refresh cache - try invalidating cache")
    else:
        print("✅ PERFECT: No revenue in OTHER channel!")
    
    # Check for new B2B_CORPORATE channel
    print()
    b2b_corp = next((r for r in results if r.get("transaction_lines.channel_type") == "B2B_CORPORATE"), None)
    if b2b_corp:
        corp_revenue = float(b2b_corp.get("transaction_lines.total_revenue", 0))
        print(f"✅ NEW CHANNEL DETECTED: B2B_CORPORATE (€{corp_revenue:,.2f})")
    else:
        print("ℹ️  B2B_CORPORATE channel not yet showing (cache may need refresh)")

else:
    print(f"❌ Error: {data}")

print()
