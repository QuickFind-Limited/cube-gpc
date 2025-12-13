# b2c_customer_channels Cube Fix

**Date**: 2025-12-08
**Issue**: BigQuery error "Name channel_type not found inside l at [25:5]"

---

## Problem

The `b2c_customer_channels` cube SQL was trying to reference `l.channel_type` from the `locations` BigQuery table:

```sql
SELECT
  ...
  l.channel_type,  -- ❌ This column doesn't exist in BigQuery
  ...
FROM gpc.transaction_lines tl
LEFT JOIN gpc.locations l ON tl.location = l.id
GROUP BY t.custbody_customer_email, t.billing_country, l.channel_type
```

**Root Cause**: `channel_type` is NOT a physical column in the `gpc.locations` BigQuery table. It's a **calculated dimension** defined in the `locations` Cube.js cube using a CASE statement.

---

## Solution

Inline the `channel_type` CASE statement directly into the `b2c_customer_channels` cube SQL:

```sql
SELECT
  t.custbody_customer_email as email,
  t.billing_country,
  -- Channel type logic (inline from locations cube)
  CASE
    WHEN l.name IS NULL THEN 'D2C'
    WHEN l.name LIKE 'Bleckmann%' AND l.name NOT LIKE '%Quarantine%' AND l.name NOT LIKE '%Miscellaneous%' THEN 'D2C'
    WHEN l.name IN ('Meteor Space', '2Flow') THEN 'D2C'
    WHEN l.name IN (
      'Dundrum Town Centre', 'Mahon Point', 'Crescent Centre', 'Liffey Valley',
      'Kildare Village', 'Blanchardstown Centre', 'Galway', 'Swords Pavillon', 'Jervis Centre',
      'Westfield London', 'Manchester', 'Belfast', 'Liverpool'
    ) THEN 'RETAIL'
    WHEN l.name LIKE 'Wholesale%' THEN 'B2B_WHOLESALE'
    WHEN l.name LIKE 'Lifestyle Sports%' AND l.name NOT LIKE '%Quarantine%' THEN 'B2B_WHOLESALE'
    WHEN l.name IN ('Otrium', 'The Very Group', 'Digme', 'Academy Crests') THEN 'PARTNER'
    WHEN l.name LIKE 'Events%' THEN 'EVENTS'
    ELSE 'OTHER'
  END as channel_type,
  ...
FROM gpc.transaction_lines tl
JOIN gpc.transactions_analysis t ON tl.transaction = t.id
LEFT JOIN gpc.locations l ON tl.location = l.id
WHERE t.custbody_customer_email IS NOT NULL
  AND t.custbody_customer_email != ''
GROUP BY
  t.custbody_customer_email,
  t.billing_country,
  channel_type  -- ✅ Now using the column alias from SELECT
```

---

## Key Changes

1. **Lines 7-22**: Replaced `l.channel_type` with inline CASE statement (copied from `locations.yml`)
2. **Lines 53-56**: Updated GROUP BY to use `channel_type` column alias instead of `l.channel_type`

---

## Why This Happened

Cube.js cubes have two types of SQL:

1. **Cube SQL** (in `sql:` property) - Executes directly against BigQuery
   - Can only reference PHYSICAL columns from BigQuery tables
   - Cannot reference calculated dimensions from other cubes

2. **Dimension SQL** (in `dimensions[].sql` property) - Executes after cube SQL
   - Can reference columns from the cube's SELECT statement
   - Can use CASE statements and calculations

The `locations` cube defines `channel_type` as a dimension (not in the base SQL), so it's NOT available in the BigQuery table - only within Cube.js queries AFTER the cube SQL runs.

---

## Files Modified

- `/home/produser/cube-gpc/model/cubes/b2c_customer_channels.yml`

**Git Status**: Modified, ready to commit

---

## Testing

After this fix, the cube should build successfully. Test with:

```bash
cd /home/produser/cube-gpc
# Cube will automatically rebuild on next query
```

Query to test:

```json
{
  "measures": ["b2c_customer_channels.customer_count", "b2c_customer_channels.total_channel_ltv"],
  "dimensions": ["b2c_customer_channels.channel_type"]
}
```

Expected result: Customer counts and LTV broken down by D2C, RETAIL, B2B_WHOLESALE, PARTNER, EVENTS, OTHER

---

## Related Documentation

- **SKILL v54**: Already documented this cube in `SKILL_CUBE_REST_API-v54.md` (lines 446-479)
- **Locations Cube**: See `/home/produser/cube-gpc/model/cubes/locations.yml` for original channel_type logic
