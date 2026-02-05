#!/usr/bin/env python3
"""
STOCK001 Validation Test - Verify inventory_with_commitments cube works correctly

Tests the exact scenario from Dave Testing #1/#2 to validate:
1. Data exists and is correct
2. Measures return expected values
3. Dimensions work with commitment measures
4. This will help separate data issues from Source AI following documentation

Run this BEFORE testing with Source to ensure the underlying data/cube is correct.
"""
import requests
import json

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NzAyNTQyNjZ9.MH0FaftWUw1KUFhvQJRDEbVEmffIh9qzHizfKK09Pk0"

headers = {"Authorization": AUTH_TOKEN}

print("="*80)
print("STOCK001 VALIDATION TEST")
print("Testing inventory_with_commitments cube")
print("="*80)
print()

# Test 1: Basic zero stock count
print("TEST 1: Basic Zero Stock Count")
print("-" * 80)

query1 = {
    "measures": ["inventory_with_commitments.zero_stock_count"]
}

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query1)})
data = response.json()

if "error" in data:
    print("❌ ERROR:", data["error"])
    print("Response:", json.dumps(data, indent=2))
else:
    zero_stock = int(data["data"][0]["inventory_with_commitments.zero_stock_count"])
    print(f"Zero Stock Count: {zero_stock:,}")

    if 15800 <= zero_stock <= 16000:
        print(f"✅ PASS: Within expected range (~15,891)")
    else:
        print(f"⚠️  UNEXPECTED: Expected ~15,891, got {zero_stock:,}")

print()

# Test 2: Zero stock WITH commitment breakdown (Dave Testing #1 critical question)
print("TEST 2: Zero Stock WITH Commitment Breakdown")
print("-" * 80)
print("This is the question that FAILED in Dave Testing #1")
print()

query2 = {
    "measures": [
        "inventory_with_commitments.zero_stock_count",
        "inventory_with_commitments.zero_stock_with_orders",
        "inventory_with_commitments.zero_stock_without_orders"
    ]
}

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query2)})
data = response.json()

if "error" in data:
    print("❌ ERROR:", data["error"])
    print("Response:", json.dumps(data, indent=2))
else:
    result = data["data"][0]
    total = int(result["inventory_with_commitments.zero_stock_count"])
    with_orders = int(result["inventory_with_commitments.zero_stock_with_orders"])
    without_orders = int(result["inventory_with_commitments.zero_stock_without_orders"])

    print(f"Total Zero Stock:          {total:,}")
    print(f"With Orders (on order):    {with_orders:,}")
    print(f"Without Orders (NO PO):    {without_orders:,}")
    print()

    # Validation
    checks = []

    if with_orders + without_orders == total:
        print(f"✅ PASS: Breakdown sums correctly ({with_orders:,} + {without_orders:,} = {total:,})")
        checks.append(True)
    else:
        print(f"❌ FAIL: Breakdown doesn't sum ({with_orders:,} + {without_orders:,} ≠ {total:,})")
        checks.append(False)

    if 750 <= with_orders <= 800:
        print(f"✅ PASS: With orders ~762 (got {with_orders:,})")
        checks.append(True)
    else:
        print(f"⚠️  UNEXPECTED: Expected ~762 with orders, got {with_orders:,}")
        checks.append(False)

    if 15000 <= without_orders <= 15200:
        print(f"✅ PASS: Without orders ~15,129 (got {without_orders:,})")
        checks.append(True)
    else:
        print(f"⚠️  UNEXPECTED: Expected ~15,129 without orders, got {without_orders:,}")
        checks.append(False)

    if all(checks):
        print()
        print("🎉 TEST 2 PASSED: Commitment breakdown working correctly!")

print()

# Test 3: Zero stock with gender dimension (Dave Testing #2 scenario)
print("TEST 3: Zero Stock by Gender (Dave Testing #2 scenario)")
print("-" * 80)

