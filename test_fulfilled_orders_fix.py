#!/usr/bin/env python3
"""
Test the fulfilled_orders fix - verify January 2025 shows 13,359 (not 14,030)
Tests OM002 measure using ItemShip status 'C' instead of CustInvc/CashSale status 'B'
"""
import requests
import json

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njk2MzY1NTZ9.j5ivQl6s3pkUMhpH09Nfs7OAarQyeXKKO7RSs-Moq3A"

headers = {"Authorization": AUTH_TOKEN}

query = {
    "measures": ["transactions.fulfilled_orders"],
    "timeDimensions": [{
        "dimension": "transactions.trandate",
        "dateRange": ["2025-01-01", "2025-01-31"],
        "granularity": "month"
    }]
}

print("="*80)
print("FULFILLED ORDERS FIX VALIDATION (OM002)")
print("="*80)
print()
print("Testing transactions.fulfilled_orders for January 2025...")
print("Expected: 13,359 (ItemShip status 'C')")
print("Previous incorrect value: 14,030 (CustInvc/CashSale status 'B')")
print()

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query)})
data = response.json()

if "error" in data:
    print("❌ ERROR:", data["error"])
    print()
    print("Full response:")
    print(json.dumps(data, indent=2))
elif "data" in data:
    results = data["data"]

    if results:
        fulfilled = int(results[0].get("transactions.fulfilled_orders", 0))

        print(f"January 2025 Fulfilled Orders: {fulfilled:,}")
        print()

        print("VALIDATION RESULTS:")
        print("-" * 60)
        if fulfilled == 13359:
            print(f"✅ PERFECT: Exactly 13,359 fulfilled orders")
            print("   Fix is working correctly - using ItemShip status 'C'")
        elif 13300 <= fulfilled <= 13400:
            print(f"✅ SUCCESS: {fulfilled:,} fulfilled orders (within expected range)")
            print("   Fix is working - close to expected 13,359")
        elif fulfilled == 14030:
            print(f"❌ FAILED: Still showing {fulfilled:,} (old incorrect value)")
            print("   Cube may need restart or pre-agg rebuild")
        else:
            print(f"⚠️  UNEXPECTED: {fulfilled:,} fulfilled orders")
            print(f"   Expected: 13,359")
            print(f"   Difference: {fulfilled - 13359:+,}")
        print()
    else:
        print("❌ No data returned")
        print()
else:
    print("❌ Unexpected response format")
    print(json.dumps(data, indent=2))

# Also test weekly breakdown
print()
print("="*80)
print("WEEKLY BREAKDOWN TEST")
print("="*80)
print()

query_weekly = {
    "measures": ["transactions.fulfilled_orders"],
    "timeDimensions": [{
        "dimension": "transactions.trandate",
        "dateRange": ["2025-01-01", "2025-01-31"],
        "granularity": "week"
    }]
}

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query_weekly)})
data = response.json()

if "data" in data:
    results = data["data"]
    total = 0

    print(f"{'Week':<25} {'Fulfilled Orders':<20}")
    print("-" * 45)

    for row in results:
        week = row.get("transactions.trandate.week", "N/A")
        fulfilled = int(row.get("transactions.fulfilled_orders", 0))
        total += fulfilled
        print(f"{week:<25} {fulfilled:>18,}")

    print("-" * 45)
    print(f"{'TOTAL':<25} {total:>18,}")
    print()

    print("Expected weekly breakdown:")
    print("  Week 1: ~4,678 orders")
    print("  Week 2: ~4,175 orders")
    print("  Week 3: ~3,773 orders")
    print("  Week 4: ~731 orders")
    print(f"  Total:  ~13,357 orders")
else:
    print("❌ Could not retrieve weekly breakdown")
