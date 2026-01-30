#!/usr/bin/env python3
"""
Test OM003 Fix: Verify average_salesord_value is consistent
"""

import requests
import json

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njk2MzY1NTZ9.j5ivQl6s3pkUMhpH09Nfs7OAarQyeXKKO7RSs-Moq3A"

headers = {
    'Authorization': f'Bearer {AUTH_TOKEN}',
    'Content-Type': 'application/json'
}

def query_cube(query_dict):
    response = requests.get(
        CUBE_API_URL,
        headers=headers,
        params={'query': json.dumps(query_dict)},
        timeout=60
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

print("=" * 90)
print("OM003 FIX VALIDATION - average_salesord_value Consistency Test")
print("=" * 90)
print()

# Test 1: Component measures (Jan 2025)
print("TEST 1: Component Measures - Jan 2025")
print("-" * 90)

query1 = {
    "measures": [
        "transaction_lines.salesord_revenue",
        "transaction_lines.salesord_count"
    ],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2025-01-01", "2025-01-31"]
    }]
}

result = query_cube(query1)
if result and 'data' in result and len(result['data']) > 0:
    data = result['data'][0]
    revenue = float(data.get('transaction_lines.salesord_revenue', 0))
    count = float(data.get('transaction_lines.salesord_count', 0))

    print(f"SalesOrd Revenue:  €{revenue:>15,.2f}")
    print(f"SalesOrd Count:    {count:>18,.0f}")
    if count > 0:
        manual_aov = revenue / count
        print(f"Manual AOV Calc:   €{manual_aov:>15,.2f}")
        print()

# Test 2: Calculated measure (Jan 2025)
print("TEST 2: Calculated Measure (average_salesord_value) - Jan 2025")
print("-" * 90)

query2 = {
    "measures": [
        "transaction_lines.average_salesord_value"
    ],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2025-01-01", "2025-01-31"]
    }]
}

result2 = query_cube(query2)
if result2 and 'data' in result2 and len(result2['data']) > 0:
    data2 = result2['data'][0]
    aov = float(data2.get('transaction_lines.average_salesord_value', 0))

    print(f"Average SalesOrd Value: €{aov:,.2f}")

    if count > 0:
        manual_aov = revenue / count
        diff = abs(aov - manual_aov)
        if diff < 0.01:
            print(f"✅ PASS: Matches manual calculation (€{manual_aov:,.2f})")
        else:
            print(f"❌ FAIL: Doesn't match manual calc (€{manual_aov:,.2f}), diff: €{diff:.2f}")
    print()

# Test 3: Consistency across dimensions (Oct 2024)
print("TEST 3: Consistency Test - Multiple Dimensions (Oct 2024)")
print("-" * 90)
print()

query3 = {
    "measures": [
        "transaction_lines.average_salesord_value",
        "transaction_lines.salesord_revenue",
        "transaction_lines.salesord_count"
    ],
    "dimensions": [
        "transaction_lines.channel_type"
    ],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2024-10-01", "2024-10-31"]
    }]
}

result3 = query_cube(query3)
if result3 and 'data' in result3:
    print(f"{'Channel':<20} | {'SalesOrd AOV':>15} | {'Revenue':>18} | {'Count':>10} | {'Manual AOV':>15} | {'Match?':>8}")
    print("─" * 120)

    all_pass = True
    for item in result3['data']:
        channel = item.get('transaction_lines.channel_type', 'NULL')
        aov = float(item.get('transaction_lines.average_salesord_value', 0))
        revenue = float(item.get('transaction_lines.salesord_revenue', 0))
        count = float(item.get('transaction_lines.salesord_count', 0))

        if count > 0:
            manual = revenue / count
            diff = abs(aov - manual)
            match = "✅" if diff < 0.01 else "❌"
            if diff >= 0.01:
                all_pass = False

            print(f"{channel:<20} | €{aov:>14,.2f} | €{revenue:>17,.2f} | {count:>10,.0f} | €{manual:>14,.2f} | {match:>7}")

    print()
    if all_pass:
        print("✅ ALL PASS: AOV calculated consistently across all channels")
    else:
        print("❌ SOME FAILURES: AOV calculation inconsistent")
    print()

# Test 4: Comparison with overall AOV (Jan 2025)
print("TEST 4: SalesOrd AOV vs Overall AOV - Jan 2025")
print("-" * 90)

query4 = {
    "measures": [
        "transaction_lines.average_order_value",
        "transaction_lines.average_salesord_value"
    ],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2025-01-01", "2025-01-31"]
    }]
}

result4 = query_cube(query4)
if result4 and 'data' in result4 and len(result4['data']) > 0:
    data4 = result4['data'][0]
    overall_aov = float(data4.get('transaction_lines.average_order_value', 0))
    salesord_aov = float(data4.get('transaction_lines.average_salesord_value', 0))

    print(f"Overall AOV (all transactions):  €{overall_aov:,.2f}")
    print(f"SalesOrd AOV (SalesOrd only):    €{salesord_aov:,.2f}")

    if overall_aov > 0:
        diff = salesord_aov - overall_aov
        pct_diff = (diff / overall_aov) * 100
        print(f"Difference:                      €{diff:,.2f} ({pct_diff:+.1f}%)")

        print()
        print("INTERPRETATION:")
        print(f"  SalesOrd transactions have {'higher' if diff > 0 else 'lower'} AOV than overall average")
        print(f"  This is expected as SalesOrd represents order intent, not post-fulfillment value")
    print()

print("=" * 90)
print("OM003 VALIDATION COMPLETE")
print("=" * 90)