query3 = {
    "measures": [
        "inventory_with_commitments.zero_stock_count",
        "inventory_with_commitments.zero_stock_with_orders",
        "inventory_with_commitments.zero_stock_without_orders"
    ],
    "dimensions": ["items.gender"]
}

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query3)})
data = response.json()

if "error" in data:
    print("❌ ERROR:", data["error"])
    print("Response:", json.dumps(data, indent=2))
else:
    results = data["data"]

    print(f"{'Gender':<20} {'Zero Stock':<15} {'With Orders':<15} {'Without Orders':<15}")
    print("-" * 65)

    total_zero = 0
    total_with = 0
    total_without = 0

    for row in results:
        gender = row.get("items.gender") or "NULL"
        zero = int(row["inventory_with_commitments.zero_stock_count"])
        with_ord = int(row["inventory_with_commitments.zero_stock_with_orders"])
        without_ord = int(row["inventory_with_commitments.zero_stock_without_orders"])

        print(f"{gender:<20} {zero:<15,} {with_ord:<15,} {without_ord:<15,}")

        total_zero += zero
        total_with += with_ord
        total_without += without_ord

    print("-" * 65)
    print(f"{'TOTAL':<20} {total_zero:<15,} {total_with:<15,} {total_without:<15,}")
    print()

    if len(results) > 0:
        print(f"✅ PASS: Gender dimension works with commitment measures")
        print(f"   Found {len(results)} gender categories")
    else:
        print(f"❌ FAIL: No results returned")

print()

# Test 4: Markdown vs Full Price (Dave Testing #2 follow-up)
print("TEST 4: Zero Stock (No Orders) by Markdown Status")
print("-" * 80)
print("Markdown vs Full Price analysis")
print()

query4 = {
    "measures": ["inventory_with_commitments.zero_stock_without_orders"],
    "dimensions": ["items.markdown"],
    "filters": [{
        "member": "inventory_with_commitments.zero_stock_without_orders",
        "operator": "gt",
        "values": ["0"]
    }]
}

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query4)})
data = response.json()

if "error" in data:
    print("❌ ERROR:", data["error"])
    print("Response:", json.dumps(data, indent=2))
else:
    results = data["data"]

    print(f"{'Markdown Status':<25} {'Zero Stock (No Orders)':<25}")
    print("-" * 50)

    markdown_count = 0
    fullprice_count = 0
    null_count = 0

    for row in results:
        markdown_status = row.get("items.markdown") or "NULL"
        count = int(row["inventory_with_commitments.zero_stock_without_orders"])

        print(f"{markdown_status:<25} {count:<25,}")

        if markdown_status in ["T", "true", "True", "1"]:
            markdown_count += count
        elif markdown_status in ["F", "false", "False", "0"]:
            fullprice_count += count
        else:
            null_count += count

    print("-" * 50)
    print()

    print("Summary:")
    print(f"  Markdown (T):   {markdown_count:>6,} (expected ~14,743)")
    print(f"  Full Price (F): {fullprice_count:>6,} (expected ~355)")
    print(f"  NULL/Unknown:   {null_count:>6,} (expected ~20)")
    print()

    if 14700 <= markdown_count <= 14800:
        print("✅ PASS: Markdown count within expected range")
    else:
        print(f"⚠️  UNEXPECTED: Markdown count outside expected range")

    if 350 <= fullprice_count <= 400:
        print("✅ PASS: Full price count within expected range")
    else:
        print(f"⚠️  UNEXPECTED: Full price count outside expected range")

print()
print("="*80)
print("VALIDATION COMPLETE")
print("="*80)
print()
print("Next Steps:")
print("1. If all tests passed, the cube and data are correct")
print("2. Test with Source AI using queries from /tmp/STOCK001_SOURCE_TEST.md")
print("3. Verify Source uses inventory_with_commitments cube (not inventory)")
print("4. Verify Source returns the same numbers as these tests")
print()
print("Expected Source Behavior:")
print("  - Should use inventory_with_commitments cube")
print("  - Should NOT mention cross-cube join errors")
print("  - Should return ~762 with orders, ~15,129 without orders")
print()
