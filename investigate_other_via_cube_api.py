#!/usr/bin/env python3
"""
Investigate "OTHER" channel via Cube API
"""
import requests
import json

CUBE_API_URL = "https://aqua-stingray.gcp-us-central1.cubecloudapp.dev/cubejs-api/v1/load"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njk2MzY1NTZ9.j5ivQl6s3pkUMhpH09Nfs7OAarQyeXKKO7RSs-Moq3A"

headers = {
    "Authorization": AUTH_TOKEN
}

# Query 1: Revenue by channel
query1 = {
    "measures": ["transaction_lines.total_revenue"],
    "dimensions": ["transaction_lines.channel_type"],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2022-07-01", "2025-10-31"]
    }]
}

print("="*80)
print("QUERY 1: Total Revenue by Channel")
print("="*80)
print()

response = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query1)})
data = response.json()

if "data" in data:
    results = data["data"]

    # Sort by revenue descending
    results.sort(key=lambda x: float(x.get("transaction_lines.total_revenue", 0)), reverse=True)

    # Calculate total
    total_revenue = sum(float(r.get("transaction_lines.total_revenue", 0)) for r in results)

    print(f"{'Channel':<20} {'Revenue (EUR)':<20} {'% of Total':<15}")
    print("-" * 55)

    for row in results:
        channel = row.get("transaction_lines.channel_type", "N/A")
        revenue = float(row.get("transaction_lines.total_revenue", 0))
        pct = (revenue / total_revenue * 100) if total_revenue > 0 else 0
        print(f"{channel:<20} €{revenue:>18,.2f} {pct:>13.1f}%")

    print("-" * 55)
    print(f"{'TOTAL':<20} €{total_revenue:>18,.2f} {100:>13.1f}%")
    print()

    # Find OTHER revenue
    other_row = next((r for r in results if r.get("transaction_lines.channel_type") == "OTHER"), None)
    if other_row:
        other_revenue = float(other_row.get("transaction_lines.total_revenue", 0))
        other_pct = (other_revenue / total_revenue * 100) if total_revenue > 0 else 0
        print(f"⚠️  OTHER channel: €{other_revenue:,.2f} ({other_pct:.1f}% of total)")
    else:
        print("✅ No revenue in OTHER channel!")
else:
    print(f"Error: {data}")

print()

# Query 2: What departments are in OTHER?
# We need to add department_name dimension and filter to OTHER channel
query2 = {
    "measures": ["transaction_lines.total_revenue", "transaction_lines.line_count"],
    "dimensions": ["transaction_lines.department_name"],
    "filters": [{
        "member": "transaction_lines.channel_type",
        "operator": "equals",
        "values": ["OTHER"]
    }],
    "timeDimensions": [{
        "dimension": "transaction_lines.transaction_date",
        "dateRange": ["2022-07-01", "2025-10-31"]
    }]
}

print("="*80)
print("QUERY 2: What Departments are in OTHER channel?")
print("="*80)
print()

response2 = requests.get(CUBE_API_URL, headers=headers, params={"query": json.dumps(query2)})
data2 = response2.json()

if "data" in data2:
    results2 = data2["data"]

    if len(results2) > 0:
        # Sort by revenue descending
        results2.sort(key=lambda x: float(x.get("transaction_lines.total_revenue", 0)), reverse=True)

        print(f"{'Department Name':<40} {'Revenue (EUR)':<20} {'Line Count':<15}")
        print("-" * 75)

        for row in results2:
            dept = row.get("transaction_lines.department_name", "NULL/UNKNOWN")
            revenue = float(row.get("transaction_lines.total_revenue", 0))
            lines = int(row.get("transaction_lines.line_count", 0))
            print(f"{dept:<40} €{revenue:>18,.2f} {lines:>14,}")

        print()
        print("ANALYSIS:")
        print("These departments are falling into OTHER because they don't match any of:")
        print("  - Department 109 → D2C")
        print("  - Department 108 → RETAIL")
        print("  - Department 207 → B2B_MARKETPLACE")
        print("  - Department name LIKE '%Wholesale%' → B2B_WHOLESALE")
        print("  - Department name LIKE '%Event%' → EVENTS")
        print()
        print("NEXT STEPS:")
        print("1. Review each department above")
        print("2. Determine the correct channel for each")
        print("3. Update channel_type CASE logic in /home/produser/cube-gpc/model/cubes/transaction_lines.yml")
    else:
        print("✅ No departments found in OTHER channel!")
else:
    print(f"Error: {data2}")

print()
